import inflection
import json
import networkx as nx
import functools
import hashlib
import typing
import inspect


### Hash function
def build_hash(obj, hsh):
    if isinstance(obj, Schema):
        hsh.update( obj.get_hash().encode() )
    elif isinstance(obj, str):
        hsh.update( obj.encode() )
    elif isinstance(obj, bytes):
        hsh.update( obj )
    elif isinstance(obj, typing.Mapping):
        for k, item in obj.items():
            build_hash(k, hsh)
            build_hash(item, hsh)
    elif isinstance(obj, typing.Iterable):
        for item in obj:
            build_hash(item, hsh)  
    elif hasattr(obj, '__schema__'):
        hsh.update( obj.__schema__.get_hash().encode() )
    else:
        hsh.update(str(hash(obj)).encode())


### Identity function
def identity(x):
    return x


class Undefined:
    def __repr__(self):
        return "<Undefined>"

    def __bool__(self):
        return False

Undefined = Undefined()


class ValidationError(ValueError):
    pass


class SchemaFailure(ValidationError):
    def __init__(self, schema, constraints=None, message="could not validate the instance against the schema"):
        self.schema = schema
        self.context = dict(schema.__dict__, schema=schema)
        self.constraints = constraints or {}
        self.message = message
        self.sub_errors = {}

    def __str__(self):
        return self.format()

    def format(self, prefix="  ", depth=0):
        parts = [(prefix * depth) + self.message.format(self.context)]
        for name, error in (self.sub_errors or {}).items():
            parts.append(error.format(prefix, depth+1))
        return "\n".join(parts)


class ConstraintFailure(ValidationError):
    def __init__(self, constraint, sub_errors=None, path=[], message=None, schema=None):
        self.constraint = constraint
        self.sub_errors = sub_errors
        self.message = message
        self.path = path or []
        self.schema = schema

    def __str__(self):
        err = self.constraint.describe(self.message)
        parts = [err]
        if self.path:
            path = "/".join(self.path)
            parts.insert(0, path)
        if self.schema and self.schema._name:
            parts.insert(0, self.schema._name)
        return " -- ".join(parts)


class SchemaValidationResult:
    def __init__(self, schema, instance, errors):
        self.schema = schema
        self.instance = instance
        self.errors = errors
        self.success = True
        for constraint, error in errors.items():
            if error is not None:
                self.success = False
                break

    def __bool__(self):
        return self.success

    def items(self):
        return self.errors.items()

    def __iter__(self):
        return iter(self.items())

    def __repr__(self):
        return f"{self.__class__.__name__}(success={self.success})"

    def format(self):
        if self.success:
            return "Schema valid."

        lines = ["Could not validate the instance against the schema.", 
                  "", 
                  "Instance:", 
                  f"  {self.instance!r}",
                  ""
                  "Errors:"]

        for constraint, err in self:
            lines.append(f"  {err!r}")

        return "\n".join(lines)

    def print_errors(self):
        print(self.format())


class Constraint:
    description = ""

    def __init__(self, schema, value):
        self.schema = schema
        self.value = value
        self.compile(schema.system)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.value)

    def compile(self, system):
        pass

    def fail(self, sub_errors=None, message=None):
        raise ConstraintFailure(self, sub_errors=sub_errors, message=message)

    def assertEqual(self, a, b):
        if a != b:
            self.fail()

    def assertIs(self, a, b):
        if a is not b:
            self.fail()

    def assertNotEqual(self, a, b):
        if a == b:
            self.fail()

    def assertIsNot(self, a, b):
        if a is b:
            self.fail()

    def assertTrue(self, a):
        if not a:
            self.fail()

    def assertFalse(self, a):
        if a:
            self.fail()

    def assertNone(self, a):
        if a is not None:
            self.fail()

    def assertNotNone(self, a):
        if a is None:
            self.fail()

    def is_valid(self, instance, partial=False):
        return self.validate(instance, partial=partial) is None

    def validate(self, instance, partial=False):
        try:
            self(instance, validate=True, partial=partial)
        except ValidationError as e:
            return e

    def describe(self, description=None):
        return (description or self.description).format(**self.__dict__)

    def transform(self, system, other):
        return other.schema(self.value)

    def __call__(self, instance, validate=False, partial=False):
        return instance


class System:
    """
    primitives = schema.InstanceOf(type, mapping=True)
    constraints = schema.InstanceOf(Constraint, mapping=True)
    transforms = schema.InstanceOf(Callable, mapping=True)
    marshals = schema.InstanceOf(Callable, mapping=True)
    name_inflection = schema.InstanceOf(Callable, default=inflection.underscore)
    empty_values = schema.Any(repeated=True, default=[Undefined])
    reserved_constraints = schema.String(repeated=True, default=['system'])
    schema_factory = schema.InstanceOf(Callable)
    ignore_all_formats = schema.Boolean(default=False)
    ignore_these_formats = schema.String(repeated=True)
    """
    def __init__(self, **attrs):
        self.name = None
        self.primitives = {}
        self.network = nx.Graph()
        
        self.schema_transformations = {}
        self.constraint_transformations = {}
        self.constraint_analogs = {}
        self.constraints = {}
        self.constraint_primitives = {}
        self.name_inflection = inflection.underscore
        self.empty_values = [Undefined]
        self.reserved_constraints = ['system']
        self.schema_factory = getattr(self, 'schema_factory', Schema)
        self.schema_instancers = {}
        self.ignore_all_formats = False
        self.ignore_these_formats = []
        self.adapters = {}
        self.config(attrs)

    def __repr__(self):
        return f"System({self.name!r})"

    def config(self, attrs):
        # TODO build schema, assign it
        for k in attrs.keys():
            if k not in self.__dict__:
                raise ValidationError(f"Unknown attribute: {k!r}")
        self.__dict__.update(attrs)

    def register_constraint(self, constraint, primitives=None, name=None):
        # Get the name like this, because a subclass will have it's parent's name.
        name = name or getattr(constraint, 'name', constraint.__name__)
        name = self.name_inflection(name)
        if name in self.reserved_constraints:
            raise ValueError(
                "Constraints cannot be any of: {!r}".format(self.reserved_constraints))
        self.constraint_primitives[name] = primitives
        self.constraints[name] = constraint
        self.network.add_node((self.name, 'constraint', name), cls=constraint)
        return constraint

    def constraint(self, primitives, name=None):
        def decorator(fn):
            self.register_constraint(fn, primitives, name)
            return fn
        return decorator

    def get_constraint(self, name, default=Undefined):
        name = self.name_inflection(name.lstrip('_'))
        if name not in self.constraints:
            if default is Undefined:
                raise TypeError(f"unknown constraint named: {name}")
            else:
                return None, default
        return name, self.constraints[name]

    def get_constraint_primitives(self, name):
        name = self.name_inflection(name.lstrip('_'))
        return self.constraint_primitives.get(name, [])

    def schema(self, value={}, name=None):
        if hasattr(value, '__schema__'):
            value = value.__schema__
        if isinstance(value, Schema):
            schema = value
            if not schema.system:
                schema.compile(self)
            return schema
        return self.schema_factory(value=value, system=self, name=name)

    def is_applicable(self, constraint_name, instance):
        primitives = self.get_constraint_primitives(constraint_name)
        if primitives is None:
            return True
        for name in primitives:
            if isinstance(instance, self.primitives[name]):
                return True
        return False

    def borrow_constraint(self, other_system, their_name, our_name=None, primitives=None, transform_to_theirs=identity, transform_to_ours=identity):
        our_name = self.name_inflection(our_name or their_name)
        their_name, constraint = other_system.get_constraint(their_name)
        
        self.register_constraint(constraint, name=our_name, primitives=primitives)

        self.add_constraint_transformation(our_name, their_name, 
                                           from_system=self, to_system=other_system, 
                                           fn=transform_to_theirs)
        self.add_constraint_transformation(their_name, our_name, 
                                           from_system=other_system, to_system=self, 
                                           fn=transform_to_ours)

    def add_constraint_transformation(self, from_name, to_name, fn=identity, from_system=None, to_system=None):
        from_system = from_system or self
        to_system = to_system or self

        from_name, from_constraint = from_system.get_constraint(from_name)
        to_name, to_constraint = to_system.get_constraint(to_name)

        from_node = (from_system.name, 'constraint', from_name)
        to_node = (to_system.name, 'constraint', to_name)
        
        if not self.network.has_node(from_node):
            self.network.add_node(from_node, name=from_name, cls=from_constraint)

        if not self.network.has_node(to_node):
            self.network.add_node(to_node, name=to_name, cls=to_constraint)

        self.network.add_edge(from_node, to_node, fn=fn)

    def add_schema_transformation(self, source_schema, destination_name, fn=identity):
        pass
        from_node = self.get_node(from_system, 'schema', from_name)
        to_node = self.get_node(to_system, 'schema', to_name)

        if not self.network.has_node(from_node):
            self.network.add_node(from_node, name=from_name, cls=from_constraint)

        if not self.network.has_node(to_node):
            self.network.add_node(to_node, name=to_name, cls=to_constraint)


    def transform_instance_via_constraint(self, instance, from_name, to_name, from_system=None, to_system=None):
        """
        Transforms data `instance` from satisfying constraint `from_name` to satisfying constraint `to_name`.
        By default, we mean with the system, but by specifying `from_system` or `to_system` one can
        transform into others.

        This is usually done to tranform from one system to another.  For instance, native max_length
        to json maxLength.  In that case, the transformer is `identity()`, but this might not always be
        the case.
        """
        from_node = self.get_node(from_system, 'constraint', from_name)
        to_node = self.get_node(to_system, 'constraint', to_name)
        
        path = nx.shortest_path(from_node, to_node)
        source = path.pop(0)
        while path:
            dest = path.pop(0)
            instance = self.network[source][dest]['fn'](data)
            source = dest
        
        return instance

    def transform_instance_to_system(self, instance, schema, to_system, to_schema_name=None):
        from_schema_name = schema.name
        to_schema_name = to_schema_name or schema.name

        #find A'
        from_node = self.get_node(from_system, 'primitive', from_name)
        to_node = self.get_node(to_system, 'primitive', to_name)

        if not self.network.has_node(to_node):
            self.derive_analog_schema(schema, to_system)

    
    def derive_analog_schema(self, schema, other_system):
        """
        Creates an analog schema that exists within the other_system and a transformation
        to get there.  Adds it to the system's network.
        """
        for name, value in schema.constraints.items():
            #First see if there is a
            pass

    def get_node(self, system, type, name):
        system = system or self
        return (sysem.name, type, system.name_inflection(name))

    def transform_instance_via_primitive(self, instance, from_name, to_name, from_system=None, to_system=None):
        from_node = self.get_node(from_system, 'primitive', from_name)
        to_node = self.get_node(to_system, 'primitive', to_name)
        
        path = nx.shortest_path(self.network, from_node, to_node)
        instance = self.transform_via_path(instance, path)
        
        return instance

    def transform_schema_to_other_system(self, schema, other_system):
        pass
    
    def transform_instance_to_other_system(self, schema, instance, from_system=None, to_system=None, to_schema_name=None):
        from_node = self.get_node(from_system, 'schema', schema.name)
        to_node = self.get_node(to_system, 'schema', other_schema_name or schema.name)

        if self.network.has(to_node):
            path = nx.shortest_path(self.network, from_node, to_node)
            if path:
                instance = self.transform_via_path(instance, path)
                return instance

        return instance

    def transform_via_path(self, instance, path):
        source = path.pop(0)
        while path:
            dest = path.pop(0)
            instance = self.network[source][dest]['fn'](data)
            source = dest
        return instance

    def register_instancer(self, schema, fn):
        if not isinstance(schema, str):
            schema = schema.name
        self.schema_instancers[schema] = fn

    def instantiate(self, schema, values):
        if not isinstance(schema, str):
            schema = schema.name
        return self.schema_instancers[schema](values)

    def unserialize(self, schema, data, content_type):
        if (content_type.endswith('+json') or content_type.startswith('application/json')):
            data = schema(json.loads(data))
            if schema.name in self.schema_instancers:
                return self.instantiate(schema, data)
            return data
        raise RuntimeError(f"Unable to unserialize content type: {content_type!r}")

    def serialize(self, schema, data, content_type):
        if hasattr(data, '__dict__'):
            data = data.__dict__
        if (content_type.endswith('+json') or content_type.startswith('application/json')):
            return json.dumps(data)
        raise RuntimeError(f"Unable to serialize content type: {content_type!r}")

    def transform_schema(self, schema, other_system):
        if schema.name:
            sig = (other_system, schema.name)
            transformation = self.schema_transformations.get(sig, None)
            if transformation:
                return transformation(self, schema, other_system)
        return schema.transform(self, other_system)

    def transform_constraint(self, c, other_system):
        sig = (other_system, c.name)
        transformation = self.constraint_transformations.get(sig, None)
        if transformation:
            return transformation(self, c, other_system)
        return c.transform(self, other_system)


class Schema:
    def __init__(self, value={}, system=None, name=None):
        self._name = name
        self.system = system
        self.value = value
        self.constraints = {}
        self.examples = {}
        if system:
            self.compile(system)
    
    def __repr__(self):
        if self._name:
            return f"{self.__class__.__name__}(name={self._name!r}, value={self.value!r})"
        return f"{self.__class__.__name__}({self.value!r})"

    def get_hash(self):
        if not hasattr(self, '_hash'):
            hsh = hashlib.new('md5', self.system.name.encode())
            build_hash(self.value, hsh)
            self._hash = hsh.hexdigest()
        return self._hash

    def __call__(self, instance, partial=False):
        assert self.system, "Schema needs a system before it is used."

        # Coerce type first
        type_constraint = self.get_constraint_instance('type')
        if type_constraint is not None:
            try:
                instance = type_constraint(instance, validate=False, partial=partial)
            except ConstraintFailure as e:
                e.schema = self
                e.path.insert(0, 'type')
                raise
            except ValueError as e:
                raise ConstraintFailure(type_constraint, None, ['type'], str(e))

        for name, c in self.constraints.items():
            if c is type_constraint:
                continue
            if not self.system.is_applicable(name, instance):
                continue
            try:
                instance = c(instance, validate=False, partial=partial)
            except ConstraintFailure as e:
                e.schema = self
                e.path.insert(0, name)
                raise

        return instance

    def validate(self, instance, partial=False):
        results = {}

        # Coerce type first
        type_constraint = self.get_constraint_instance('type')
        if type_constraint is not None:
            try:
                instance = type_constraint(instance, validate=True, partial=partial)
                results[type_constraint] = None
            except ValueError as e:
                results[type_constraint] = e
                return SchemaValidationResult(self, instance, results)

        for name, c in self.constraints.items():
            if c is type_constraint:
                continue
            if not self.system.is_applicable(name, instance):
                continue
            results[c] = c.validate(instance, partial=partial)

        return SchemaValidationResult(self, instance, results)

    def compile(self, system):
        self.system = system
        self.value = self.compile_constraints(self.value)

    def unserialize(self, data, content_type='application/json'):
        return self.system.unserialize(self, data, content_type)

    def serialize(self, data, content_type='application/json'):
        return self.system.serialize(self, data, content_type)

    def compile_constraints(self, value):
        results = {}
        for k, v in value.items():
            name = self._set_constraint(k, v)
            if name:
                results[name] = v
            else:
                results[k] = v
        return results

    def is_valid(self, instance, partial=False):
        return bool(self.validate(instance, partial=partial))

    def get_constraint_instance(self, name, default=None):
        name = self.system.name_inflection(name)
        return self.constraints.get(name, default)

    def get_constraint_value(self, name, default=Undefined):
        c = self.get_constraint_instance(name)
        if c is not None:
            return c.value
        if default is Undefined:
            raise NameError(f"Cannot find constraint: {name}")
        else:
            return default

    def marshal(self, ohter_system):
        pass

    def transform(self, system, other):
        return other.schema(self.value)

    def _set_constraint(self, name, value):
        if value is Undefined:
            return self._del_constraint(name)
        name, cls = self.system.get_constraint(name, None)
        if cls is None:
            return None
        self.constraints[name] = cls(self, value)
        return name

    def _del_constraint(self, name):
        name = self.system.name_inflection(name)
        self.constraints.pop(name, None)
        return name

    @property
    def properties(self):
        props = self.get_constraint_value('properties', None)
        if props is None:
            return ()
        return props.items()

    @property
    def name(self):
        if not self._name:
            return self.get_hash()
        return self._name

    @property
    def full_name(self):
        return f'{self.schema.name}:{self.name}'

System.schema_factory = Schema
