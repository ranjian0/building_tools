"""Hospital — H-shaped multi-wing plan, window rows, flat roof"""

TAGS = ('fp-h', 'roof-flat', 'windows', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="H_SHAPED", width=26.0, length=18.0)
        ctx.floors(floor_count=3, floor_height=3.4)
        ctx.roof(type="FLAT", add_border=True)
        ctx.windows(storeys=(0, 1, 2), array={"count": 6})
