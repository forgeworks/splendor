from .schema import Configurable, Schematic
from .schema import fields
from uuid import uuid4
from collections import defaultdict


def get_object_data(schema, item):
    if issubclass(schema, Schematic):
        schema = schema.__schema__

    if not isinstance(item, dict):
        item = item.__dict__

    data = {}
    for name, field in schema.properties:
        if name in item:
            data[name] = item.get(name)

    print('get_object_data', data)
    return data


class DataStore(Configurable):
    def delete(self, schema, key):
        raise NotImplementedError()

    def save(self, schema, key, item, partial=False):
        raise NotImplementedError()

    def load(self, schema, key):
        raise NotImplementedError()


class MemoryStore(DataStore):
    data = fields.Field(default=lambda: defaultdict(dict))

    def delete(self, schema, key):
        table = self.data[schema]
        table.discard(str(key))

    def save(self, schema, key, item, partial=False):
        if key is None:
            key = self.get_item_default_key(schema, item)
        else:
            key = str(key)

        table = self.data[schema]

        if partial:
            data = table.get(key, None)
            if data is None:
                table[key] = get_object_data(schema, item)
            else:
                item = table[key] = dict(data, **get_object_data(schema, item))
        else:
            table[key] = get_object_data(schema, item)
        
        self.set_item_key(schema, item, key)
        return key, item

    def load(self, schema, key):
        key = str(key)
        table = self.data[schema]
        data = table.get(key, None)
        if data is None:
            return None
        item = schema(**data)
        self.set_item_key(schema, item, key)
        return item

    def query(self, schema, filters):
        return [schema(**t) for t in self.data[schema].values()]

    def set_item_key(self, schema, item, key):
        if hasattr(schema, '__schema__'):
            schema = schema.__schema__

        for k, prop in schema.get_constraint_value('properties', {}).items():
            if prop.value.get('primary_key', False):
                if isinstance(item, dict):
                    item[k] = key
                else:
                    setattr(item, k, key)
                return

        raise RuntimeError("Unnable to set key on item, schema has no property with 'primary_key'.")

    def get_item_default_key(self, schema, item):
        if issubclass(schema, Schematic):
            schema = schema.__schema__

        for k, prop in schema.get_constraint_value('properties', {}).items():
            if prop.value.get('primary_key', False):
                return prop.get_default(item)

        raise RuntimeError("Unnable to get default key for item, schema has no property with 'primary_key'.")


class GoogleDataStore(MemoryStore):
    kind = fields.String(required=True)

class ElasticSearch(MemoryStore):
    index = fields.String(required=True)

