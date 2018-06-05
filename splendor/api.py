from pathlib import PurePosixPath
import inspect
from .schema import Schematic, Configurable, fields
from .operation import Operation
from . import common
from flask import Blueprint


def setup_operations(cls):
    for name, attr in vars(cls).items():
        if isinstance(attr, LazyOperation):
            LazyOperation


def operation(**kwargs):
    def decorator(fn):
        return LazyOperation(callable=fn, kwargs=kwargs)
    return decorator

class Contact(Schematic):
    name = fields.String(required=True)
    url = fields.String()
    email = fields.String()

class License(Schematic):
    name = fields.String(required=True)
    url = fields.String()

class Server(Schematic):
    url = fields.String(required=True)
    description = fields.String(required=True)

class Api(Schematic):
    name = fields.String(required=True)
    version = fields.String(required=True)
    description = fields.String()
    contact = fields.InstanceOf(Contact)
    license = fields.InstanceOf(License)
    servers = fields.InstanceOf(Server, repeated=True)
    schemas = fields.Field(repeated=True)

    def register(self, app, options, first_registration=False):
        for path, resource in this.path.items():
            if isinstance(resource, type):
                resource = resource()
            resource.register(app, path, self)

        super().register(app, options, first_registration)


class CollectionBase(Configurable):
    pass


class Collection(CollectionBase):
    title = fields.String(required=True)
    schema = fields.Schema()
    parent = fields.InstanceOf(CollectionBase, default=None)
    auditor = fields.Callable(default=None)
    storage = fields.Duck(["write", "load"], map=True)
    filters = fields.InstanceOf(fields.Field, map=True)
    enrich = fields.Duck(["enrich"], map=True)
    paths = fields.Dict(map=True, default={
        '/':        {'get': 'list_items',
                     'post': 'post_item'},
        '/<key>':   {'get': 'get_item',
                     'put': 'put_item',
                     'patch': 'patch_item',
                     'delete': 'delete_item'}
    })
    _root = fields.String(read_only=True)

    ### Meta ###
    def __repr__(self):
        return f'{self.__class__}({self.title})'

    def register_operation(self, api, path, view_func, **kwargs):
        if 'method' in kwargs:
            methods = [kwargs['method']]
        else:
            methods = None
        if isinstance(view_func, str):
            view_func = getattr(self, view_func)
        if isinstance(view_func, common.CollectionOperation):
            view_func = view_func.build(self)
        if isinstance(view_func, Operation):
            operation = view_func
            operation.operation_id = f'{self.name}:{view_func.__name__}'
            view_func.register(api, path, methods, **kwargs)
        else:
            api.add_url_rule(str(path), endpoint=f'{self.name}:{view_func.__name__}', view_func=view_func, methods=methods)

    def register(self, api, options, first_registration):
        """
        Register this collection like a flask blueprint.
        """
        root = PurePosixPath(options.get('url_prefix', ''))
        self._root = str(root)
        for path, mapping in self.paths.items():
            path = root / path.lstrip('/')
            if isinstance(mapping, dict):
                for method, view_func in mapping.items():
                    self.register_operation(api, path, view_func, method=method)
            else:
                view_func = mapping
                self.register_operation(api, path, view_func)

    @property
    def name(self):
        return self.title.lower()

    ### Interface ###
    def save(self, key, item, partial=False):
        return self.storage.save(self.schema, key, item, partial)

    def load(self, key):
        return self.storage.load(self.schema, key)

    def delete(self, key):
        return self.storage.delete(self.schema, key)

    def query(self, **filters):
        return self.storage.query(self.schema, filters)

    def audit(self, perm, **args):
        if self.auditor:
            self.auditor(self, perm, **args)

    def enrich(self, key, item):
        item._url = f'{self._root}/{key}'
        return item

    def enrich_results(self, results):
        results = [self.enrich(0, item) for item in results]
        return results


    ### Operations ###
    @common.listing
    def list_items(self, q:fields.String()):
        self.audit('list', q)
        return self.enrich_results(self.query(q))
    
    @common.post
    def post_item(self, item):
        self.audit('post', item=item)
        key, item = self.save(None, item)
        return self.enrich(key, item)
    
    @common.get
    def get_item(self, key):
        self.audit('get:key', key=key)
        item = self.load(key)
        self.audit('get:item', key=key, item=item)
        return self.enrich(key, item)
    
    @common.put
    def put_item(self, key, item):
        self.audit('put', key=key, item=item)
        key, item = self.save(key, item)
        return self.enrich(key, item)
    
    @common.patch
    def patch_item(self, key, item):
        self.audit('patch', key=key, item=item)
        key, item = self.save(key, item, partial=True)
        return self.enrich(key, self.schema(**item))
    
    @common.delete
    def delete_item(self, key):
        self.audit('delete', key=key)
        self.delete(key)


class Storage(Configurable):
    collection = fields.InstanceOf(Collection)

    def save(self, schema, key, item, partial=False):
        pass

    def load(self, schema, key):
        pass

    def delete(self, schema, key):
        pass

    def query(self, schema, filters):
        pass

