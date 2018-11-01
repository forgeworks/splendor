.. module:: splendor.api

Collections
============

The real power of Splendor is in the ``Collection`` class.  A collection is not a construct found
in the Open API spec.  But it allows us to quickly build API ``PathItem`` and ``Operation`` 
instances that can be.

The concept of a collection is simple.  Over and over again, we end up defining a set of common
operations around a single schema, for instance::

    from splendor import Api
    
    from .pets import (list_pet, add_new_pet, get_pet, 
                       replace_pet, update_pet, delete_pet)

    class PetServiceV0(Api):
        info = {'name': 'Pet Service v0', 'version': '0.0.1'}
        paths = {
            '/pets': {
                'get': list_pets,
                'post': add_new_pet
            },
            '/pets/<id>': {
                'get': get_pet,
                'put': replace_pet,
                'patch': update_pet,
                'delete': delete_pet
            }
        }

These endpoints represent the primary interface to a collection of pets.  We are able to list,
add, get, replace, update, and delete them in a RESTful way.

Here instead we use a Splendor collection::

    from splendor import Api
    from .pets import PetCollection

    class PetServiceV0(Api):
        info = {'name': 'Pet Service v0', 'version': '0.0.1'}
        paths = {
            '/pets': PetCollection
        }
    
As you can see, a collection can be used anywhere you would add a mapping of paths, and along with 
it comes all your basic endpoints.  With some customization, you can add other endpoints easily.  
The Collection becomes a simple building block to compose your API quickly::

    from splendor import Collection
    from splendor.schema import fields
    from splendor.data.google import GoogleStorage

    class Pet(fields.Schematic):
        name = fields.String(min_length=3, max_length=50)
        status = fields.Enum(['available', 'pending', 'sold'],
                             default='available')

    class PetCollection(Collection):
        schema = Pet
        storage = GoogleStorage(kind='pets', 
                                project='pet-store-example')
        extra_paths = {
            '/<id>/uploadImage': {'post': 'upload_image'}
        }

        def upload_image(self, id):
            #TODO: Upload the file
            pass
    
That's it.  We can now post, put, get, delete pets all day long.  And more importantly, we have live
docs that inform our users exactly how to do it.


Data Storage
-------------------

Each Collection object has ``storage`` property that can be any object that implements "save",
"load", "delete", and "query" functions.  You can use an already built Storage class or build your
own.  All you have to do is implement these simple functions.


Security + Auditing
-------------

Security is handled via an Auditor, which is any function or callable object.  It should be of the 
following signature::

    def audit(collection, action, **kwargs):
        ...

The auditor can feel free to raise a Flask HTTP error, for instance with ``abort(404)``, or 
do nothing at all.  Also, an auditor doesn't need to necessarily be security focused, it might want
to simply log all activities.


Enrichment
--------------

Before an item or query result is returned by a Collection, it is "enriched".  That is to say, the 
Collection has a chance to process it.  Usually this is to add more data.  For instance, we might
want add a list of *Pet* items when we query for a *Store* item::
    
    from splendor import Collection
    from splendor.schema import fields
    
    from .data import our_data_store

    class Pet(fields.Schematic):
        name = fields.String()
        store_id = fields.UUID()

    class Store(fields.Schematic):
        id = fields.UUID()
        name = fields.String()
        pets = fields.InstanceOf(Pet, list=True, read_only=True)

    class StoreCollection(Collection):
        schema = Store
        storage = our_data_store

        def enrich(self, store):
            store.pets = \
                self.storage.query('Pet').filter(store_id=store.id)

Now when we GET from our Store Collection, our item will have a *pets* property with a list of 
all the pets in the store.

Note, on the *Store* schematic, the *pets* property is set to ``read_only=True``, which means we
won't write this to the datastore, and it tells the end user that they shouldn't try to write to it.

.. warning::

    Enrichment is powerful, but depending on your data storage can quickly become a time sink.  
    If your load times are growing, it's a perfect time to apply caching.

