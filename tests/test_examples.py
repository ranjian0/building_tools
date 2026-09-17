"""The examples gallery doubles as a validation corpus (pip-package roadmap).

Every example must build cleanly, pass the matgroup contract and satisfy
its own EXPECT block. Suite-level coverage asserts the option matrix is
exercised across the gallery."""

import unittest

import bpy

import btools
from btools.examples import discover


def _run_example(ex):
    btools.ensure_registered()
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    import btools.rules as rules_mod

    ctx = rules_mod.RuleContext()
    mod = (
        rules_mod.load_rule_module(ex.path)
        if hasattr(rules_mod, "load_rule_module")
        else None
    )
    if mod is None:
        from btools.cli import _load_rule_module

        mod = _load_rule_module(ex.path)
    mod.build(ctx)
    if not ctx.objects and not bpy.data.objects:
        raise AssertionError(
            "example built nothing — check for nested/shadowed build()"
        )
    return ctx, mod


def _check_expect(ctx, mod):
    expect = getattr(mod, "EXPECT", None)
    problems = []
    if expect:
        groups = expect.get("groups", [])
        for obj_name in ctx.objects:
            obj = ctx.object_data(obj_name)
            if obj is None:
                continue
            from btools.api.validate import validate_object

            report = validate_object(obj, include_geometry=False)
            if not report["ok"]:
                problems.extend(report["problems"][:1])
        import bpy

        names = {
            mt.name
            for o in [ctx.object_data(n) for n in ctx.objects]
            if o
            for mt in getattr(o, "bt_materials", [])
        }
        for g in groups:
            # group presence via material slots (BT_<group>)
            if ("BT_" + g) not in names and (g not in names):
                problems.append("missing group slot: %s" % g)
    return problems


class TestExamples(unittest.TestCase):
    def test_all_examples_build(self):
        examples = discover()
        self.assertGreaterEqual(len(examples), 40, "gallery should stay large")
        for ex in examples:
            with self.subTest(example=ex.id):
                ctx, mod = _run_example(ex)
                failures = [r for r in ctx.results if not r.ok]
                self.assertFalse(failures, (ex.id, [f.errors[:1] for f in failures]))
                problems = _check_expect(ctx, mod)
                self.assertFalse(problems, (ex.id, problems))

    def test_coverage(self):
        """Every option-matrix cell appears in at least one example's tags."""
        required = [
            # floorplan types
            "fp-rect",
            "fp-circle",
            "fp-composite",
            "fp-h",
            "fp-random",
            # roof types + modes
            "roof-flat",
            "roof-gable",
            "roof-hip",
            "roof-flattop",
            "roof-mansard",
            "roof-halfhip",
            "slope-height",
            "slope-angle",
            "slope-percentage",
            # roof extras
            "gutters",
            "chimney",
            "ridge-cap",
            # floors extras
            "cornice",
            "columns",
            "double-shell",
            # openings
            "door",
            "door-double",
            "door-arch",
            "windows",
            "window-circle",
            "fill-panels",
            "fill-glass",
            "door-louver",
            "window-louver",
            "fill-bar",
            "multigroup",
            "casing",
            "hardware",
            "bevel",
            # interiors
            "interiors-treemap",
            "interiors-skeleton",
            "double-shell",
            # elements
            "balcony",
            # workflows
            "preset",
            "seed",
        ]
        covered = set()
        for ex in discover():
            import importlib.util

            safe = "cov_" + ex.id.replace(".", "_")
            spec = importlib.util.spec_from_file_location(safe, ex.path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            covered.update(getattr(mod, "TAGS", ()))
        for tag in required:
            self.assertIn(tag, covered, "option-matrix cell not exercised: " + tag)


if __name__ == "__main__":
    unittest.main()
