import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)

import bpy  # must precede bmesh/mathutils imports (also registers submodules)

# -- clean slate: user prefs may auto-enable an old installed copy of the
#    addon, whose registration would collide with the working tree
bpy.ops.wm.read_factory_settings(use_empty=True)
for _mod in [m for m in sys.modules if "building_tools" in m or m == "btools"]:
    del sys.modules[_mod]

import tools

try:
    import test_api
    import test_api_options
    import test_api_probe
    import test_floorplan
    import test_floors
    import test_utils
    import test_utils_skeleton
except Exception:
    # XXX Error importing test modules.
    # Print Traceback and close blender process
    import traceback

    traceback.print_exc()
    sys.exit()


def main():
    # Load the addon module
    tools.LoadModule(os.path.join(addon_dir, "__init__.py"))
    print("-" * 70, end="\n\n")

    # initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(test_utils))
    suite.addTests(loader.loadTestsFromModule(test_utils_skeleton))
    suite.addTests(loader.loadTestsFromModule(test_floors))
    suite.addTests(loader.loadTestsFromModule(test_floorplan))
    suite.addTests(loader.loadTestsFromModule(test_api_options))
    suite.addTests(loader.loadTestsFromModule(test_api_probe))
    suite.addTests(loader.loadTestsFromModule(test_api))

    # initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)

    # close blender process
    sys.exit()


if __name__ == "__main__":
    main()
