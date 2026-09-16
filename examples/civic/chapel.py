"""Chapel — small gabled chapel with arched entry"""

TAGS = ('fp-rect', 'roof-gable', 'door-arch', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=6.0, length=9.0)
        ctx.floors(floor_count=1, floor_height=4.5)
        ctx.roof(type="GABLE", slope_mode="ANGLE", slope_angle=0.8)
        ctx.doors(add_arch=True, size_offset={"size": [1.4, 2.4]})
