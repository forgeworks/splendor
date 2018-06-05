"""
Common operation factories.
"""
import types
import inspect
from functools import wraps

from .schema import fields, Schematic, Undefined
from .operation import Operation

def get_schema(instance):
    if hasattr(instance, '__schema__'):
        return instance.__schema__
    return instance


class CollectionOperation(Schematic):
    callable = fields.Callable()
    template = fields.Callable()
    kwargs = fields.Dict()

    def build(self, collection, **kwargs):
        kwargs = dict(self.kwargs, **kwargs)
        if collection.schema:
            kwargs.setdefault('schema', collection.schema)
        return self.template(types.MethodType(self.callable, collection), **kwargs)

    def register(self, api, path, **kwargs):
        api.add_url_rule(str(path), endpoint=self.operation_id, view_func=self.__call__, methods=methods)


def build_parameters(signature, ignore={}, path=0):
    results = []
    for i, param in enumerate(signature.parameters.values()):
        if param.name in ignore:
            continue

        if param.name == 'self':
            continue

        if param.annotation is not inspect.Parameter.empty:
            if isinstance(param.annotation, dict) or isinstance(param.annotation, fields.Schema):
                param_schema = param.annotation
            elif hasattr(param.annotation, '__schema__'):
                param_schema = param.annotation.__schema__
            else:
                param_schema = {'type': param.annotation}
        else:
            param_schema = {}

        if param.default is not inspect.Parameter.empty:
            required = bool(param.default)
        else:
            required = Undefined

        if i <= path:
            results.append({'name': param.name,
                            'location': 'path',
                            'required': True,
                            'schema': param_schema})
        else:
            results.append({'name': param.name,
                            'location': 'query',
                            'required': required,
                            'style': 'matrix',
                            'schema': param_schema})

    return results


def operation_template(fn):
    "Decorates a function to act as a template, which takes a callable and returns an operation."
    def wrapper(callable, **kwargs):
        sig = inspect.signature(callable)
        fn_parameters = list(sig.parameters.values())
        if fn_parameters[0].name == 'self':
            return CollectionOperation(callable=callable, 
                                       template=fn,
                                       kwargs=kwargs)
        return fn(callable, **kwargs)

    def decorator(callable=None, **kwargs):
        def inner_wrapper(callable):
            return wrapper(callable, **kwargs)
        if not kwargs:
            return wrapper(callable)
        else:
            return inner_wrapper
    return decorator


@operation_template
def put(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), ignore=['item'], path=1)
    schema = get_schema(schema)
    name = schema.name.lower()

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
                'application/json': {
                    'schema': schema,
                    'examples': schema.examples or Undefined
                }
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
def get(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), path=1)

    schema = get_schema(schema)
    name = schema.name.lower()

    attrs = dict(
        callable = callable,
        operation_id = f'get_{name}',
        description = callable.__doc__ or f'GET {name} item by key',
        method = "get",
        tags = [name, 'get'] + kwargs.get('extra_tags', []),
        parameters = parameters + kwargs.get('extra_parameters', []),
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
                'read:{name}'
            }
        }
    , **kwargs)
    op = Operation(**attrs)
    op.__name__ = op.operation_id
    return op

@operation_template
def post(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), ignore=['item'])

    schema = get_schema(schema)
    name = schema.name.lower()

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
                'application/json': {
                    'schema': schema,
                    'examples': schema.examples or Undefined
                }
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
def patch(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), ignore=['item'], path=1)

    schema = get_schema(schema)
    name = schema.name.lower()

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
                'application/json': {
                    'schema': schema,
                    'examples': schema.examples or Undefined
                }
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
def delete(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), path=1)

    schema = get_schema(schema)
    name = schema.name.lower()

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
def listing(callable, schema=None, **kwargs):
    parameters = build_parameters(inspect.signature(callable), path=-1)

    schema = get_schema(schema)
    name = schema.name.lower()

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

