from ..utils import extrude_face_region


def add_frame_depth(bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal):
    """ Add depth to frame
    """
    if depth != 0.0:
        n_doors = len(door_faces)
        n_windows = len(window_faces)
        n_arch = len(arch_faces)
        all_faces = door_faces + window_faces + arch_faces + frame_faces
        all_faces, surrounding_faces = extrude_face_region(bm, all_faces, -depth, normal)
        if depth < 0.0:
            return (
                all_faces[:n_doors],
                all_faces[n_doors : n_doors + n_windows],
                all_faces[n_doors + n_windows : n_doors + n_windows + n_arch],
                all_faces[n_doors + n_windows + n_arch :] + surrounding_faces,
            )
        else:
            return (
                all_faces[:n_doors],
                all_faces[n_doors : n_doors + n_windows],
                all_faces[n_doors + n_windows : n_doors + n_windows + n_arch],
                all_faces[n_doors + n_windows + n_arch :],
            )
    else:
        return door_faces, window_faces, arch_faces, frame_faces
