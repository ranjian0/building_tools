"""Garage — low gable, single wide door"""

TAGS = ('fp-rect', 'roof-gable', 'door', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=6.0, length=6.5)
        ctx.floors(floor_count=1, floor_height=2.8)
        ctx.roof(type="GABLE", height=1.2)
        ctx.doors(size_offset={"size": [2.6, 2.2]})
