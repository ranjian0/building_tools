

## =======================================================
#
#           ROOF UTILS
#
## =======================================================

def make_flat_roof(bm, thickness=.1, outset=.1):
    """ Create a flat extrusion on selected faces """

    # -- get selected edges    
    edges = [e for e in bm.edges if e.select]

    # -- extrude edges and scale outwards
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    verts = filter_geom(ret['geom'], BMVert)

    bmesh.ops.scale(bm, verts=verts, vec=(1 + outset, 1 + outset, 1))
    nedges = list(set([e for v in verts for e in v.link_edges if e.is_boundary]))

    # -- extrude edges upwards and fill face
    ret = bmesh.ops.extrude_edge_only(bm, edges=nedges)
    verts = filter_geom(ret['geom'], BMVert)
    edges = filter_geom(ret['geom'], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, thickness))

    bmesh.ops.contextual_create(bm, geom=edges)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def make_gable_roof(bm, height=.5, outset=.1, thickness=.1, orient='LEFT'):
    """ Create an open/box gable roof """
    '''
    This routine only works if a single quad face has been selected
    '''
    selected = [f for f in bm.faces if f.select]
    if len(selected) > 1 or len(selected[-1].verts) != 4:
        return
    selected[-1].select = False
    # -- extrude the face to height
    ret = bmesh.ops.extrude_face_region(bm, geom=selected)
    verts = filter_geom(ret['geom'], BMVert)
    edges = filter_geom(ret['geom'], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, height))
    bmesh.ops.delete(bm, geom=selected, context=3)

    # -- merge opposite edge verts
    if orient == 'LEFT':
        merge_edges = filter_vertical_edges(edges, Vector((0, 0, 1)))
    else:
        merge_edges = filter_horizontal_edges(edges, Vector((0, 0, 1)))

    for e in merge_edges:
        cen = calc_edge_median(e)
        bmesh.ops.pointmerge(bm, verts=list(e.verts), merge_co=cen)

    # -- now get roof boundary edges for offset
    maxz = max([v.co.z for v in bm.verts])
    top_verts = [v for v in bm.verts if v.co.z == maxz]
    faces = list(set([f for v in top_verts for f in v.link_faces if f.normal.z]))
    b_edges = [e for f in faces for e in f.edges if len(set(faces + list(e.link_faces))) != 2]

    loner_edge = list(set([e for f in faces for e in f.edges]).difference(b_edges))
    bmesh.ops.delete(bm, geom=loner_edge, context=2)

    ret = bmesh.ops.extrude_edge_only(bm, edges=b_edges)
    verts = filter_geom(ret['geom'], BMVert)

    bmesh.ops.scale(bm, verts=verts, vec=(1 + outset, 1 + outset, 1))
    nedges = list(set([e for v in verts for e in v.link_edges if e.is_boundary]))

    # -- extrude edges upwards and fill face
    ret = bmesh.ops.extrude_edge_only(bm, edges=nedges)
    verts = filter_geom(ret['geom'], BMVert)
    edges = filter_geom(ret['geom'], BMEdge)
    bmesh.ops.translate(bm, verts=verts, vec=(0, 0, thickness))

    if orient == 'LEFT':
        fill_edges = filter_vertical_edges(edges, Vector((0, 0, 1)))
        fill_edges.sort(key=lambda ed: calc_edge_median(ed).y)
    else:
        fill_edges = filter_horizontal_edges(edges, Vector((0, 0, 1)))
        fill_edges.sort(key=lambda ed: calc_edge_median(ed).x)

    bmesh.ops.contextual_create(bm, geom=fill_edges[:2])
    bmesh.ops.contextual_create(bm, geom=fill_edges[2:])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
