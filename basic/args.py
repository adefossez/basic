import functools
import json
from pathlib import Path
import sys

from . import struct, types, inspection
from .utils import unflatten


class ArgumentParser:
    def __init__(self,
                 type,
                 name=None,
                 description=None,
                 help=True,
                 includes=True,
                 use_eval=True):
        self.name = name or Path(sys.argv[0]).name
        self.type = type
        self.description = description
        self.help = help
        self.includes = includes
        self.use_eval = use_eval

    @staticmethod
    def _get_description(type_, name=None, indent=0):
        lines = []
        base = "  " * indent
        if name is not None:
            intro = base
            intro += name

        if isinstance(type_, struct.StructType):
            if name is not None:
                if type_._default is not types.EMPTY:
                    intro += ": [{!r}]".format(type_._default)
                lines.append(intro)
            for name, field in type_._schema.items():
                lines.extend(
                    ArgumentParser._get_description(field, name, indent + 2))
        else:
            intro += "[{}] = {!r}".format(type_.name, type_._default)
            lines.append(intro)
        return lines

    def show_help(self, file=None):
        _print = functools.partial(print, file=file)
        _print(f"usage: {self.name}: [key=value ...]")
        if self.description:
            _print(self.description)
        _print("\n".join(ArgumentParser._get_description(self.type)))

    def get_type(self, path):
        type_ = self.type
        for part in path.split("."):
            type_ = type_._schema[part]
        return type_

    def argv_to_json(self, argv, out=None):
        args = {}
        if out is None:
            out = {}
        for arg in argv:
            if arg == "--help":
                if not self.help:
                    raise ValueError("Show help requested but is disallowed")
                self.show_help()
                sys.exit(0)
            elif arg.startswith('@'):
                if not self.includes:
                    raise ValueError("Include requested but is disallowed")
                with open(arg[1:] + ".json") as file:
                    entries = json.load(file)
                for path, value in entries.items():
                    args[path] = value
            elif "=" in arg:
                path, value = arg.split('=', 1)
                field = self.get_type(path)
                if issubclass(field.klass, (str, Path)):
                    if value.startswith("@"):
                        value = value[1:]
                    else:
                        args[path] = value
                        continue
                if self.use_eval:
                    value = eval(value, {}, {
                        "null": None,
                        "false": False,
                        "true": True
                    })
                else:
                    value = json.loads(value)
                args[path] = value
            else:
                field = self.get_type(arg)
                if field.klass is bool:
                    args[arg] = True
                else:
                    args[arg] = {}
        return unflatten(args, out)

    def parse_args(self, argv=None, convert=True):
        if argv is None:
            argv = sys.argv[1:]
        parsed = self.parse_json(self.argv_to_json(argv))
        if convert:
            return inspection.convert(self.type, parsed)
        return parsed

    def parse_json(self, json):
        return self.type.from_json(json)
