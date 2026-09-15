"""Tests for the bay-grid facade layer (CGA subset, roadmap item 6)."""

import unittest

import bpy

import btools
from btools.api.facade import BayGrid, bay_matches, resolve_bay_grid
from btools.api.presets import BuildingPreset, FacadeRule, build_preset
from btools.api import probe


class TestBayGrid(unittest.TestCase):
    def test_fill_exact(self):
        grid = resolve_bay_grid(14.0, "fill", 3.5)
        self.assertEqual((grid.count, grid.bay_width), (4, 3.5))

    def test_fill_stretches(self):
        # -- 9m face, 3.5m module: 2 bays stretched to 4.5 (no remainder)
        grid = resolve_bay_grid(9.0, "fill", 3.5)
        self.assertEqual((grid.count, grid.bay_width), (2, 4.5))

    def test_fill_clamps_tiny_face(self):
        grid = resolve_bay_grid(2.0, "fill", 3.5)
        self.assertEqual((grid.count, grid.bay_width), (1, 2.0))

    def test_int_bays(self):
        grid = resolve_bay_grid(10.0, 3, None)
        self.assertEqual(grid.count, 3)
        self.assertAlmostEqual(grid.bay_width, 10.0 / 3, places=6)

    def test_fill_requires_bay_width(self):
        with self.assertRaises(ValueError):
            resolve_bay_grid(10.0, "fill", None)
        with self.assertRaises(ValueError):
            resolve_bay_grid(10.0, "fill", 0.0)

    def test_center_offsets(self):
        grid = BayGrid(count=4, face_width=14.0, bay_width=3.5)
        offsets = [round(grid.center_offset(i), 6) for i in range(4)]
        self.assertEqual(offsets, [-5.25, -1.75, 1.75, 5.25])

    def test_clamp_size(self):
        grid = BayGrid(count=4, face_width=14.0, bay_width=3.5)
        self.assertEqual(grid.clamp_size((5.0, 2.0)), (3.5, 2.0))
        self.assertEqual(grid.clamp_size((1.6, 1.4)), (1.6, 1.4))


class TestBayMatches(unittest.TestCase):
    def test_conditions(self):
        self.assertTrue(bay_matches(0, 4, {}))
        self.assertTrue(bay_matches(0, 4, {"bay_index": "even"}))
        self.assertFalse(bay_matches(1, 4, {"bay_index": "even"}))
        self.assertTrue(bay_matches(1, 4, {"bay_index": "odd"}))
        self.assertFalse(bay_matches(0, 4, {"bay_index": "odd"}))
        self.assertTrue(bay_matches(0, 4, {"bay_index": "first"}))
        self.assertFalse(bay_matches(1, 4, {"bay_index": "first"}))
        self.assertTrue(bay_matches(3, 4, {"bay_index": "last"}))
        self.assertFalse(bay_matches(2, 4, {"bay_index": "last"}))
        self.assertTrue(bay_matches(2, 4, {"bay_index": 2}))
        self.assertTrue(bay_matches(1, 4, {"bay_index": [0, 1]}))
        self.assertFalse(bay_matches(2, 4, {"bay_index": [0, 1]}))
        # -- unknown keys ignored (forward compat)
        self.assertTrue(bay_matches(1, 4, {"future_key": "whatever"}))


def _clean_scene():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def _bay_preset():
    """Mini preset: balconies establish the 'main' grid (fill at 3m),
    windows follow it; a parity rule exercises `where`."""
    return BuildingPreset(
        id="bay-test",
        label="Bay Test",
        floorplan={"type": "RECTANGULAR", "width": 12.0, "length": 8.0},
        floors={"floor_count": 2, "floor_height": 3.0},
        facade=[
            FacadeRule(
                "balcony",
                "front_walls",
                (1,),
                {"size_offset": {"size": [2.6, 0.2]}},
                bays="fill",
                bay_width=3.0,
                align="main",
            ),
            FacadeRule(
                "window",
                "front_walls",
                (1,),
                {"size_offset": {"size": [1.2, 1.4]}},
                bays=2,
                align="main",
            ),
        ],
    )


def _front_bay_centers(obj, group, tol):
    return sorted(
        round(b["center"], 3)
        for b in probe.elevation_bays(obj, group, view="front", tol=tol)
    )


class TestFacadeIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_api_options

        test_api_options.register_all()

    def setUp(self):
        _clean_scene()

    def test_alignment_holds_under_scaling(self):
        # -- THE capability: windows follow the balcony grid at any scale
        for scale, want_bays in ((1.0, 4), (1.5, 6)):
            with self.subTest(scale=scale):
                _clean_scene()
                res = build_preset(_bay_preset(), width_scale=scale)
                self.assertTrue(res.ok, res.errors)
                obj = bpy.data.objects[res.created_object]

                wb = _front_bay_centers(obj, "window", 0.2)
                bb = _front_bay_centers(obj, "balcony", 0.35)
                self.assertGreaterEqual(len(bb), want_bays, bb)
                # -- every window bay center sits on a balcony bay center
                for w in wb:
                    self.assertTrue(
                        any(abs(w - b) < 0.3 for b in bb),
                        (scale, w, bb),
                    )

    def test_where_parity_skips_bays(self):
        preset = BuildingPreset(
            id="parity-test",
            label="Parity Test",
            floorplan={"type": "RECTANGULAR", "width": 12.0, "length": 8.0},
            floors={"floor_count": 2, "floor_height": 3.0},
            facade=[
                FacadeRule(
                    "window",
                    "front_walls",
                    (1,),
                    {"size_offset": {"size": [1.2, 1.4]}},
                    bays=4,
                    where={"bay_index": "even"},
                ),
            ],
        )
        res = build_preset(preset)
        self.assertTrue(res.ok, res.errors)
        obj = bpy.data.objects[res.created_object]
        # -- 2 of 4 bays per front face
        centers = _front_bay_centers(obj, "window", 0.2)
        self.assertEqual(len(centers), 2, centers)

    def test_seeded_per_bay_variation(self):
        def make():
            return BuildingPreset(
                id="seed-bay-test",
                label="Seed Bay Test",
                floorplan={"type": "RECTANGULAR", "width": 12.0, "length": 8.0},
                floors={"floor_count": 2, "floor_height": 3.0},
                facade=[
                    FacadeRule(
                        "window",
                        "front_walls",
                        (1,),
                        {"size_offset": {"size": [1.2, 1.4]}},
                        bays=4,
                        variations={"fill_type": ["BAR", "GLASS_PANES"]},
                    ),
                ],
            )

        r1 = build_preset(make(), seed="s1")
        r2 = build_preset(make(), seed="s1")
        self.assertTrue(r1.ok and r2.ok, (r1.errors[:1], r2.errors[:1]))
        self.assertEqual(r1.matgroup_counts, r2.matgroup_counts)
        self.assertEqual(r1.decisions, r2.decisions)
        # -- one draw per bay (1 front face x 4 bays)
        self.assertEqual(len(r1.decisions), 4)
        for path, decision, value in r1.decisions:
            self.assertEqual(decision, "choice")
            self.assertIn(value, ("BAR", "GLASS_PANES"))


if __name__ == "__main__":
    unittest.main()
