

## =======================================================
#
#           STAIRCASE UTILS
#
## =======================================================

"""
TODO:
    - The stair case system was unfortunately developed before
      the railing system, theres a good chance most of the railing
      for the staircase can be done with railing utils

    - This system still needs alot of work to make it more extensible
      and dynamic, including some nasty bugfixes.

    - There are some really messy math intensive parts down there
      esp where you see alot of 'ifeven', its too hacky.
"""


def make_stair_case(bm, landings=3, landing_width=4, landing_length=2.5, landing_height=.25, l_offz=2, l_offy=4,
                    landing_sup_width=.25, landing_post_width=.1, landing_post_height=1, landing_post_density=.4,
                    landing_rail_width=.2, landing_rail_height=1, steps=5, step_gap=.25, step_sup_count=2,
                    step_sup_width=.2, step_post_height=1, step_post_width=.1, step_rail_width=.15,
                    has_landing_support=True, has_landing_rails=True, has_step_support=True, has_step_rails=True,
                    has_inner_step_rails=True, has_outer_step_rails=True):
    """ Make a complex staircase system with landings, supports, railings and beams"""

    ref = bpy.context.scene.cursor_location
    step_width = landing_width / 2
    step_length = (l_offy / steps) - (landing_length / 2) / steps
    step_height = (l_offz / steps)

    # Clamp step_gap
    if step_gap > step_height:
        step_gap = step_height

    for i in range(landings):

        # LANDING
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        land = cube(bm, landing_width, landing_length, landing_height)

        ply = ref.y + ifeven(i, l_offy, -landing_length / 2)
        plz = ref.z + ((i + 1) * l_offz)
        bmesh.ops.translate(bm, verts=land['verts'], vec=(ref.x, ply, plz))

        # Create supports for landing
        if has_landing_support:
            support_landing(bm, land, condition(i == 0, l_offz, l_offz * 2), landing_sup_width, landing_height)

        # Add rails for landing
        if has_landing_rails:
            is_top = True if i in [landings - 1, landings - 2] else False
            direction = ifeven(i, 1, -1)
            landing_rails(bm, land, direction, landing_rail_width, landing_post_height, landing_post_width,
                          landing_post_density, landing_sup_width, is_top or not has_landing_support)

        # STEPS
        # ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        for j in range(steps):
            step = cube(bm, step_width, step_length, step_height - step_gap)

            px = ref.x + ifeven(i, step_width / 2, -step_width / 2)
            py = ref.y + ifeven(i, (j * step_length) + step_length / 2,
                                -(j * step_length) + (l_offy - (landing_length / 2)) - step_length / 2)
            pz = ref.z + (j * step_height) + (i * l_offz) + step_height / 2
            bmesh.ops.translate(bm, verts=step['verts'], vec=(px, py, pz))

            # Add step railing
            if has_step_rails:
                step_posts(bm, step, step_post_width, step_post_height, has_inner_step_rails, has_outer_step_rails)

        if has_step_rails:
            sph = step_post_height
            srw = step_rail_width

            px_left = ref.x + ifeven(i, srw / 2, -step_width + srw / 2)
            px_right = ref.x + ifeven(i, step_width - srw / 2, -srw / 2)

            bpy_ = ref.y + ifeven(i, 0, l_offy - (landing_length / 2))
            tpy_ = ref.y + ifeven(i, l_offy - (landing_length / 2), 0)

            bpz = ref.z + sph + srw / 2 + (i * l_offz)
            tpz = ref.z + sph + srw / 2 + ((i + 1) * l_offz)

            left = [(px_left, bpy_, bpz), (px_left, tpy_, tpz)]
            right = [(px_right, bpy_, bpz), (px_right, tpy_, tpz)]

            rails = []
            if has_inner_step_rails:
                rails += ifeven(i, [left], [right])
            if has_outer_step_rails:
                rails += ifeven(i, [right], [left])
            step_railing(bm, rails, step_rail_width)

        # Create supports for steps
        if has_step_support:
            px = ifeven(i, ref.x, ref.x - step_width)

            # right and left
            bpy_ = ref.y + ifeven(i, step_length, l_offy - (landing_length / 2 + step_length))
            tpy_ = ref.y + ifeven(i, l_offy - landing_length / 2, 0)

            # bottom and top
            bpz = ref.z + (i * l_offz) + step_height / 2
            tpz = ref.z + ((i + 1) * l_offz) - step_height / 2

            support_steps(bm, (px, bpy_, bpz), (px, tpy_, tpz), step_sup_count, (step_height - step_gap) / 2,
                          step_width)

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # bmesh.update_edit_mesh(me, True)
    return bm


def support_landing(bm, land, support_height, support_width, landing_height):
    """ Create posts that support staircase landings """

    # Get bottom vertices
    bot_verts = sorted(land['verts'], key=lambda v: v.co.z)[:-4]
    ref = face_with_verts(bm, bot_verts).calc_center_median()

    support_height -= landing_height
    for v in bot_verts:
        off_x = -support_width / 2 if v.co.x > ref.x else support_width / 2
        off_y = -support_width / 2 if v.co.y > ref.y else support_width / 2

        px = v.co.x + off_x
        py = v.co.y + off_y
        pz = v.co.z - (support_height / 2)

        sup = cube(bm, support_width, support_width, support_height)
        bmesh.ops.translate(bm, verts=sup['verts'], vec=(px, py, pz))

        # delete bottom and top faces
        tverts = sorted(sup['verts'], key=lambda v: v.co.z)[4:]
        bverts = sorted(sup['verts'], key=lambda v: v.co.z)[:-4]
        faces = [face_with_verts(bm, v) for v in [tverts, bverts]]
        bmesh.ops.delete(bm, geom=faces, context=3)


def landing_rails(bm, land, _dir, rail_width, post_height, post_width, post_density, landing_sup_width, is_top):
    """ Create railing for landings of the staircase """

    def del_faces(post, top=True, bottom=True):
        # Delete top and bottom faces of post
        vts = post['verts']
        vts.sort(key=lambda v: v.co.z)
        tf, bf = face_with_verts(bm, vts[4:]), face_with_verts(bm, vts[:-4])
        faces = [] + condition(top, [tf], []) + condition(bottom, [bf], [])
        bmesh.ops.delete(bm, geom=faces, context=3)


        # Get top edges

    t_verts = sorted(land['verts'], key=lambda v: v.co.z)[4:]
    t_face = face_with_verts(bm, t_verts)
    edges = list(t_face.edges)

    # Determine valid edges for putting railing
    if _dir > 0:
        front_verts = sorted(t_verts, key=lambda v: v.co.y)[2:]
    else:
        front_verts = sorted(t_verts, key=lambda v: v.co.y)[:-2]
    valid = [e for v in front_verts for e in v.link_edges if e in edges]

    verts = list({v for e in valid for v in e.verts})
    face = face_with_verts(bm, verts)
    ref = face.calc_center_median()

    # Corner posts
    if is_top:
        for vert in verts:
            post = cube(bm, landing_sup_width, landing_sup_width, post_height - (rail_width / 2))

            off_x = -landing_sup_width / 2 if vert.co.x > ref.x else landing_sup_width / 2
            off_y = -landing_sup_width / 2 if vert.co.y > ref.y else landing_sup_width / 2
            pos = (vert.co.x + off_x, vert.co.y + off_y, vert.co.z + (post_height / 2) - (rail_width / 4))
            bmesh.ops.translate(bm, verts=post['verts'], vec=pos)

            # Delete bottom faces
            del_faces(post, False, True)

    for e in valid:
        # Rails
        # '''''

        # Calculate size and offsets
        cen = calc_edge_median(e)
        if len(set([v.co.x for v in e.verts])) == 1:
            # edge along y-axis
            size = (rail_width, e.calc_length(), rail_width)
            off_x, off_y = -rail_width / 2 if cen.x > ref.x else rail_width / 2, 0
        else:
            # edge along x-axis
            size = (e.calc_length(), rail_width, rail_width)
            off_x, off_y = 0, -rail_width / 2 if cen.y > ref.y else rail_width / 2

        rail = cube(bm, *size)
        pos = cen.x + off_x, cen.y + off_y, cen.z + post_height
        bmesh.ops.translate(bm, verts=rail['verts'], vec=pos)

        # Mid Posts
        # '''''''''
        num_posts = int((e.calc_length() / (post_width * 2)) * post_density)
        rng_y = sorted([v.co.y for v in e.verts])
        rng_x = sorted([v.co.x for v in e.verts])

        # Calculate positions and offsets
        if len(set(rng_y)) == 2:
            # edge along y-axis
            dx, dy = 0, (rng_y[1] - rng_y[0]) / (num_posts + 1)
            off_x, off_y = -post_width / 2 if cen.x > ref.x else post_width / 2, 0
        else:
            # edge along x-axis
            dx, dy = (rng_x[1] - rng_x[0]) / (num_posts + 1), 0
            off_x, off_y = 0, -post_width / 2 if cen.y > ref.y else post_width / 2

        for i in range(num_posts):
            px = rng_x[0] + off_x + (dx * (i + 1))
            py = rng_y[0] + off_y + (dy * (i + 1))
            pz = cen.z + (post_height / 2)

            mid_post = cube(bm, post_width, post_width, post_height - (rail_width / 2))
            bmesh.ops.translate(bm, verts=mid_post['verts'], vec=(px, py, pz - (rail_width / 4)))

            # Delete top and bottom faces
            del_faces(mid_post)


def support_steps(bm, bottom, top, scount, sw, step_width):
    """ Add support beams to the staircase steps """

    for i in range(scount):
        off_x = step_width / (scount + 1)

        edges = []
        for pos in [bottom, top]:
            sup = plane(bm, sw, sw)

            px, py, pz = pos
            px += ((i + 1) * off_x)
            trans = Matrix.Translation((px, py, pz))
            rot = Matrix.Rotation(radians(90), 4, 'X')
            bmesh.ops.transform(bm, verts=sup['verts'], matrix=trans * rot)

            edges.extend(list({e for v in sup['verts'] for e in v.link_edges}))
        bmesh.ops.bridge_loops(bm, edges=edges)


def step_posts(bm, step, pw, ph, inner, outer):
    """ Create posts on each stair step """

    def del_faces(post, top=True, bottom=True):
        # Delete top and bottom faces of post
        vts = post['verts']
        vts.sort(key=lambda v: v.co.z)
        tf, bf = face_with_verts(bm, vts[4:]), face_with_verts(bm, vts[:-4])
        faces = [] + condition(top, [tf], []) + condition(bottom, [bf], [])
        bmesh.ops.delete(bm, geom=faces, context=3)

    tverts = sorted(step['verts'], key=lambda v: v.co.z)[4:]
    tface = face_with_verts(bm, tverts)
    ref = tface.calc_center_median()

    edges = filter_vertical_edges(tface.edges, tface.normal)
    c = bpy.context.scene.cursor_location
    if ref.x > c.x:
        if not inner:
            edges = sorted(edges, key=lambda e: calc_edge_median(e).x)[1:]
        if not outer:
            edges = sorted(edges, key=lambda e: calc_edge_median(e).x)[:-1]
    else:
        if not inner:
            edges = sorted(edges, key=lambda e: calc_edge_median(e).x)[:-1]
        if not outer:
            edges = sorted(edges, key=lambda e: calc_edge_median(e).x)[1:]

    for e in edges:
        c = calc_edge_median(e)

        post = cube(bm, pw, pw, ph)
        off_x = -pw / 2 if c.x > ref.x else pw / 2
        off_y = -pw / 2 if c.y > ref.y else pw / 2
        pos = (c.x + off_x, c.y + off_y, c.z + (ph / 2))
        bmesh.ops.translate(bm, verts=post['verts'], vec=pos)

        del_faces(post)


def step_railing(bm, rails, rw):
    """ Create some railings on each stair step"""

    for rail in rails:
        edges = []
        for pos in rail:
            rail = plane(bm, rw, rw)

            trans = Matrix.Translation(pos)
            rot = Matrix.Rotation(radians(90), 4, 'X')
            bmesh.ops.transform(bm, verts=rail['verts'], matrix=trans * rot)

            edges.extend(list({e for v in rail['verts'] for e in v.link_edges}))
        bmesh.ops.bridge_loops(bm, edges=edges)


def update_sgap(self, context):
    if self.sgap > (self.l_offz / self.scount):
        self.sgap = self.l_offz / self.scount
    return None
