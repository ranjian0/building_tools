"""Barn — steep gable, big entry door, minimal windows"""

TAGS = ('fp-rect', 'roof-gable', 'door', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=12.0, length=18.0)
    ctx.floors(floor_count=1, floor_height=5.0)
    ctx.roof(type="GABLE", slope_mode="ANGLE", slope_angle=0.9)
    ctx.doors(size_offset={"size": [3.0, 3.5]})
