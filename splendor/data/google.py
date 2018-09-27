from google.cloud import datastore
from google.api_core.exceptions import BadRequest
from flask import current_app
from . import MemoryStore

class GoogleDataStore(MemoryStore):
    kind = fields.String(required=True)
    project = fields.String(required=True)
    namespace = fields.String(default=None)

    @property
    def client(self):
        if not hasattr(self, '_client'):
            self._client = datastore.Client(project=self.project, namespace=self.namespace)
        return self._client

    def marshal(self, schema, entity):
        if entity is None:
            return None

        if isinstance(entity, datastore.Key):
            return tuple(entity.flat_path)

        if isinstance(entity, list):
            entity = data.pop()

        print("marshal", schema, entity)

        item = schema(**entity)
        self.set_item_key(schema, item, entity.key.flat_path)
        return item

    def delete(self, schema, key):
        raise NotImplementedError()

    def save(self, schema, key, item, partial=False):
        raise NotImplementedError()

    def load(self, schema, key):
        print("load", schema, key)
        try:
            key = self.client.key(*key)
            entity = self.client.get(key)
        except BadRequest:
            current_app.logger.exception("Entity get failed for key: %r", key)
            return None
        return self.marshal(schema, entity)

    #def init_app(self, app):
    #    namespace = app.config.get('GOOGLE_DATASTORE_NAMESPACE', None)
