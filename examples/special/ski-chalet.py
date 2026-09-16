"""Ski chalet — steep half-hip roof, wrap-around balcony"""

TAGS = ('fp-rect', 'roof-halfhip', 'balcony', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
        ctx.floors(floor_count=2, floor_height=3.0)
        ctx.roof(type="HALF_HIP", slope_mode="ANGLE", slope_angle=0.9,
                 ridge_fraction=0.4)
        ctx.feature("balcony", "front_walls", storeys=(1,),
                    size_offset={"size": [6.0, 1.6]})
