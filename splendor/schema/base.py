import inflection
import json


Undefined = object()


class ValidationError(ValueError):
    pass


class SchemaFailure(ValidationError):
    def __init__(self, schema, constraints=None, message="could not validate the instance against the schema"):
        self.schema = schema
        self.context = dict(schema.__dict__, schema=schema)
        self.constraints = constraints or {}
        if context:
            self.context.update(context)

    def __str__(self):
        return self.format()

    def format(self, prefix="  ", depth=0):
        parts = [(prefix * depth) + self.message.format(self.context)]
        for name, error in (sub_errors or {}).items():
            parts.append(error.format(prefix, depth+1))
        return "\n".join(parts)


class ConstraintFailure(ValidationError):
    def __init__(self, constraint, sub_errors=None, path=[], message=None):
        self.constraint = constraint
        self.sub_errors = sub_errors
        self.message = message
        self.path = path or []

    def __str__(self):
        err = self.constraint.describe(self.message)
        if self.path:
            path = "/".join(self.path)
            return f'{path} -- {err}'
        else:
            return err


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
        self.transformations = {}
        self.constraints = {}
        self.constraint_primitives = {}
        self.name_inflection = inflection.underscore
        self.empty_values = [Undefined]
        self.reserved_constraints = ['system']
        self.schema_factory = getattr(self, 'schema_factory', None)
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
        return constraint

    def constraint(self, primitives, name=None):
        def decorator(fn):
            self.register_constraint(fn, primitives, name)
            return fn
        return decorator

    def get_constraint_cls(self, name, default=Undefined):
        name = self.name_inflection(name.lstrip('_'))
        if name not in self.constraints:
            if default is Undefined:
                raise TypeError(f"unknown constraint named: {name}")
            else:
                return default
        return self.constraints[name]

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

    def map_primitives(self, system, map):
        for other_name, our_name in map.items():
            our_name = self.name_inflection(our_name)
            other_name = other_system.name_inflection(other_name)
            edge = (other_system.name + '.' + other_name, our_name)
            self.transformations[edge] = lambda x: other_system.primitives[other_name](x)

    def borrow_constraint(self, other_system, name, new_name=None, primitives=None):
        c = other_system.constraints[other_system.name_inflection(name)]
        new_name = self.name_inflection(new_name or name)
        self.register_constraint(c, name=new_name, primitives=primitives)

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



class Schema:
    def __init__(self, value={}, system=None, name=None):
        self.system = system
        self.value = value
        self.name = name
        self.constraints = {}
        self.examples = {}
        if system:
            self.compile(system)
    
    def __repr__(self):
        if self.name:
            return f"{self.__class__.__name__}(name={self.name!r}, value={self.value!r})"
        return f"{self.__class__.__name__}({self.value!r})"

    def __call__(self, instance, partial=False):
        assert self.system, "Schema needs a system before it is used."

        # Coerce type first
        type_constraint = self.get_constraint_instance('type')
        if type_constraint is not None:
            try:
                instance = type_constraint(instance, validate=False, partial=partial)
            except ValueError as e:
                e.path.insert(0, 'type')
                raise

        for name, c in self.constraints.items():
            if c is type_constraint:
                continue
            if not self.system.is_applicable(name, instance):
                continue
            try:
                instance = c(instance, validate=False, partial=partial)
            except ConstraintFailure as e:
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

    def _set_constraint(self, name, value):
        if value is Undefined:
            return self._del_constraint(self, name)
        name = self.system.name_inflection(name)
        cls = self.system.get_constraint_cls(name, None)
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
    

System.schema_factory = Schema