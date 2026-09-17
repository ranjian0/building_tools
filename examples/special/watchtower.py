"""Watchtower — tall shaft with a skeleton-core lookout"""

TAGS = ('fp-rect', 'roof-hip', 'interiors-skeleton', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=6.0, length=6.0)
    ctx.floors(floor_count=2, floor_height=5.0)
    ctx.roof(type="HIP", height=2.0, outset=0.6)
    ctx.interior(partition_mode="SKELETON", min_corridor=2.0)
