import inspect, types, json
from collections.abc import Mapping, Sequence

import inflection
from flask import request, jsonify, make_response, current_app, abort
from werkzeug.exceptions import BadRequest, HTTPException
from werkzeug.routing import parse_rule
from werkzeug.wrappers import Response as WerkzeugResponse

from .schema import Configurable, Schematic, Undefined, Schema
from .schema import fields, ConstraintFailure


### Helpers ###
def get_schema(instance):
    if hasattr(instance, "__schema__"):
        return instance.__schema__
    else:
        return instance


def get_request_parameters(parameters, body, call_args):
    """
    Build kwargs and body values to send into the operator based on the request context.
    """
    kwargs = {}

    for p in parameters:
        # Get the parameter value
        if p.location == "path":
            value = call_args[p.name]
        elif p.location == "header":
            value = request.headers.get(p.name)
        elif p.location == "query":
            if p.explode:
                value = request.args.getlist(p.name)
            else:
                value = request.args.get(p.name, Undefined)
        elif p.location == "cookie":
            value = request.cookies.get(p.name)

        if value is Undefined:
            if not p.allow_empty_value:
                raise BadRequest(f"Parameter {p.name} is required.")
            continue

        # Run the value through the schema
        if p.schema:
            try:
                value = p.schema(value)
            except ValueError as e:
                raise BadRequest(f"Parameter {p.name} is invalid -- {e}: {e!r}")

        # Add to kwargs
        kwargs[inflection.underscore(p.name)] = value

    if body:
        if request.content_type in body.content:  # TODO: Handle media type ranges
            media_object = body.content[request.content_type]
        elif "*/*" in body.content:
            media_object = body.content["*/*"]
        else:
            raise BadRequest("Request requires a body.")  # TODO: explain more what is required
        try:
            data = request.get_data(as_text=True)
            kwargs[body.arg] = media_object.unserialize(data, request.content_type, partial=True)
        except ConstraintFailure as fail:
            raise BadRequest("Body media schema failure: %s" % fail)
        except ValueError:
            raise BadRequest("Unnable to unserialize request body, please check the content type.")

    return kwargs


### Schema ###
StyleField = fields.Enum(
    ["matrix", "label", "form", "simple", "spaceDelimited", "pipeDelimited", "deepObject"],
    default="simple",
)


class Encoding(Schematic):
    content_type = fields.String(required=True, default="application/json")
    headers = fields.Any(map=True)  # Should be Header later
    style = StyleField
    explode = fields.Boolean(default=False)
    allow_reserved = fields.Boolean(default=False)


class MediaType(Schematic):
    name = fields.String(
        internal=False,
        default=None,
        description="Application specific name to build response and body descriptions.",
    )

    schema = fields.SchemaField(required=True)
    example = fields.Dict()
    examples = fields.Dict(map=True)
    encoding = fields.InstanceOf(Encoding, map=True)

    factory = fields.Callable(internal=False, default=lambda x: x)
    content_types = fields.String(repeated=True, internal=False)
    serializers = fields.Duck(["serialize", "unserialize", "name"], map=True, internal=False)
    version = fields.String(internal=False, default=None)

    def __init__(self, schema=None, **kwargs):
        if isinstance(schema, type) and issubclass(schema, Schematic):
            name = inflection.dasherize(schema.__name__.lower())
            kwargs.setdefault("factory", schema)
            kwargs.setdefault("name", name)
            kwargs.setdefault("content_types", [])
            schema = schema.__schema__
        super().__init__(schema=schema, **kwargs)

    def unserialize(self, data, content_type="application/json", partial=False):
        if (
            content_type.endswith("+json")
            or content_type.startswith("application/json")
            or content_type == "*/*"
        ):
            data = self.schema(json.loads(data), partial=partial)
        else:
            raise RuntimeError(f"Unable to unserialize content type: {content_type!r}")

        if isinstance(data, Sequence):
            data = [self.factory(x) for x in data]
        else:
            data = self.factory(data)
        return data

    def serialize(self, data, content_type="application/json"):
        if (
            content_type.endswith("+json")
            or content_type.startswith("application/json")
            or content_type == "*/*"
        ):
            if isinstance(data, Sequence):
                data = [self.get_instance_data(x) for x in data]
            else:
                data = self.get_instance_data(data)
            return json.dumps(data)
        elif content_type.startswith("text/"):
            return data
        else:
            raise RuntimeError(f"Unable to serialize content type: {content_type!r}")

    def get_instance_data(self, instance):
        if hasattr(instance, "get_schema_value"):
            return instance.get_schema_value(ignore_default=True, ignore_internal=True)
        elif hasattr(instance, "__dict__"):
            return instance.__dict__
        return instance

    def get_content_types(self):
        """
        Returns a mapping of Content-Type string to media information from this instance.

        TODO: Return this right
        """
        content_types = self.content_types or ["application/json"]

        return {c: self for c in content_types}

    def get_result_content_types(self):
        """
        Returns a mapping of Content-Type string to media information to describe a list of results
        for this instance.
        """
        content_types = self.get_content_types()
        results = {}
        for mimetype, media_type in content_types.items():
            results[mimetype] = {"schema": {"type": "list", "items": self.schema}}
        return results

    @classmethod
    def from_schema(cls, schema, **kwargs):
        if schema is None:
            schema = Any
        elif hasattr(schema, "__schema__"):
            kwargs.setdefault("schema", schema.__schema__)
            kwargs.setdefault("factory", schema)
        else:
            kwargs.setdefault("schema", schema)
        return cls(**kwargs)


class Parameter(Schematic):
    name = fields.String(required=True)
    description = fields.String()
    location = fields.Enum(["path", "header", "query", "cookie"], default="path")
    deprecated = fields.Boolean(default=False)
    allow_empty_value = fields.Boolean(default=False)
    style = StyleField
    explode = fields.Boolean(default=False)
    allow_reserved = fields.Boolean(default=False)
    schema = fields.SchemaField()
    example = fields.Dict()
    examples = fields.Dict(map=True)
    content = fields.InstanceOf(MediaType)
    arg = fields.String(internal=False, default="body")

    def get_schema_value(self, **kwargs):
        schema = super().get_schema_value(**kwargs)
        schema["in"] = schema.get("location")
        return schema


class Header(Parameter):
    name = fields.String(required=False)
    location = fields.String(const="header")


class RequestBody(Schematic):
    description = fields.String()
    required = fields.Boolean(default=False)
    content = fields.InstanceOf(MediaType, map=True)
    arg = fields.String(internal=False, default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ServerVar(Schematic):
    enum = fields.String(repeated=True)
    default = fields.String(required=True)
    description = fields.String()


class Server(Schematic):
    url = fields.String(required=True)
    description = fields.String()
    variables = fields.InstanceOf(ServerVar, map=True)


class Link(Schematic):
    description = fields.String()
    operation_ref = fields.String()
    operation_id = fields.String()
    parameters = fields.String(map=True)
    request_body = fields.Any()
    server = fields.InstanceOf(Server)


class Response(Schematic):
    description = fields.String()
    headers = fields.InstanceOf(Header, map=True)
    content = fields.InstanceOf(MediaType, map=True)
    links = fields.InstanceOf(Link, map=True)


class Operation(Schematic):
    callable = fields.Callable(required=True, internal=False, default=None)
    register_hook = fields.Callable(required=False, internal=False, default=None)

    operation_id = fields.String(primary_key=True, default=None)
    method = fields.Enum(
        ["get", "put", "post", "delete", "options", "head", "patch", "trace"],
        default="get",
        required=True,
    )
    tags = fields.String(repeated=True)
    description = fields.String()
    summary = fields.String()
    parameters = fields.InstanceOf(Parameter, repeated=True)
    request_body = fields.InstanceOf(
        RequestBody,
        default=None,
        description="The request body applicable for this operation. The requestBody is only supported in HTTP methods where the HTTP 1.1 specification RFC7231 has explicitly defined semantics for request bodies. In other cases where the HTTP spec is vague, requestBody SHALL be ignored by consumers.",
    )
    responses = fields.InstanceOf(Response, map=True)
    callbacks = fields.Dict(map=True)  # This needs to be a PathObject
    deprecated = fields.Boolean(default=False)
    security = fields.List(map=True, items={"type": "str"})
    servers = fields.InstanceOf(Server, repeated=True)

    def __call__(self, **args):
        if not self.callable:
            abort(501, "Operation is not implemented.")

        try:
            params = get_request_parameters(self.parameters or [], self.request_body, args)
            response = self.callable(**params)
        except HTTPException as e:
            if str(e.code) in self.responses:
                return self.create_response(e.description, e.code)
            else:
                return e.get_response()

        if isinstance(response, WerkzeugResponse):
            return response
        elif isinstance(response, tuple):
            return self.create_response(*response)

        return self.create_response(response, 200)

    def __str__(self):
        return self.operation_id or "unnamed"

    def __repr__(self):
        return f"<{self.__class__.__name__} {self!s}>"

    @property
    def __name__(self):
        """For flask to register us."""
        return self.operation_id or "<unnamed>"

    @property
    def methods(self):
        """For flask registration."""
        return [self.method]

    def create_response(self, body, status_code, **kwargs):
        try:
            response = self.responses[str(status_code)]
        except KeyError:
            if "default" in self.responses:
                response = self.responses["default"]
            elif isinstance(body, dict):
                current_app.logger.error(
                    "Operation returned a dictionary, but we don't know how to return that."
                )
                return make_response(f"The server doesn't know how to return the response.", 501)
            elif status_code == 200:
                return make_response(body, 200, **kwargs)
            else:
                current_app.logger.error(
                    f"Unable to find response for status code: {status_code!r}"
                )
                return make_response(
                    f"Unable to find response for status code: {status_code!r}", 500
                )

        if not response.content:
            return make_response(body or "", status_code, **kwargs)

        content_type, content = self.find_desired_content_object_from_request(response.content)
        if content is None:
            return make_response(
                f"Not able to find acceptable content to return. Available types: {response.content.keys()}",
                406,
            )

        # TODO: Need to pick language, encoding / charsets
        # TODO: Need to figure out cache_control / if-modified

        if content.schema:
            response = make_response(content.serialize(body, content_type), status_code, **kwargs)
        else:
            response = make_response(body or "", status_code, **kwargs)

        response.headers["Content-Type"] = content_type
        return response

    def find_desired_content_object_from_request(self, content_objects):
        mimetypes = request.accept_mimetypes
        if not mimetypes.provided:
            best = next(iter(content_objects.keys()))
        else:
            best = mimetypes.best_match(content_objects.keys(), "application/json")
        return best, content_objects.get(best, None)

    def register(self, app, options, first_registration=False):
        if first_registration:
            self.setup(app, options)
            self.validate()
        path = options.get("url_prefix", "")
        methods = options.get("methods", None) or [self.method]

        app.add_url_rule(str(path), endpoint=self.operation_id, view_func=self, methods=methods)

    def setup(self, app, options):
        if self.register_hook:
            self.register_hook(self, app, options)

        if not self.parameters:
            if self.request_body:
                ignore = [self.request_body.arg]
            else:
                ignore = []
            self.parameters, unused = build_parameters(
                self.callable, path=str(options["url_prefix"]), ignore=ignore
            )

        if self.callable:
            if not self.responses:
                self.responses = build_responses(self.callable)

            if not self.operation_id:
                self.operation_id = self.callable.__name__

            if not hasattr(self, "summary"):
                self.summary = self.callable.__name__

        if options.get("collection"):
            collection = options["collection"]
            if not self.operation_id.startswith(collection.name):
                self.operation_id = f"{collection.name}:{self.operation_id}"

    def x_setup(self, app, options):
        """
        This doesn't make sense here, place in factory functions
        """
        assert self.callable, "Operation must have a callable by the time it gets registered"
        self.operation_id = self.operation_id or callable.__name__
        if not hasattr(self, "summary"):
            self.summary = inflection.titleize(self.callable.__name__)
        if self.responses is None:
            self.responses = build_responses(callable)
        if "parameters" not in props or "request_body" not in props:
            parameters, body = build_parameters(callable)
            props.setdefault("parameters", parameters)
            props.setdefault("request_body", body)
        return props


class MediaOperation(Operation):
    """
    An operation built around a media object.
    """

    media = fields.InstanceOf(MediaType, internal=False, default=None)

    def register(self, *args, **kwargs):
        super().register(*args, **kwargs)
        if not hasattr(self, "media"):
            raise RuntimeError(
                f"{self.__class__.__name__} object has no media by registration time. Did you forget to add a `media` property on the collection?"
            )


### Define ###
def define_operation(callable, method="get", **kwargs):
    return Operation(callable=callable, method=method.lower(), **kwargs)


def build_operation_from_callable(callable, **config):
    config.setdefault("summary", inflection.titleize(callable.__name__))
    if callable.__doc__:
        config.setdefault("description", callable.__doc__)
    config["parameters"] = config.get("parameters") or build_parameters(callable)
    config["responses"] = config.get("responses") or build_responses(callable)
    config["request_body"] = config.get("request_body") or build_body(callable)


def build_schema(obj):
    if isinstance(obj, dict) or isinstance(obj, fields.Schema):
        return obj

    elif hasattr(obj, "__schema__"):
        return obj.__schema__

    elif isinstance(obj, type):
        return {"type": obj.__name__}

    else:
        return {"type": obj}


def build_responses(callable):
    """
    TODO: Build out
    """
    signature = inspect.signature(callable)

    if signature.return_annotation is str:
        return {"200": {"content": {"text/plain": {"schema": {"type": "str"}}}}}

    if (
        signature.return_annotation is inspect.Signature.empty
        or signature.return_annotation is None
    ):
        return Undefined

    return {
        "200": {
            "content": {"application/json": {"schema": build_schema(signature.return_annotation)}}
        }
    }


def adjust_path_parameters(parameters, path):
    path_args = set()
    for converter, arguments, variable in parse_rule(path):
        if converter and variable:
            path_args.add(variable)

    for param in parameters:
        if param.name in path_args:
            param.location = "path"
            param.allow_empty_value = False
            if hasattr(param, "style"):
                del param.style


def build_parameters(callable, ignore=[], path=""):
    signature = inspect.signature(callable)

    path_args = set()
    for converter, arguments, variable in parse_rule(path):
        if converter and variable:
            path_args.add(variable)

    results = []
    for param in signature.parameters.values():
        if param.name == "self":
            continue

        if param.name in ignore:
            continue

        if param.annotation is not inspect.Parameter.empty:
            if isinstance(param.annotation, Parameter):
                p = param.annotation
                p.name = param.name
                if param.default is not inspect.Parameter.empty:
                    p.allow_empty_value = True
                results.append(p)
                continue
            else:
                param_schema = build_schema(param.annotation)
        elif param.default is not inspect.Parameter.empty:
            param_schema = build_schema(type(param.default))
        else:
            param_schema = {}

        if param.default is inspect.Parameter.empty:
            required = True
        else:
            required = False

        if param.name in path_args:
            results.append(
                {
                    "name": param.name,
                    "required": required,
                    "location": "path",
                    "allow_empty_value": not required,
                    "required": required,
                    "schema": param_schema or {"type": "str"},
                }
            )
            path_args.remove(param.name)
        else:
            results.append(
                {
                    "name": param.name,
                    "location": "query",
                    "allow_empty_value": not required,
                    "required": required,
                    "style": "simple",
                    "schema": param_schema,
                }
            )

        if path_args:
            raise RuntimeError(
                "build_parameters of %r expected the following path args, but weren't seen in the callable's parameter list: %r"
                % (callable, list(path_args))
            )

    return results, path_args


### Query String ###

# So this isn't working because QueryString is defined as the type, which converts it, but doesn't
# reflect itself in the openapi spec


def QueryString(
    style="simple",
    location="query",
    description=Undefined,
    deprecated=Undefined,
    allow_empty_value=Undefined,
    explode=Undefined,
    content=Undefined,
    arg=Undefined,
    **kwargs,
):
    return Parameter(
        style=style,
        location=location,
        description=description,
        deprecated=deprecated,
        allow_empty_value=allow_empty_value,
        explode=explode,
        content=content,
        arg=arg,
        schema=fields.String(**kwargs),
    )


class File:
    def __init__(self, data):
        self.data = data


class FileType(MediaType):
    content_types = ["application/octet-stream"]
    factory = File


f = FileType(schema=Schema({"type": "str", "format": "binary"}))

