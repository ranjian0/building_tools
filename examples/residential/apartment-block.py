"""Apartment block — 5 storeys, balconies with railings, flat parapet"""

TAGS = ('fp-rect', 'roof-flat', 'balcony', 'windows', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=16.0, length=11.0)
    ctx.floors(floor_count=5, floor_height=3.0)
    ctx.roof(type="FLAT", add_border=True, border=0.3)
    ctx.windows(storeys=(1, 2, 3, 4), array={"count": 4}, fill_type="GLASS_PANES")
