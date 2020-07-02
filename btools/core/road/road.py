import bmesh
from .road_types import create_road
from ...utils import (
    crash_safe,
)


class Road:
    @classmethod
    @crash_safe
    def build(cls, context, props):
        return {"CANCELLED"}