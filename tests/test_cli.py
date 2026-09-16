"""Tests for the btools CLI and rule-file contract (pip-package phase 2-3)."""

import json
import os
import unittest


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        import bpy

        if bpy.context.object and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)

    def test_list_presets(self):
        from btools.cli import main

        import io
        from contextlib import redirect_stdout

        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["list-presets", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(len(data), 8)

    def test_preset_with_render(self):
        import tempfile

        from btools.cli import main

        out_base = os.path.join(tempfile.gettempdir(), "btools_cli_test")
        for view in ("front", "iso"):
            p = f"{out_base}.{view}.png"
            if os.path.exists(p):
                os.remove(p)
        code = main(
            ["preset", "suburban-house", "--render", out_base, "--views", "front,iso"]
        )
        self.assertEqual(code, 0)
        # multi-view renders append the view name to the base path
        for view in ("front", "iso"):
            self.assertTrue(os.path.isfile(f"{out_base}.{view}.png"), view)

    def test_run_rule_file(self):
        import tempfile

        from btools.cli import main

        rule = os.path.join(tempfile.gettempdir(), "btools_rule_test.py")
        with open(rule, "w") as fh:
            fh.write(
                "def build(ctx):\n"
                "    ctx.floorplan(type='RECTANGULAR', width=8.0, length=6.0)\n"
                "    ctx.floors(floor_count=1, floor_height=3.0)\n"
            )
        try:
            code = main(["run", rule, "--json"])
            self.assertEqual(code, 0)
        finally:
            os.remove(rule)


if __name__ == "__main__":
    unittest.main()
