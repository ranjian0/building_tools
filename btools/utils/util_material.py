import bpy


def link_material(obj, mat):
    """link material mat to obj"""
    if not has_material(obj, mat.name):
        obj.data.materials.append(mat)


def has_material(obj, name):
    """check if obj has a material with name"""
    return name in obj.data.materials.keys()


def create_object_material(obj, mat_name):
    """Create a new material and link it to the given object"""
    if not has_material(obj, mat_name):
        if bpy.data.materials.get(mat_name, None):
            # XXX if material with this name already exists in another object
            # append the object name to this material name
            mat_name += ".{}".format(obj.name)

        mat = bpy.data.materials.new(mat_name)
        link_material(obj, mat)
        return mat
    return obj.data.materials.get(mat_name)


def uv_map_active_editmesh_selection(faces, method):
    """perform uv mapping on `faces` using the provided `method`"""
    # -- ensure we are in editmode
    if not bpy.context.object.mode == "EDIT":
        return

    # -- if faces are not selected, do selection
    selection_state = [f.select for f in faces]
    for f in faces:
        f.select_set(True)

    # -- perform mapping
    if method == "UNWRAP":
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    elif method == "CUBE_PROJECTION":
        bpy.ops.uv.cube_project(cube_size=0.5)

    # -- restore previous selection state
    for f, sel in zip(faces, selection_state):
        f.select_set(sel)
