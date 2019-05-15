import bpy

DEFAULT_MATERIALS = {
    "mat_slab": (0.208, 0.183, 0.157),
    "mat_wall": (0.190, 0.117, 0.04),
    "mat_window_frame": (0.8, 0.8, 0.8),
    "mat_window_pane": (0, 0.6, 0),
    "mat_window_bars": (0, 0.7, 0),
    "mat_window_glass": (0, 0.1, 0.6),
    "mat_door_frame": (0.8, 0.8, 0.8),
    "mat_door_pane": (0.13, 0.05, 0),
    "mat_door_groove": (0.13, 0.05, 0),
    "mat_door_glass": (0, 0.1, 0.6),
}


def create_default_materials(obj):
    for name, color in DEFAULT_MATERIALS.items():
        if has_material(obj, name):
            continue

        # -- the material exists but not linked to object
        # -- happens due to undo-redo esp when changing object data
        if name in bpy.data.materials.keys():
            mat = bpy.data.materials[name]
            link_mat(obj, mat)
            continue

        mat = bpy.data.materials.new(obj.name + "_" + name)
        mat.diffuse_color = color + (1,)
        mat.use_nodes = True
        link_mat(obj, mat)


def link_mat(obj, mat):
    if not has_material(obj, mat.name):
        obj.data.materials.append(mat)


def has_material(obj, name):
    return name in obj.data.materials.keys()


def set_material(faces, name_or_index):
    obj = bpy.context.object
    if not obj:
        return

    mat_idx = -1
    if isinstance(name_or_index, str):
        name = name_or_index
        for i, mat in enumerate(obj.data.materials):
            if name in mat.name:
                mat_idx = i
                break
    elif isinstance(name_or_index, int):
        mat_idx = name_or_index

    if mat_idx == -1:
        return

    for f in faces:
        f.material_index = mat_idx
