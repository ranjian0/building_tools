# Plan: Default materials with textures for face-map groups (#210)

- **Issue**: https://github.com/ranjian0/building_tools/issues/210
- **Type**: Enhancement
- **Request**: Ship reasonable default materials (with textures) that users can
  assign/edit per building face-map group, since the face-map material system
  has a learning curve.

## Current State

- Face-map/material-group system: `btools/building/materialgroup.py`
  (MaterialGroup enum: WALLS, ROOF, ROOF_HANGS, DOOR, FRAME, BALCONY, COLUMNS,
  CUSTOM, ...), face-int attribute stores group per face.
- `btools/building/material.py` (297 lines): `BTOOLS_OT_create_material`
  creates a material for the active matgroup; `set_material_for_active_matgroup`
  binds a user material; UV mapping methods via `uv_mapping_method` prop
  (BOX/CUBE...). **No default materials are created automatically.**
- Constraint from issue: keep the addon zip small (release script checks zip
  size — commit `0216534` "check zip size on release").

## Design Decisions

- **Procedural, not image textures**: Blender node-based materials (brick
  texture node, noise, principled BSDF) generate realistic walls/roof/glass at
  zero bytes of bundled textures and scale with any scene units.
- **On-demand, not automatic**: a "Apply Defaults" button creates materials
  only for existing matgroups on the object (avoids cluttering scenes and
  respects the file-size goal).

## Implementation Steps

1. New module `btools/building/default_materials.py`:
   - factory functions `make_wall_material()`, `make_roof_material()`,
     `make_roof_hangs_material()`, `make_glass_material()`,
     `make_frame_material()`, `make_concrete_material()` (balcony/columns),
     each returning a `bpy.types.Material` built from nodes:
     - Walls: Brick Texture → Principled (roughness variation via Noise).
     - Roof/Hangs: Noise-driven dark principled.
     - Glass: Transmission=1, IOR 1.45, thin.
     - Frame/Concrete: flat principled with subtle noise bump.
   - Cache per blend session (reuse by name `BT_Walls` etc., `use_fake_user` off).
2. Operator `BTOOLS_OT_apply_default_materials`: iterates the object's
   matgroups, appends the matching default material if the group has none, and
   binds it via the existing `set_material_for_active_matgroup` logic
   (`materialgroup.py:153`).
3. UI: button in the Material Tools panel (`__init__.py:89-143` draw) next to
   the existing create/remove material row — only shown when groups lack materials.
4. API: expose `apply_default_materials(obj)` in `btools/api` so batch
   generation (#214) can call it per building (opt-in flag in batch props).
5. Optional style prop (enum: `Realistic | Flat`) for Cycles/EEVEE-friendly
   flat colors — keep v1 minimal: one style.
6. Verify UV mapping: defaults rely on generated/box mapping — confirm the
   existing `uv_mapping_method` produces usable UVs with procedural textures
   (object coordinates, no UV map needed → use Object/Generated texture
   coordinates in the node tree so no UV pass required).

## Acceptance Criteria

- One click assigns sensible materials to every populated matgroup of a
  building; viewport (EEVEE) and render (Cycles) look reasonable.
- Zip size unchanged (no bundled images).

## Test Plan

- Headless: build floorplan+floors+roof+door; run apply-defaults; assert every
  matgroup has a bound material and material node count > 0.

## Risks

- Procedural brick scale looks off on odd scene scales — drive node scale from
  `get_scaled_unit` / scene unit settings.
