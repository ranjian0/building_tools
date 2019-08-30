import bmesh
from .window_types import create_window
from ...utils import get_edit_mesh, FaceMap, add_facemap_for_groups


class Window:
    @classmethod
    def build(cls, context, prop):
        me = get_edit_mesh()
        bm = bmesh.from_edit_mesh(me)
        faces = [face for face in bm.faces if face.select]

        if cls.validate(faces):
            cls.add_window_facemaps()
            create_window(bm, faces, prop)
            bmesh.update_edit_mesh(me, True)
            return {"FINISHED"}
        return {"CANCELLED"}

    @classmethod
    def add_window_facemaps(cls):
        groups = FaceMap.WINDOW, FaceMap.WINDOW_FRAMES
        add_facemap_for_groups(groups)

    @classmethod
    def validate(cls, faces):
        if faces:
            if not any([round(f.normal.z, 1) for f in faces]):
                return True
        return False
