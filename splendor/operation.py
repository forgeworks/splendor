import inspect, types, json
from collections.abc import Mapping, Sequence

import inflection
from flask import request, jsonify, make_response, current_app
from werkzeug.exceptions import BadRequest
from werkzeug.routing import parse_rule

from .schema import Configurable, Schematic, Undefined
from .schema import fields


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
        if request.content_type in body.content:                # TODO: Handle media type ranges
            media_object = body.content[request.content_type]
        elif '*/*' in body.content:
            media_object = body.content['*/*']
        else:
            raise BadRequest("Request requires a body.")        # TODO: explain more what is required
        try:
            body = media_object.unserialize(request.data, request.content_type)
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


class MediaType(Schematic):
    name = fields.String(export=False, default=None, description="Name used internally to build response and body descriptions.")
    schema = fields.SchemaField(required=True)
    example = fields.Dict()
    examples = fields.Dict(map=True)
    encoding = fields.InstanceOf(Encoding, map=True)
    factory = fields.Callable(export=False, default=lambda x: x)

    def unserialize(self, data, content_type='application/json'):
        if (content_type.endswith('+json') or
            content_type.startswith('application/json') or
            content_type == '*/*'):
                data = self.schema(json.loads(data))
        else:
            raise RuntimeError(f"Unable to unserialize content type: {content_type!r}")

        if isinstance(data, Sequence):
            data = [self.factory(x) for x in data]
        else:
            data = self.factory(data)
        return data

    def serialize(self, data, content_type='application/json'):
        if (content_type.endswith('+json') or
            content_type.startswith('application/json') or
            content_type == '*/*'):
                if isinstance(data, Sequence):
                    data = [self.get_instance_data(x) for x in data]
                else:
                    data = self.get_instance_data(data)
                return json.dumps(data)
        else:
            raise RuntimeError(f"Unable to serialize content type: {content_type!r}")

    def get_instance_data(self, instance):
        if hasattr(instance, 'get_schema_value'):
            return instance.get_schema_value(ignore_default=True, export=True)
        elif hasattr(instance, '__dict__'):
            return instance.__dict__
        return instance

    @classmethod
    def from_schema(cls, schema, **kwargs):
        if schema is None:
            schema = Any
        elif hasattr(schema, '__schema__'):
            kwargs.setdefault('schema', schema.__schema__)
            kwargs.setdefault('factory', schema)
        else:
            kwargs.setdefault('schema', schema)
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
    arg = fields.String(export=False, default='body')


class Header(Parameter):
    name = fields.String(required=False)
    location = fields.String(const="header")


class RequestBody(Schematic):
    description = fields.String()
    required = fields.Boolean(default=False)
    content = fields.InstanceOf(MediaType, map=True)
    arg = fields.String(export=False, default=None)


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
    callable = fields.Callable(required=True, export=False)
    operation_id = fields.String(primary_key=True, default=fields.uuid4hex)
    method = fields.Enum(["get", "put", "post", "delete", "options", "head", "patch", "trace"], default="get", required=True)
    tags = fields.String(repeated=True)
    description = fields.String()
    summary = fields.String()
    parameters = fields.InstanceOf(Parameter, repeated=True, default=None)
    body = fields.InstanceOf(RequestBody, default=None)
    responses = fields.InstanceOf(Response, map=True)
    callbacks = fields.Dict(map=True)                   # This needs to be a PathObject
    deprecated = fields.Boolean(default=False)
    security = fields.List(map=True, items={'type': 'str'})
    servers = fields.InstanceOf(Server, repeated=True)

    def __init__(self, callable=None, **kwargs):
        if callable:
            kwargs.setdefault('summary', inflection.titleize(callable.__name__))
            #if 'body' not in kwargs:
            #    kwargs['body'] = build_body(callable)
            if 'responses' not in kwargs:
                kwargs['responses'] = build_responses(callable)
        super().__init__(callable=callable, **kwargs)

    def __new__(cls, callable=None, **kwargs):
        """Makes the class able to be used as a decorator which accepts optional overriding
           keyword arguments."""
        if callable is None:
            return lambda x: cls(x, **kwargs)
        else:
            return super().__new__(cls)

    def __str__(self):
        return self.operation_id

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.operation_id}>'

    def __call__(self, **args):
        try:
            params, body = get_request_parameters(self.parameters or [], self.body, args)
            if self.body and self.body.arg:
                params[self.body.arg] = body

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
            elif isinstance(body, dict):
                current_app.logger.error('Operation returned a dictionary, but we don\'t know how to return that.')
                return make_response(f'The server doesn\'t know how to return the response.', 501)
            elif status_code == 200:
                return make_response(body, 200, **kwargs)
            else:
                current_app.logger.error(f'Unable to find response for status code: {status_code!r}')
                return make_response(f'Unable to find response for status code: {status_code!r}', 500)

        if not response.content:
            return make_response(body or '', status_code, **kwargs)

        content_type, content = self.find_desired_content_object_from_request(response.content)
        if content is None:
            return make_response(f'Not able to find acceptable content to return. Available types: {response.content.keys()}', 406)

        if content.schema:
            response = make_response(content.serialize(body, content_type), status_code, **kwargs)
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
        
        if self.parameters is None and self.callable:
            self.parameters = build_parameters(self.callable, path=str(path))
        else:
            adjust_path_parameters(self.parameters, str(path))

    def bind(self, collection):
        """
        Binds the operation to a collection, the callable will be injected with 'self' assigned to the
        collection, and the schema.
        """
        self.callable = types.MethodType(self.callable, obj)


class MediaOperation(Operation):
    """
    An operation that builds dynamically around a media type object.
    """
    media_type = fields.InstanceOf(MediaType, export=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()

    def build(self):
        


### Define ###
def define_operation(callable, method='get', **kwargs):
    return Operation(callable=callable, method=method.lower(), **kwargs)


def build_operation_from_callable(callable, **config):
    config.setdefault('summary', inflection.titleize(callable.__name__))
    if callable.__doc__:
        config.setdefault('description', callable.__doc__)
    config['parameters'] = config.get('parameters') or build_parameters(callable)
    config['responses'] = config.get('responses') or build_responses(callable)
    config['body'] = config.get('body') or build_body(callable)


def build_schema(obj):
    if isinstance(obj, dict) or isinstance(obj, fields.Schema):
        return obj
    
    elif hasattr(obj, '__schema__'):
        return obj.__schema__
    
    else:
        return {'type': obj}


def build_responses(callable):
    signature = inspect.signature(callable)

    if signature.return_annotation is inspect.Signature.empty or signature.return_annotation is None:
        return Undefined

    return {'200': {'content': {'application/json': {'schema': build_schema(signature.return_annotation)}}}}


def adjust_path_parameters(parameters, path):
    path_args = set()
    for converter, arguments, variable in parse_rule(path):
        if converter and variable:
            path_args.add(variable)
    
    for param in parameters:
        if param.name in path_args:
            param.location = 'path'
            param.allow_empty_value = False
            if hasattr(param, 'style'):
                del param.style


def build_parameters(callable, ignore=[], path=''):
    signature = inspect.signature(callable)

    path_args = set()
    for converter, arguments, variable in parse_rule(path):
        if converter and variable:
            path_args.add(variable)

    results = []
    for param in signature.parameters.values():
        if param.name == 'self':
            continue

        if param.name in ignore:
            continue

        if param.annotation is not inspect.Parameter.empty:
            if isinstance(param.annotation, Parameter):
                p = param.annotation
                p.name = param.name
                results.append(p)
                continue
            else:
                param_schema = build_schema(param.annotation)
        else:
            param_schema = {}

        if param.default is inspect.Parameter.empty:
            required = True
        else:
            required = False

        if param.name in path_args:
            results.append({'name': param.name,
                            'location': 'path',
                            'allow_empty_value': False,
                            'schema': param_schema})
            path_args.remove(param.name)
        else:
            results.append({'name': param.name,
                            'location': 'query',
                            'allow_empty_value': True,
                            'style': 'matrix',
                            'schema': param_schema})

        if path_args:
            raise RuntimeError("build_parameters expected the following path args, but weren't seen in the callable's parameter list: %r" % list(path_args))

    return results



### Query String ###
def QueryString(style='matrix', 
                location='query', 
                description=Undefined, 
                deprecated=Undefined,
                allow_empty_value=Undefined,
                explode=Undefined,
                content=Undefined,
                arg=Undefined, **kwargs):
    return Parameter(style=style,
                     location=location,
                     description=description,
                     deprecated=deprecated,
                     allow_empty_value=allow_empty_value,
                     explode=explode,
                     content=content,
                     arg=arg,
                     schema=fields.String(**kwargs))