"""Example btools rule file: a 2-storey gabled house with interiors."""


def build(ctx):
    ctx.floorplan(type="RECTANGULAR", width=10.0, length=8.0)
    ctx.floors(floor_count=2, floor_height=3.0, wall_thickness=0.25)
    ctx.roof(type="GABLE", height=1.8, add_gutters=True)
    ctx.interior(partition_mode="TREEMAP", room_count=4, inset=0.25)
    ctx.windows(storeys=(1,), fill_type="GLASS_PANES")
