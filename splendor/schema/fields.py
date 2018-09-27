from .base import Schema, Undefined, ValidationError
from .native import system as native
from uuid import uuid4

"""
    Field = Schema != Class || Type

    Constraints are descriptions of data.
    Schemas are collections of constraints.
    Types are classifications for the interpreter/compiler.

    A class can have a schema.
    A class can have many fields.
    Fields are schemas that are descriptors on a class as well as a schema property.

    A field should match the interface of a schema perfectly.
    A schema optionally has a name, a field MUST have a name after it's class is compiled,
    this allows it to act as a descriptor.

    A schema can compile itself in order to maximize its efficiency.
    A schema is given its system at compile time.
    
    A constraint is immutable, it can compile itself at __init__, but not in a 
    separate step.  It must be given a schema (with a system) to create.

    After a schema is compiled, if a constraint is changed, the whole schema MUST be recompiled.

    Changing a schema MAY be through a migration, which is a transformation from
    one version of a schema to another.

    Both schemas and constraints instances MUST have a system which provides services and registrations
    for objects within it.  Schemas and constaints are registered to a system.

    A Schematic is a class that has a schema and field descriptors.  This makes the class validate
    itself as its attributes are changed.
"""


class FieldSetupError(Exception):
    def __init__(self, field, name, original):
        self.original = original
        self.name = name
        self.field = field

    def __str__(self):
        return f'Error setting up field({self.name}), original error is: {self.original!r}'


class Field:
    order = 0

    meta = set(['repeated',
                'map',
                'required',
                'deprecated',
                'aliases',
                'description',
                'title',
                'read_only',
                'write_only',
                'default',
                'name',
                'primary_key',
                'export',
                'import'
                'system'])

    def __init__(self, **config):
        self.config = config
        self.schema = None
        self.default = Undefined
        self.order = self.__class__.order
        self.__class__.order += 1
        self.setup( config.get('name', None), config.get('system', native) )

    def __call__(self, **config):
        config = dict(self.config, **config)
        return self.__class__(**config)

    # So that a field can be used as a schema
    @property
    def __schema__(self):
        return self.schema

    def setup(self, name, system):
        self.name = name
        self.system = system

        value = {}
        for k, v in self.config.items():
            name = system.name_inflection(k)
            value[name] = v

        self.default = self.config.get('default', Undefined)

        try:
            if 'repeated' in self.config:
                meta = {'type': 'list'}
                for k in self.meta:
                    if k in value:
                        meta[k] = value.pop(k)
                meta['items'] = value
                self.schema = system.schema(meta)
                self.default = self.default or list
            elif 'map' in self.config:
                meta = {'type': 'dict'}
                for k in self.meta:
                    if k == 'default':
                        continue
                    if k in value:
                        meta[k] = value.pop(k)
                meta['additional_properties'] = value
                self.schema = system.schema(meta)
                self.default = self.default or dict
            else:
                self.schema = system.schema(value)
        except Exception as e:
            raise FieldSetupError(self, self.name, e)

    def get_default(self, obj):
        if self.default is not Undefined:
            if callable(self.default):
                return self.default()
            return self.default
        else:
            return Undefined

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        result = obj.__dict__.get(self.name, Undefined)
        if result is Undefined:
            default = self.get_default(obj)
            if default is not Undefined:
                obj.__dict__[self.name] = default
                return default
            raise AttributeError("%r object has no value for field %r, and no default is defined" % (obj, self.name))
        return result

    def __set__(self, obj, value):
        if value is Undefined:
            self.__delete__(obj)
        else:
            obj.__dict__[self.name] = self.schema(value)

    def __delete__(self, obj):
        obj.__dict__.pop(self.name, None)


def get_fields(type):
    fields = {}
    for name, field in vars(type).items():
        if isinstance(field, Field):
            fields[name] = field
    return fields


def get_field_values(instance, export=False):
    properties = {}
    for name, field in get_fields(instance.__class__).items():
        if export is True and field.config.get('export', True) is False:
            continue
        value = getattr(instance, name, Undefined)
        if value is not Undefined:
            properties[name] = value
    return properties


def generate_schema_for_class(name, bases, namespace, system=None):
    if '__schema__' in namespace:
        value = namespace['__schema__']
    else:
        value = {'type': 'object'}

    system = namespace.get('__schema_namespace__', system)

    for base in bases:
        if hasattr(base, '__schema__') and base.__schema__:
            value = dict(value, **base.__schema__.value)
            system = system or base.__schema__.system

    system = system or native

    new_values = {}
    properties = {}
    for k, v in namespace.items():
        if isinstance(v, Field):
            v.setup(k, system)
            properties[k] = v.schema
        else:
            if value is not Undefined:
                new_values[k] = v

    ## Validate New Values ###
    old_schema = Schema(value, system=system or native)
    namespace.update( old_schema(new_values, partial=True) )

    from pprint import pprint
    print(name)
    if name == 'GuideCollection':
        print("-- OLD SCHEMA --")
        pprint(old_schema)
        print("-- New Values --")
        pprint(new_values)
        print("-- Namespace --")
        pprint(namespace)

    if properties:
        value['properties'] = properties

    schema = Schema(value, system=system or native)
    schema.name = name

    return schema


Schematic = None

class SchematicType(type):
    def __new__(cls, name, bases, namespace):
        schema = None
        if Schematic:
            schema = namespace['__schema__'] = generate_schema_for_class(name, bases, namespace)
        typ = type.__new__(cls, name, bases, namespace)
        if schema:
            schema.system.register_instancer(schema.name, typ)
        return typ


class Schematic(metaclass=SchematicType):
    def __init__(self, __schematic_config__=None, **kwargs):
        super().__init__()
        if __schematic_config__:
            for k, v in __schematic_config__.items():
                kwargs.setdefault(k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.validate()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__!r})'

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def validate(self):
        self.__schema__.validate(self.__dict__)

    def is_valid(self):
        return self.validate() is None


class Configurable(Schematic):
    def __call__(self, **value):
        return self.__class__(**dict(self.__schema__.value, **value))


Boolean = Field(type='bool')
Integer = Field(type='int')
String = Field(type='str')
Number = Field(type='number')
Callable = Field(type='callable')
Object = Field(type='object')
Dict = Field(type='dict')
List = Field(type='list')
Set = Field(type='set')
DateTime = Field(type='datetime')
Date = Field(type='date')
URIString = Field(type='str', format='validate_uri')
Any = Field()

def AnyOf(t, **kwargs):
    return Field(any_of=t, **kwargs)

def InstanceOf(t, **kwargs):
    return Object(instance_of=t, **kwargs)

def AnyInstanceOf(types, **kwargs):
    return Field(any_of=[InstanceOf(t) for t in types], **kwargs)

def Enum(choices, **kwargs):
    return String(enum=choices, **kwargs)

def Duck(t, **kwargs):
    return Object(has_attrs=t, **kwargs)

def SchemaField(**kwargs):
    return Field(schema_value=True, **kwargs)


def uuid4hex():
    return uuid4().hex

def UUID(**kwargs):
    kwargs.setdefault('default', uuid4hex)
    return String(**kwargs)


"""
### Simple Fields ###
Boolean = Field(bool)
Integer = Field(int)
String = Field(str)
Float = Field(float)
Complex = Field(complex)

DictField = Field(dict)


### Useful Fields ###
Any = Field(lambda x: x)
PositiveInteger = Field(int, ensure(lambda x: x >= 0, "Value must be greater or equal to zero: {value}"))


class Function(Field):
    "" "
    A function field must not call its default when returning it.
    "" "
    def config(self, kwargs):
        super().config(kwargs)
        self.factory = kwargs.get('factory', None)

    def get_default(self):
        if self.default is not Undefined:
            return self.default
        elif self.factory:
            return self.factory()
        else:
            return Undefined

def get_schema(dct):
    if isinstance(dct, Schema):
        return dct
    elif isinstance(dct, dict):
        return Schema(dct)
    raise ValidationError("Must be a Schema instance or a dictionary that will be placed in a Schema().")

SchemaField = Field(get_schema)

def get_field(value):
    if isinstance(value, Field):
        return value
    elif callable(value):
        return Field(value)
    raise ValidationError("Must be a Field instance or a callable that will be placed in a Field().")

FieldField = Field(get_field)

def InstanceOf(type, **args):
    return Field(type_filter(type), **args)

def Duck(method_names, **args):
    def filter(obj):
        for name in method_names:
            if not callable(getattr(obj, name)):
                raise ValidationError("Object must have the following methods: %s" % name)
        return obj
    return Field(filter, **args)

class QueryString(String):
    found_in = "query"

class PathString(String):
    found_in = "path"
"""
