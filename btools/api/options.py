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

