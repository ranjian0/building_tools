"""Deterministic, scriptable core for building feature operations.

Operations take explicit inputs -- a FaceTarget (object + face indices) and an
options dataclass -- and return an OpResult. Nothing here reads viewport
selection or requires a specific active object; edit-mode transitions are
managed internally.

GUI operators are unaffected: the ops `build()` wrappers keep their own
selection-based path. Both paths call the same `create_*` geometry functions.
"""

import dataclasses
import enum
import traceback
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields

import bmesh
import bpy

from ..building.balcony import BalconyProperty
from ..building.balcony.balcony_ops import add_balcony_matgroups, validate_balcony_faces
from ..building.balcony.balcony_types import create_balcony
from ..building.door import DoorProperty
from ..building.door.door_ops import add_door_matgroups, validate_door_faces
from ..building.door.door_types import create_door
from ..building.fill import FillProperty
from ..building.fill.fill_ops import validate_fill_faces
from ..building.fill.fill_types import add_fill
from ..building.floor import FloorProperty
from ..building.floor.floor_ops import add_floor_matgroups
from ..building.floor.floor_types import create_floors
from ..building.floorplan import FloorplanProperty
from ..building.floorplan.floorplan_types import (
    create_circular_floorplan,
    create_composite_floorplan,
    create_hshaped_floorplan,
    create_random_floorplan,
    create_rectangular_floorplan,
)
from ..building.materialgroup import (
    MaterialGroup,
    add_faces_to_group,
    find_faces_without_matgroup,
    verify_matgroup_attribute_for_object,
)
from ..building.multigroup import MultigroupProperty
from ..building.multigroup.multigroup_ops import (
    add_multigroup_matgroups,
    validate_multigroup_faces,
)
from ..building.multigroup.multigroup_types import create_multigroup
from ..building.roof import RoofProperty
from ..building.roof.roof_ops import add_roof_matgroups
from ..building.roof.roof_types import create_roof
from ..building.stairs import StairsProperty
from ..building.stairs.stairs_ops import add_stairs_matgroup, validate_stair_faces
from ..building.stairs.stairs_types import create_stairs
from ..building.window import WindowProperty
from ..building.window.window_ops import add_window_matgroups, validate_window_faces
from ..building.window.window_types import create_window
from ..utils import (
    bm_from_obj,
    bm_to_obj,
    calc_face_dimensions,
    create_mesh,
    create_object,
    dict_from_prop,
    link_obj,
    prop_from_dict,
)
from .options import (
    BalconyOptions,
    DoorOptions,
    FillOptions,
    FloorOptions,
    FloorplanOptions,
    MultigroupOptions,
    RoofOptions,
    StairsOptions,
    WindowOptions,
)
from .result import OpResult

# ---------------------------------------------------------------- plumbing


@dataclass
class FaceTarget:
    """Explicit operation target: an object plus face indices.

    Empty face_indices means "all faces" (matching the ops' behavior for
    floor/roof which operate on the whole mesh when nothing is selected).
    """

    object: bpy.types.Object
    face_indices: list = field(default_factory=list)


@contextmanager
def _prop_instance(prop_cls, name):
    """Yield a PropertyGroup instance attached to the scene (scene-attach
    pattern used by the ops and tests). Detached on exit."""
    try:
        bpy.utils.register_class(prop_cls)
    except ValueError:
        pass  # already registered (addon loaded)
    setattr(bpy.types.Scene, name, bpy.props.PointerProperty(type=prop_cls))
    try:
        yield getattr(bpy.context.scene, name)
    finally:
        delattr(bpy.types.Scene, name)


@contextmanager
def _target_context(obj):
    """Route bpy.context.object/active_object/edit_object to obj for the
    duration of the block, so geometry helpers reading context.object
    (e.g. materialgroup.add_faces_to_group) act on the target."""
    with bpy.context.temp_override(object=obj, active_object=obj, edit_object=obj):
        yield


@contextmanager
def _edit_session(target):
    """Enter edit mode on the target object, yield (bm, faces), then flush and
    return to object mode. Faces are picked by index; empty indices = all."""
    obj = target.object
    prev_active = bpy.context.view_layer.objects.active

    # -- isolate selection: mode_set(EDIT) would otherwise enter multi-object
    #    edit mode over every selected object
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # -- the .bt_material_group_index layer must exist BEFORE the edit bmesh
    #    is created, so its face-int layers propagate (ops do the same)
    verify_matgroup_attribute_for_object(obj)

    if obj.mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    if target.face_indices:
        # -- resolve by the face's own index (authoritative), not positional
        #    sequence access: edit-bmesh ordering can diverge from mesh polygons
        by_index = {f.index: f for f in bm.faces}
        missing = [i for i in target.face_indices if i not in by_index]
        if missing:
            raise IndexError("face indices out of range: %s" % missing)
        faces = [by_index[i] for i in target.face_indices]
    else:
        faces = list(bm.faces)

    # -- mirror the operator precondition: some geometry code reads the
    #    bmesh selection state directly (e.g. balcony get_selection_groups)
    for f in bm.faces:
        f.select = False
    for f in faces:
        f.select = True

    try:
        yield bm, faces
    finally:
        bmesh.update_edit_mesh(obj.data, loop_triangles=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = prev_active


def _strip_nones(value):
    """Drop None leaves from nested option dicts (None = 'keep prop default')."""
    if isinstance(value, dict):
        return {k: _strip_nones(v) for k, v in value.items() if v is not None}
    return value


def _options_into_prop(prop, options):
    """Apply an options dataclass onto a PropertyGroup instance."""
    props_dict = dict_from_prop(prop)
    props_dict.update(_strip_nones(asdict(options)))
    prop_from_dict(prop, props_dict)


def _cancelled(feature, obj, why):
    return OpResult(
        "cancelled", feature, object_name=obj.name if obj else None, errors=[why]
    )


def _error(feature, obj, exc):
    return OpResult(
        "error",
        feature,
        object_name=obj.name if obj else None,
        errors=["%s: %s" % (type(exc).__name__, exc), traceback.format_exc()],
    )


# ---------------------------------------------------------------- runners


def apply_floorplan(options) -> OpResult:
    """Create a new floorplan object. No target needed."""
    feature = "floorplan"
    try:
        with _prop_instance(FloorplanProperty, "bt_api_floorplan") as prop:
            _options_into_prop(prop, options)

            name = "building_" + str(f"{len(bpy.data.objects) + 1:0>3}")
            obj = create_object(name, create_mesh(name + "_mesh"))
            bm = bm_from_obj(obj)

            dispatch = {
                "RECTANGULAR": create_rectangular_floorplan,
                "CIRCULAR": create_circular_floorplan,
                "COMPOSITE": create_composite_floorplan,
                "H-SHAPED": create_hshaped_floorplan,
                "RANDOM": create_random_floorplan,
            }
            fn = dispatch.get(prop.type)
            if fn is None:
                raise ValueError("unknown floorplan type %r" % prop.type)
            fn(bm, prop)

            bm_to_obj(bm, obj)
            link_obj(obj)

        from .validate import matgroup_report

        return OpResult(
            "ok",
            feature,
            object_name=obj.name,
            created_object=obj.name,
            matgroup_counts=matgroup_report(obj)["groups"],
        )
    except Exception as exc:
        return _error(feature, None, exc)


def _apply_face_feature(
    feature,
    target,
    options,
    prop_cls,
    validate_fn,
    matgroup_fn,
    create_fn,
    needs_init=True,
):
    """Shared runner for edit-mode face features."""
    obj = target.object
    if obj is None:
        raise ValueError("no target object")
    try:
        from .validate import matgroup_report

        with _edit_session(target) as (bm, faces):
            # -- validators either return a face list (door/window/multigroup/
            #    fill) or a bool verdict (balcony/stairs/roof-style)
            if validate_fn:
                validated = validate_fn(faces)
                valid = list(validated) if not isinstance(validated, bool) else (
                    list(faces) if validated else []
                )
            else:
                valid = faces
            rejected = len(faces) - len(valid)
            warnings = []
            if rejected:
                warnings.append(
                    "%d of %d faces rejected by %s validation"
                    % (rejected, len(faces), feature)
                )
            if not valid:
                result = _cancelled(feature, obj, "no valid faces for %s" % feature)
                result.warnings = warnings
                return result

            with _prop_instance(prop_cls, "bt_api_%s" % feature) as prop:
                if needs_init:
                    # -- initialize size_offset/arch state from the target face
                    #    BEFORE applying options, so options override init
                    #    values (this mirrors operator execute())
                    w, h = calc_face_dimensions(valid[0])
                    prop.init((w, h))
                _options_into_prop(prop, options)
                with _target_context(obj):
                    if matgroup_fn:
                        matgroup_fn()
                    create_fn(bm, valid, prop)
                    # -- untouched faces carry the -1 "no group" sentinel;
                    #    they are wall surface -> WALLS (door/window/multigroup
                    #    already run this pass internally)
                    nulfaces = find_faces_without_matgroup(bm)
                    if nulfaces:
                        add_faces_to_group(bm, nulfaces, MaterialGroup.WALLS)

        # -- read counts in object mode (edit-mode obj.data is stale)
        return OpResult(
            "ok",
            feature,
            object_name=obj.name,
            matgroup_counts=matgroup_report(obj)["groups"],
            warnings=warnings,
        )
    except Exception as exc:
        return _error(feature, obj, exc)


def apply_floor(target, options) -> OpResult:
    feature = "floor"
    obj = target.object
    try:
        from .validate import matgroup_report

        with _edit_session(target) as (bm, faces):
            zs = {round(v.co.z, 4) for f in faces for v in f.verts}
            if len(zs) != 1:
                return _cancelled(
                    feature,
                    obj,
                    "target faces are not coplanar in Z (%d levels)" % len(zs),
                )
            with _prop_instance(FloorProperty, "bt_api_floor") as prop:
                _options_into_prop(prop, options)
                with _target_context(obj):
                    add_floor_matgroups(bpy.context, prop)
                    create_floors(bm, faces, prop)
        return OpResult(
            "ok",
            feature,
            object_name=obj.name,
            matgroup_counts=matgroup_report(obj)["groups"],
        )
    except Exception as exc:
        return _error(feature, obj, exc)


def apply_roof(target, options) -> OpResult:
    feature = "roof"
    obj = target.object
    try:
        from .validate import matgroup_report

        with _edit_session(target) as (bm, faces):
            # XXX match ops behavior: fix inverted (Z-) normals first
            for f in faces:
                if f.normal.z < 0:
                    f.normal_flip()
            if not all(round(f.normal.z, 1) for f in faces):
                return _cancelled(feature, obj, "target faces are not upward facing")
            with _prop_instance(RoofProperty, "bt_api_roof") as prop:
                _options_into_prop(prop, options)
                with _target_context(obj):
                    add_roof_matgroups()
                    create_roof(bm, faces, prop)
        return OpResult(
            "ok",
            feature,
            object_name=obj.name,
            matgroup_counts=matgroup_report(obj)["groups"],
        )
    except Exception as exc:
        return _error(feature, obj, exc)


def apply_door(target, options) -> OpResult:
    return _apply_face_feature(
        "door",
        target,
        options,
        DoorProperty,
        validate_door_faces,
        add_door_matgroups,
        create_door,
    )


def apply_window(target, options) -> OpResult:
    return _apply_face_feature(
        "window",
        target,
        options,
        WindowProperty,
        validate_window_faces,
        add_window_matgroups,
        create_window,
    )


def apply_multigroup(target, options) -> OpResult:
    return _apply_face_feature(
        "multigroup",
        target,
        options,
        MultigroupProperty,
        validate_multigroup_faces,
        add_multigroup_matgroups,
        create_multigroup,
    )


def apply_balcony(target, options) -> OpResult:
    return _apply_face_feature(
        "balcony",
        target,
        options,
        BalconyProperty,
        validate_balcony_faces,
        add_balcony_matgroups,
        create_balcony,
    )


def apply_stairs(target, options) -> OpResult:
    return _apply_face_feature(
        "stairs",
        target,
        options,
        StairsProperty,
        validate_stair_faces,
        add_stairs_matgroup,
        create_stairs,
    )


def apply_fill(target, options) -> OpResult:
    return _apply_face_feature(
        "fill",
        target,
        options,
        FillProperty,
        validate_fill_faces,
        None,
        add_fill,
        needs_init=False,
    )


FEATURES: dict[str, Callable[..., OpResult]] = {
    "floorplan": apply_floorplan,
    "floor": apply_floor,
    "roof": apply_roof,
    "door": apply_door,
    "window": apply_window,
    "multigroup": apply_multigroup,
    "balcony": apply_balcony,
    "stairs": apply_stairs,
    "fill": apply_fill,
}

OPTION_TYPES: dict = {
    "floorplan": FloorplanOptions,
    "floor": FloorOptions,
    "roof": RoofOptions,
    "door": DoorOptions,
    "window": WindowOptions,
    "multigroup": MultigroupOptions,
    "balcony": BalconyOptions,
    "stairs": StairsOptions,
    "fill": FillOptions,
}

# features whose options dataclass carries nested groups requiring an
# initialized prop (wall_dimensions derived from the first target face)
INIT_FEATURES = {"door", "window", "multigroup", "balcony", "stairs"}


def options_from_dict(cls, data):
    """Instantiate an options dataclass from a plain dict (recursive; enum
    fields accept their value strings). Unknown keys raise ValueError."""
    by_name = {f.name: f for f in fields(cls)}
    kwargs = {}
    for key, value in data.items():
        if key not in by_name:
            raise ValueError("%s has no option %r" % (cls.__name__, key))
        ftype = by_name[key].type
        if dataclasses.is_dataclass(ftype) and isinstance(value, dict):
            value = options_from_dict(ftype, value)
        elif isinstance(ftype, type) and issubclass(ftype, enum.Enum):
            value = ftype(value)
        kwargs[key] = value
    return cls(**kwargs)


def apply_feature(feature, options, target=None) -> OpResult:
    """Dispatch to the feature runner.

    feature: key of FEATURES
    options: options dataclass instance for the feature
    target:  FaceTarget; floorplan ignores it, face features may omit it to
             use the active object with its current selection.
    """
    try:
        fn = FEATURES[feature]
    except KeyError:
        raise ValueError("unknown feature %r (have: %s)" % (feature, sorted(FEATURES)))

    if feature == "floorplan":
        return fn(options)

    if target is None:
        target = target_from_context()
    return fn(target, options)


def target_from_context() -> FaceTarget:
    """FaceTarget from the active object; face indices from the current
    selection when in edit mode, else all faces."""
    view_layer = bpy.context.view_layer
    active = view_layer.objects.active if view_layer else None
    obj = bpy.context.object or active
    if obj is None or obj.type != "MESH":
        raise ValueError("no active mesh object to target")
    indices = []
    if bpy.context.mode == "EDIT_MESH":
        me = obj.data
        if not isinstance(me, bpy.types.Mesh):
            raise ValueError("target data is not a mesh")
        bm = bmesh.from_edit_mesh(me)
        indices = [f.index for f in bm.faces if f.select]
    return FaceTarget(obj, indices)
