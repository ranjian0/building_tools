"""Seeded variants — the same rule, different decisions per seed."""
TAGS = ("pipeline", "seed", "facade", "variations")


def build(ctx):
    from btools.api.presets import BuildingPreset, FacadeRule
    from btools.api.presets import PRESETS

    base = dict(PRESETS["suburban-house"].__dict__)
    for seed in (1, 2, 3):
        preset = BuildingPreset(
            id="variant-%d" % seed,
            label="Variant %d" % seed,
            floorplan={"type": "RECTANGULAR", "width": 10.0, "length": 8.0},
            floors={"floor_count": 2, "floor_height": 3.0},
            facade=[
                FacadeRule(
                    "window",
                    "front_walls",
                    (1,),
                    {"size_offset": {"size": [1.2, 1.4]}},
                    variations={"fill_type": ["BAR", "GLASS_PANES", "LOUVER"]},
                ),
            ],
        )
        from btools.api.presets import build_preset

        build_preset(preset, seed="variant-%d" % seed)
