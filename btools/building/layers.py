from enum import IntEnum, StrEnum, auto


class BTLayers(StrEnum):
  MATERIAL_GROUP  = ".bt_material_group_index"
  FRAME_FACE_TYPE = ".bt_frame_face_type"


class FrameFaceLayer(IntEnum):
    DOOR = auto()
    WINDOW = auto()
    ARCH = auto()
    FRAME = auto()


def ensure_layers_for_object(obj):
    """
    Ensures that all necessary persistent BMesh custom data layers
    for Building Tools are present on the mesh.
    Call this when an object is first processed by a btools operator.
    """
    if not obj.data.attributes.get(BTLayers.MATERIAL_GROUP.value): 
        obj.data.attributes.new(
            name=BTLayers.MATERIAL_GROUP.value,
            type="INT",
            domain="FACE")

    if not obj.data.attributes.get(BTLayers.FRAME_FACE_TYPE.value):
        obj.data.attributes.new(
            name=BTLayers.FRAME_FACE_TYPE.value,
            type="INT",
            domain="FACE")
