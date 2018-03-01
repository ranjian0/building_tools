
## =======================================================
#
#           BALCONY UTILS
#
## =======================================================

"""
TODO:
    - Corner posts need some more work for alignment
"""


def make_balcony(width, railing, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, has_corner_posts, delete_faces, fill, hsplit,
                 vsplit, soffx, soffy, soffz, has_split):
    """ Extrudes selected faces outwards and adds railings to outer edges """

    # Get current edit mesh
    me = get_edit_mesh()
    bm = bmesh.from_edit_mesh(me)

    # Find selected face
    faces = [f for f in bm.faces if f.select]
    if not faces:
        return

    for f in faces:
        # Split the faces
        if has_split:
            f = split(bm, f, vsplit, hsplit, soffx, soffy, soffz)

        # Extrude
        f.select = False
        ret = bmesh.ops.extrude_face_region(bm, geom=[f])
        verts = filter_geom(ret['geom'], BMVert)
        bmesh.ops.translate(bm, verts=verts, vec=-f.normal * width)

        if railing:
            face = filter_geom(ret['geom'], BMFace)[0]
            top_verts1 = list(face.verts)
            top_verts1.sort(key=lambda v: v.co.z)
            top_verts2 = list(f.verts)
            top_verts2.sort(key=lambda v: v.co.z)

            top_face = bm.faces.get(top_verts1[2:] + top_verts2[2:])
            reject = bm.edges.get(top_verts2[2:])

            edges = set(list(top_face.edges)).difference([reject])
            make_railing(bm, edges, pw, ph, pd, rw, rh, rd, ww, wh, cpw, cph, has_corner_posts, delete_faces, fill)

        bmesh.ops.delete(bm, geom=[f], context=3)
    bmesh.update_edit_mesh(me, True)

