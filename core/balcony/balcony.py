import bpy
import bmesh

from .balcony_types import make_balcony
from ...utils import (
    get_edit_mesh,
    kwargs_from_props
    )

class Balcony:

    @classmethod
    def build(cls, context, props):
        make_balcony(**kwargs_from_props(props))