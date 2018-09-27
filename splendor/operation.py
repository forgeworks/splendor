import inspect, types
import inflection
from .schema import Configurable, Schematic, Undefined
from .schema import fields

from flask import request, jsonify, make_response, current_app
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
    callable = fields.Callable(required=True, export=False)
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

    def __str__(self):
        return self.operation_id

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.operation_id}>'

    def __call__(self, **args):
        try:
            params, body = get_request_parameters(self.parameters or [], self.body, args)
            arg = getattr(self.body, 'arg', None)
            if arg:
                params[arg] = body

            result = self.callable(**params)
            
            if isinstance(result, int):
                result = str(result)

            if isinstance(result, tuple):
                return self.build_response(*result)
            elif isinstance(result, str) and result in self.responses:
                return self.build_response('', result)
            else:
                return self.build_response(result, 200)
        except BadRequest as e:
            r = jsonify(str(e))
            r.status_code=400
            return r

    def build_response(self, body, status_code, **kwargs):
        try:
            response = self.responses[str(status_code)]
        except KeyError:
            if 'default' in self.responses:
                response = self.responses['default']
            elif status_code == 200:
                return make_response(body, 200, **kwargs)
            else:
                current_app.logger.error(f'Unnable to find response for status code: {status_code!r}')
                return make_response(f'Unnable to find response for status code: {status_code!r}', 500)

        if not response.content:
            return make_response(body or '', status_code, **kwargs)

        content_type, content = self.find_desired_content_object_from_request(response.content)
        if content is None:
            return make_response(f'Not able to find acceptable content to return. Available types: {response.content.keys()}', 406)

        if content.schema:
            response = make_response(content.schema.serialize(body, content_type), status_code, **kwargs)
        else:
            response = make_response(body or '', status_code, **kwargs)

        response.headers['Content-Type'] = content_type
        return response

    def find_desired_content_object_from_request(self, content_objects):
        mimetypes = request.accept_mimetypes
        best = mimetypes.best_match(content_objects.keys(), 'application/json')
        return best, content_objects.get(best, None)

    def register(self, app, options, first_registration=False):
        path = options.get('url_prefix', '')
        methods = options.get('methods', None) or [self.method]
        app.add_url_rule(str(path), endpoint=self.operation_id, view_func=self, methods=methods)

    def bind(self, collection):
        """
        Binds the operation to a collection, the callable will be injected with 'self' assigned to the
        collection, and the schema.
        """
        self.callable = types.MethodType(self.callable, obj)


### Define ###

def define_operation(callable, method='get', **kwargs):
    return Operation(callable=callable, method=method.lower(), **kwargs)


