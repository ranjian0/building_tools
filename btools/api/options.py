from dataclasses import dataclass, field
from enum import Enum


class ArchFunctionType(Enum):
    SINE = "SINE"
    SPHERE = "SPHERE"


@dataclass
class ArchOptions:
    resolution: int = 6
    depth: float = 0.05
    height: float = 0.1
    function: ArchFunctionType = ArchFunctionType.SPHERE


@dataclass
class ArrayOptions:
    count: int = 1
    spread: float = 0.0


@dataclass
class SizeOffsetOptions:
    # None = use the feature's operator default (computed by SizeOffsetProperty
    # init() from the target face; e.g. door = (1.0, 1.8), window = (1.0, 1.0))
    size: tuple | None = None
    offset: tuple | None = None


@dataclass
class FillPanelOptions:
    panel_count_x: int = 1
    panel_count_y: int = 1
    panel_border_size: float = 0.1
    panel_margin: float = 0.05
    panel_depth: float = 0.01


@dataclass
class FillBarOptions:
    bar_count_x: int = 1
    bar_count_y: int = 1
    bar_width: float = 0.1
    bar_depth: float = 0.04


@dataclass
class FillLouverOptions:
    louver_count: int = 10
    louver_border: float = 0.01
    louver_margin: float = 0.1
    louver_depth: float = 0.05


@dataclass
class FillGlassPaneOptions:
    pane_count_x: int = 1
    pane_count_y: int = 1
    pane_margin: float = 0.1
    pane_depth: float = 0.1


class FloorPlanType(Enum):
    RECTANGULAR = "RECTANGULAR"
    CIRCULAR = "CIRCULAR"
    COMPOSITE = "COMPOSITE"
    H_SHAPED = "H-SHAPED"
    RANDOM = "RANDOM"


@dataclass
class FloorplanOptions:
    tw1: float = 1.0
    tw2: float = 1.0
    tw3: float = 1.0
    tw4: float = 1.0
    tl1: float = 1.0
    tl2: float = 1.0
    tl3: float = 1.0
    tl4: float = 1.0
    type: FloorPlanType = FloorPlanType.RECTANGULAR
    seed: int = 1
    width: float = 4.0
    length: float = 4.0
    radius: float = 1.0
    segments: int = 32
    tail_angle: float = 0.0
    extension_amount: int = 4
    random_extension_amount: bool = True


@dataclass
class FloorOptions:
    floor_count: int = 1
    floor_height: float = 2.7
    add_slab: bool = True
    add_columns: bool = False
    slab_thickness: float = 0.2
    slab_outset: float = 0.1
    wall_thickness: float = 0.0  # >0 creates the double-shell interior

    add_decoration: bool = False
    alternate_decoration: bool = False
    decoration_nb: int = 5
    decoration_padding: float = 0.01
    decoration_ratio: float = 1.0


class DoorFillType(Enum):
    NONE = "NONE"
    PANELS = "PANELS"
    GLASS_PANES = "GLASS_PANES"
    LOUVER = "LOUVER"


@dataclass
class DoorOptions:
    arch: ArchOptions = field(default_factory=ArchOptions)
    array: ArrayOptions = field(default_factory=ArrayOptions)
    size_offset: SizeOffsetOptions = field(default_factory=SizeOffsetOptions)
    panel_fill: FillPanelOptions = field(default_factory=FillPanelOptions)
    louver_fill: FillLouverOptions = field(default_factory=FillLouverOptions)
    glass_fill: FillGlassPaneOptions = field(default_factory=FillGlassPaneOptions)

    frame_thickness: float = 0.06
    frame_depth: float = 0.05
    door_depth: float = 0.045
    add_arch: bool = False
    fill_type: DoorFillType = DoorFillType.NONE
    double_door: bool = False
    add_bevel: bool = False
    bevel_width: float = 0.003
    add_casing: bool = False
    casing_width: float = 0.06
    casing_depth: float = 0.015
    add_hardware: bool = True
    handle_height: float = 1.05
    handle_style: str = "LEVER"


class WindowType(Enum):
    CIRCULAR = "CIRCULAR"
    RECTANGULAR = "RECTANGULAR"


class WindowFillType(Enum):
    NONE = "NONE"
    BAR = "BAR"
    GLASS_PANES = "GLASS_PANES"
    LOUVER = "LOUVER"


@dataclass
class WindowOptions:
    arch: ArchOptions = field(default_factory=ArchOptions)
    array: ArrayOptions = field(default_factory=ArrayOptions)
    size_offset: SizeOffsetOptions = field(default_factory=SizeOffsetOptions)
    bar_fill: FillBarOptions = field(default_factory=FillBarOptions)
    louver_fill: FillLouverOptions = field(default_factory=FillLouverOptions)
    glass_fill: FillGlassPaneOptions = field(default_factory=FillGlassPaneOptions)

    type: WindowType = WindowType.RECTANGULAR
    frame_thickness: float = 0.06
    frame_depth: float = 0.05
    window_depth: float = 0.05
    resolution: int = 32
    add_arch: bool = False
    fill_type: WindowFillType = WindowFillType.NONE
    add_bevel: bool = False
    bevel_width: float = 0.003
    add_casing: bool = False
    casing_width: float = 0.06
    casing_depth: float = 0.015


@dataclass
class MultigroupOptions:
    arch: ArchOptions = field(default_factory=ArchOptions)
    array: ArrayOptions = field(default_factory=ArrayOptions)
    size_offset: SizeOffsetOptions = field(default_factory=SizeOffsetOptions)

    bar_fill_window: FillBarOptions = field(default_factory=FillBarOptions)
    panel_fill_window: FillPanelOptions = field(default_factory=FillPanelOptions)
    louver_fill_window: FillLouverOptions = field(default_factory=FillLouverOptions)
    glass_fill_window: FillGlassPaneOptions = field(
        default_factory=FillGlassPaneOptions
    )

    panel_fill_door: FillPanelOptions = field(default_factory=FillPanelOptions)
    louver_fill_door: FillLouverOptions = field(default_factory=FillLouverOptions)
    glass_fill_door: FillGlassPaneOptions = field(default_factory=FillGlassPaneOptions)

    frame_thickness: float = 0.1
    frame_depth: float = 0.1
    dw_depth: float = 0.05
    add_arch: bool = False
    add_hardware: bool = True
    components: str = "dw"
    window_height: float = 1.0
    show_door_fill: bool = False
    fill_type_door: DoorFillType = DoorFillType.NONE
    show_window_fill: bool = False
    fill_type_window: WindowFillType = WindowFillType.NONE


class RoofType(Enum):
    FLAT = "FLAT"
    GABLE = "GABLE"
    HIP = "HIP"
    FLAT_TOP = "FLAT_TOP"
    MANSARD = "MANSARD"
    HALF_HIP = "HALF_HIP"


class GableRoofType(Enum):
    OPEN = "OPEN"
    BOX = "BOX"


class RoofSlopeMode(Enum):
    HEIGHT = "HEIGHT"
    ANGLE = "ANGLE"
    PERCENTAGE = "PERCENTAGE"


@dataclass
class RoofOptions:
    type: RoofType = RoofType.HIP
    gable_type: GableRoofType = GableRoofType.OPEN
    thickness: float = 0.1
    outset: float = 0.1
    height: float = 1.0
    slope_mode: RoofSlopeMode = RoofSlopeMode.HEIGHT
    slope_angle: float = 0.6108652  # math.radians(35), pitch of the roof planes
    slope_percentage: float = 70.0
    flat_height: float = 0.8
    lower_height: float = 0.8
    upper_height: float = 0.4
    ridge_fraction: float = 0.5
    edge_weights: str | None = None  # comma-separated per-edge pitch degrees
    add_border: bool = True
    border: float = 0.1
    add_gutters: bool = False
    gutter_size: float = 0.08
    add_chimney: bool = False
    add_ridge_cap: bool = True
    coping_size: float = 0.02


@dataclass
class PostFillOptions:
    size: float = 0.05
    density: float = 0.5


@dataclass
class RailFillOptions:
    size: float = 0.05
    density: float = 0.4


@dataclass
class WallFillOptions:
    width: float = 0.075


class RailFillType(Enum):
    POSTS = "POSTS"
    RAILS = "RAILS"
    WALL = "WALL"


@dataclass
class RailOptions:
    fill: RailFillType = RailFillType.POSTS
    corner_post_width: float = 0.1
    corner_post_height: float = 0.7
    has_corner_post: bool = True
    offset: float = 0.05

    post_fill: PostFillOptions = field(default_factory=PostFillOptions)
    rail_fill: RailFillOptions = field(default_factory=RailFillOptions)
    wall_fill: WallFillOptions = field(default_factory=WallFillOptions)

    bottom_rail: bool = True
    bottom_rail_offset: float = 0.0


@dataclass
class BalconyOptions:
    rail: RailOptions = field(default_factory=RailOptions)
    array: ArrayOptions = field(default_factory=ArrayOptions)
    size_offset: SizeOffsetOptions = field(default_factory=SizeOffsetOptions)

    depth: float = 1.0
    depth_offset: float = 0.0
    has_railing: bool = True
    group_selection: bool = True


class StairsBottomType(Enum):
    FILLED = "FILLED"
    BLOCKED = "BLOCKED"
    SLOPE = "SLOPE"


@dataclass
class StairsOptions:
    rail: RailOptions = field(default_factory=RailOptions)
    size_offset: SizeOffsetOptions = field(default_factory=SizeOffsetOptions)

    depth_offset: float = 0.0
    step_count: int = 3
    step_width: float = 0.2
    step_height: float = 0.12
    landing_width: float = 1.0
    landing: bool = True
    bottom: StairsBottomType = StairsBottomType.FILLED
    has_railing: bool = True


class FillType(Enum):
    PANELS = "PANELS"
    GLASS_PANES = "GLASS_PANES"
    LOUVER = "LOUVER"
    BAR = "BAR"


class FillComponentType(Enum):
    DOOR = "DOOR"
    WINDOW = "WINDOW"


@dataclass
class FillOptions:
    panel_fill: FillPanelOptions = field(default_factory=FillPanelOptions)
    glass_fill: FillGlassPaneOptions = field(default_factory=FillGlassPaneOptions)
    louver_fill: FillLouverOptions = field(default_factory=FillLouverOptions)
    bar_fill: FillBarOptions = field(default_factory=FillBarOptions)

    fill_type: FillType = FillType.PANELS
    comp: FillComponentType = FillComponentType.DOOR
