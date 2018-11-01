

class Loft(Api):
    """

    """
    title = 'Loft API'
    version = '1.0.1'
    description = "Loft api / service for the Loft family of websites."
    contact = Contact(
        name = "Api Support",
        url = "http://help.loft.io",
        email = "help@loft.io")
    license = License(
        name = "Apache 2.0",
        url = "https://www.apache.org/licenses/LICENSE-2.0.html")

    servers = [
        Server(url="api.loft.io", description="Primary Server")
    ]

    paths = {
        '/pets': {'get': 'get_pets',
                  'post': 'add_pet'},
        '/pets/{id}': {'put': 'put_pet',
                       'get': 'get_pet',
                       'delete': 'delete_pet'},
        '/accounts': accounts.Collection
    }

    schemas = [

    ]

    security = {
        'default': 
    }

    @operation(
        method="get",
        tags=['tag1', 'tag2'],
        summary="Short summary",
        external_docs={'description': 'Find out more info here', 'url': 'http://help.loft.io/loft-api/pets'},
        args = {
            'kind': fields.String(in="query", description="kind of pet to filter", deprecated=True),
        },
        result = http.Ok(schema=Pet, repeated=True, description="all pets matching the filter"),
        error = 
        responses=[
            Ok(schema=Pet, repeated=True, description="name of the pet"),
        ],
        responses={
            'success': Success(schema=Pet, repeated=True, description="name of the pet")
        }
        )
    def get_pets(kind, pet):
        """
        Gets all the pets you want to see.

        -- Contract --
        kind: 
            in: query
            schema: string
            deprecated: true
            description: "kind of pets"

        -- Operation --
        *tags: pets, animals, family
        *summary: Get your pets.
        *external_docs: http://help.loft.io/loft-api/pets
        *responses:
            - hello
            - hi
        """
        return Success([pets])

    @put(schema=Pet)
    def put_pet(id, pet):
        """
        Add or replace a pet resource.

        -- Operation --
        tags: pets, animals, family
        summary: Put a pet
        """
        pass


class PetCollection(ChildCollection):
    home = ParentCollection('home_id', get_home_by_id)

    def get(self):
        return self.home.get_pets()


class PetCollection(SimpleCollection):
    schema = Pet

    def store(self, id, pet):
        pass

    def load(self, id):
        pass

    def audit(self, method, id, pet):
        pass


Kinds = fields.String(choices=['dog', 'cat', 'bird'])


class Pet(Schema):
    id = fields.AutoUUID()
    name = fields.String()
    age = fields.Integer()
    kind = Kinds(required=True)

Pet.examples = [
    {'name': 'Fred', 'age': 12, 'kind': 'dog'},
    {'name': 'Mr. Puddles', 'age': 4, 'kind': 'cat'},
    {'name': 'Birbert Brown', 'age': 6, 'kind': 'bird'},
]


@put(schema=Pet)
def put_pet(id, pet):
    """
    Add or replace a pet resource.

    -- Operation --
    tags: pets, animals, family
    summary: Put a pet
    """
    pass


def put_pet(id, pet):
    """
    Add or replace a pet resource.

    -- Operation --
    tags: pets, animals, family
    summary: Put a pet
    servers:
        - alt.example.com: 'Alternative Server'
    """
    pass

define_operation(
    callable=put_pet,
    method="put",
    operation_id="petput",
    tags=["pets", "animals", "family"],
    description="Add or replace a pet resource",
    summary="Put a pet",
    parameters = {
        'id': fields.PathString('id of the pet')
    },
    request_body = {
        '*/*':
            fields.RequestBody(schema=Pet),
        }
    },
    responses = {
        '200': {
            http.Response(description="Updated pet object.", schema=Pet)
        }
    },
    callbacks = {
        'onData': data_callback
    },
    deprecated = False,
    security = ,
    servers = [
        {'url': 'alt.example.com', 'description': 'Alternative Server'},
    ])



class HouseCollection(Collection):
    title = "House"
    schema = House
    storages = {
        'google': GoogleStorage('house'),
        'elastic': ElasticStorage('house')
    }
    query_filters = {
        'q': fields.QueryString('search term')
    }

    def query(self, q):
        return this.storages['elastic'].search({'query': q})

    def enrich(self, house):
        return house


class PetCollection(Collection):
    title = "Pet"
    schema = Pet
    parent = HouseCollection
    storages = [GoogleStorage('pet'), ElasticStorage('pet')]
    query = ElasticQuery('pet')
    enrich = {
        'toys': ToyCollection,
        'owner': UserCollection
    }


class Loft_v2(Loft):
    paths = {
        '/houses': HouseCollection,
        '/houses/{house_id}/pets': PetCollection,
    }



class Pet(Schema):
    toys = fields.Enrichment(Toy, 'id', repeated=True)



class Collection(Reconfigurable):
    title = fields.String
    schema = fields.InstanceOf(Schema)
    parent = fields.InstanceOf(Reconfigurable)
    storage = fields.InstanceOf(StorageEngine)
    query = fields.InstanceOf(QueryEngine)
    enrich = fields.InstanceOf(Reconfigurable, mapping=True)
    query_filters = fields.InstanceOf(fields.Field, mapping=True)
    paths = fields.InstanceOf(Dict, mapping=True, default={
        '/':        {'get': 'query_items',
                     'post': 'post_item'},
        '/{id}':    {'get': 'get_item',
                     'put': 'put_item',
                     'patch': 'patch_item',
                     'delete': 'delete_item'}
    })

    def create_operation(self, path, endpoint, **kwargs):
        if isinstance(endpoint, str):
            endpoint = getattr(self, str)
        self.paths.setdefault()

    def register(self, app, path, api):
        for path, mapping in this.path.items():
            if isinstance(mapping, dict):
                for method, endpoint in mapping.items():
                    self.create_operation(path, endpoint, method=method)
            else:
                self.create_operation(path, mapping)
            resource.register(app, path, self)
        app.add_url_rule(path, )

    def query_items(self, **filters):
        pass

    def post_item(self, item):
        self.audit('write', None, item)
        return self.storage.write(self.schema, None, item)

    def get_item(self, id):
        self.audit('read', id)
        return self.storage.load(self.schema, id)

    def put_item(self, id, item):
        self.audit('write', id, item)
        return self.storage.write(self.schema, id, item)

    def patch_item(self, id, item):
        self.audit('write', id, item)
        return self.storage.write(self.schema, id, item, patch=True)

    def delete_item(self, id):
        self.audit('write', id)
        self.storage.remove(self.schema, id)

    def audit(self, perm, id, item):
        self.security.audit(self, perm, id, item)


class Api(Blueprint):
    def register(self, app, options, first_registration=False):
        for path, resource in this.path.items():
            if isinstance(resource, type):
                resource = resource()
            resource.register(app, path, self)

        super().register(app, options, first_registration)



