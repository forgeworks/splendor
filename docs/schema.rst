.. currentmodule:: splendor.schema.fields

Schema
========

Schema at a High Level
------------------------

Let's first define what we mean by *schema*:

    A *schema* is a collection of *constraints* that define the range of values a piece of data
    can have.

One way to think of a schema is as a hat box.  You can put a lot of hats in any given hat box, 
different colors, designs, materials, but the hat box gives it specific dimensions that it must 
adhere to.

In the same way, you can think of a database row schema as a hat box, or a variable in a strongly
typed language as a hat box.  In fact a "type" is another way of saying a schema, or more
specifically it is a constraint within a schema.

Each constraint can be something simple, like "must be a string", or "must not be over 12 characters."
Some can be complex, like it must adhere to a specific regular expression, or it must match the 
RFC 3987 date format.

Schema can be implicit, like when your functions just assumes the object they receive has a certain
attribute.  Or they can be explicit, like in a Django models.py, or in a JSON Schema definition file.

One of the goals for Splendor is to foster a transition from implicit schema early on when you are
problem solving to explicit schema later when you need to ensure quality and communication.

JSON Schema
------------

The Open API specification makes heavy use of `JSON Schema`_.  This means Splendor must be able to 
output all schema as JSON Schema definitions.

Gratefully, the `JSON Schema`_ specification is well done, portable, and defines most of the
features you'll ever need, and is extensible for the rest.

Splendor has an inner module ``splendor.schema`` which defines ``Schema`` and ``Constraint`` 
classes.  These can readily be transformed into JSON Schema objects.

JSON Schema can be created like so::

    from splendor.schema.json import Schema

    Coordinates = Schema({
        "required": [ "latitude", "longitude" ],
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "minimum": -90,
                "maximum": 90
            },
            "longitude": {
                "type": "number",
                "minimum": -180,
                "maximum": 180
            }
        }
    })

We can use it to validate pieces of data::

    >>> bool( Coordinates.validate({"latitude": "48.858093",
    ...                             "longitude": "2.294694"}) )
    True

    >>> bool( Coordinates.validate("bad data") )
    False

For our purposes, however, validation is only one part of it.  Most of the time, we don't care
if the data validates to a schema, rather we want it to match the schema.

The object returned is a Schema instance, and can be used as a function to coerce its input into
well structured data. Here we give the properties strings, but they are coerced into Python floats::

    >>> coords = Coordinates({"latitude": "48.858093", 
    ...                       "longitude": "2.294694"})
    >>> coords.latitude
    48.858093
    >>> coords.longitude
    2.294694

A Schema instance will do its best to coerce a value, or otherwise raise a ValidationError.

Any value coerced into the json schema system can be readily serialized into a proper JSON string::

    >>> import json
    >>> json.dumps( Coordinates({"latitude": "48.858093",
    ...                          "longitude": "2.294694"}) )
    '{"latitude": 48.858093, "longitude": 2.294694}'

A Schema is made up of various named ``Constraint`` values.  The names are registered to the 
``System`` we are working in.  JSON Schema defines a plethora of constraints such as 'required', 
'type', 'properties', etc.  Splendor currently defines two systems, ``splendor.schema.json`` and
``splendor.schema.native``.  The native system borrows most of the constraints but has room for 
other primitive types like 'set', 'decimal', 'bytes', etc.

Custom constraints can be added easily, see ``splendor.schema.json`` for examples.


Schematics
-----------

``splendor.schema.fields`` is a module that helps us build schema quickly using a familiar 
class-based approach::

    from splendor.schema import fields

    class Pet(fields.Schematic):
        name = fields.String(min_length=3, max_length=50)
        status = fields.Enum(['available', 'pending', 'sold'],
                             default='available')
    
One can then use the object as one would expect::

    >>> mittens = Pet(name="Mr. Mittens", status="pending")
    >>> mittens.status = 'sold'
    >>> print(mittens.name, "is now", mittens.status)
    Mr. Mittens is now sold

Trying to assign an incorrect value will raise an error::

    mittens.status = 'not a status'  # raises ConstraintFailure

We can also marshal it to a JSONable object::

    >>> import json
    >>> json.dumps(mittens.marshal_as('json'))
    {"name": "Mr. Mittens", "status": "sold"}

The ``Pet`` class has a ``__schema__`` object, that defines the actual schema::

    >>> Pet.__schema__

.. todo: continue this

.. _`JSON Schema`: https://json-schema.org/specification.html