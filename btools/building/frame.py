from .layers import BTLayers, FrameFaceLayer
from ..utils import extrude_face_region, validate

def add_frame_depth(
    bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal
):
    """Add depth to frame"""
    if depth == 0.0:
        return door_faces, window_faces, arch_faces, frame_faces

    new_door_faces = []
    new_window_faces = []
    new_arch_faces = []
    
    new_frame_faces_main = []
    new_frame_faces_shell = []

    face_type_layer = bm.faces.layers.int.get(BTLayers.FRAME_FACE_TYPE.value)
    try:
        valid_door_faces = validate(door_faces)
        valid_window_faces = validate(window_faces)
        valid_arch_faces = validate(arch_faces)
        valid_frame_faces = validate(frame_faces)

        for f in valid_door_faces:
            f[face_type_layer] = FrameFaceLayer.DOOR.value
        for f in valid_window_faces:
            f[face_type_layer] = FrameFaceLayer.WINDOW.value
        for f in valid_arch_faces:
            f[face_type_layer] = FrameFaceLayer.ARCH.value
        for f in valid_frame_faces:
            f[face_type_layer] = FrameFaceLayer.FRAME.value
        
        all_extrudable_faces = list(set(valid_door_faces + valid_window_faces + valid_arch_faces + valid_frame_faces))
        if not all_extrudable_faces:
            return door_faces, window_faces, arch_faces, frame_faces

        extruded_main_faces, surrounding_shell_faces = extrude_face_region(
            bm, all_extrudable_faces, -depth, normal 
        )
        new_frame_faces_shell.extend(surrounding_shell_faces)
        
        for f in validate(extruded_main_faces): 
            face_type_val = f[face_type_layer]
            if face_type_val == FrameFaceLayer.DOOR.value:
                new_door_faces.append(f)
            elif face_type_val == FrameFaceLayer.WINDOW.value:
                new_window_faces.append(f)
            elif face_type_val == FrameFaceLayer.ARCH.value:
                new_arch_faces.append(f)
            elif face_type_val == FrameFaceLayer.FRAME.value:
                new_frame_faces_main.append(f)
        
        final_frame_faces = new_frame_faces_main
        if depth < 0.0:
            final_frame_faces.extend(new_frame_faces_shell)

    finally:
        # -- reset the layer values to default for the next usage
        for f in bm.faces:
            f[face_type_layer] = -1


    return new_door_faces, new_window_faces, new_arch_faces, final_frame_faces
