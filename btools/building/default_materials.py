"""Default materials per material group (start of #210).

Gives preset-built (and api-built) buildings a usable starting point: every
face tagged to a material group gets a flat `BT_<group>` material from the
palette. Materials are reused across builds (created once per blend session).
"""

import bpy

# -- flat palette per material group (mirrors the reference renderer)
MATGROUP_COLORS = {
    "walls": (0.66, 0.63, 0.59),
    "slabs": (0.52, 0.52, 0.55),
    "columns": (0.60, 0.60, 0.62),
    "roof": (0.60, 0.27, 0.19),
    "roof_hangs": (0.42, 0.19, 0.14),
    "door": (0.43, 0.27, 0.12),
    "door_panels": (0.56, 0.37, 0.19),
    "door_panes": (0.56, 0.37, 0.19),
    "door_louvers": (0.56, 0.37, 0.19),
    "frame": (0.13, 0.13, 0.14),
    "window": (0.42, 0.65, 0.82),
    "window_bars": (0.13, 0.13, 0.14),
    "window_panes": (0.56, 0.76, 0.88),
    "window_louvers": (0.56, 0.76, 0.88),
    "balcony": (0.78, 0.64, 0.28),
    "railing_posts": (0.25, 0.25, 0.28),
    "railing_walls": (0.36, 0.39, 0.43),
    "railing_rails": (0.25, 0.25, 0.28),
    "stairs": (0.63, 0.56, 0.46),
    "custom": (0.65, 0.45, 0.65),
}
FALLBACK_COLOR = (0.50, 0.50, 0.50)
UNTAGGED_COLOR = (0.90, 0.10, 0.10)


def _material(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = next(
            (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
        )
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = (*color, 1.0)  # viewport / workbench color
    return mat


def apply_default_materials(obj, untagged=True):
    """Assign a flat `BT_<group>` material to every face by its material
    group. Faces without a group are skipped unless `untagged` is set, in
    which case they get the bright BT_Untagged alarm color."""
    me = obj.data
    me.materials.clear()

    group_names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = me.attributes.get(".bt_material_group_index")

    slots = {}
    default = _material("BT_Default", FALLBACK_COLOR)
    me.materials.append(default)
    default_index = 0

    def slot_for(name, color):
        if name not in slots:
            me.materials.append(_material(name, color))
            slots[name] = len(me.materials) - 1
        return slots[name]

    if layer is None:
        return

    vals = [0] * len(me.polygons)
    layer.data.foreach_get("value", vals)
    untagged_index = slot_for("BT_Untagged", UNTAGGED_COLOR) if untagged else default_index

    for i, g in enumerate(vals):
        if 0 <= g < len(group_names):
            name = "BT_" + group_names[g]
            me.polygons[i].material_index = slot_for(
                name, MATGROUP_COLORS.get(group_names[g], FALLBACK_COLOR))
        else:
            me.polygons[i].material_index = untagged_index
