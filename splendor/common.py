"""
Common operation factories.

Fundemental Issue:
    We want to create the operation right away, but we don't have some info:
        - MediaType
        - Path
    
    We can make a transient object that gets turned into the full Operation at registration
    We can make the Operation set itself up at registration
    We can demand the info needed at creation

"""
import functools, inspect
import types

from .schema import fields, Schematic, Undefined
from .operation import Operation, MediaOperation, Parameter, build_parameters, MediaType, FileType
from .util import get_schema


def decorator(func):
    """Allow to use decorator either with arguments or not."""

    def is_function(*args, **kw):
        return (
            len(args) == 1
            and len(kw) == 0
            and (inspect.isfunction(args[0]) or isinstance(args[0], type))
        )

    @functools.wraps(func)
    def func_wrapper(*args, **kw):
        if is_function(*args, **kw):
            return func(*args, **kw)

        def functor(user_func):
            return func(user_func, *args, **kw)

        return functor

    return func_wrapper


@decorator
def put(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=op.callable.__doc__ or f"add a new {m.name} item with a known url",
            tags=[m.name] + extra_tags,
            request_body={
                "description": f"{m.name} data that will become the new item",
                "arg": body_arg,
                "content": m.get_content_types(),
            },
            responses={"200": {"content": m.get_content_types()}},
            security={f"{m.name}_auth": {f"write:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)


@decorator
def patch(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=callable.__doc__ or f"update an {m.name} item",
            tags=[m.name] + extra_tags,
            request_body={
                "description": f"{m.name} item partial to update in the collection",
                "arg": body_arg,
                "content": m.get_content_types(),
            },
            responses={"200": {"content": m.get_content_types()}},
            security={f"{m.name}_auth": {f"write:{m.name}", f"read:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)


@decorator
def post(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=callable.__doc__ or f"create a new {m.name} item without a known url",
            tags=[m.name] + extra_tags,
            request_body={
                "description": f"{m.name} data that will become a new item",
                "arg": body_arg,
                "content": m.get_content_types(),
            },
            responses={"200": {"content": m.get_content_types()}},
            security={f"{m.name}_auth": {f"write:{m.name}", f"read:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)


@decorator
def delete(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=callable.__doc__ or f"delete an item in the collection",
            tags=[m.name] + extra_tags,
            responses={"200": {"description": "The resource was deleted successfully."}},
            security={f"{m.name}_auth": {f"write:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)


@decorator
def get(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=callable.__doc__ or f"get {m.name} item",
            summary=f"get {m.name} item",
            tags=[m.name] + extra_tags,
            responses={"200": {"content": m.get_content_types()}},
            security={f"{m.name}_auth": {f"read:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)


@decorator
def query(callable, cls=MediaOperation, media=None, extra_tags=[], body_arg="item", **kwargs):
    def register(op, app, options):
        m = media or op.media
        attrs = dict(
            operation_id=kwargs.get("operation_id", f"{m.name}_{callable.__name__}"),
            description=callable.__doc__ or "",
            summary=f"{m.name} query",
            tags=[m.name] + extra_tags,
            responses={
                "200": {
                    "description": f"a list of {m.name} items as results",
                    "content": m.get_result_content_types(),
                }
            },
            security={f"{m.name}_auth": {f"read:{m.name}"}},
            **kwargs,
        )
        op.update_schema_value(attrs)

    return cls(callable=callable, register_hook=register, **kwargs)

