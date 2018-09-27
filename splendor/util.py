import inspect
from werkzeug.routing import parse_rule
from .schema import fields

__all__ = ['merge_paths', 'get_schema', 'build_parameters']


def merge_paths(*dicts):
    """
    Merges dicts, stupidly.  TODO: Make smart
    """
    result = {}
    for d in dicts:
        if isinstance(d, fields.Field):
            d = d.default
        result.update(d)
    return result

def get_schema(instance):
    if hasattr(instance, '__schema__'):
        return instance.__schema__
    return instance

def build_parameters(signature, ignore={}, path=''):
    from .operation import Parameter

    if callable(signature):
        signature = inspect.signature(signature)

    path_args = set()
    for converter, arguments, variable in parse_rule(path):
        if converter and variable:
            path_args.add(variable)

    results = []
    for param in signature.parameters.values():
        if param.name in ignore:
            continue

        if param.name == 'self':
            continue

        if param.annotation is not inspect.Parameter.empty:
            if isinstance(param.annotation, Parameter):
                p = param.annotation
                p.name = param.name
                results.append(p)
                continue
            elif isinstance(param.annotation, dict) or isinstance(param.annotation, fields.Schema):
                param_schema = param.annotation
            elif hasattr(param.annotation, '__schema__'):
                param_schema = param.annotation.__schema__
            else:
                param_schema = {'type': param.annotation}
        else:
            param_schema = {}

        if param.default is inspect.Parameter.empty:
            required = True
        else:
            required = False

        if param.name in path_args:
            results.append({'name': param.name,
                            'location': 'path',
                            'required': True,
                            'schema': param_schema})
            path_args.remove(param.name)
        else:
            results.append({'name': param.name,
                            'location': 'query',
                            'required': required,
                            'style': 'matrix',
                            'schema': param_schema})

        if path_args:
            raise RuntimeError("build_parameters expected the following path args, but weren't seen in the callable's parameter list: %r" % list(path_args))

    return results
