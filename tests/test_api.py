import pytest
from splendor import *
from splendor.schema import fields
from splendor.data import MemoryStore
from splendor.api import Collection, Api
from splendor.operation import Operation
from splendor import common, merge_paths


class House(fields.Schematic):
    id = fields.UUID(primary_key=True)
    name = fields.String
    zip = fields.String(max_length=6)


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
        return house

    def open_the_house_door(self, key):
        return f"open {key}"


def say_hello(who):
    """Generic view, hello world sort of thing."""
    return f'Hello {who}'


@pytest.fixture
def api():
    houses = HouseCollection()
    class TestApi(Api):
        info = {
            'title': 'Test API v1.0.0',
            'version': '1.0.0',
            'description': """
                # Test API (v1.0.0)

                This is the test api for *Splendor*.  It is a good example of a finished API.
            """,
            'contact': {
                'name': 'DeadWisdom',
                'url': 'https://github.com/DeadWisdom',
                'email': 'deadwisdom@gmail.com'
            },
            'license': {
                'name': 'MIT',
                'url': 'https://opensource.org/licenses/MIT'
            }
        }
        paths = {
            '/houses': houses,
            #'/hello/<who>': say_hello,
        }

    return TestApi()


#def test_api_info(api):
#    #print(api._url_prefix)
#    #assert api.pack() == None
#    pass
#
#
#def test_api_basics(app, client, api):
#    app.register_blueprint(api)
#
#    # Test collection
#    house = House(name="Cottage 1")
#
#    r = client.put('/houses/1', json=vars(house))
#    assert r.status_code == 200
#
#    r = client.get('/houses/1')
#    assert r.status_code == 200
#    assert r.json['_url'] == '/houses/1'
#    assert r.json['name'] == house.name
#
#    client.delete('/houses/1')
#
#    assert client.get('/houses/1').status_code == 404
#
#
#def test_extra_view(app, client, api):
#    app.register_blueprint(api)
#
#    r = client.put('/hello/world')
#    assert r.status_code == 200
#    assert r.data.decode('utf-8') == 'Hello world'
