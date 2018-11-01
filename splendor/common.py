"""
Common operation factories.
"""
import types
from functools import wraps

from .schema import fields, Schematic, Undefined
from .operation import Operation, Parameter, build_parameters, MediaType
from .util import get_schema


class OperationTemplate(Schematic):
    callable = fields.Callable()
    template = fields.Callable()
    kwargs = fields.Dict()

    def build(self, binding, schema, **kwargs):
        kwargs = dict(self.kwargs, schema=schema, **kwargs)
        return self.template(types.MethodType(self.callable, binding), **kwargs)


def operation_template(fn):
    "Decorates a function to act as a template, which takes a callable and returns an operation."
    def wrapper(callable, schema=Undefined, **kwargs):
        if schema is Undefined:
            return OperationTemplate(callable=callable, 
                                     template=fn,
                                     kwargs=kwargs)
        if isinstance(schema, Schematic):
            return fn(callable, schema=schema.__schema__, factory=schema, **kwargs)
        else:
            return fn(callable, schema=schema, **kwargs)

    # This stuff just lets you do @put or @put(kwarg=value)
    def decorator(callable=None, **kwargs):
        if not kwargs:
            return wrapper(callable)

        def inner_wrapper(callable):
            return wrapper(callable, **kwargs)
        return inner_wrapper

    return decorator


@operation_template
def put(callable, schema=None, factory=Undefined, name=None, **kwargs):
    parameters = build_parameters(callable, ignore=['item'], path="<id>")

    media = MediaType.from_schema(schema)
    name = name or media.schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'put_{name}',
        description = callable.__doc__ or f'PUT {name} item',
        method = "put",
        tags = [name, 'put'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        body = {
            'description': f'{name} item to add to the collection',
            'arg': 'item',
            'content': {
                '*/*': media
            }
        },
        responses = {
            "200": {
                "description": f'{name} item that was added.',
                "content": {
                    'application/json': {
                        'schema': schema
                    }
                }
            }
        },
        security = {
            f'{name}_auth': {
                'write:{name}',
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op


@operation_template
def get(callable, schema=None, name=None, **kwargs):
    parameters = build_parameters(callable, path="<id>")

    schema = get_schema(schema)
    name = name or schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'get_{name}',
        description = callable.__doc__ or f'GET {name} item by id',
        method = "get",
        tags = [name, 'get'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        responses = {
            "200": {
                "description": f'{name} item found in the datastore.',
                "content": {
                    'application/json': {
                        'schema': schema
                    }
                }
            },
            "404": {
                "description": f'{name} item cannot be found.',
            }
        },
        security = {
            f'{name}_auth': {
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op

@operation_template
def post(callable, schema=None, factory=Undefined, name=None, **kwargs):
    parameters = build_parameters(callable, ignore=['item'])

    media = MediaType.from_schema(schema)
    name = name or media.schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'post_{name}',
        description = callable.__doc__ or f'POST {name} item',
        method = "post",
        tags = [name, 'post'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        body = {
            'description': f'{name} item to add to the collection',
            'arg': 'item',
            'content': {
                '*/*': media
            }
        },
        responses = {
            "200": {
                "description": f'{name} item that was added.',
                "content": {
                    'application/json': {
                        'schema': schema
                    }
                }
            }
        },
        security = {
            f'{name}_auth': {
                'write:{name}',
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op


@operation_template
def patch(callable, schema=None, factory=Undefined, name=None, **kwargs):
    parameters = build_parameters(callable, ignore=['item'], path="<id>")

    media = MediaType.from_schema(schema)
    name = name or media.schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'patch_{name}',
        description = callable.__doc__ or f'PATCH {name} item',
        method = "patch",
        tags = [name, 'patch'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        body = {
            'description': f'{name} item partial to update in the collection',
            'arg': 'item',
            'content': {
                '*/*': media
            }
        },
        responses = {
            "200": {
                "description": f'Updated {name} item.',
                "content": {
                    'application/json': {
                        'schema': schema
                    }
                }
            }
        },
        security = {
            f'{name}_auth': {
                'write:{name}',
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op


@operation_template
def delete(callable, schema=None, name=None, **kwargs):
    parameters = build_parameters(callable, path="<id>")

    schema = get_schema(schema)
    name = name or schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'delete_{name}',
        description = callable.__doc__ or f'DELETE {name} item by key',
        method = "delete",
        tags = [name, 'delete'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        responses = {
            "200": {
                "description": f'The {name} item was deleted.'
            }
        },
        security = {
            f'{name}_auth': {
                'write:{name}',
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op
    

@operation_template
def listing(callable, schema=None, name=None, **kwargs):
    parameters = build_parameters(callable)

    schema = get_schema(schema)
    name = name or schema.name.split('.')[-1].lower()

    attrs = dict(
        callable = callable,
        operation_id = f'list_{name}',
        description = callable.__doc__ or f'Get a list of {name} items',
        method = "get",
        tags = [name, 'listing'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
        responses = {
            "200": {
                "description": f'A list of {name} item results.',
                "content": {
                    'application/json': {
                        'schema': {
                            'type': 'list',
                            'items': schema
                        }
                    }
                }
            }
        },
        security = {
            f'{name}_auth': {
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op

