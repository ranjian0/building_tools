import bpy
import bmesh

def make_roof(bm, faces, type, **kwargs):

    if type == 'FLAT':
        make_flat_roof(bm, faces, **kwargs)
    elif type == 'GABLE':
        make_gable_roof(bm, faces, **kwargs)
    elif type == 'HIP':
        make_hip_roof(bm, faces, **kwargs)

def make_flat_roof(bm, faces, **kwargs):
    pass

def make_gable_roof(bm, faces, **kwargs):
    pass

def make_hip_roof(bm, faces, **kwargs):
    pass