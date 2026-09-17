"""Japanese house — low profile, wide hip roof, sliding-door fills"""

TAGS = ('fp-rect', 'roof-hip', 'door-louver', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=9.0, length=7.0)
    ctx.floors(floor_count=1, floor_height=2.7)
    ctx.roof(type="HIP", height=1.2, outset=0.6)
    ctx.doors(fill_type="LOUVER", size_offset={"size": [1.8, 2.0]})
