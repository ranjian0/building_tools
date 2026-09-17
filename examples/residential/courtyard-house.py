"""Courtyard house — H-shaped plan with a double-shell interior"""

TAGS = ('fp-h', 'roof-hip', 'double-shell', 'interiors-treemap', 'showcase')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="H-SHAPED", width=14.0, length=12.0)
    ctx.floors(floor_count=2, floor_height=3.0, wall_thickness=0.3)
    ctx.roof(type="HIP", height=2.0)
    ctx.interior(partition_mode="TREEMAP", room_count=6, inset=0.3)
