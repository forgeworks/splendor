from splendor import Api

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