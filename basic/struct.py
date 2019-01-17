import pydoc

from . import types
from .utils import top_calling_module_name


class Struct:
    def __init__(self, **kwargs):
        remaining = set(self._schema.keys())
        self.__dict__["_fields"] = {}
        for name, value in kwargs.items():
            if name not in remaining:
                raise NameError("Invalid argument {}".format(name))
            remaining.remove(name)
            self._fields[name] = value

        for name in remaining:
            type = self._schema[name]
            if type._default is types.REQUIRED:
                raise TypeError("Missing argument {}".format(name))
            elif type._default is types.MISSING:
                continue
            else:
                self._fields[name] = type.default_value()

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join("{}={!r}".format(name, value)
                      for name, value in self._fields.items()))

    def __hash__(self):
        return hash(self._cmp_repr)

    def __eq__(self, other):
        if isinstance(other, Struct):
            return self._cmp_repr == other._cmp_repr
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    @property
    def _cmp_repr(self):
        return tuple([(name, self._fields.get(name, types.MISSING))
                      for name in self._schema.keys()])

    def __getattr__(self, name):
        schema = self.__getattribute__("_schema")
        if name in schema:
            try:
                return self._fields[name]
            except KeyError:
                raise AttributeError(f"Field {name} not set")
        elif name.startswith('_'):
            return self.__getattribute__(name)
        else:
            raise AttributeError(f"{self} has no attribute {name}")

    def __setattr__(self, name, value):
        if name in self._schema:
            self._fields[name] = value
        elif name.startswith('_'):
            self.__dict__[name] = value
        else:
            raise AttributeError(f"{self} has no attribute {name}")

    def __delattr__(self, name):
        if name in self._schema:
            try:
                del self._fields[name]
            except KeyError:
                raise AttributeError(f"Field {name} not set")
        elif name.startswith('_'):
            try:
                del self.__dict__[name]
            except KeyError:
                raise AttributeError(f"{self} has no attribute {name}")
        else:
            raise AttributeError(f"{self} has no attribute {name}")

    @property
    def _json(self):
        schema = self.__getattribute__("_schema")
        return _to_jsony(self, schema, target=types.JSON)

    @property
    def _bson(self):
        schema = self.__getattribute__("_schema")
        return _to_jsony(self, schema, target=types.BSON)


def _to_jsony(struct, schema, target):
    return {
        name: schema[name].to_jsony(value, target)
        for name, value in struct._fields.items()
    }


def _from_jsony(jsony, factory, schema, source):
    return factory(
        **{
            name: schema[name].from_jsony(value, source)
            for name, value in jsony.items()
        })


class StructType(types.BasicType):
    def __init__(self,
                 *,
                 schema,
                 klass,
                 factory,
                 name=None,
                 toplevel_path=None,
                 **kwargs):
        super(StructType, self).__init__(klass=klass)
        self._schema = schema
        self._factory = factory
        self._name = name
        self._toplevel_path = toplevel_path

    def _apply(self, value, func):
        kwargs = {
            name: self._schema[name].apply(field, func)
            for name, field in value._fields.items()
        }
        return func(self, self._factory(**kwargs))

    def _to_jsony(self, value, target):
        return _to_jsony(value, self._schema, target)

    def _from_jsony(self, jsony, source):
        return _from_jsony(jsony, self._factory, self._schema, source)

    def new(self, *args, **kwargs):
        return self._factory(*args, **kwargs)

    def field(self, name):
        return self._schema[name]

    def __copy__(self):
        copied = self.__class__.__new__(self.__class__)
        copied.__dict__.update(self.__dict__)
        copied._toplevel_path = None
        return copied

    def __reduce__(self):
        if self._toplevel_path is None:
            return super(StructType, self).__reduce__()
        else:
            return pydoc.locate, (self._toplevel_path, )

    def __eq__(self, other):
        if not super(StructType, self).__eq__(other):
            return False
        return (self._schema, self._factory,
                self._name) == (other._schema, other._factory, other._name)

    @property
    def name(self):
        if self._name is not None:
            return self._name
        else:
            schema_repr = ", ".join("{}={}".format(name, field.name)
                                    for name, field in self._schema.items())
            return f"struct({schema_repr})"


class _WithAttrsFactory:
    def __init__(self, klass, **attrs):
        self._attrs = attrs
        self._klass = klass

    def __call__(self, *args, **kwargs):
        value = self._klass.__new__(self._klass, *args, **kwargs)
        value.__dict__.update(self._attrs)
        value.__init__(*args, **kwargs)
        return value

    def __eq__(self, other):
        if not isinstance(other, _WithAttrsFactory):
            return False
        return self._attrs == other._attrs and self._klass == other._klass

    def __ne__(self, other):
        return not (self == other)


def struct(__name, __bases=(), **schema):
    klass = type(__name, __bases + (Struct, ), {})
    module = top_calling_module_name()
    klass.__module__ = module
    klass.__qualname__ = f"{__name}.{__name}"
    klass._schema = schema
    factory = klass
    type_ = StructType(
        schema=schema,
        klass=klass,
        factory=factory,
        name=__name,
        toplevel_path=f"{module}.{__name}")
    setattr(type_, __name, klass)
    return type_


def lambda_struct(__name=None, **schema):
    klass = Struct
    factory = _WithAttrsFactory(klass, _schema=schema)
    type_ = StructType(
        schema=schema, klass=klass, factory=factory, name=__name)
    return type_
