import pytest
from unittest.mock import MagicMock

from splendor.operation import Operation
from splendor.common import put, get, post, patch, delete, query
from splendor.schema import fields
from .test_collections import House, houses


@pytest.mark.skip
def test_put(app, client):
    house = {'name': 'House', 'zip': '60618'}
    add_house = MagicMock()

    @app.route('/houses/<id>')
    @app.route('/houses/<section>/<id>/')
    @put(media=House, route='/houses/<id>', app=app)
    def put_item(id:int, item:House, section:str = None):
        """Adds a house."""
        add_house(id, item.__dict__)
        return item

    assert put_item.method == 'put'
    assert set(put_item.tags) == set(['house'])
    assert put_item.description == 'Adds a house.'
    assert put_item.responses['200']

    r = client.put("/houses/1", json=house)

    add_house.assert_called_once_with(1, house)

    house_json = r.get_json()
    assert house_json == house

@pytest.mark.skip
def test_patch(app, client):
    house = {'name': 'House', 'zip': '60618'}
    update_house = MagicMock()

    @app.route('/houses/<id>', methods=["patch"])
    @patch(schema=House)
    def patch_item(id:fields.Integer(), item):
        """Updates a house."""
        update_house(id, item.__dict__)
        house.update(item.__dict__)
        return house

    assert patch_item.method == 'patch'
    assert set(patch_item.tags) == set(['house', 'patch'])
    assert patch_item.description == 'Updates a house.'

    r = client.patch("/houses/1", json={'zip': '60601'})

    update_house.assert_called_once_with(1, {'zip': '60601'})

    house_json = r.get_json()
    assert house_json == house

@pytest.mark.skip
def test_get(app, client):
    house = {'name': 'House', 'zip': '60618'}
    get_house = MagicMock()

    # Get
    @app.route('/houses/<id>', methods=["get"])
    @get(schema=House)
    def get_item(id:fields.Integer()):
        """Get a house."""
        get_house(id)
        return house

    assert get_item.method == 'get'
    assert set(get_item.tags) == set(['house', 'get'])
    assert get_item.description == 'Get a house.'

    r = client.get("/houses/1")
    get_house.assert_called_once_with(1)
    house_json = r.get_json()
    assert house_json == house

@pytest.mark.skip
def test_post(app, client):
    house = {'name': 'House', 'zip': '60618'}
    add_house = MagicMock()

    # Get
    @app.route('/houses', methods=["post"])
    @post(schema=House)
    def post_item(item):
        """Post a house to the collection."""
        add_house(1, item.__dict__)
        return house

    assert post_item.method == 'post'
    assert set(post_item.tags) == set(['house', 'post'])
    assert post_item.description == 'Post a house to the collection.'

    r = client.post("/houses", json=house)
    add_house.assert_called_once_with(1, house)
    house_json = r.get_json()
    assert house_json == house

@pytest.mark.skip
def test_delete(app, client):
    delete_house = MagicMock()

    # Get
    @app.route('/houses/<id>', methods=["delete"])
    @delete(schema=House)
    def delete_item(id:fields.Integer()):
        """Delete a house."""
        delete_house(id)

    assert delete_item.method == 'delete'
    assert set(delete_item.tags) == set(['house', 'delete'])
    assert delete_item.description == 'Delete a house.'

    r = client.delete("/houses/1")
    delete_house.assert_called_once_with(1)
    house_json = r.get_json()
    assert house_json == None

@pytest.mark.skip
def test_query(app, client):
    house = {'name': 'House', 'zip': '60618'}
    filter_houses = MagicMock()

    # Get
    @app.route('/houses', methods=["get"])
    @query(schema=House)
    def query_houses(q:fields.String(), page:int=0):
        """Filter houses."""
        filter_houses(q, page)
        return [house]

    assert query_houses.method == 'get'
    assert set(query_houses.tags) == set(['house', 'query'])
    assert query_houses.description == 'Filter houses.'

    r = client.get("/houses")       # Must specify q
    assert r.status_code == 400

    r = client.get("/houses?q=*")
    assert r.status_code == 200
    filter_houses.assert_called_once_with('*', 0)
    house_json = r.get_json()
    assert house_json == [house]

    r = client.get("/houses?q=hello&page=1")
    assert r.status_code == 200
    filter_houses.assert_called_with('hello', 1)
    house_json = r.get_json()
    assert house_json == [house]

@pytest.mark.skip
def test_param_missing(app, client):
    with pytest.raises(RuntimeError):
        @app.route('/houses/<id>', methods=["get"])
        @get(schema=House)
        def should_not_work(not_key):
            pass

