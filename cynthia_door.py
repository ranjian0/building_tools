
## =======================================================
#
#           DOOR UTILS
#
## =======================================================


# TODO:
#     - Please clean up this mess
#         - Subdivisions in the groove create artifacts
#     - Double door looks ugly - no offence
#     - more door types please - Its lonely up in here
#     - grooves cause issues when user removes doubles



class Door:

    def __init__(self, properties):
        self.props = properties

    def build(self):
        """ Build door geomerty from selected faces """
        pass



def grooved(bm, f, gcx=3, gcy=1, gt=.1, gd=.01, gw=1, goff=0):
    """ Create grooves on selected faces of bmesh (subdivide, inset, offset depth)"""

    # Create main groove to hold child grooves
    bmesh.ops.inset_individual(bm, faces=[f], thickness=gt)
    bmesh.ops.scale(bm, verts=list({v for e in f.edges for v in e.verts}), vec=(1, 1, gw))
    bmesh.ops.translate(bm, verts=list({v for e in f.edges for v in e.verts}), vec=(0, 0, goff))

    # Calculate edges to be subdivided
    n = f.normal
    vedgs = filter_vertical_edges(f.edges, n)
    hedgs = list((set(f.edges).difference(vedgs)))

    # Subdivide the edges
    res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=gcx)
    edgs = filter_geom(res1['geom_inner'], BMEdge)
    res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=gcy)

    # Get all groove faces
    vts = filter_geom(res2['geom_inner'], BMVert)
    faces = list(filter(lambda f: len(f.verts) == 4, {f for v in vts for f in v.link_faces if f.normal == n}))

    # Make groove
    bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)
    bmesh.ops.inset_individual(bm, faces=faces, thickness=gt / 2)

    v = list({v for f in faces for v in f.verts})
    bmesh.ops.translate(bm, verts=v, vec=n * gd)

    # Clean geometry
    vts2 = [v for e in filter_geom(res1['geom_split'], BMEdge) for v in e.verts]
    vts2.sort(key=lambda v: v.co.z)
    vts2 = vts2[2:len(vts2) - 2]

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0)
    bmesh.ops.dissolve_verts(bm, verts=list(set(vts + vts2)))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def door_panes(bm, f, pcx=2, pcy=2, pt=.01, pd=.01, offset=0.5, width=.7):
    n = f.normal
    v_edges = filter_vertical_edges(f.edges, n)
    res = bmesh.ops.subdivide_edges(bm, edges=v_edges, cuts=2)
    edges = filter_geom(res['geom_inner'], BMEdge)

    ret_face = min({f for e in edges for f in e.link_faces}, key=lambda f: f.calc_center_median().z)

    bmesh.ops.scale(bm, verts=list({v for e in edges for v in e.verts}), vec=(1, 1, width))
    bmesh.ops.translate(bm, verts=list({v for e in edges for v in e.verts}), vec=(0, 0, offset))

    # get pane face
    pane_face = list(set(list(edges)[0].link_faces).intersection(set(list(edges)[1].link_faces)))[-1]
    bmesh.ops.inset_individual(bm, faces=[pane_face], thickness=0.01)

    # cut panes
    vedgs = filter_vertical_edges(pane_face.edges, n)
    hedgs = list((set(pane_face.edges).difference(vedgs)))

    res1 = bmesh.ops.subdivide_edges(bm, edges=vedgs, cuts=pcx)
    edgs = filter_geom(res1['geom_inner'], BMEdge)
    res2 = bmesh.ops.subdivide_edges(bm, edges=hedgs + edgs, cuts=pcy)

    # panels
    e = filter_geom(res2['geom_inner'], BMEdge)
    pane_faces = list({f for ed in e for f in ed.link_faces})
    panes = bmesh.ops.inset_individual(bm, faces=pane_faces, thickness=pt)

    for f in pane_faces:
        bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * pd)

    return ret_face


def door(ft, fd, ift, ifd, has_double_door, panes, pcx, pcy, pt, pd, offset, width, groov, gcx, gcy, gt, gd, gw, goff,
         hsplit, vsplit, soffx, soffy, soffz, has_split):
    """ Simple door type (Double Door, Grooves, Window Panes at the top)"""

    # Get active mesh
    me = bpy.context.edit_object.data
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]

    for f in faces:
        # Split the faces
        if has_split:
            f = split(bm, f, vsplit, hsplit, soffx, soffy, soffz)

        f.select = False

        # -- Frame
        # Make frame inset - frame thickness
        bmesh.ops.inset_individual(bm, faces=[f], thickness=ft)

        # Make frame extrude - frame depth
        if fd > 0:
            ret = bmesh.ops.extrude_discrete_faces(bm, faces=[f])
            f = ret['faces'][0]
            bmesh.ops.translate(bm, verts=f.verts, vec=-f.normal * fd)

        # Double door
        if has_double_door:
            edgs = filter_horizontal_edges(f.edges, f.normal)
            ret = bmesh.ops.subdivide_edges(bm, edges=edgs, cuts=1)

            new_faces = list(filter_geom(ret['geom_inner'], BMEdge)[-1].link_faces)

        for face in new_faces if has_double_door else [f]:

            # create door outline
            if ift > 0:
                bmesh.ops.inset_individual(bm, faces=[face], thickness=ift)
                if ifd > 0:
                    ret = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
                    face = ret['faces'][0]
                    bmesh.ops.translate(bm, verts=face.verts, vec=-face.normal * ifd)

            if panes:
                face = door_panes(bm, face, pcx, pcy, pt, pd, offset, width)

            if groov:
                grooved(bm, face, gcx, gcy, gt, gd, gw, goff)

    bmesh.update_edit_mesh(me, True)

