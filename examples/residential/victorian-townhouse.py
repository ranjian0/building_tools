"""Victorian townhouse — mansard roof, arched windows, ornate door"""

TAGS = ('fp-rect', 'roof-mansard', 'door-arch', 'window-arch', 'casing', 'bevel', 'standard')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=8.0, length=10.0)
    ctx.floors(floor_count=3, floor_height=3.1)
    ctx.roof(type="MANSARD", lower_height=1.6, upper_height=1.2)
    ctx.windows(fill_type="GLASS_PANES", add_arch=True)
    ctx.doors(add_arch=True, add_casing=True)
