import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty

from ...utils import get_scaled_unit


class BatchProperty(bpy.types.PropertyGroup):
    roof_type_attr: StringProperty(
        name="Roof Type Attr",
        default="roof:shape",
        description="Custom property holding the roof shape (OSM roof:shape "
        "vocabulary; also reads BlenderGIS exports)",
    )

    height_attr: StringProperty(
        name="Height Attr",
        default="height",
        description="Custom property holding the total height in meters",
    )

    levels_attr: StringProperty(
        name="Levels Attr",
        default="building:levels",
        description="Custom property holding the storey count",
    )

    roof_height_attr: StringProperty(
        name="Roof Height Attr",
        default="roof:height",
        description="Custom property holding the roof rise in meters",
    )

    roof_angle_attr: StringProperty(
        name="Roof Angle Attr",
        default="roof:angle",
        description="Custom property holding the roof pitch in degrees",
    )

    floor_height_attr: StringProperty(
        name="Floor Height Attr",
        default="floor_height",
        description="Custom property holding the storey height in meters",
    )

    storey_height: FloatProperty(
        name="Storey Height",
        min=get_scaled_unit(1.0),
        max=get_scaled_unit(20.0),
        default=get_scaled_unit(3.0),
        unit="LENGTH",
        description="Fallback storey height (OSM 3m-per-level convention)",
    )

    default_floor_count: IntProperty(
        name="Default Floors",
        min=1,
        max=100,
        default=2,
        description="Storey count when no attribute resolves",
    )

    default_roof_type: bpy.props.EnumProperty(
        name="Default Roof",
        items=[
            ("FLAT", "Flat", "", 0),
            ("GABLE", "Gable", "", 1),
            ("HIP", "Hip", "", 2),
            ("FLAT_TOP", "Flat Top", "", 3),
            ("MANSARD", "Mansard", "", 4),
            ("HALF_HIP", "Half Hip", "", 5),
        ],
        default="HIP",
        description="Roof type when no attribute resolves",
    )

    default_roof_height: FloatProperty(
        name="Default Roof Height",
        min=get_scaled_unit(0.1),
        max=get_scaled_unit(10.0),
        default=get_scaled_unit(1.0),
        unit="LENGTH",
        description="Roof height when no attribute resolves",
    )

    window_density: FloatProperty(
        name="Window Density",
        min=0.0,
        max=1.0,
        default=0.0,
        subtype="PERCENTAGE",
        description="Fraction of upper-storey wall faces that receive a "
        "window (0 disables the window pass)",
    )

    seed: IntProperty(
        name="Seed",
        min=0,
        default=0,
        description="Batch seed: per-building sub-streams derive from it, so "
        "the same seed reproduces the same batch",
    )

    dry_run: BoolProperty(
        name="Dry Run",
        default=False,
        description="Validate and report only; no buildings created",
    )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.label(text="Attribute Names:")
        col.prop(self, "roof_type_attr")
        col.prop(self, "height_attr")
        col.prop(self, "levels_attr")
        col.prop(self, "roof_height_attr")
        col.prop(self, "roof_angle_attr")
        col.prop(self, "floor_height_attr")

        col = layout.column(align=True)
        col.label(text="Fallbacks:")
        col.prop(self, "storey_height")
        col.prop(self, "default_floor_count")
        col.prop(self, "default_roof_type")
        col.prop(self, "default_roof_height")

        col = layout.column(align=True)
        col.label(text="Windows:")
        col.prop(self, "window_density")
        col.prop(self, "seed")
        col.prop(self, "dry_run")
