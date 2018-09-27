from flask import current_app
from . import MemoryStore

class ElasticSearch(MemoryStore):
    index = fields.String(required=True)
