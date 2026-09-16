"""Bank — columned portico, arched entry, cornice bands"""

TAGS = ('fp-rect', 'roof-hip', 'door-arch', 'columns', 'cornice', 'showcase')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=14.0, length=10.0)
        ctx.floors(floor_count=2, floor_height=4.0, add_cornice=True,
                   cornice_size=0.2, add_columns=True, add_column_base=True,
                   add_column_capital=True)
        ctx.roof(type="HIP", height=2.0)
        ctx.doors(add_arch=True, size_offset={"size": [2.4, 3.0]})
