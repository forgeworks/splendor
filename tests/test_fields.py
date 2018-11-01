import pytest
from splendor.schema.fields import *


def test_descriptor():
    class Person(Schematic):
        name = String(min_length=3)
        age = Integer(minimum=0)

    p = Person()
    p.name = "Bob"
    p.age = 52

    assert p.age == 52
    assert p.name == "Bob"

    with pytest.raises(ValidationError):
        p.name = ""

    p.age = -10
    assert p.age == 0

    p = Person(age=12, name=666)

    assert p.name == '666'


def test_items():
    class Item(Schematic):
        name = String()

    class List(Schematic):
        items = InstanceOf(Item, repeated=True)

    list = List(items=[{'name': 1}, {'name': 2}])

    assert isinstance(list.items[0], Item)


def test_schema_field():
    class A(Schematic):
        name = String()
 
    class B(Schematic):
        schema = SchemaField()

    assert B(schema=A)


def test_name():
    class A(Schematic):
        name = String()
    
    assert A.__schema__.name == 'splendor.A'

    