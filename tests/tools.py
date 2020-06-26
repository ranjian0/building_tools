""" Adapted from Script Watcher Addon
https://github.com/wisaac407/blender-script-watcher
"""
import os
import sys
import types
import traceback


def get_paths(filepath):
    """Find all the python paths surrounding the given filepath."""

    dirname = os.path.dirname(filepath)

    paths = []
    filepaths = []

    for root, dirs, files in os.walk(dirname, topdown=True):
        if '__init__.py' in files:
            paths.append(root)
            for f in files:
                filepaths.append(os.path.join(root, f))
        else:
            dirs[:] = [] # No __init__ so we stop walking this dir.

    # If we just have one (non __init__) file then return just that file.
    return paths, filepaths or [filepath]


def get_mod_name(filepath):
    """Return the module name and the root path of the given python file path."""
    dir, mod = os.path.split(filepath)

    # Module is a package.
    if mod == '__init__.py':
        mod = os.path.basename(dir)
        dir = os.path.dirname(dir)

    # Module is a single file.
    else:
        mod = os.path.splitext(mod)[0]

    return mod, dir


def remove_cached_mods(filepath):
    """Remove all the script modules from the system cache."""
    paths, files = get_paths(filepath)
    for mod_name, mod in list(sys.modules.items()):
        try:
            if hasattr(mod, '__file__') and os.path.dirname(mod.__file__) in paths:
                del sys.modules[mod_name]
        except TypeError:
            pass


def load_module(filepath):
    remove_cached_mods(filepath)
    try:
        f = open(filepath)
        paths, files = get_paths(filepath)

        # Get the module name and the root module path.
        mod_name, mod_root = get_mod_name(filepath)

        # Create the module and setup the basic properties.
        mod = types.ModuleType('__main__')
        mod.__file__ = filepath
        mod.__path__ = paths
        mod.__package__ = mod_name

        # Add the module to the system module cache.
        sys.modules[mod_name] = mod

        # Fianally, execute the module.
        exec(compile(f.read(), filepath, 'exec'), mod.__dict__)
    except IOError:
        print('Could not open script file.')
    except Exception:
        sys.stderr.write("There was an error when running the script:\n" + traceback.format_exc())
    else:
        f.close()
