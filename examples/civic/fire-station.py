"""Fire station — twin equipment-bay doors, flat roof"""

TAGS = ('fp-rect', 'roof-flat', 'door-double', 'simple')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=14.0, length=10.0)
        ctx.floors(floor_count=1, floor_height=4.5)
        ctx.roof(type="FLAT")
        ctx.doors(double_door=True, size_offset={"size": [2.6, 3.2]},
                  array={"count": 2})
