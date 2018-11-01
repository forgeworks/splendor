Quick Start
============

Here we go.  

We assume you have gone through the Flask and Splendor :doc:`installation`.

A Minimal API
-------------

We create two files, both alike in dignity, one `api_v1.py`::

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

Let's review:

    1. We create our greeting function `hello_world`, which simply returns a string: `Hello World`
    2. Next we define our API, give it a title and a version, both required.
    3. We also define our single path `/hello`, which routes to our `hello_world` function.  This function is automatically wrapped as a GET Operation.

Next a Flask file, called `app.py`::
    
    from flask import Flask
    from api_v1 import GreetingV1

    app = Flask(__name__)
    app.register_blueprint(GreetingV1(), url_prefix='/v1')

Here we simply create a Flask App, like you might in the `Flask Quick Start`_, and we register
our API as one would a blueprint, giving it a URL prefix at `/v1`, since it is version one of our
API.

We run our app exactly like Flask::

    $ export FLASK_APP=app.py
    $ flask run
     * Running on http://127.0.0.1:5000/

Now open the browser to `http://127.0.0.1:5000/v1/hello <http://127.0.0.1:5000/v1/hello>`_ to see 
our operation in action.

.. note::

    Windows users might need to see `Flask Quick Start`_ on how to run the app.

.. note::
    
    Having trouble?  If you're getting a 404 error, you might not be going to the full
    url: `http://127.0.0.1:5000/v1/hello <http://127.0.0.1:5000/v1/hello>`_
        
    Otherwise, check out `Flask Quick Start`_ for troubleshooting.

Live Docs
--------------

    .. image:: img/minimal-swagger.png
        :scale: 40%

Now that our api is running, we can check out it's live documentation.  


The **OpenAPI** JSON file, which can be imported directly into something like Postman or SwaggerHub, is by default available at:
    
    `http://127.0.0.1:5000/v1/openapi.json <http://127.0.0.1:5000/v1/openapi.json>`_

**Swagger** is, by default, viewable at:
    
    `http://127.0.0.1:5000/v1/swagger <http://127.0.0.1:5000/v1/swagger>`_

Both of these paths can be changed on the `Api` object definition.


A New Version
--------------

Our user's are pretty happy with our greeting API, but "world" is just so generic, and they'd
really like to be able to customize that.  Also they want a JSON object instead of just a string.
And finally, they agree `/hello` needs to be the endpoint, and that it can't change, because... 
well because it helps me write this tutorial.  Nice folks.

This is a breaking change, our legacy users will not be able to use the new system.  So 
we are forced to create a new version, and since it's not backwards compatible, it should be a new 
major version.

So let's create a new file, `api_v2.py`::

    from splendor import Api, QueryString
    from splendor.schema import json 

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

Most of what we're doing is the same, but note we are using a few new Python 3 features,
specifically we add type hinting to our function: We say that the new `target` parameter
should be a `QueryString`, and that the function should return a JSON object.

When the Api takes the `hello_anything` function as a `PathItem`, it will wrap it in an Operation, 
which gleans information from the function to properly configure itself.  By providing some type 
hints, we tell Splendor where to get the parameters and how to build a Flask Response with the data 
returned from the function.  All of this is automatically reflected in our OpenApi spec / Swagger 
documentation so that our users have no ambiguity on our new feature.

Finally, we update `app.py` with our new version::
    
    from flask import Flask
    from api_v1 import GreetingV1
    from api_v2 import GreetingV2

    app = Flask(__name__)
    app.register_blueprint(GreetingV1(), url_prefix='/v1')
    app.register_blueprint(GreetingV2(), url_prefix='/v2')

Note that we still have all the functions and features at `/v1`, all of our past code, bugs 
and all, is still available to legacy users so they don't need to upgrade or touch anything.  We can
still support this major version with bug fixes, even new features, keeping the same codebase without
forking, and new users can focus on `/v2`.

.. _`Flask Installation`: http://flask.pocoo.org/docs/1.0/installation/
.. _`Flask Quick Start`: http://flask.pocoo.org/docs/1.0/quickstart/