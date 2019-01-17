import sys


class _Keyword:
    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return self._name

    def __str__(self):
        return self._name


def set_path(args, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        if part not in args:
            args[part] = {}
        args = args[part]
    args[parts[-1]] = value


def unflatten(args):
    unflattened = {}
    for path, value in args.items():
        set_path(unflattened, path, value)
    return unflattened


def flatten(entry):
    flattened = {}

    def _flatten(entry, path=[]):
        path.append(None)
        for key, value in entry.items():
            path[-1] = key
            if isinstance(value, dict):
                _flatten(value, path)
            else:
                path[-1] = key
                flattened[".".join(path)] = value
        path.pop(-1)

    _flatten(entry)
    return flattened


def top_calling_module_name():
    return sys._getframe(2).f_globals.get('__name__', '__main__')
