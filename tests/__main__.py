import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)

import bpy  # must precede bmesh/mathutils imports (also registers submodules)

# -- clean slate: factory settings + purge any stale copies of the package
bpy.ops.wm.read_factory_settings(use_empty=True)
for _mod in [m for m in sys.modules if "building_tools" in m or m == "btools"]:
    del sys.modules[_mod]

try:
    import test_api
    import test_api_options
    import test_batch
    import test_cli
    import test_export
    import test_facade
    import test_api_probe
    import test_floorplan
    import test_floors
    import test_interiors
    import test_offsets
    import test_partitions
    import test_randomizer
    import test_roofs
    import test_utils
    import test_utils_skeleton
except Exception:
    # XXX Error importing test modules.
    # Print Traceback and close blender process
    import traceback

    traceback.print_exc()
    sys.exit()


def main():
    # -- register everything the api needs (idempotent bootstrap)
    import btools

    btools.register()

    # initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(test_utils))
    suite.addTests(loader.loadTestsFromModule(test_utils_skeleton))
    suite.addTests(loader.loadTestsFromModule(test_randomizer))
    suite.addTests(loader.loadTestsFromModule(test_roofs))
    suite.addTests(loader.loadTestsFromModule(test_floors))
    suite.addTests(loader.loadTestsFromModule(test_offsets))
    suite.addTests(loader.loadTestsFromModule(test_floorplan))
    suite.addTests(loader.loadTestsFromModule(test_interiors))
    suite.addTests(loader.loadTestsFromModule(test_partitions))
    suite.addTests(loader.loadTestsFromModule(test_batch))
    suite.addTests(loader.loadTestsFromModule(test_cli))
    suite.addTests(loader.loadTestsFromModule(test_export))
    suite.addTests(loader.loadTestsFromModule(test_api_options))
    suite.addTests(loader.loadTestsFromModule(test_facade))
    suite.addTests(loader.loadTestsFromModule(test_api_probe))
    suite.addTests(loader.loadTestsFromModule(test_api))

    # initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)

    # close blender process
    sys.exit()


if __name__ == "__main__":
    main()
