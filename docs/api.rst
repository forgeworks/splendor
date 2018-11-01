APIs
============

Open API
--------

The `Open API`_ specification is a standard for describing a web service in such a way as to make 
discovery of it trivial.  It is used by tools like Swagger to quickly integrate with your system.

For our purposes, we use it as a base for our architecture.  Splendor API classes are made to mirror
the Open API version 3 spec.  Where the Open API spec defines an `Info`_ object, Splendor defines
an Info class.

This allows us two primary features.  Firstly, we get a well thought out and comprehensive
architecture that is well structured, yet general enough for almost any case.  Secondly, we are
able to directly translate our service into the OpenAPI spec, allowing us integration with a wide
array of services and, importantly documentation generating services that let us communicate our
API while we build it.


Splendor Api Class
-------------

Normally in Flask, we would define our endpoints via a route like::

    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.route('/pets/<id>')
    def get_pet(id):
        return jsonify( get_pet_data(id) )

    ... # Define the rest of our endpoints.

It's quick, it's simple, it's Flask, and it's fine, but it really doesn't do much for your users 
unless they know how it works.  Developers trying to use your service will need to either crack open 
the code, or get a description from you in some other way, usually, let's face it, a Slack message 
or an email.  Documentation is always the last thing.

But in Splendor, we define declaratively, building our API::

    from splendor import Api

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

Most of this is self explanatory.  We have two main sections defined, ``info`` and ``paths``.  The info
section is necessary, it describes our API in its most basic terms.  In it we can define other
properties like ``license``, ``contact``, etc.

The ``paths`` section maps urls to functions, operations, collections, or other paths.  When you
supply just a naked function, it wraps it as GET Operation.  If you wanted to instead respond to a
POST request, you would do the following::

    class PetService(Api):
        ...

        paths = {
            '/pets': {'POST': post_a_pet}
        }

And in fact, you can continue with other request methods and further paths::

    class PetService(Api):
        ...

        paths = {
            '/pets': {
                'GET': list_pets,
                'POST': post_pet
            },
            '/pets/<id>': {
                'PUT': put_pet,
                'GET': get_pet,
                'DELETE': delete_pet
            }
        }

.. note::

    The Api class is a *Schematic*, which is a class that lets us quickly define properties on an 
    object or class.  See :ref:`schema` for more information.


Flask Integration
-----------------

We integrate with Flask very simply, just register the API object as you would a blueprint, with
a ``url_prefix`` if you like::

    from flask import Flask
    from api_v1 import PetService

    app = Flask(__name__)
    app.register_blueprint(PetService(), url_prefix='/v1')

And in our operation functions, we still have all the power of Flask, our thread-local ``request``
object, ``current_app``, etc.  Further, if something cannot be readily defined in Splendor objects,
it's easy enough to drop back down generic Flask endpoints for custom functionality.


Live Docs
-------------

Because of our well-defined API, we can generate two important endpoints automatically:

    - ``/openapi.json``: Your service definition file in the Open API specification.  This link is what you use to integrate with Swagger or a similar tool.
    - ``/swagger``: A web UI to browse your service's definition.

If you wish to change these paths, you can add an attribute to your ``Api`` object, ``spec_path`` and 
``swagger_path``.  Or set them to None to disable this feature.

.. note::
    
    The above URLs are relative to the API ``url_prefix``, so if you registered your API at "/v1",
    then the Swagger endpoint would be something like: http://127.0.0.1:5000/v1/swagger


Operations
-------------

All of our endpoint functions within the Api definition are wrapped as Operation objects. Operations
define the basic inputs and outputs of a given endpoint as well as the metadata and documentation.

If given just a naked function, Splendor wraps it as an GET Operation, which is to say an 
Operation with the ``method`` property set to 'GET'.  But we can alter this by defining more
information through a decorator::

    from splendor import operation
    from splendor.schema import Any

    @operation(summary='Post An Pet', 
               method='POST',
               tags=['pets'],
               body = {
                    'description': 'Pet item to post',
                    'arg': 'pet',       # The name of the variable 
                                        # injected into the function
                    'content': {
                        'application/json': {
                            'schema': Any
                        }
                    }
               },
               responses = {
                    '200': {
                        'description': 
                            'Pet item that was added.',
                        'content': {
                            'application/json': {
                                'schema': Any
                            }
                        }
                    }
                },
                security = {
                    'pets_auth': {
                        'write:pets',
                        'read:pets'
                    }
                })
    def post_pet(pet):
        """
        Posts a Pet item to the pets datastore.
        """
        ... # Do something with the data

This is a lot to parse at first, and not all of it is required, but let's break it down:

1. First we provide a `summary`, which is like a name or a short description.
2. Next we give it our HTTP request method we expect the function to respond to.
3. Then some tags, which are simply used for searching our API.
4. Next we define our `body`, which lets your users know what sort of data should be put in the request body.  Here we say it's some arbitrary JSON, with a schema of anything.  Ideally, we would define our schema, but we'll get to that later.
5. We now define what the user can expect to get as a return object.  In this case, they will get a 200 OK response that contains a JSON document of the Pet item that was added.
6. Then we define our `security` parameter, which will tell the system what sort of OAuth tags are needed to perform the operation.
7. Finally, we define our actual function.  The parameter `pet` is used, as per our body's `arg` property.  Also, the `description` property for our operation gets set to our docstring.

Phew, that was a lot.  But now we have a fully defined operation that leaves very little ambiguity 
to the end developer.  A front-end engineer, for instance would be able to take this endpoint
and run with it, knowing exactly what to expect.

If you are reeling a bit that you'll have to do this to every endpoint in your system, read on to 
the following sections, and you will find ways to mitigate the boiler plate.  A main design goal of 
Splendor is to provide ways to maximize the expression of your API with a minimum of code.


.. _`Open API`: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md
.. _`Info`: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#info-object