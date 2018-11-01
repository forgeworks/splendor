import pytest
from pprint import pprint

from splendor import *
from splendor.schema import fields
from splendor.data import MemoryStore

from splendor.api import Collection
from splendor.operation import Operation
from splendor import common, merge_paths


def post(url):
    def decorator(fn):
        return fn
    return decorator


class House(fields.Schematic):
    id = fields.UUID(primary_key=True)
    name = fields.String(required=True)
    zip = fields.String(max_length=6)
    _url = fields.String(write_only=True)



### Collections / Schemas ###
@pytest.fixture
def houses():
    class HouseCollection(Collection):
        title = "House"
        schema = House
        storage = MemoryStore()
        query_filters = {
            'q': fields.String(description='search term')
        }
        paths = merge_paths(Collection.paths, {
            '/open/<key>': {'POST': 'open_the_house_door'}
        })

        def enrich(self, key, house):
            house = super().enrich(key, house)
            house._url = f'{self.url_prefix}/{key.id}'
            return house

        def open_the_house_door(self, key):
            return f"open {key}"

    return HouseCollection()


def test_collection_sanity(houses):
    class HouseCollection(Collection):
        schema = House

    #assert HouseCollection.schema.system is not None


def test_get(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    get_house = rules['house:get_house']
    assert get_house.rule == '/houses/<id>'
    assert get_house.methods == {'GET', 'HEAD', 'OPTIONS'}
    assert isinstance(app.view_functions[get_house.endpoint], Operation)

    house = House(name='Cottage 1')
    houses.save(['splendor.House', '1'], house)

    r = client.get('/houses/1')
    assert r.status_code == 200
    assert r.json['_url'] == '/houses/1'
    assert r.json['name'] == house.name


def test_put(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    put_house = rules['house:put_house']
    assert put_house.rule == '/houses/<id>'
    assert put_house.methods == {'PUT', 'OPTIONS'}
    assert isinstance(app.view_functions[put_house.endpoint], Operation)

    house = House(name="Cottage 2")

    r = client.put('/houses/2', json=vars(house))
    assert r.status_code == 200
    assert r.json['_url'] == '/houses/2'
    assert r.json['name'] == house.name


def test_post(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    post_house = rules['house:post_house']
    assert post_house.rule == '/houses'
    assert post_house.methods == {'POST', 'OPTIONS'}
    assert isinstance(app.view_functions[post_house.endpoint], Operation)

    house = House(name="Cottage X")
    
    r = client.post('/houses', json=vars(house))
    assert r.status_code == 200
    assert r.json['_url'].startswith('/houses/')
    assert r.json['name'] == house.name
    assert len(r.json['id']) == 32


def test_patch(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    patch_house = rules['house:patch_house']
    assert patch_house.rule == '/houses/<id>'
    assert patch_house.methods == {'PATCH', 'OPTIONS'}
    assert isinstance(app.view_functions[patch_house.endpoint], Operation)

    house = House(name='Cottage 1', zip='60650')
    houses.save(['splendor.House', '1'], house)

    r = client.patch('/houses/1', json={'zip': '90210'})
    assert r.status_code == 200
    assert r.json['_url'] == '/houses/1'
    assert r.json['name'] == house.name
    assert r.json['zip'] == '90210'


def test_delete(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    delete_house = rules['house:delete_house']
    assert delete_house.rule == '/houses/<id>'
    assert delete_house.methods == {'DELETE', 'OPTIONS'}
    assert isinstance(app.view_functions[delete_house.endpoint], Operation)

    house = House(name='Cottage 1')
    houses.save(['House', '1'], house)

    r = client.delete('/houses/1')
    assert r.status_code == 200
    assert r.json is None

    r = client.get('/houses/1')
    assert r.status_code == 404


def test_listing(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    list_house = rules['house:list_house']
    assert list_house.rule == '/houses'
    assert list_house.methods == {'GET', 'HEAD', 'OPTIONS'}
    assert isinstance(app.view_functions[list_house.endpoint], Operation)

    op = app.view_functions[list_house.endpoint]
    param = op.parameters[0]
    assert param.name == 'q'
    assert param.location == 'query'

    for i in range(10):
        house = House(name=f'Cottage {i}')
        houses.save(['House', str(i)], house)

    r = client.get('/houses')
    assert r.status_code == 200
    assert r.json[0]


def test_open_door(app, client, houses):
    app.register_blueprint(houses, url_prefix='/houses')
    rules = {x.endpoint: x for x in app.url_map.iter_rules()}

    open_the_house_door = rules['house:open_the_house_door']
    assert open_the_house_door.rule == '/houses/open/<key>'
    assert open_the_house_door.methods == {'POST', 'OPTIONS'}
    assert isinstance(app.view_functions[open_the_house_door.endpoint], Operation)

    r = client.post('/houses/open/2')
    assert r.status_code == 200
    assert r.data.decode('utf-8') == "open 2"

