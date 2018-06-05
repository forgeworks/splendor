import pytest
from pprint import pprint

from splendor import *
from splendor.schema import fields
from splendor.data import GoogleDataStore, ElasticSearch

from splendor.api import Collection
from splendor.operation import Operation
from splendor import common


def post(url):
    def decorator(fn):
        return fn
    return decorator


class House(fields.Schematic):
    id = fields.String(primary_key=True)
    name = fields.String
    zip = fields.String(max_length=6)


### Collections / Schemas ###
@pytest.fixture
def houses():
    class HouseCollection(Collection):
        title = "House"
        schema = House
        storage = GoogleDataStore(kind='house')
        query_filters = {
            'q': fields.String(description='search term')
        }

        def enrich(self, key, house):
            house = super().enrich(key, house)
            return house

        @common.post
        def open_the_house_door(self, key):
            asdfasdfsdf

    return HouseCollection()


def test_put(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    put_item = rules['house:put_house']
    assert put_item.rule == '/houses/<key>'
    assert put_item.methods == {'PUT', 'OPTIONS'}
    assert isinstance(app.view_functions[put_item.endpoint], Operation)

    house = House(name="Cottage")

    r = client.put('/houses/1', json=vars(house))
    assert r.status_code == 200
    print(r.json)
    assert r.json['_url'] == '/houses/1'

# make put, get, etc work on collections
#make path logic
