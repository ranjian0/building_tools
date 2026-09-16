"""Aircraft hangar — wide arch-door opening"""

TAGS = ('fp-rect', 'roof-gable', 'multigroup', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=20.0, length=16.0)
        ctx.floors(floor_count=1, floor_height=6.5)
        ctx.roof(type="GABLE", gable_type="BOX", height=3.0)
        ctx.feature("multigroup", "front_walls",
                    size_offset={"size": [10.0, 5.0]}, components="d")
