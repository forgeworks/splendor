from ..schema import Configurable, Schematic
from ..schema import fields
from uuid import uuid4
from collections import defaultdict
from ..util import get_schema


def get_object_data(schema, item):
    if hasattr(schema, '__schema__'):
        schema = schema.__schema__

    if not isinstance(item, dict):
        item = item.__dict__

    data = {}
    for name, field in schema.properties:
        if name in item:
            data[name] = item.get(name)

    return data


class DataKey:
    def __init__(self, *path):
        self.path = []
        for p in path:
            if isinstance(p, str):
                self.path.append(p)
            else:
                self.path.extend(list(p))

    def __repr__(self):
        parts = ", ".join([repr(p) for p in self.path])
        return f'{self.__class__.__name__}({parts})'

    def __str__(self):
        return ":".join(self.path)

    def __iter__(self):
        return iter(self.path)

    def __hash__(self):
        return hash(str(self))

    @property
    def id(self):
        return self.path[-1]

    @property
    def type(self):
        return self.path[-2]
    


class DataStore(Configurable):
    def delete(self, schema, key):
        raise NotImplementedError()

    def save(self, schema, key, item, partial=False):
        raise NotImplementedError()

    def load(self, schema, key):
        raise NotImplementedError()


class MemoryStore(DataStore):
    data = fields.Field(default_factory=lambda: defaultdict(dict))

    def delete(self, key):
        self.data.pop(str(DataKey(key)), None)

    def save(self, key, item, partial=False):
        key = DataKey(key)

        if partial and str(key) in self.data:
            existing = self.data[str(key)]
            existing.update(item)
            return key, existing
        else:
            self.data[str(key)] = item

        return key, item

    def load(self, key):
        key = DataKey(key)
        item = self.data.get(str(key), None)
        return item

    def query(self, filters):
        for key, value in self.data.items():
            yield DataKey(key), value


class No():    
    def get_key_from_entity(self, entity):
        if entity is None:
            return None
        elif hasattr(entity, 'key'):
            return entity.key
        elif isinstance(entity, dict) and '_key' in entity:
            return self.client.key(*entity['_key'])
        return self.client.key(*entity)

    def marshal_entity(self, entity):
        if entity is None:
            return None

        if isinstance(entity, datastore.Key):
            return entity.flat_path

        if isinstance(entity, list):
            entity = data.pop()

        entity['_key'] = entity.key.flat_path
        return entity

    def fetch(self, query, cursor=None, limit=None):
        args = query.get_attributes(('filters', 'projection', 'order', 'distinct_on', 'ancestor'))

        if query._type:
            args['kind'] = query._type

        ancestor = args.get('ancestor')
        if ancestor:
            args['ancestor'] = self.client.key(*ancestor)

        client_query = self.client.query(**args)

        if query._keys_only:
            client_query.keys_only()

        if limit is None:
            limit = query._limit

        query_iter = client_query.fetch(start_cursor=cursor, offset=query._offset, limit=limit)
        page = next(query_iter.pages)
        next_cursor = query_iter.next_page_token
        
        total = page.num_items

        if query._keys_only:
            page = [e.key for e in page]

        return page, total, next_cursor

    def get(self, key):
        """
        Get entity by it's key, which should be a sequence of string elements.
        """
        try:
            key = self.client.key(*key)
            entity = self.client.get(key)
        except BadRequest:
            current_app.logger.exception("Entity get failed for key: %r", key)
            return None
        return self.marshal_entity(entity)

    def put(self, data, key=None, type=None, parent=None, exclude_from_indexes=()):
        """
        Add the entity with the given data, overwriting the data with the previous data. 
        If key is not specified, data['_key'] will be used.  Alternatively, you can give
        it a `type` keyword and that will be used for the key.  Also, you can give it
        an `parent` which will take the object's '_key' or, in the case of a sequence,
        will use that as the parent key.
        """
        if key is not None:
            key = self.client.key(*key)
        elif '_key' in data:
            key = self.client.key(*data['_key'])
        elif type:
            key = self.client.key(type)
        else:
            raise RuntimeError(
                "Entity data has no _key, it must either be in the data or specified in the arguments.")

        if parent is not None:
            parent_key = self.get_key_from_entity(parent)
            if parent_key is None:
                raise RuntimeError("Cannot derive parent's key, does it have one?")
            if key.parent != parent_key:
                key = self.client.key(*key.flat_path, parent=parent_key)

        entity = datastore.Entity(key=key, exclude_from_indexes=exclude_from_indexes)
        values = dict((k, v) for k, v in data.items() if not k.startswith('_'))
        entity.update(values)
        self.client.put(entity)
        data['_key'] = entity.key.flat_path
        return self.marshal_entity(entity)

    def patch(self, data, key=None):
        """
        Updates the entitity with the given data, merges the data with the existing one
        if it's there.
        """
        if key is not None:
            key = self.client.key(*key)
        elif '_key' in data:
            key = self.client.key(*data['_key'])
        else:
            raise RuntimeError(
                "Entity data has no _key, it must either be in the data or specified in the arguments.")

        entity = self.client.get(key)
        values = dict((k, v) for k, v in data.items() if not k.startswith('_'))
        entity.update(values)
        self.client.put(entity)
        data['_key'] = entity.key.flat_path
        return self.marshal_entity(entity)

    def delete_many(self, keys):
        """
        Deletes many entities given a list of keys.
        """
        keys = [self.client.key(*k) for k in keys]
        self.client.delete_multi(keys)

    def reset(self):
        pass

