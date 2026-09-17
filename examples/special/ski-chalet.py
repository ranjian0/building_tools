"""Ski chalet — steep half-hip roof, balcony on the upper floor"""

TAGS = ('fp-rect', 'roof-halfhip', 'balcony', 'facade', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=2, floor_height=3.0)
    ctx.roof(type="HALF_HIP", slope_mode="ANGLE", slope_angle=0.9,
             ridge_fraction=0.4)
    from btools.api.presets import FacadeRule

    ctx.facade([
        FacadeRule("balcony", "front_walls", (1,),
                   {"size_offset": {"size": [6.0, 1.6]}}),
    ])
    ctx.windows(storeys=(0,))
