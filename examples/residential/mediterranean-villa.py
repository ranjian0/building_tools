"""Mediterranean villa — terracotta-style hip roof, arch windows, balcony"""

TAGS = ('fp-rect', 'roof-hip', 'window-arch', 'balcony', 'showcase')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=13.0, length=10.0)
        ctx.floors(floor_count=2, floor_height=3.2)
        ctx.roof(type="HIP", slope_mode="ANGLE", slope_angle=0.5236)
        ctx.windows(fill_type="GLASS_PANES", add_arch=True)
        ctx.feature("balcony", "front_walls", size_offset={"size": [3.0, 1.4]})
