import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)

import tools
import test_utils
import test_floors
import test_floorplan


def main():
    # Load the addon module
    tools.LoadModule(os.path.join(addon_dir, "btools", "__init__.py"))
    print('-'*70, end="\n\n")

    # initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(test_utils))
    suite.addTests(loader.loadTestsFromModule(test_floors))
    suite.addTests(loader.loadTestsFromModule(test_floorplan))

    # initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3)
    runner.run(suite)
    sys.exit(0)


main()
