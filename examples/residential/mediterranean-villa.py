"""Mediterranean villa — terracotta-style hip roof, arch windows, balcony"""

TAGS = ('fp-rect', 'roof-hip', 'window-arch', 'balcony', 'facade', 'showcase')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=13.0, length=10.0)
    ctx.floors(floor_count=2, floor_height=3.2)
    ctx.roof(type="HIP", slope_mode="ANGLE", slope_angle=0.5236)
    from btools.api.presets import FacadeRule

    ctx.facade([
        FacadeRule("balcony", "front_walls", (1,),
                   {"size_offset": {"size": [3.0, 1.4]}}),
    ])
    ctx.windows(fill_type="GLASS_PANES", add_arch=True)
