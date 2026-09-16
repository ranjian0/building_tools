"""Hotel — U-shaped plan with balcony rings"""

TAGS = ('fp-composite', 'roof-flat', 'balcony', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="COMPOSITE", width=20.0, length=14.0)
        ctx.floors(floor_count=4, floor_height=3.2)
        ctx.roof(type="FLAT", add_border=True)
        ctx.feature("balcony", "front_walls", storeys=(1, 2, 3),
                    size_offset={"size": [2.6, 1.2]}, array={"count": 4})
