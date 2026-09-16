"""Town hall — hip roof, columned facade, cornice"""

TAGS = ('fp-rect', 'roof-hip', 'columns', 'cornice', 'showcase')
TIER = 'standard'


def build(ctx):
    def build(ctx):
        ctx.floorplan(type="RECTANGULAR", width=16.0, length=11.0)
        ctx.floors(floor_count=2, floor_height=3.8, add_cornice=True,
                   add_columns=True, add_column_base=True,
                   add_column_capital=True)
        ctx.roof(type="HIP", height=2.4)
