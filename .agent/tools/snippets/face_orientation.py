"""Toggle the face-orientation overlay in the 3D viewport.

Blue = front face, red = back face (inverted normals).
Pass nothing to enable; set DISABLE=1 to turn it off.
"""

import os

import bpy

enable = os.environ.get("DISABLE", "") != "1"

wm = bpy.context.window_manager
win = wm.windows[0]

for area in win.screen.areas:
    if area.type != "VIEW_3D":
        continue
    area.spaces.active.overlay.show_face_orientation = enable

print("[bt] face orientation overlay:", "ON" if enable else "OFF")
