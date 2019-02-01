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


def unflatten(args, base=None):
    base = {} if base is None else base
    for path, value in args.items():
        set_path(base, path, value)
    return base


def top_calling_module_name():
    return sys._getframe(2).f_globals.get('__name__', '__main__')
