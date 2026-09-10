"""Scenario: bare floorplan (10 x 8 rectangular).

Output contract: last line is __JSON__{...} with the object name.
"""

import bpy
import json

from building_tools.btools.api import FloorplanOptions, apply_feature


def main():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)

    r = apply_feature("floorplan", FloorplanOptions(width=10.0, length=8.0))
    if not r.ok:
        raise RuntimeError("floorplan failed: %s" % r.errors)

    print("__JSON__" + json.dumps({"object": r.created_object, "faces": {}}))


main()
