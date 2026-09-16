"""Roadside diner — box-gable roof, bar windows, double door"""

TAGS = ('fp-rect', 'roof-gable', 'gable-box', 'fill-bar', 'door-double', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=10.0, length=6.0)
        ctx.floors(floor_count=1, floor_height=3.4)
        ctx.roof(type="GABLE", gable_type="BOX", height=1.4)
        ctx.windows(array={"count": 4}, fill_type="BAR")
        ctx.doors(double_door=True)
