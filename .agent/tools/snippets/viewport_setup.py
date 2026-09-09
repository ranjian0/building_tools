"""Frame all objects in the viewport and use solid shading.
Run before screenshots for a consistent view.
"""

import bpy
import mathutils

wm = bpy.context.window_manager
win = wm.windows[0]

for area in win.screen.areas:
    if area.type != "VIEW_3D":
        continue
    space = area.spaces.active
    space.shading.type = "SOLID"
    space.overlay.show_wireframes = False
    space.clip_end = 1000

    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.view3d.view_all(center=False)
        bpy.ops.object.select_all(action="DESELECT")

print("[bt] viewport framed, solid shading")
