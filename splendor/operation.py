import inspect
import inflection
from .schema import Configurable, Schematic, Undefined
from .schema import fields

from flask import request, jsonify, make_response
from werkzeug.exceptions import BadRequest


### Helpers ###
def get_schema(instance):
    if hasattr(instance, '__schema__'):
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
        if p.location == 'path':
            value = call_args[p.name]
        elif p.location == 'header':
            value = request.headers.get(p.name)
        elif p.location == 'query':
            if p.explode:
                value = request.args.getlist(p.name)
            else:
                value = request.args.get(p.name, Undefined)
        elif p.location == 'cookie':
            value = request.cookies.get(p.name)

        if value is Undefined:
            if p.required:
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
        if request.content_type in body.content:                # TODO: Handle media type ranges
            media_object = body.content[request.content_type]
        elif '*/*' in body.content:
            media_object = body.content['*/*']
        else:
            raise BadRequest("Request requires a body.")        # TODO: explain more what is required
        try:
            body = media_object.schema.unserialize(request.data, request.content_type)
        except ValueError:
            raise BadRequest("Unnable to unserialize request body, please check the content type.")

    return kwargs, body


### Schema ###
StyleField = fields.Enum(["matrix", "label", "form", "simple", "spaceDelimited", "pipeDelimited", "deepObject"], default="simple")

class Encoding(Schematic):
    content_type = fields.String(required=True, default='application/json')
    headers = fields.Any(map=True)          # Should be Header later
    style = StyleField
    explode = fields.Boolean(default=False)
    allow_reserved = fields.Boolean(default=False)


class MediaObject(Schematic):
    schema = fields.SchemaField(required=True)
    example = fields.Dict()
    examples = fields.Dict(map=True)
    encoding = fields.InstanceOf(Encoding)


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
    content = fields.InstanceOf(MediaObject)
    arg = fields.String(export=False, default='body')


class Header(Parameter):
    name = fields.String(required=False)
    location = fields.String(const="header")


class RequestBody(Schematic):
    description = fields.String()
    required = fields.Boolean(default=False)
    content = fields.InstanceOf(MediaObject, map=True)


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
    content = fields.InstanceOf(MediaObject, map=True)
    links = fields.InstanceOf(Link, map=True)


class Operation(Schematic):
    callable = fields.Callable(required=True)
    operation_id = fields.String(primary_key=True, default=fields.uuid4hex)
    method = fields.Enum(["get", "put", "post", "delete", "options", "head", "patch", "trace"], default="get", required=True)
    tags = fields.String(repeated=True)
    description = fields.String()
    summary = fields.String()
    parameters = fields.InstanceOf(Parameter, repeated=True, default=[])
    body = fields.InstanceOf(RequestBody, default=None)
    responses = fields.InstanceOf(Response, map=True)
    callbacks = fields.Dict(map=True)                   # This needs to be a PathObject
    deprecated = fields.Boolean(default=False)
    security = fields.List(map=True, items={'type': 'str'})
    servers = fields.InstanceOf(Server, repeated=True)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.operation_id}>'

    def __call__(self, **args):
        try:
            params, body = get_request_parameters(self.parameters or [], self.body, args)
            arg = getattr(self.body, 'arg', None)
            if arg:
                params[arg] = body
            result = self.callable(**params)
            return self.create_response(result, 200)
        except BadRequest as e:
            r = jsonify(str(e))
            r.status_code=400
            return r

    def create_response(self, result, status_code=200, **kwargs):
        if result is None:
            return ('', status_code)

        try:
            response = self.responses[str(status_code)]
        except:
            response = self.responses['default']

        content = response.content['application/json']
        if content.schema:
            response = make_response( content.schema.serialize(result, 'application/json'), status_code, **kwargs)
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            response = make_response( result, status_code, **kwargs)
            response.headers['Content-Type'] = 'application/json'
            return response


    def register(self, api, path, methods=None, **kwargs):
        methods = methods or [self.method]
        api.add_url_rule(str(path), endpoint=self.operation_id, view_func=self, methods=methods)


class PathItem(Schematic):
    summary = fields.String()
    description = fields.String()
    get = fields.InstanceOf(Operation)
    put = fields.InstanceOf(Operation)
    delete = fields.InstanceOf(Operation)
    options = fields.InstanceOf(Operation)
    head = fields.InstanceOf(Operation)
    patch = fields.InstanceOf(Operation)
    trace = fields.InstanceOf(Operation)
    servers = fields.InstanceOf(Server, repeated=True)
    parameters = fields.InstanceOf(Parameter, repeated=True)



### Define ###

def define_operation(callable, method='get', **kwargs):
    return Operation(callable=callable, method=method.lower(), **kwargs)


