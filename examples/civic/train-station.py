"""Train station — long box-gable hall with wide entry bays"""

TAGS = ('fp-rect', 'roof-gable', 'gable-box', 'multigroup', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=30.0, length=12.0)
        ctx.floors(floor_count=1, floor_height=5.5)
        ctx.roof(type="GABLE", gable_type="BOX", height=2.5)
        ctx.feature("multigroup", "front_walls",
                    size_offset={"size": [4.0, 3.2]}, array={"count": 3})
