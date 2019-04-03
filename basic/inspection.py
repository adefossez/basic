import inspect
from inspect import Parameter
import typing

from . import types, struct

POSSIBLE_TYPES = [
    types.Bool, types.Int, types.Float, types.Tuple, types.List, types.Dict,
    types.Path, types.Datetime, types.Str, types.Bytes
]


class ClassType(struct.StructType):
    def __init__(self,
                 *,
                 convert_klass,
                 args_name=None,
                 kwargs_name=None,
                 **kwargs):
        super(ClassType, self).__init__(**kwargs)
        self._convert_class = convert_klass
        self._args_name = args_name
        self._kwargs_name = kwargs_name

    def get_args_kwargs(self, value):
        args = []
        kwargs = dict(value._fields)
        if self._args_name is not None:
            args = kwargs.pop(self._args_name)
        if self._kwargs_name is not None:
            kwargs.update(kwargs.pop(self._kwargs_name))
        return args, kwargs

    def _convert(self, value):
        args, kwargs = self.get_args_kwargs(value)
        return self._convert_class(*args, **kwargs)

    def convert(self, value):
        return convert(self, value)

    def _apply(self, value, func):
        if isinstance(value, struct.Struct):
            kwargs = {
                name: self.field(name).apply(field, func)
                for name, field in value._fields.items()
            }
            return func(self, self._factory(**kwargs))
        else:
            return func(self, value)

    def __eq__(self, other):
        if not super(ClassType, self).__eq__(other):
            return False
        return self._convert_class == other._convert_class


def _class_struct(convert_klass, args_name, kwargs_name, schema):
    klass = struct.Struct
    factory = struct._WithAttrsFactory(klass, _schema=schema)
    if convert_klass is not None:
        name = convert_klass.__name__ + "Struct"
    else:
        name = "ClassStruct"
    type_ = ClassType(
        convert_klass=convert_klass,
        args_name=args_name,
        kwargs_name=kwargs_name,
        schema=schema,
        klass=klass,
        factory=factory,
        name=name)
    return type_


def _parameter_type(parameter, extra=None):
    type_ = None
    default = types.MISSING

    if extra is not None:
        if isinstance(extra, types.BasicType):
            return extra
        elif isinstance(extra, type):
            type_ = extra
        else:
            default = extra
    else:
        if parameter.default is not Parameter.empty:
            default = parameter.default

    if parameter.annotation is not Parameter.empty:
        type_ = parameter.annotation
    elif default not in [None, types.MISSING]:
        type_ = type(default)
    if parameter.kind == Parameter.VAR_KEYWORD:
        if type_ is None:
            type_ = types.Dict[types.Any]
        if default is types.MISSING:
            type_ = type_.empty
    elif parameter.kind == Parameter.VAR_POSITIONAL:
        if type_ is None:
            type_ = types.List[types.Any]
        if default is types.MISSING:
            type_ = type_.empty
    basic_type = guess_type(type_)
    if default is types.MISSING:
        basic_type = basic_type.missing
    else:
        basic_type = basic_type.default(default)
    return basic_type


def _init_schema(init, klass=None, extra={}):
    signature = inspect.signature(init)
    fields = {}
    args_name = None
    kwargs_name = None

    for name, parameter in list(signature.parameters.items())[1:]:
        if parameter.kind == Parameter.VAR_KEYWORD:
            kwargs_name = name
        elif parameter.kind == Parameter.VAR_POSITIONAL:
            args_name = name
        field_type = _parameter_type(parameter, extra.get(name))
        fields[name] = field_type

    type_ = _class_struct(
        convert_klass=klass,
        args_name=args_name,
        kwargs_name=kwargs_name,
        schema=fields)
    return type_


def class_type(klass, **extra):
    return _init_schema(klass.__init__, klass, extra=extra).empty


def guess_type(value):
    if isinstance(value, types.BasicType):
        return value
    if value is None:
        return types.Any.none
    if isinstance(value, typing._GenericAlias):
        type_ = guess_type(value.__origin__)
        if value.__args__:
            type_ = type_.__getitem__(
                tuple(guess_type(arg) for arg in value.__args__))
        return type_
    elif isinstance(value, typing._SpecialForm):
        if value is typing.Any:
            type_ = types.Any
        else:
            raise ValueError(f"Unsupported special form {value}")
        return type_
    elif isinstance(value, type):
        type_ = value
    else:
        type_ = type(value)

    basic_type = None
    for possible_type in POSSIBLE_TYPES:
        if issubclass(type_, possible_type.klass):
            basic_type = possible_type
            break

    if basic_type is None:
        basic_type = class_type(type_)

    if not isinstance(value, type):
        basic_type = basic_type.default(value)
    return basic_type


def convert(basic_type, value):
    def _transform(sub_type, sub_value):
        if (isinstance(sub_type, ClassType)
                and isinstance(sub_value, struct.Struct)
                and sub_type._convert_class is not None):
            return sub_type._convert(sub_value)
        return sub_value

    return basic_type.apply(value, _transform)


def lambda_guess_struct(__name=None, **schema):
    schema = {name: guess_type(value) for name, value in schema.items()}
    return struct.lambda_struct(**schema)


def guess_struct(__name, __bases=(), **schema):
    schema = {name: guess_type(value) for name, value in schema.items()}
    return struct.lambda_struct(__name, __bases, **schema)
