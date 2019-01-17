import base64
from collections import defaultdict
import copy
import datetime
import functools
import itertools
import pathlib

from .utils import _Keyword


class DefaultValue(_Keyword):
    pass


class Target(_Keyword):
    pass


REQUIRED = DefaultValue("REQUIRED")
EMPTY = DefaultValue("EMPTY")
MISSING = DefaultValue("MISSING")
NOW = DefaultValue("NOW")

JSON = Target("JSON")
BSON = Target("BSON")


class BasicType:
    def __init__(self, *, klass, default=REQUIRED):
        self._default = default
        self._klass = klass

    def _change(self, **change):
        new_type = copy.copy(self)
        for name, value in change.items():
            setattr(new_type, "_" + name, value)
        return new_type

    def default(self, default):
        return self._change(default=default)

    @property
    def none(self):
        return self.default(None)

    @property
    def empty(self):
        return self.default(EMPTY)

    @property
    def missing(self):
        return self.default(MISSING)

    @property
    def required(self):
        return self.default(REQUIRED)

    @property
    def klass(self):
        return self._klass

    @property
    def name(self):
        return self.klass.__name__.capitalize()

    def new(self, *args, **kwargs):
        return self.klass(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.new(*args, **kwargs)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        return (self._default, self._klass) == (other._default, other._klass)

    def __ne__(self, other):
        return not (self == other)

    def default_value(self):
        if self._default is REQUIRED:
            raise ValueError("BasicType has no default value")
        elif self._default is EMPTY:
            return self.new()
        elif self._default is MISSING:
            raise ValueError("Missing can only be used inside a struct")
        elif isinstance(self._default, DefaultValue):
            raise ValueError(f"Invalid default value {self._default}")
        return self._default

    @property
    def has_default(self):
        return self._default is not REQUIRED

    def _to_jsony(self, value, target):
        raise NotImplementedError()

    def _from_jsony(self, jsony, source):
        raise NotImplementedError()

    def to_jsony(self, value, target):
        if value is None:
            return None
        return self._to_jsony(value, target=target)

    def from_jsony(self, jsony, source):
        if jsony is None:
            return None
        return self._from_jsony(jsony, source=source)

    def from_json(self, json):
        return self.from_jsony(json, source=JSON)

    def from_bson(self, bson):
        return self.from_jsony(bson, source=BSON)

    def to_json(self, json):
        return self.to_jsony(json, target=JSON)

    def to_bson(self, bson):
        return self.to_jsony(bson, target=BSON)

    def apply(self, value, func):
        if value is None:
            return func(self, value)
        return self._apply(value, func)

    def _apply(self, value, func):
        return func(self, value)

    def __repr__(self):
        name = self.name
        if self._default is REQUIRED:
            return name
        elif isinstance(self._default, DefaultValue):
            return f"{name}.{str(self._default).lower()}"
        elif self._default is None:
            return f"{name}.none"
        else:
            return f"{name}.default({self._default!r})"


def validate_class(value, klass):
    if not isinstance(value, klass):
        raise ValueError(f"Expected value of type {klass!r} but got {value!r}")
    return value


class BuiltinType(BasicType):
    def _to_jsony(self, value, target):
        return validate_class(value, self.klass)

    def _from_jsony(self, jsony, source):
        return validate_class(jsony, self.klass)


class _Any(BuiltinType):
    def __init__(self, *, klass=object, **kwargs):
        super(_Any, self).__init__(klass=object, **kwargs)

    def new(self, value):
        return value

    @property
    def name(self):
        return "Any"


class _Float(BasicType):
    def __init__(self, *, klass=float, **kwargs):
        super(_Float, self).__init__(klass=klass, **kwargs)

    def _to_jsony(self, value, target):
        return float(validate_class(value, (float, int)))

    def _from_jsony(self, jsony, source):
        return float(validate_class(jsony, (float, int)))


class _Datetime(BasicType):
    def __init__(self, *, klass=datetime.datetime, **kwargs):
        super(_Datetime, self).__init__(klass=klass, **kwargs)

    @property
    def now(self):
        return self._change(default=NOW)

    def default_value(self):
        if self._default is NOW:
            return datetime.datetime.now()
        else:
            return super(_Datetime, self).default_value()

    def _from_jsony(self, jsony, source):
        if source is JSON:
            return datetime.datetime.fromisoformat(jsony)
        elif source is BSON:
            return jsony
        else:
            raise ValueError(f"Unsupported source {source}")

    def _to_jsony(self, value, target):
        if target is JSON:
            return str(value)
        elif target is BSON:
            return value
        else:
            raise ValueError(f"Unsupported target {target}")


class _Path(BasicType):
    def __init__(self, *, klass=pathlib.Path, **kwargs):
        super(_Path, self).__init__(klass=klass, **kwargs)

    def _from_jsony(self, jsony, source):
        return self.new(jsony)

    def _to_jsony(self, value, target):
        return str(value)


class _Bytes(BasicType):
    def __init__(self, *, klass=bytes, **kwargs):
        super(_Bytes, self).__init__(klass=klass, **kwargs)

    def _from_jsony(self, jsony, source):
        if source is JSON:
            return base64.b85decode(jsony)
        elif source is BSON:
            return validate_class(jsony, self.klass)
        else:
            raise ValueError(f"Unsupported source {source}")

    def _to_jsony(self, value, target):
        if target is JSON:
            return base64.b85encode(value).decode('ascii')
        elif target is BSON:
            return validate_class(value, self.klass)
        else:
            raise ValueError(f"Unsupported target {target}")


class Enum(BasicType):
    def __init__(self, *, klass, **kwargs):
        super(Enum, self).__init__(klass=klass, **kwargs)

    def _from_jsony(self, jsony, source):
        return self.new(validate_class(jsony, int))

    def _to_jsony(self, value, target):
        return validate_class(value, self.klass).value


Int = BuiltinType(klass=int)
Str = BuiltinType(klass=str)
Bool = BuiltinType(klass=bool)

Any = _Any()
Bytes = _Bytes()
Datetime = _Datetime()
Float = _Float()
Path = _Path()


def _as_tuple(value):
    if not isinstance(value, tuple):
        return (value, )
    return value


class TemplateType(BasicType):
    def __init__(self, *, parameters=None, **kwargs):
        super(TemplateType, self).__init__(**kwargs)
        self._parameters = parameters

    @property
    def base_name(self):
        return super(TemplateType, self).name

    def __eq__(self, other):
        if not super(TemplateType, self).__eq__(other):
            return False
        return self._parameters == other._parameters

    @property
    def name(self):
        base_name = self.base_name
        if self._parameters is None:
            return base_name
        return "{}[{}]".format(base_name,
                               ", ".join([p.name for p in self._parameters]))

    def __getitem__(self, parameters):
        parameters = _as_tuple(parameters)
        if self._parameters is not None:
            raise ValueError("Cannot specialize already specialized type")
        return self._change(parameters=parameters)


class _List(TemplateType):
    def __init__(self, *, klass=list, **kwargs):
        super(_List, self).__init__(klass=klass, **kwargs)

    def __getitem__(self, parameters):
        parameters = _as_tuple(parameters)
        if len(parameters) != 1:
            raise ValueError("List takes only one template parameter")
        return super(_List, self).__getitem__(parameters)

    def _get_parameter(self):
        parameters = self._parameters
        if parameters is not None:
            return parameters[0]
        else:
            return Any

    def _apply(self, value, func):
        parameter = self._get_parameter()
        return func(self, [parameter.apply(item, func) for item in value])

    def _from_jsony(self, jsony, source):
        parameter = self._get_parameter()
        return [parameter.from_jsony(value, source) for value in jsony]

    def _to_jsony(self, value, target):
        parameter = self._get_parameter()
        return [parameter.to_jsony(item, target) for item in value]


class _Dict(TemplateType):
    def __init__(self, *, klass=dict, **kwargs):
        super(_Dict, self).__init__(klass=klass, **kwargs)

    def __getitem__(self, parameters):
        parameters = _as_tuple(parameters)
        if len(parameters) not in [1, 2]:
            raise ValueError("Dict takes one or two template parameters")
        if len(parameters) == 1:
            parameters = (Str, parameters[0])
        return super(_Dict, self).__getitem__(parameters)

    def _get_parameters(self):
        parameters = self._parameters
        if parameters is not None:
            return parameters
        else:
            return Any, Any

    def _apply(self, value, func):
        key_type, value_type = self._get_parameters()
        return func(
            self, {
                key_type.apply(k, func): value_type.apply(v, func)
                for k, v in value.items()
            })

    def _from_jsony(self, jsony, source):
        key_type, value_type = self._get_parameters()
        return {
            key_type.from_jsony(k, source): value_type.from_jsony(v, source)
            for k, v in jsony.items()
        }

    def _to_jsony(self, value, target):
        key_type, value_type = self._get_parameters()
        return {
            key_type.to_jsony(k, target): value_type.to_jsony(v, target)
            for k, v in value.items()
        }


class _DefaultDict(_Dict):
    def __init__(self, *, klass=defaultdict, **kwargs):
        super(_DefaultDict, self).__init__(klass=klass, **kwargs)

    @property
    def base_name(self):
        return "DefaultDict"

    def new(self, *args, **kwargs):
        _, value_type = self._get_parameters()
        return self._klass(value_type.default_value, *args, **kwargs)

    def _from_jsony(self, jsony, source):
        return self.new(super(_DefaultDict, self)._from_jsony(jsony, source))


class _Tuple(TemplateType):
    def __init__(self, *, klass=tuple, **kwargs):
        super(_Tuple, self).__init__(klass=klass, **kwargs)

    def _get_parameters(self, value):
        parameters = self._parameters
        if parameters is not None:
            if len(value) != len(parameters):
                raise ValueError(f"Expected tuple of length {len(parameters)} "
                                 f"but got {len(value)}")
        else:
            parameters = itertools.repeat(Any)
        return parameters

    def _apply(self, value, func):
        parameters = self._get_parameters(value)
        return func(
            self,
            tuple([
                parameter.apply(item, func)
                for parameter, item in zip(parameters, value)
            ]))

    def _to_jsony(self, value, target):
        parameters = self._get_parameters(value)
        return [
            parameter.to_jsony(i, target)
            for parameter, i in zip(parameters, value)
        ]

    def _from_jsony(self, jsony, source):
        parameters = self._get_parameters(jsony)
        return tuple([
            parameter.from_jsony(i, source)
            for parameter, i in zip(parameters, jsony)
        ])


List = _List()
Dict = _Dict()
DefaultDict = _DefaultDict()
Tuple = _Tuple()

# This is a very ugly way of handling recursive types.
# Can be used
#   >>> _Node = Placeholder("Node")
#   >>> Node = basic.struct("Node", children=basic.List[_Node])
#   >>> _Node.resolve(Node)
# It is not fully tested. Don't try to use `Node` before `_Node` is resolved.


class Placeholder(BasicType):
    def __init__(self, name):
        super(Placeholder, self).__init__(klass=None)
        self._type = None
        self._name = name

    def _forward(name):
        def method(self, *args, **kwargs):
            if self._type is None:
                return getattr(super(self, Placeholder), name)(*args, **kwargs)
            return getattr(self._type.default(self._default), name)(*args,
                                                                    **kwargs)

        method.__name__ = name
        return method

    def _forward_property(name):
        def getter(self):
            if self._type is None:
                return getattr(super(self, Placeholder), name)
            return getattr(self._type.default(self._default), name)

        getter.__name__ = name
        return property(getter)

    def _forward_if(method):
        @functools.wraps(method)
        def wrapped(self, *args, **kwargs):
            if self._type is not None:
                return getattr(
                    self._type.default(self._default),
                    method.__name__)(*args, **kwargs)
            else:
                return method(self, *args, **kwargs)

        return method

    klass = _forward_property("klass")
    default_value = _forward("default_value")
    _to_jsony = _forward("_to_jsony")
    _from_jsony = _forward("_from_jsony")
    _apply = _forward("_apply")
    new = _forward("new")
    __repr__ = _forward("__repr__")

    @property
    @_forward_if
    def name(self):
        return self._name

    def resolve(self, type):
        assert self._type is None
        self._type = type

    del _forward, _forward_property, _forward_if
