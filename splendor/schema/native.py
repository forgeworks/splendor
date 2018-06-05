import re
import itertools
import ipaddress
import inflection
import logging
from collections import OrderedDict
from collections.abc import Mapping, MutableMapping, Sequence, Callable
from numbers import Number
from decimal import Decimal

AnyNumber = (Number, Decimal)

from .base import Schema, System, Constraint, ValidationError, Undefined

system = System(
    name="native",
    name_inflection = inflection.underscore,
    primitives={
        'int': int,
        'float': float,
        'complex': complex,
        'decimal': Decimal,
        'number': AnyNumber,
        'str': str,
        'bytes': bytes,
        'callable': Callable,
        'mapping': Mapping,
        'sequence': Sequence,
        'list': list,
        'tuple': tuple,
        'dict': dict,
        'bool': bool,
        'object': object
    })

primitives = system.primitives
constraints = system.constraints
schema = system.schema

from .json_object import system as json


#system.map_transformations({
#    'json.integer': {'int': int, 'decimal': Decimal, 'number': int},
#    'int': {'json.integer': int, 'json.string': str},
#    'decimal': {'json.integer': int, 'json.string': str},
#    'number': {'json.integer': float, 'json.string': str}
#
#    'json.string': {'str': str, 'bytes': lambda x: x.encode()},
#    'bytes': {'json.string': {lambda x: x.decode()},
#    'str': {'json.string': str, 'json.int': int},
#
#    'json.object': {'dict': dict, 'sequence': },
#
#    'json.array': {''
#})


system.borrow_constraint(json, 'type', primitives=None)
system.borrow_constraint(json, 'enum', primitives=None)
system.borrow_constraint(json, 'const', primitives=None)

system.borrow_constraint(json, 'multiple_of', primitives=['int', 'float', 'number'])
system.borrow_constraint(json, 'maximum', primitives=['int', 'float', 'number'])
system.borrow_constraint(json, 'exclusive_maximum', primitives=['int', 'float', 'number'])
system.borrow_constraint(json, 'minimum', primitives=['int', 'float', 'number'])
system.borrow_constraint(json, 'exclusive_minimum', primitives=['int', 'float', 'number'])

system.borrow_constraint(json, 'max_length', primitives=['str'])
system.borrow_constraint(json, 'min_length', primitives=['str'])
system.borrow_constraint(json, 'pattern', primitives=['str'])

system.borrow_constraint(json, 'items', primitives=['sequence', 'list', 'tuple'])
system.borrow_constraint(json, 'additional_items', primitives=['sequence', 'list', 'tuple'])
system.borrow_constraint(json, 'max_items', primitives=['list', 'tuple'])
system.borrow_constraint(json, 'min_items', primitives=['list', 'tuple'])
system.borrow_constraint(json, 'unique_items', primitives=['sequence', 'list', 'tuple'])
system.borrow_constraint(json, 'contains', primitives=['sequence', 'list', 'tuple'])

system.borrow_constraint(json, 'max_properties', primitives=['dict'])
system.borrow_constraint(json, 'min_properties', primitives=['dict'])
system.borrow_constraint(json, 'required', primitives=['dict'])
system.borrow_constraint(json, 'properties', primitives=['dict'])
system.borrow_constraint(json, 'pattern_properties', primitives=['dict'])
system.borrow_constraint(json, 'additional_properties', primitives=['dict'])
system.borrow_constraint(json, 'dependencies', primitives=['dict'])
system.borrow_constraint(json, 'property_names', primitives=['dict'])

system.borrow_constraint(json, 'if', primitives=None)
system.borrow_constraint(json, 'then', primitives=None)
system.borrow_constraint(json, 'else', primitives=None)

system.borrow_constraint(json, 'all_of', primitives=None)
system.borrow_constraint(json, 'any_of', primitives=None)
system.borrow_constraint(json, 'one_of', primitives=None)
system.borrow_constraint(json, 'not', primitives=None)

system.borrow_constraint(json, 'format', primitives=['str'])


@system.constraint(['object'])
class HasAttrs(Constraint):
    description = "must have the following attrs: {value!r}"

    def __call__(self, instance, validate=False, partial=False):
        for attr in self.value:
            if not hasattr(instance, attr):
                self.fail()
        return instance


@system.constraint(['object', 'dict'])
class InstanceOf(Constraint):
    description = "must be an instance of: {value!r}"

    def __call__(self, instance, validate=False, partial=False):
        if isinstance(instance, self.value):
            return instance
        elif isinstance(instance, dict):
            return self.value(**instance)
        else:
            self.fail()

