import inspect, typing
from uuid import uuid4

from .base import Schema, Undefined, ValidationError
from .native import system as native

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
        return f'Error setting up field <{self.name}> -- original error is -- {self.original.__class__.__name__}: {self.original}'


class Field:
    order = 0

    meta = set(['repeated',
                'map',
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
                'import',
                'system'])

    def __init__(self, required=False, system=None, **config):
        self.config = config
        self.schema = None
        self.required = required
        self.system = system
        self.order = self.__class__.order
        self.__class__.order += 1
        if system:
            self.setup( config.get('name', None), system )

    def __call__(self, **config):
        config = dict(self.config, **config)
        config.setdefault('required', self.required)
        config.setdefault('system', self.system)
        return self.__class__(**config)

    # So that a field can be used as a schema
    @property
    def __schema__(self):
        if self.schema is None:
            self.setup(None, native)
        return self.schema

    def setup(self, name, system):
        self.name = name
        self.system = system

        schema_value = {}
        meta = {}
        for k, v in self.config.items():
            name = system.name_inflection(k)
            if name in self.meta:
                meta[name] = v
            else:
                schema_value[name] = v

        try:
            if 'repeated' in self.config:
                meta['type'] = 'list'
                meta['items'] = schema_value
                meta.setdefault('default', list)
                self.schema = system.schema(meta)
                self.default = meta.get('default', list)
            elif 'map' in self.config:
                meta['type'] = 'dict'
                meta['additional_properties'] = schema_value
                meta.setdefault('default', dict)
                self.schema = system.schema(meta)
            else:
                self.schema = system.schema(dict(schema_value, **meta))
        except Exception as e:
            raise
            raise FieldSetupError(self, name, e)

        return self.schema

    def get_default(self, obj):
        default = self.schema.value.get('default', Undefined)
        if self.schema.value.get('type') != 'callable' and callable(default):
            return default()
        return default

    def has_value(self, obj):
        return self.name in obj.__dict__

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

    system = namespace.get('__schema_system__', None)
    fields = {}   # List of fields
    default = value.get('default', {})    # Default value for an instance
    default_inherited = {}
    properties = {}

    ### Inherited ###
    for base in bases:
        if hasattr(base, '__schema__') and base.__schema__:
            value = dict(base.__schema__.value, **value)        # Merge parent schema with this one.  TODO: make better
            system = system or base.__schema__.system
            default_inherited.update(base.__schema__.value.get('default', {}))
        if hasattr(base, '__fields__'):
            fields.update(base.__fields__)
    
    ### Properties ###
    for k, v in namespace.items():
        if isinstance(v, Field):
            fields[k] = v
        elif value is Undefined:
            # If the new class sets a field to Undefined, get rid of it
            fields.pop(k, None)
    
    for k, v in fields.items():
        properties[k] = v.setup(k, system or native)

    if properties:
        value['properties'] = properties
    
    ### Default Values ###
    # Merge given default and inherited
    default = dict(default_inherited, **default)   
    
    # Add defaults from properties
    for k, v in namespace.items():
        if v is Undefined:
            default.pop(None)
        elif k in properties and not isinstance(v, Field):
            default[k] = fields[k].schema(v)
    
    if default:
        value['default'] = default

    schema = Schema(value, name=name, system=system or native)

    ## Validate New Values ###
    if default:
        try:
            value['default'] = schema(default, partial=True)
        except ValidationError as e:
            raise ValidationError("Default values for class %r did not validate against "
                                  "its own schema, error was:\n%s" % (name, e))
    
    return fields, schema


Schematic = None 

class SchematicType(type):
    def __new__(cls, name, bases, namespace):
        schema = None
        if Schematic:
            full_name = namespace.get('__schema_name__', inspect.getmodule(cls).__name__.split('.', 1)[0] + '.' + name)
            fields, schema = generate_schema_for_class(full_name, bases, namespace)
            namespace['__schema__'] = schema
            namespace['__fields__'] = fields
        typ = type.__new__(cls, name, bases, namespace)
        if schema:
            schema.system.register_instancer(schema.name, typ)
        return typ

class Schematic(metaclass=SchematicType):   # pylint: disable-msg=E0102
    """
    Construct that carries a schema (`__schema__`) and enforces its properties
    to follow it.
    """
    __schema__ = None
    __fields__ = []

    def __init__(self, __value__=None, **kwargs):
        super().__init__()
        value = {}
        if self.__schema__:
            value.update(self.__schema__.value.get('default', {}))
        if __value__:
            value.update(__value__)
        value.update(kwargs)
        self.set_schema_value(value)
        self.validate()

    def __repr__(self): 
        return f'{self.__class__.__name__}({self.__dict__!r})'

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def validate(self):
        self.__schema__.validate(self.__dict__)

    def is_valid(self):
        return self.validate() is None

    def get_schema(self):
        return self.__schema__

    def get_schema_value(self, ignore_default=False, ignore_empty=True, export=False):
        """
        Combines the schema-property values of this object with the inherited ones,
        and returns it as a dict.

        If `ignore_default` is `True` (default) properties with default values won't
        be included.
        """
        value = {}
        fields = self.__class__.__fields__
        for k, field in fields.items():
            if field.config.get('export') is False:
                continue
            if field.has_value(self):
                v = getattr(self, k)
            elif not ignore_default:
                try:
                    v = getattr(self, k)
                except AttributeError:
                    continue
            else:
                continue
            if v or ignore_empty is False:
                value[k] = v
        return value

    def set_schema_value(self, value):
        self.__dict__ = self.__schema__(value)

    def marshal_as(self, system, export=True):
        if system is not 'json':
            raise NotImplementedError("Marshalling is kinda fake right now, so we can only marshal to json")
        return marshal_to_json(self.get_schema_value(export=export))
    
    @classmethod
    def get_field(cls, k):
        getattr(cls, k)


def marshal_to_json(obj, export=True):
    if isinstance(obj, Schematic):
        return obj.marshal_as('json', export)
    elif isinstance(obj, Schema):
        return marshal_to_json(obj.config, export)
    elif isinstance(obj, typing.Mapping):
        return {k: marshal_to_json(v, export) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, float):
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, bool):
        return obj
    elif obj is None:
        return None
    elif isinstance(obj, typing.Iterable):
        return [marshal_to_json(v, export) for v in obj]
    return str(obj)


def transform_schema_value(schematic, value, ignore_default=True):
    if isinstance(value, Schematic):
        return value.get_schema_properties(ignore_default)

    elif isinstance(value, dict):
        for k, v in value.items():
            v = transform_schema_value(schematic, v, ignore_default=True)
            if v is Undefined:
                continue
            if k in schematic.__fields__:
                pass
            if isinstance(v, Schematic):
                props[k] = v.get_schema_properties()
            elif v is Undefined or v == [] or v == {}:
                del props[k]

    result = {}
    for k, v in values.items():
        if isinstance(v, Schematic):
            props[k] = v.get_schema_properties()
        elif v is Undefined or v == [] or v == {}:
            del props[k]



class Configurable(Schematic):
    """
    A Schematic that can be reconfigured by calling it as a function with
    new schema-properties.  This returns a new instance.
    """
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

def SubclassOf(t, **kwargs):
    return Object(subclass_of=t, **kwargs)

def AnyInstanceOf(types, **kwargs):
    return Field(any_of=[InstanceOf(t) for t in types], **kwargs)

def Enum(choices, **kwargs):
    return String(enum=choices, **kwargs)

def Duck(t, **kwargs):
    return Object(required=t, **kwargs)

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
