"""A-frame cabin — very steep gable from a 60-degree pitch"""

TAGS = ('fp-rect', 'roof-gable', 'slope-angle', 'simple')
TIER = 'standard'


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=8.0, length=7.0)
    ctx.floors(floor_count=2, floor_height=2.6)
    ctx.roof(type="GABLE", slope_mode="ANGLE", slope_angle=1.0472)  # 60 deg
    ctx.windows(fill_type="GLASS_PANES")
