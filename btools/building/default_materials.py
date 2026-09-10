"""Default PBR materials per material group.

Every material group gets a lightweight procedural node material (stucco
walls, tiled roof, painted door, real glass, metal railings...) so generated
buildings start life looking production-adjacent in both Cycles and EEVEE.
Flat `diffuse_color` values are kept in sync for workbench / reference
renders.

Materials are cached per blend session and reused across builds; set the
`bt_pbr` id-prop to force a rebuild when the palette version changes.
"""

import bpy

PALETTE_VERSION = 2

# -- flat colors per material group: syncs workbench / reference renders
#    with the node-based Base Color used in Cycles/EEVEE
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


def _rgb(color):
    return (*color, 1.0)


def _principled(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def _base_nodes(mat, color, roughness, metallic=0.0):
    """Principled + object-mapped noise bump; returns the bsdf node."""
    nt = mat.node_tree
    bsdf = _principled(mat)
    bsdf.inputs["Base Color"].default_value = _rgb(color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic

    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    objinfo = nt.nodes.new("ShaderNodeObjectInfo")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    # -- per-object random rotation/offset breaks tiling repetition
    nt.links.new(objinfo.outputs["Random"], mapping.inputs["Rotation"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bsdf, noise


def _mat_stucco(mat):
    bsdf = _base_nodes(mat, MATGROUP_COLORS["walls"], 0.85)
    bsdf.inputs["Specular IOR Level"].default_value = 0.2


def _mat_concrete(mat, color=None):
    _base_nodes(mat, color or MATGROUP_COLORS["slabs"], 0.9)


def _mat_roof(mat):
    color = MATGROUP_COLORS["roof"]
    _base_nodes(mat, color, 0.7)
    nt = mat.node_tree
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.5
    brick.inputs["Scale"].default_value = 6.0
    brick.inputs["Mortar Size"].default_value = 0.012
    brick.inputs["Color1"].default_value = _rgb(color)
    brick.inputs["Color2"].default_value = (
        color[0] * 0.8,
        color[1] * 0.75,
        color[2] * 0.72,
        1.0,
    )
    brick.inputs["Mortar"].default_value = (0.12, 0.10, 0.09, 1.0)
    # -- stretch along the roof slope for a tile/seam reading
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0, 4.0, 1.0)
    coord = next(n for n in nt.nodes if n.type == "TEX_COORDINATE")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    nt.links.new(brick.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


def _mat_door(mat):
    color = MATGROUP_COLORS["door"]
    bsdf = _base_nodes(mat, color, 0.45)
    nt = mat.node_tree
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 8.0
    wave.inputs["Distortion"].default_value = 6.0
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.3, 0.3, 4.0)
    coord = next(n for n in nt.nodes if n.type == "TEX_COORDINATE")
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (
        color[0] * 0.7,
        color[1] * 0.7,
        color[2] * 0.7,
        1.0,
    )
    ramp.color_ramp.elements[1].color = _rgb(color)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])


def _mat_frame(mat):
    _base_nodes(mat, MATGROUP_COLORS["frame"], 0.35, metallic=0.8)


def _mat_glass(mat, color=None):
    bsdf = _base_nodes(mat, color or MATGROUP_COLORS["window"], 0.05)
    bsdf.inputs["Transmission Weight"].default_value = 1.0
    bsdf.inputs["IOR"].default_value = 1.52


def _mat_railing(mat, color=None):
    _base_nodes(mat, color or MATGROUP_COLORS["railing_posts"], 0.35, metallic=0.9)


_BUILDERS = {
    "walls": _mat_stucco,
    "columns": lambda m: _mat_concrete(m, MATGROUP_COLORS["columns"]),
    "slabs": _mat_concrete,
    "roof": _mat_roof,
    "roof_hangs": lambda m: _mat_concrete(m, MATGROUP_COLORS["roof_hangs"]),
    "door": _mat_door,
    "door_panels": lambda m: _mat_door(m),
    "door_panes": lambda m: _mat_glass(m, (0.56, 0.37, 0.19)),
    "door_louvers": lambda m: _mat_door(m),
    "frame": _mat_frame,
    "window": _mat_glass,
    "window_bars": _mat_frame,
    "window_panes": lambda m: _mat_glass(m, (0.56, 0.76, 0.88)),
    "window_louvers": lambda m: _mat_glass(m, (0.56, 0.76, 0.88)),
    "balcony": lambda m: _mat_concrete(m, MATGROUP_COLORS["balcony"]),
    "railing_posts": _mat_railing,
    "railing_walls": lambda m: _mat_railing(m, MATGROUP_COLORS["railing_walls"]),
    "railing_rails": _mat_railing,
    "stairs": lambda m: _mat_concrete(m, MATGROUP_COLORS["stairs"]),
    "custom": lambda m: _mat_concrete(m, MATGROUP_COLORS["custom"]),
}


def _material(name):
    """Get-or-build the BT_ material for a group name."""
    mat = bpy.data.materials.get(name)
    if mat is not None and mat.get("bt_pbr") == PALETTE_VERSION:
        return mat

    mat = bpy.data.materials.new(name) if mat is None else mat
    mat.use_nodes = True

    group = name.removeprefix("BT_")
    color = MATGROUP_COLORS.get(group, FALLBACK_COLOR)
    builder = _BUILDERS.get(group)
    if builder:
        builder(mat)
    else:
        bsdf = _base_nodes(mat, color, 0.8)
        del bsdf

    mat.diffuse_color = _rgb(color)  # workbench / viewport display color
    mat["bt_pbr"] = PALETTE_VERSION
    return mat


def apply_default_materials(obj, untagged=True):
    """Assign a BT_<group> material to every face by its material group.

    Faces without a group get the bright BT_Untagged alarm material when
    `untagged` is set, otherwise the neutral BT_Default.
    """
    me = obj.data
    me.materials.clear()

    group_names = [mt.name for mt in getattr(obj, "bt_materials", [])]
    layer = me.attributes.get(".bt_material_group_index")

    default = _material("BT_Default")
    me.materials.append(default)

    untagged_mat = _material("BT_Untagged") if untagged else default
    me.materials.append(untagged_mat)
    untagged_index = len(me.materials) - 1

    if layer is None:
        return

    vals = [0] * len(me.polygons)
    layer.data.foreach_get("value", vals)
    slot_cache = {}

    def slot_for(group_index):
        if group_index not in slot_cache:
            name = (
                "BT_" + group_names[group_index]
                if group_index < len(group_names)
                else "BT_Untagged"
            )
            me.materials.append(_material(name))
            slot_cache[group_index] = len(me.materials) - 1
        return slot_cache[group_index]

    for i, g in enumerate(vals):
        if 0 <= g < len(group_names):
            me.polygons[i].material_index = slot_for(g)
        else:
            me.polygons[i].material_index = untagged_index
