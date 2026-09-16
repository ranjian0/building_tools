"""Building Tools — procedural building generation for Blender's Python API.

    pip install building-tools

    import btools
    btools.register()

    from btools.api import apply_feature, FloorplanOptions
    apply_feature("floorplan", FloorplanOptions(width=10, length=8))

Requires the ``bpy`` pip wheel (pinned). All geometry, materials and
exports run headless; see ``btools.cli`` for the command line.
"""

__version__ = "2.0.0a0"

_registered = False


def register():
    """Register every PropertyGroup / scene binding the api needs.

    Idempotent. Called automatically by the api entry points and the CLI;
    call explicitly when embedding btools in your own pipeline."""
    global _registered
    if _registered:
        return
    from .building.register import register_building
    from .utils import detail

    register_building()
    detail.register()
    _registered = True


def unregister():
    global _registered
    if not _registered:
        return
    from .building.register import unregister_building
    from .utils import detail

    detail.unregister()
    unregister_building()
    _registered = False


def ensure_registered():
    if not _registered:
        register()
