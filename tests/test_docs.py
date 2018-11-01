from splendor import Api, QueryString
from splendor.schema import json
from flask import Flask

def test_quick_start_api_v1(app, client):
    def hello():
        return "Hello World!"

    class GreetingV1(Api):
        info = {
            'title': 'Greeting API',
            'version': '1.0.0'
        }
        paths = {
            '/hello': hello
        }
    
    api = GreetingV1()

    assert api.info.title == 'Greeting API'
    assert api.info.version == '1.0.0'
    assert api.paths['/hello'].get.callable is hello

    app.register_blueprint(api, url_prefix='/v1')

    r = client.get('/v1/hello')
    assert r.data.decode('utf-8') == hello()

    r = client.get('/v1/openapi.json')
    assert r.json['info'] == GreetingV1.info
    assert r.json['openapi'] == '3.0.1'
    assert r.json['paths']['/hello']['get']['summary'] == 'Hello'


def test_quick_start_api_v2(app, client):
    def hello(target:QueryString()) -> json.Object:
        return {'target': target,
                'greeting': f'Hello {target}!'}

    class GreetingV2(Api):
        info = {
            'title': 'Greeting API',
            'version': '2.0.0'
        }
        paths = {
            '/hello': hello
        }
        
    api = GreetingV2()
    app.register_blueprint(api, url_prefix='/v2')

    assert api.info.title == 'Greeting API'
    assert api.info.version == '2.0.0'
    assert api.paths['/hello'].get.callable is hello
    assert api.paths['/hello'].get.parameters

    r = client.get('/v2/hello?target=Python')
    assert r.json == hello('Python')


def test_api(app, client):
    def get_pet(id):
        return jsonify( get_pet_data(id) )

    class PetService(Api):
        info = {
            'title': 'Pet Service',
            'version': '1.0.0',
            'description': 'This is an *example* API.'
        }
        paths = {
            '/pets/<id>': get_pet
        }

    class PetService(Api):
        info = {
            'title': 'Pet Service',
            'version': '1.0.0',
            'description': 'This is an *example* API.'
        }
        paths = {
            '/pets': {
                'GET': lambda: 'get',
                'POST': lambda: 'post'
            },
            '/pets/<id>': {
                'PUT': lambda id: id,
                'GET': lambda id: id,
                'DELETE': lambda id: id
            }
        }
    

