from splendor import Api
from splendor.schema import fields, super_dict, json
from splendor.data import MemoryStore
from splendor.api import Collection, QueryString
from splendor.common import post
from splendor.operation import FileType


class Category(fields.Schematic):
    id = fields.Integer(primary_key=True, format="int32")
    name = fields.String(required=True)


class Tag(fields.Schematic):
    id = fields.Integer(primary_key=True, format="int32")
    name = fields.String(required=True)


class Pet(fields.Schematic):
    id = fields.Integer(primary_key=True, format="int32")
    category = fields.InstanceOf(Category)
    name = fields.String(description="Example: doggie", required=True)
    photo_urls = fields.String(repeated=True)
    tags = fields.InstanceOf(Tag, repeated=True)
    status = fields.Enum(["available", "pending", "sold"])


class ApiResponse(fields.Schematic):
    code = fields.Integer(primary_key=True, format="int32")
    type = fields.String()
    message = fields.String()


class Order(fields.Schematic):
    id = fields.Integer(primary_key=True, format="int32")
    pet_id = fields.Integer(primary_key=True, format="int32")
    quantity = fields.Integer(primary_key=True, format="int32")
    ship_date = fields.DateTime()
    status = fields.Enum(["placed", "approved", "delivered"], description="Order Status")
    complete = fields.Boolean(default=False)


class User(fields.Schematic):
    id = fields.Integer(primary_key=True, format="int32")
    username = fields.String()
    name = fields.String()
    short_name = fields.String()
    email = fields.String()
    password = fields.String()
    phone = fields.String()
    user_status = fields.Integer(format="int32", description="User Status")


def hello(target="world") -> str:
    return f"hello {target}"


class PetCollection(Collection):
    title = "Pet"
    media = Pet
    storage = MemoryStore()
    query_filters = {"q": fields.String(description="search term")}
    paths = super_dict({"/<id>/uploadImage": {"POST": "upload_image"}, "/hello": {"GET": hello}})

    def enrich(self, key, house):
        house = super().enrich(key, house)
        house._url = f"{self.url_prefix}/{key.id}"
        return house

    @post(summary="uploads an image")
    def upload_image(
        self,
        id: str,
        file: FileType,
        additional_metadata: QueryString(description="Additional data to pass to server") = None,
    ) -> ApiResponse:
        return f"open {key}"


class GreetingV1(Api):
    info = {"title": "Petstore", "version": "1.0.3"}
    paths = {"/pet": PetCollection()}

