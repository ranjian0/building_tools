"""Bay-grid facade layer -- a CGA subset over the existing feature api.

Bay grids are horizontal subdivisions of a selector face. Each bay maps
to a feature placement through ``size_offset``: sizes and offsets are
absolute meters in the FACE-LOCAL frame (x runs left-to-right along the
wall, y up; offset is measured from the face center -- see
``SizeOffsetProperty`` and ``create_window_split``), so no world-space
math is needed and the layout follows the face regardless of rotation.

Rules sharing an ``align`` key derive the same grid per face: the first
rule to touch a face establishes the grid, later rules reuse it. This
keeps multi-rule facades (windows + balconies, shutters over windows)
aligned under floorplan scaling -- the hand-tuned ``array.count``
coupling it replaces breaks there.

Wall faces persist across feature applications (features extrude from
sub-faces without consuming the parent), so face indices and widths are
stable between rules and the align cache stays valid.
"""

from dataclasses import dataclass

__all__ = ["BayGrid", "bay_matches", "face_widths", "resolve_bay_grid"]


@dataclass
class BayGrid:
    """Horizontal bay layout for one face."""

    count: int
    face_width: float
    bay_width: float

    def center_offset(self, index):
        """Face-local x offset of a bay's center (from the face center)."""
        return -self.face_width / 2 + (index + 0.5) * self.bay_width

    def clamp_size(self, size):
        """Clamp a (width, height) rule size to fit inside a bay."""
        return (min(size[0], self.bay_width), size[1])


def resolve_bay_grid(face_width, bays, bay_width):
    """Bay grid for a face.

    bays      -- int count, or "fill" (as many bays as fit)
    bay_width -- required for "fill"; bays stretch to cover the face
                 evenly (CGA float/repeat-split semantics), so the grid
                 stays symmetric with no remainder strip.
    """
    if bays == "fill":
        if not bay_width or bay_width <= 0.0:
            raise ValueError('bays="fill" requires a positive bay_width')
        count = max(1, int(face_width // bay_width))
    else:
        count = max(1, int(bays))
    return BayGrid(count, face_width, face_width / count)


def bay_matches(index, count, where):
    """Evaluate a rule's ``where`` conditions for bay ``index``.

    Recognized keys (unknown keys are ignored for forward compat):
      bay_index -- "even" | "odd" | "first" | "last" | int | list[int]
    """
    if not where:
        return True
    for key, value in where.items():
        if key != "bay_index":
            continue
        if value == "even" and index % 2 != 0:
            return False
        if value == "odd" and index % 2 != 1:
            return False
        if value == "first" and index != 0:
            return False
        if value == "last" and index != count - 1:
            return False
        if isinstance(value, int) and index != value:
            return False
        if isinstance(value, (list, tuple)) and index not in value:
            return False
    return True


def face_widths(obj, indices):
    """{face_index: width} for the given faces (temp bmesh, no edits)."""
    import bmesh

    from ..utils import calc_face_dimensions

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # fresh bmeshes have unset (0) indices
    try:
        return {i: calc_face_dimensions(bm.faces[i])[0] for i in indices}
    finally:
        bm.free()


def _face_anchors(obj, indices):
    """Pre-edit geometry anchors for per-bay placement: center, face-local
    x direction and normal per face index (temp bmesh, no edits)."""
    import bmesh

    from ..utils import local_xyz

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    try:
        anchors = []
        for i in indices:
            f = bm.faces[i]
            x, _y, _z = local_xyz(f)
            anchors.append(
                {
                    "center": f.calc_center_median().copy(),
                    "x_dir": x.normalized(),
                    "normal": f.normal.copy(),
                }
            )
        return anchors
    finally:
        bm.free()


def locate_wall_fragment(obj, target, normal, tol=0.05):
    """Face index of the wall fragment containing ``target`` on the plane
    defined by ``normal`` (per-bay placement after earlier bays split the
    original face; indices do not survive edits). Largest match wins."""
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    try:
        best, best_area = None, -1.0
        for f in bm.faces:
            n = f.normal
            if (
                abs(n.x - normal.x) > 0.1
                or abs(n.y - normal.y) > 0.1
                or abs(n.z - normal.z) > 0.1
            ):
                continue
            c = f.calc_center_median()
            # -- containment within the face's plane bounds
            dims = [v.co for v in f.verts]
            xs = [v.x for v in dims]
            ys = [v.y for v in dims]
            zs = [v.z for v in dims]
            if not (
                min(xs) - tol <= target.x <= max(xs) + tol
                and min(ys) - tol <= target.y <= max(ys) + tol
                and min(zs) - tol <= target.z <= max(zs) + tol
            ):
                continue
            # -- target must lie on the fragment's plane
            if abs((target - c).dot(n)) > 0.05:
                continue
            area = f.calc_area()
            if area > best_area:
                best, best_area = f.index, area
        return best
    finally:
        bm.free()
