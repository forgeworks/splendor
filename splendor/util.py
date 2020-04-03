import inspect
from .schema import fields

__all__ = ['merge_paths', 'get_schema']


def merge_paths(*dicts):
    """
    Merges dicts, stupidly.  TODO: Make smart
    """
    result = {}
    for d in dicts:
        if isinstance(d, fields.Field):
            d = d.get_default(None)
        else:
            result.update(d)
    return result

def get_schema(instance):
    if hasattr(instance, '__schema__'):
        return instance.__schema__
    return instance

