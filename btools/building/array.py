import bpy 
from bpy.props import (
    IntProperty,
    FloatProperty
)

from ..utils import clamp


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
        col.prop(self, "spread", slider=True)


class ArrayGetSet:
    """ Provide getset redirection in classes that use ArrayProperty
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

def clamp_count(face_width, frame_width, prop):
    prop.count = clamp(prop.count, 1, int(face_width / frame_width) - 1)


def array_fit_elements(prop):
    """ Ensure that array elements fit nicely within parent faces
    """
    # -- Make each element in array fit into the parent
    parent_width = prop["wall_dimensions"][0]
    if prop.width > parent_width / prop.count:
        prop.width = parent_width / prop.count

    # -- keep horizontal offset within bounds of parent face
    element_width = parent_width / prop.count
    item_width = prop.width
    max_offset = (element_width / 2) - (item_width / 2)
    prop.offsetx = clamp(
        prop.offsetx, -max_offset, max_offset
    )

def get_array_edges(afaces, prop):
    """ Get the edges between array faces
    """
    if prop.count < 2:
        return []

    result = []
    edges = list({e for f in afaces for e in f.edges})
    for e in edges:
        if all(f in afaces for f in e.link_faces):
            result.append(e)
    return result


def spread_array_edges(bm, edges, median, prop):
    """ Move an array split edge nearer/away from center
    """
    for e in edges:
        em = calc_edge_median(e)
        diff = Vector((em - median).to_tuple(3)).normalized()
        diff.z = 0
        bmesh.ops.translate(bm, verts=e.verts, vec=diff*prop.spread)


def spread_array_face(bm, f, median, prop):
    """ Move split face nearer/away from center
    """
    fm = f.calc_center_median()
    corner_verts = list(f.verts)
    split_verts = []
    for v in corner_verts:
        split_edge = [e for e in v.link_edges if e not in f.edges].pop()
        split_verts.append(split_edge.other_vert(v))
    
    vts = corner_verts + split_verts
    diff = Vector((fm - median).to_tuple(3)).normalized()
    diff.z = 0
    bmesh.ops.translate(bm, verts=vts, vec=diff*prop.spread)