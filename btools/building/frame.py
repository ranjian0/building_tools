from ..utils import extrude_face_region


def add_frame_depth(
    bm, door_faces, window_faces, arch_faces, frame_faces, depth, normal
):
    """Add depth to frame"""
    if depth != 0.0:
        all_faces = door_faces + window_faces + arch_faces + frame_faces
        
        def hash_face(f):
            face_hash = hash((
                f.calc_perimeter(),
                f.calc_area(),
                f.calc_center_median().to_tuple(4),
            ))
            return face_hash
    
        def hash_face_after(f):
            face_hash = hash((
                f.calc_perimeter(),
                f.calc_area(),
                (f.calc_center_median() + normal * depth).to_tuple(4),
            ))
            return face_hash

        
        door_hashes = list(map(hash_face, door_faces))
        window_hashes = list(map(hash_face, window_faces))
        arch_hashes = list(map(hash_face, arch_faces))
        frame_hashes = list(map(hash_face, frame_faces))

        all_faces, surrounding_faces = extrude_face_region(
            bm, list(set(all_faces)), -depth, normal
        )
        
        new_door_faces = [f for f in all_faces if hash_face_after(f) in door_hashes]
        new_window_faces = [f for f in all_faces if hash_face_after(f) in window_hashes]
        new_arch_faces = [f for f in all_faces if hash_face_after(f) in arch_hashes]
        new_frame_faces = [f for f in all_faces if hash_face_after(f) in frame_hashes]
        
     
        if depth < 0.0:
            return (
                new_door_faces,
                new_window_faces,
                new_arch_faces,
                new_frame_faces + surrounding_faces,
            )
        else:
            return (
                new_door_faces,
                new_window_faces,
                new_arch_faces,
                new_frame_faces,
            )
    else:
        return door_faces, window_faces, arch_faces, frame_faces
