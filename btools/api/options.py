from enum import Enum
from dataclasses import dataclass

class ArchFunctionType(Enum):
    SINE = 'SINE'
    SPHERE = 'SPHERE'

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
    size: tuple[float, float] = (0.5, 0.5)
    offset: tuple[float, float] = (0.0, 0.0) 

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
    RECTANGULAR = 'RECTANGULAR'
    CIRCULAR = 'CIRCULAR'
    COMPOSITE = 'COMPOSITE'
    H_SHAPED = 'H-SHAPED'
    RANDOM = 'RANDOM'

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
    floor_height: float = 2.0
    add_slab: bool = True 
    add_columns: bool = False 
    slab_thickness: float = 0.2 
    slab_outsset: float = 0.1

class DoorFillType(Enum):
    NONE = 'NONE' 
    PANELS = 'PANELS'
    GLASS_PANES = 'GLASS_PANES'
    LOUVER = 'LOUVER'

@dataclass
class DoorOptions:
    arch: ArchOptions = ArchOptions()
    array: ArrayOptions = ArrayOptions()
    size_offset: SizeOffsetOptions = SizeOffsetOptions()
    panel_fill: FillPanelOptions = FillPanelOptions()
    louver_fill: FillLouverOptions = FillLouverOptions()
    glass_fill: FillGlassPaneOptions = FillGlassPaneOptions()

    frame_thickness: float = 0.1
    frame_depth: float = 0.1
    door_depth: float = 0.05
    add_arch: bool = False
    fill_type: DoorFillType = DoorFillType.NONE
    double_door: bool = False


class WindowType(Enum):
    CIRCULAR = 'CIRCULAR'
    RECTANGULAR = 'RECTANGULAR'

class WindowFillType(Enum):
    NONE = 'NONE' 
    BAR = 'BAR'
    GLASS_PANES = 'GLASS_PANES'
    LOUVER = 'LOUVER'

@dataclass
class WindowOptions:
    arch: ArchOptions = ArchOptions()
    array: ArrayOptions = ArrayOptions()
    size_offset: SizeOffsetOptions = SizeOffsetOptions()
    bar_fill: FillBarOptions = FillBarOptions()
    louver_fill: FillLouverOptions = FillLouverOptions()
    glass_fill: FillGlassPaneOptions = FillGlassPaneOptions()

    type: WindowType = WindowType.RECTANGULAR
    frame_thickness: float = 0.1
    frame_depth: float = 0.1
    window_depth: float = 0.05
    resolution: int = 20 
    add_arch: bool = False 

@dataclass
class MultigroupOptions:
    arch: ArchOptions = ArchOptions()
    array: ArrayOptions = ArrayOptions()
    size_offset: SizeOffsetOptions = SizeOffsetOptions()

    bar_fill_window: FillBarOptions = FillBarOptions()
    panel_fill_window: FillPanelOptions = FillPanelOptions()
    louver_fill_window: FillLouverOptions = FillLouverOptions()
    glass_fill_window: FillGlassPaneOptions = FillGlassPaneOptions()

    panel_fill_door: FillPanelOptions = FillPanelOptions()
    louver_fill_door: FillLouverOptions = FillLouverOptions()
    glass_fill_door: FillGlassPaneOptions = FillGlassPaneOptions()

    frame_thickness: float = 0.1
    frame_depth: float = 0.1
    dw_depth: float = 0.05 
    add_arch: bool = False
    components: str = 'dw'
    show_door_fill: bool = False 
    fill_type_door: DoorFillType = DoorFillType.NONE
    show_window_fill: bool = False 
    fill_type_window: WindowFillType = WindowFillType.NONE 

class RoofType(Enum):
    FLAT = 'FLAT'
    GABLE = 'GABLE'
    HIP = 'HIP'

class GableRoofType(Enum):
    OPEN = 'OPEN'
    BOX = 'BOX'

@dataclass
class RoofOptions:
    type: RoofType = RoofType.HIP
    gable_type: GableRoofType = GableRoofType.OPEN
    thickness: float = 0.1
    outset: float = 0.1
    height: float = 1.0
    add_border: bool = True 
    border: float = 0.1


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
    POSTS = 'POSTS'
    RAILS = 'RAILS'
    WALL = 'WALL'
@dataclass
class RailOptions:
    fill: RailFillType = RailFillType.POSTS
    corner_post_width: float = 0.1
    corner_post_height: float = 0.7
    has_corner_post: bool = True
    offset: float = 0.05

    post_fill: PostFillOptions = PostFillOptions()
    rail_fill: RailFillOptions = RailFillOptions()
    wall_fill: WallFillOptions = WallFillOptions()

    bottom_rail: bool = True 
    bottom_rail_offset: float = 0.0



@dataclass
class BalconyOptions:
    rail: RailOptions = RailOptions()
    array: ArrayOptions = ArrayOptions()
    size_offset: SizeOffsetOptions = SizeOffsetOptions()

    depth: float = 1.0
    depth_offset: float = 0.0
    has_railing: bool = True 
    group_selection: bool = True