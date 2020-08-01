import operator as op
from mathutils import Vector

EPS = 0.0001

VEC_UP = Vector((0, 0, 1))
VEC_RIGHT = Vector((1, 0, 0))
VEC_FORWARD = Vector((0, 1, 0))

GLOBAL_XYZ = (VEC_RIGHT, VEC_FORWARD, VEC_UP)
VEC_DOWN, VEC_LEFT, VEC_BACK = tuple(map(op.neg, [VEC_UP, VEC_RIGHT, VEC_FORWARD]))
