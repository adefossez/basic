# basic: a utility for handling basic types

basic gives a framework for the definition of basic types (int, float, str etc)
and how to combine them into more complex structures (dict, struct, list etc).\
basic can be used to document a specific structure and serialize to/from
JSON.\
basic can be used to specify the structure of a MongoDB collection.\
Finally, basic can be used in order to automatically build a highly
structured commandline interface from inspection of class constructors.

This is small personnal library. I do not intend on providing full support
for it. This is an on-going work and major rewrites are likely.
Not everything has been recently tested.


## License

`basic` is provided under the MIT license. See the LICENSE file for more details.


## Quick tutorial

### Builtin types and template types

Basic types are defined as `basic.*`, for instance `basic.Int`
represents an integer, `basic.Str` a string and `Basic.Bytes` a bytestring.

Template types for dictionaries, lists and tuples are also available. For instance `basic.List` represents a list of any elements while `basic.List[basic.Int]` is a list of integers.

Each type knows how to convert itself to and from JSON serializable basic structures (using only dict, list and other builtin types). We also support BSON (used by MongoDB).
For instance, bytestring will be base84 encoded when exported to JSON.

```python
>>> import basic
>>> basic.List[basic.Bytes].to_json([b"hello"])
['Xk~0{Zv']
>>> basic.List[basic.Bytes].from_json(['Xk~0{Zv'])
[b'hello']

```

On the other hand, BSON supports natively bytestring, therefore
requiring no conversion.

```
>>> import basic
>>> basic.List[basic.Bytes].to_bson([b"hello"])
[b'hello']

```

Note that `basic` does not peform the JSON/BSON serialization. It only transform the data so that it only use types supported by JSON/BSON.

### Structured types

Basic allows to define custom structures with strongly type fields. They can either be named structure which must be assigned to some top level module variable (similar to `namedtuple`).
Otherwise, they can be anonymous structures that do not need such assignement.
In both case, the structure will be picklable, but named structure
will use their own class while anonymous structure will use a generic one,
which requires also pickling the entire type schema information.

```
>>> import basic
>>> import pickle
>>> Dog = basic.struct("Dog", name=basic.Str)
>>> dog = Dog(name="Laika"); print(dog)
Dog(name='Laika')
>>> pickle.loads(pickle.dumps(dog)).name
Laika

```

### Default values

In the previous example, `Dog` is a basic type while `Dog.Dog`
is the actual class used to represent a dog structure.
A basic type represents both a type signature as well as containing information about whether a field is required, or which
default value to use if not provided.

```
>>> import basic
>>> Dog = basic.struct("Dog",
...     name=basic.Str, # field required
...     created=basic.Datetime.now, # field not required, default is current time
... )
>>> Dog(name='Laika').created
datetime.datetime(2018, 10, 31, 11, 31, 14, 576919)
```

In this example, `basic.Datetime.now` represents a field containing `datetime.datetime` whose default value will be
obtained calling `datetime.datetime.now()` any time a new `Dog` object is created.

Other possiblities default values specifiers:

```
basic.Int.none # default to None
basic.Str.missing # if the value is not provided, this field will not be set on the structure
basic.List.empty # if the value is not provided, create one
# calling the constructor of the type with no arguments
basic.Float.default(0.) # default value will be 0.
```

### Automatic class inspection

It is possible to automatically inspect a class constructor in order to build a matching structure that can then be automatically converted to the target class. This is especially useful for instanciating classes from JSON. Inspection
is done in cascade as long as type information is provided or guessable
from the default value.

```
import basic


def _repr(klass):
    def __repr(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{klass.__name__}({attrs})"

    if klass.__repr__ is object.__repr__:
        klass.__repr__ = __repr
    return klass


@_repr
class Trick:
    def __init__(self, name: str, difficulty=0):
        self.name = name
        self.difficulty = difficulty


@_repr
class Owner:
    def __init__(self, name: str):
        self.name = name


@_repr
class SubEasy:
    def __init__(self, a=12):
        self.a = a


@_repr
class Easy:
    def __init__(self, subeasy: SubEasy, answer=True):
        self.answer = answer
        self.subeasy = subeasy


class Dog:
    def __init__(
            self,
            name: str,
            owner: Owner,
            # Easy has all default values, so here Easy will automatically
            # be converted to class_type(Easy).empty.
            easy: Easy,
            # When using a basic type with a default value as annotation
            # the argument default value must be None.
            created: basic.Datetime.now = None,
            # A little bit verbose for now...
            tricks: basic.List[basic.class_type(Trick)].empty = None):
        self.name = name
        self.owner = owner
        self.easy = easy
        self.created = created
        self.tricks = tricks

    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Dog({attrs})"


DogType = basic.class_type(Dog)
dog = DogType.convert(
    DogType.from_json({
        "name": "Laika",
        "owner": {
            "name": "Alex"
        },
        "tricks": [{
            "name": "flying",
            "difficulty": 5
        }]
    }))
print(dog)
```

A structured representation can be obtained from JSON/BSON using
the `from_json/from_bson` method on `basic.class_type(Dog)`.
It can then be converted using `basic.class_type(Dog).convert`.
This is a two stage process to allow for potential modification of the
structure before the actual instantiation.

### Argument parsing

```
import basic

class Module:
    def __init__(self, layers=42):
        self.layers = layers

    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Module({attrs})"

class Main:
    def __init__(self,
                 path,
                 module: basic.class_type(Module).empty,
                 lr=0.001,
                 special=False):
        self.module = module
        self.lr = lr
        self.special = special
        self.path = path

    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Main({attrs})"

if __name__ == "__main__":
    parser = basic.ArgumentParser(basic.class_type(Main,
        path="/path/to/data"))
    print(parser.parse_args(["module.layers=32"]))
    print(parser.parse_args(["special", "lr=0.1"]))
```
