"""Detail-level control (Low / Medium / High) — production-detail phase 5.

A scene-level setting plus an api helper that gates optional detail
features. Feature code reads it through ``resolve_detail_flags`` (api) or
``detail_flags(context)`` (ui) so both paths share one table.

Low    -- clean massing: no gutters, chimney, ridge caps, cornices,
           casings, hardware, window fills stay
Medium -- default: everything the user explicitly opts into stays on
High   -- like Medium plus the close-up tier (casings default on for
           new placements)
"""

import bpy

_LEVELS = (
    ("LOW", "Low", "Clean massing: silhouette extras off"),
    ("MEDIUM", "Medium", "Detail as configured (default)"),
    ("HIGH", "High", "Close-up tier: casings on by default"),
)

_DEFAULT = "MEDIUM"

# -- features gated per level: each maps to (low, high) behavior;
#    Medium = user's own props untouched
_GATED = {
    "gutters": {"LOW": False},
    "chimney": {"LOW": False},
    "ridge_cap": {"LOW": False},
    "cornice": {"LOW": False},
    "casing": {"HIGH": True},
}


def detail_level(context=None):
    """Scene detail level ('LOW' | 'MEDIUM' | 'HIGH')."""
    context = context or bpy.context
    scene = getattr(context, "scene", None)
    if scene is None:
        return _DEFAULT
    return getattr(scene, "btools_detail_level", _DEFAULT) or _DEFAULT


def detail_flag(feature, level=None, user_value=None):
    """Resolve a detail feature flag for a level.

    user_value is what the user's own prop says (or None when unset);
    the level table overrides it at LOW (force off) and HIGH (force on
    where configured). MEDIUM keeps the user value."""
    level = level or _DEFAULT
    rule = _GATED.get(feature, {})
    if level in rule:
        return rule[level]
    return user_value


def register():
    bpy.types.Scene.btools_detail_level = bpy.props.EnumProperty(
        name="Detail Level",
        items=_LEVELS,
        default=_DEFAULT,
        description="Gates optional detail features (gutters, chimney, "
        "cornices, casings) across all building tools",
    )


def unregister():
    del bpy.types.Scene.btools_detail_level
