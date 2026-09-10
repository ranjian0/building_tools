"""Reference corpus manifest.

Each case: base scenario (optional) + ordered feature steps + expectations.
Consumed by snippets/reference_sweep.py (via `bt reference generate`).

Case schema:
    id           unique, <feature>-<variant> (scenario baselines: scenario-*)
    scenario     base scene builder in snippets/scenarios/ (optional)
    steps        [{feature, options, faces}] -- faces is a selector name
                 (top_face, ground_wall, ground_walls, upper_wall, front,
                 inner, all) resolved live per step, or an index list
    expect       {"groups": [...]} passed to validate_object
    known_issues accepted flaw markers, e.g. "non_manifold" (frame seams)
"""

CASES = [
    # -- scenario baselines -------------------------------------------------
    {"id": "scenario-wall", "scenario": "wall"},
    {"id": "scenario-curved-wall", "scenario": "curved_wall"},
    {"id": "scenario-floorplan", "scenario": "floorplan"},
    {"id": "scenario-floors-only", "scenario": "floors_only"},
    {"id": "scenario-multi-storey", "scenario": "multi_storey"},
    # -- floorplan types -----------------------------------------------------
    {"id": "floorplan-circular", "steps": [
        {"feature": "floorplan", "options": {"type": "CIRCULAR"}}]},
    {"id": "floorplan-composite", "steps": [
        {"feature": "floorplan", "options": {"type": "COMPOSITE"}}]},
    {"id": "floorplan-h-shaped", "steps": [
        {"feature": "floorplan", "options": {"type": "H-SHAPED"}}]},
    {"id": "floorplan-random", "steps": [
        {"feature": "floorplan", "options": {"type": "RANDOM", "seed": 1}}]},
    # -- floor variants (on bare floorplan) ----------------------------------
    {"id": "floor-count-1", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 1}, "faces": "all"}]},
    {"id": "floor-slabs-off", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 3, "add_slab": False}, "faces": "all"}]},
    {"id": "floor-columns", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 2, "add_columns": True}, "faces": "all"}],
     "known_issues": ["non_manifold"]},
    {"id": "floor-decoration", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 2, "add_decoration": True}, "faces": "all"}],
     "known_issues": ["non_manifold"]},
    # -- roof types (on floors-only) ------------------------------------------
    {"id": "roof-flat", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "FLAT"}, "faces": "top_face"}]},
    {"id": "roof-gable-open", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "GABLE", "gable_type": "OPEN"}, "faces": "top_face"}]},
    {"id": "roof-gable-box", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "GABLE", "gable_type": "BOX"}, "faces": "top_face"}]},
    {"id": "roof-hip", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "HIP"}, "faces": "top_face"}]},
    # -- door variants (on floors-only, ground wall) --------------------------
    {"id": "door-default", "scenario": "floors_only", "steps": [
        {"feature": "door", "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "door-panels", "scenario": "floors_only", "steps": [
        {"feature": "door", "options": {"fill_type": "PANELS"}, "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "door-louver", "scenario": "floors_only", "steps": [
        {"feature": "door", "options": {"fill_type": "LOUVER"}, "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "door-glass-panes", "scenario": "floors_only", "steps": [
        {"feature": "door", "options": {"fill_type": "GLASS_PANES"}, "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "door-double", "scenario": "floors_only", "steps": [
        {"feature": "door", "options": {"double_door": True, "size_offset": {"size": [1.6, 1.8]}}, "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "door-arch", "scenario": "floors_only", "steps": [
        {"feature": "door", "options": {"add_arch": True, "size_offset": {"size": [1.0, 2.0]}}, "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold", "flaky_arch_unpack"]},
    # -- window variants -------------------------------------------------------
    {"id": "window-default", "scenario": "floors_only", "steps": [
        {"feature": "window", "faces": "upper_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "window-bar", "scenario": "floors_only", "steps": [
        {"feature": "window", "options": {"fill_type": "BAR"}, "faces": "upper_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "window-louver", "scenario": "floors_only", "steps": [
        {"feature": "window", "options": {"fill_type": "LOUVER"}, "faces": "upper_front_wall"}],
     "known_issues": ["non_manifold", "flaky_louver_max_empty"]},
    {"id": "window-glass-panes", "scenario": "floors_only", "steps": [
        {"feature": "window", "options": {"fill_type": "GLASS_PANES"}, "faces": "upper_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "window-circular", "scenario": "floors_only", "steps": [
        {"feature": "window", "options": {"type": "CIRCULAR", "size_offset": {"size": [1.0, 1.0]}}, "faces": "upper_front_wall"}],
     "known_issues": ["non_manifold"]},
    # -- multigroup --------------------------------------------------------------
    {"id": "multigroup-default", "scenario": "floors_only", "steps": [
        {"feature": "multigroup", "faces": "ground_front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "multigroup-fills", "scenario": "floors_only", "steps": [
        {"feature": "multigroup",
         "options": {"show_door_fill": True, "fill_type_door": "PANELS",
                      "show_window_fill": True, "fill_type_window": "BAR"},
         "faces": "ground_front_wall"}],
     "known_issues": ["zero_width_window_fill"]},
    # -- balcony -------------------------------------------------------------------
    {"id": "balcony-posts-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "faces": "front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "balcony-rails-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "options": {"rail": {"fill": "RAILS"}}, "faces": "front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "balcony-wallfill-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "options": {"rail": {"fill": "WALL"}}, "faces": "front_wall"}],
     "known_issues": ["non_manifold"]},
    {"id": "balcony-inner-curved", "scenario": "curved_wall", "steps": [
        {"feature": "balcony", "faces": "inner"}],
     "known_issues": ["non_manifold", "inverted_normals",
                      "grouped_balcony_curved_platform"]},
    # -- stairs ------------------------------------------------------------------------
    {"id": "stairs-filled", "scenario": "wall", "steps": [
        {"feature": "stairs", "faces": "front_wall"}]},
    {"id": "stairs-blocked", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"bottom": "BLOCKED"}, "faces": "front_wall"}]},
    {"id": "stairs-slope", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"bottom": "SLOPE"}, "faces": "front_wall"}]},
    {"id": "stairs-no-landing", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"landing": False}, "faces": "front_wall"}]},
    # -- fill types ------------------------------------------------------------------------
    {"id": "fill-panels", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "PANELS", "comp": "WINDOW"}, "faces": "front_wall"}]},
    {"id": "fill-glass-panes", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "GLASS_PANES", "comp": "WINDOW"}, "faces": "front_wall"}]},
    {"id": "fill-louver", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "LOUVER", "comp": "WINDOW"}, "faces": "front_wall"}]},
    {"id": "fill-bar", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "BAR", "comp": "WINDOW"}, "faces": "front_wall"}]},
]
