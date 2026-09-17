"""Hotel — U-shaped plan with balcony rings over a glazed ground floor"""

TAGS = ('fp-composite', 'roof-flat', 'balcony', 'facade', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="COMPOSITE", width=20.0, length=14.0)
    ctx.floors(floor_count=4, floor_height=3.2)
    ctx.roof(type="FLAT", add_border=True)
    from btools.api.presets import FacadeRule

    ctx.facade([
        FacadeRule("balcony", "front_walls", (1, 2, 3),
                   {"size_offset": {"size": [2.6, 1.2]}, "array": {"count": 4}}),
    ])
    ctx.windows(storeys=(0,), array={"count": 6})
