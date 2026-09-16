"""Library — corniced facade, tall arched reading-room windows"""

TAGS = ('fp-rect', 'roof-flat', 'cornice', 'window-arch', 'standard')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=16.0, length=12.0)
        ctx.floors(floor_count=2, floor_height=4.2, add_cornice=True,
                   cornice_size=0.25)
        ctx.roof(type="FLAT")
        ctx.windows(fill_type="GLASS_PANES", add_arch=True,
                    size_offset={"size": [1.8, 2.6]})
