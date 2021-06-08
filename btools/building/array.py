import bpy
import bmesh
from bpy.props import IntProperty, FloatProperty

from ..utils import (
    clamp,
    VEC_DOWN,
    sort_edges,
    sort_faces,
    edge_is_vertical,
    calc_edge_median,
    calc_faces_median,
    calc_face_dimensions,
)

from mathutils import Vector


class ArrayProperty(bpy.types.PropertyGroup):

    count: IntProperty(
        name="Count",
        min=1,
        max=100,
        default=1,
        description="Number of elements",
    )

    spread: FloatProperty(
        name="Spread",
        min=-1.0,
        max=1.0,
        default=0.0,
        description="Relative distance between elements",
    )

    def draw(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "count")

        rl = col.row(align=True)
        rl.enabled = self.count > 1
        rl.prop(self, "spread", slider=True)


class ArrayGetSet:
    """Provide getset redirection in classes that use ArrayProperty
    i.e allow for Parent.count instead of Parent.array.count
    """

    @property
    def count(self):
        return self.array.count

    @count.setter
    def count(self, val):
        self.array.count = val

    @property
    def spread(self):
        return self.array.spread

    @spread.setter
    def spread(self, val):
        self.array.spread = val


def clamp_array_count(face, prop):
    """Keep array count to minimum number that fits all elements in the parent face"""
    prop.count = clamp(prop.count, 1, calc_face_dimensions(face)[0] // prop.width)


def get_array_split_edges(afaces):
    """Return all the split edges between arrayed faces"""
    result = []
    edges = list({e for f in afaces for e in f.edges})
    for e in edges:
        if len(e.link_faces) != 2:
            continue

        if all(f in afaces for f in e.link_faces):
            result.append(e)
    return result


def spread_array(bm, split_edges, split_faces, max_width, prop):
    """perform spreading for array faces"""
    if prop.count == 1:
        return

    normal = split_faces[0].normal.copy()
    median = calc_faces_median(split_faces)

    right = normal.cross(VEC_DOWN)
    split_edges = sort_edges(split_edges, right)
    split_faces = sort_faces(split_faces, right)

    # -- map each split edge to its neighbouring faces
    edge_neighbour_face_map = {
        edge:[split_faces[idx], split_faces[idx+1]]
        for idx, edge in enumerate(split_edges)
    }

    def get_all_splitface_verts(f):
        corner_verts = list(f.verts)
        split_verts = []
        for v in corner_verts:
            split_edge = [e for e in v.link_edges if e not in f.edges].pop()
            if edge_is_vertical(split_edge):
                split_verts.append(split_edge.other_vert(v))
        return corner_verts + split_verts

    # XXX Fixme if you can
    # HACK(ranjian0) Setting spread to 1.0 causes multigroup jitters
    prop.spread = clamp(prop.spread, -1, 0.9999)

    # -- spread the array faces
    for f in split_faces:
        fm = f.calc_center_median()
        vts = get_all_splitface_verts(f)

        diff = Vector((fm - median).to_tuple(3))
        spread_factor = (max_width - prop.width) * (diff.length / max_width)
        if prop.spread > 0:
            spread_factor /= prop.count - 1
        bmesh.ops.translate(bm, verts=vts, vec=diff.normalized() * prop.spread * spread_factor)

    # -- move the split edges to the middle of their neighbour faces
    for edge in split_edges:
        neighbours = edge_neighbour_face_map[edge]
        nmedian = calc_faces_median(neighbours)

        diff = nmedian - calc_edge_median(edge)
        diff.z = 0  # XXX prevent vertical offset from influencing split edges
        bmesh.ops.translate(bm, verts=edge.verts, vec=diff)
