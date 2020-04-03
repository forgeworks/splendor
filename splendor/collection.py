import types

from flask import abort

from pathlib import PurePosixPath

from .schema import Schematic, Configurable, fields
from .operation import MediaType, Operation, MediaOperation, QueryString
from .data import DataKey
from .util import get_schema
from . import common


class Collection(Schematic):
    """
    A collection is a Splendor specific construct that describes a group of operations that have a 
    common media type.
    """

    title = fields.String(required=True)
    media = fields.InstanceOf(MediaType, default=None)
    auditor = fields.Callable(default=None)
    storage = fields.Duck(["save", "load", "delete"])
    filters = fields.InstanceOf(fields.Field, map=True)
    url_prefix = fields.String(default=None)
    paths = fields.Dict(
        map=True,
        default={
            "/": {"get": "query_items", "post": "post_item"},
            "/<id>": {
                "get": "get_item",
                "put": "put_item",
                "patch": "patch_item",
                "delete": "delete_item",
            },
        },
    )

    def __repr__(self):
        return f"{self.__class__}({self.title})"

    @property
    def name(self):
        """Used to register as a blueprint."""
        return self.title.lower()

    ### Register Operations ###
    def register(self, app, options, first_registration=False):
        url_prefix = PurePosixPath(options.get("url_prefix", ""))
        self.url_prefix = str(url_prefix)

        for path, mapping_or_fn in self.paths.items():
            path = url_prefix / path.lstrip("/")

            if isinstance(mapping_or_fn, dict):
                for method, op in tuple(mapping_or_fn.items()):
                    op = mapping_or_fn[method] = self.create_operation(op, url_prefix=path)
                    op.register(
                        app=app,
                        options=dict(options, url_prefix=path, collection=self, methods=[method]),
                        first_registration=first_registration,
                    )
            else:
                op = self.create_operation(mapping_or_fn, url_prefix=path)
                self.paths[path] = {op.method: op}
                op.register(
                    app=app,
                    options=dict(options, url_prefix=path, collection=self, methods=[op.method]),
                    first_registration=first_registration,
                )

    def create_operation(self, op, url_prefix, is_method=False):
        if isinstance(op, str):
            is_method = True
            op = getattr(self, op)

        if isinstance(op, MediaOperation):
            op.media = op.media or self.media

        if not isinstance(op, Operation):
            op = Operation(callable=op)

        if is_method and not isinstance(op.callable, types.MethodType):
            op.callable = types.MethodType(op.callable, self)

        tags = set(op.tags)
        tags.add(self.name)
        op.tags = list(tags)

        return op

    ### Interface ###
    def save(self, key, item, partial=False):
        if not self.media:
            return self.storage.save(key, item, partial)

        data = self.media.get_instance_data(item)
        key, data = self.storage.save(key, data, partial)
        if data is not None and self.media.factory:
            return key, self.media.factory(data)
        else:
            return key, data

    def load(self, key):
        if not self.media:
            return self.storage.load(key)

        data = self.storage.load(key)
        if self.media.factory and data is not None:
            return self.media.factory(data)
        return data

    def delete(self, key):
        return self.storage.delete(key)

    def query(self, **filters):
        return (
            (k, self.media.factory(data))
            for k, data in self.storage.query(filters)
            if data is not None
        )

    def audit(self, perm, **args):
        if self.auditor:
            self.auditor(self, perm, **args)

    def enrich(self, key, item):
        return item

    def enrich_results(self, results):
        results = [self.enrich(key, item) for key, item in results]
        return results

    ### Operations ###
    @common.query
    def query_items(self, q: QueryString() = None):
        self.audit("query", query=q)
        return self.enrich_results(self.query(q=q))

    @common.post
    def post_item(self, item):
        self.audit("post", item=item)
        key, item = self.save(DataKey(self.media.name, item.id), item)
        return self.enrich(key, item)

    @common.put
    def put_item(self, id, item):
        key = DataKey(self.media.name, id)
        self.audit("put", key=key, item=item)
        key, item = self.save(key, item)
        return self.enrich(key, item)

    @common.patch
    def patch_item(self, id, item):
        key = DataKey(self.media.name, id)
        self.audit("patch", key=key, item=item)
        key, item = self.save(key, item, partial=True)
        return self.enrich(key, item)

    @common.delete
    def delete_item(self, id):
        key = DataKey(self.media.name, id)
        self.audit("delete", key=key)
        self.delete(key)

    @common.get
    def get_item(self, id):
        key = DataKey(self.media.name, id)
        self.audit("get:key", key=key)
        item = self.load(key)
        if item is None:
            abort(404, "Item does not exist")
        self.audit("get:item", key=key, item=item)
        return self.enrich(key, item)

