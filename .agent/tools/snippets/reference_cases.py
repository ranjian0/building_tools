"""Reference corpus manifest.

Each case: base scenario (optional) + ordered feature steps + expectations.
Consumed by snippets/reference_sweep.py (via `bt reference generate`).

Case schema:
    id           unique, <feature>-<variant> (scenario baselines: scenario-*)
    scenario     base scene builder in snippets/scenarios/ (optional)
    steps        [{feature, options, faces}] -- faces is a selector name
                 (top_face, front_wall, ground_front_wall, upper_front_wall,
                 ground_walls, inner, all) resolved live per step, or an
                 index list
    expect       {"groups": [...]} -- matgroups that must exist with faces;
                 GATING: a missing group marks the case "contract violated"
    known_issues accepted flaw markers documenting current addon behavior
                 (e.g. tagging gaps the expects intentionally expose)
"""

CASES = [
    # -- scenario baselines -------------------------------------------------
    {"id": "scenario-wall", "scenario": "wall"},
    {"id": "scenario-curved-wall", "scenario": "curved_wall"},
    {"id": "scenario-floorplan", "scenario": "floorplan"},
    {"id": "scenario-floors-only", "scenario": "floors_only",
     "expect": {"groups": ["walls", "roof", "slabs"]}},
    {"id": "scenario-multi-storey", "scenario": "multi_storey",
     "expect": {"groups": ["walls", "roof", "slabs", "roof_hangs"]}},
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
        {"feature": "floor", "options": {"floor_count": 1}, "faces": "all"}],
     "expect": {"groups": ["walls", "roof", "slabs"]}},
    {"id": "floor-slabs-off", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 3, "add_slab": False}, "faces": "all"}],
     "expect": {"groups": ["walls", "roof"]}},
    {"id": "floor-columns", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 2, "add_columns": True}, "faces": "all"}],
     "expect": {"groups": ["walls", "roof", "slabs", "columns"]}},
    {"id": "floor-decoration", "scenario": "floorplan", "steps": [
        {"feature": "floor", "options": {"floor_count": 2, "add_decoration": True}, "faces": "all"}],
     "expect": {"groups": ["walls", "roof", "slabs"]},
     "known_issues": ["decoration_no_columns_no_output"]},
    # -- roof types (on floors-only) ------------------------------------------
    {"id": "roof-flat", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "FLAT"}, "faces": "top_face"}],
     "expect": {"groups": ["roof"]}},
    {"id": "roof-gable-open", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "GABLE", "gable_type": "OPEN"}, "faces": "top_face"}],
     "expect": {"groups": ["roof", "roof_hangs"]}},
    {"id": "roof-gable-box", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "GABLE", "gable_type": "BOX"}, "faces": "top_face"}],
     "expect": {"groups": ["roof", "roof_hangs"]}},
    {"id": "roof-hip", "scenario": "floors_only", "steps": [
        {"feature": "roof", "options": {"type": "HIP"}, "faces": "top_face"}],
     "expect": {"groups": ["roof", "roof_hangs"]}},
    # -- door variants (on wall: the element fills the frame) -----------------
    {"id": "door-default", "scenario": "wall", "steps": [
        {"feature": "door", "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame"]}},
    {"id": "door-panels", "scenario": "wall", "steps": [
        {"feature": "door", "options": {"fill_type": "PANELS"}, "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame", "door_panels"]},
     "known_issues": ["fill_drops_element_group"]},
    {"id": "door-louver", "scenario": "wall", "steps": [
        {"feature": "door", "options": {"fill_type": "LOUVER"}, "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame", "door_louvers"]},
     "known_issues": ["fill_drops_element_group"]},
    {"id": "door-glass-panes", "scenario": "wall", "steps": [
        {"feature": "door", "options": {"fill_type": "GLASS_PANES"}, "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame", "door_panes"]}},
    {"id": "door-double", "scenario": "wall", "steps": [
        {"feature": "door", "options": {"double_door": True, "size_offset": {"size": [1.6, 1.8]}},
         "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame"]}},
    {"id": "door-arch", "scenario": "wall", "steps": [
        {"feature": "door", "options": {"add_arch": True, "size_offset": {"size": [1.0, 2.0]}},
         "faces": "front_wall"}],
     "expect": {"groups": ["door", "frame"]},
     "known_issues": ["flaky_arch_unpack"]},
    # -- window variants -------------------------------------------------------
    {"id": "window-default", "scenario": "wall", "steps": [
        {"feature": "window", "faces": "front_wall"}],
     "expect": {"groups": ["window", "frame"]}},
    {"id": "window-bar", "scenario": "wall", "steps": [
        {"feature": "window", "options": {"fill_type": "BAR"}, "faces": "front_wall"}],
     "expect": {"groups": ["window", "frame", "window_bars"]}},
    {"id": "window-louver", "scenario": "wall", "steps": [
        {"feature": "window", "options": {"fill_type": "LOUVER"}, "faces": "front_wall"}],
     "expect": {"groups": ["window", "frame", "window_louvers"]},
     "known_issues": ["fill_drops_element_group", "flaky_louver_max_empty"]},
    {"id": "window-glass-panes", "scenario": "wall", "steps": [
        {"feature": "window", "options": {"fill_type": "GLASS_PANES"}, "faces": "front_wall"}],
     "expect": {"groups": ["window", "frame", "window_panes"]}},
    {"id": "window-circular", "scenario": "wall", "steps": [
        {"feature": "window", "options": {"type": "CIRCULAR", "size_offset": {"size": [1.0, 1.0]}},
         "faces": "front_wall"}],
     "expect": {"groups": ["window", "frame"]}},
    # -- multigroup --------------------------------------------------------------
    {"id": "multigroup-default", "scenario": "wall", "steps": [
        {"feature": "multigroup", "faces": "front_wall"}],
     "expect": {"groups": ["door", "window", "frame"]}},
    {"id": "multigroup-fills", "scenario": "wall", "steps": [
        {"feature": "multigroup",
         "options": {"show_door_fill": True, "fill_type_door": "PANELS",
                      "show_window_fill": True, "fill_type_window": "BAR"},
         "faces": "front_wall"}],
     "expect": {"groups": ["door", "window", "frame", "door_panels", "window_bars"]},
     "known_issues": ["zero_width_window_fill"]},
    # -- balcony -------------------------------------------------------------------
    {"id": "balcony-posts-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "faces": "front_wall"}],
     "expect": {"groups": ["balcony", "railing_posts"]},
     "known_issues": ["balcony_railing_untagged"]},
    {"id": "balcony-rails-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "options": {"rail": {"fill": "RAILS"}}, "faces": "front_wall"}],
     "expect": {"groups": ["balcony", "railing_rails"]},
     "known_issues": ["balcony_railing_untagged"]},
    {"id": "balcony-wallfill-wall", "scenario": "wall", "steps": [
        {"feature": "balcony", "options": {"rail": {"fill": "WALL"}}, "faces": "front_wall"}],
     "expect": {"groups": ["balcony", "railing_walls"]},
     "known_issues": ["balcony_railing_untagged"]},
    {"id": "balcony-inner-curved", "scenario": "curved_wall", "steps": [
        {"feature": "balcony", "faces": "inner"}],
     "expect": {"groups": ["balcony", "railing_posts"]},
     "known_issues": ["balcony_railing_untagged", "grouped_balcony_curved_platform"]},
    # -- stairs ------------------------------------------------------------------------
    {"id": "stairs-filled", "scenario": "wall", "steps": [
        {"feature": "stairs", "faces": "front_wall"}],
     "expect": {"groups": ["stairs", "railing_posts", "railing_rails"]}},
    {"id": "stairs-blocked", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"bottom": "BLOCKED"}, "faces": "front_wall"}],
     "expect": {"groups": ["stairs", "railing_posts", "railing_rails"]}},
    {"id": "stairs-slope", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"bottom": "SLOPE"}, "faces": "front_wall"}],
     "expect": {"groups": ["stairs", "railing_posts", "railing_rails"]}},
    {"id": "stairs-no-landing", "scenario": "wall", "steps": [
        {"feature": "stairs", "options": {"landing": False}, "faces": "front_wall"}],
     "expect": {"groups": ["stairs", "railing_posts", "railing_rails"]}},
    # -- fill types ------------------------------------------------------------------------
    {"id": "fill-panels", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "PANELS", "comp": "WINDOW"}, "faces": "front_wall"}],
     "expect": {"groups": ["door_panels"]},
     "known_issues": ["panels_ignore_comp"]},
    {"id": "fill-glass-panes", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "GLASS_PANES", "comp": "WINDOW"}, "faces": "front_wall"}],
     "expect": {"groups": ["window_panes"]}},
    {"id": "fill-louver", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "LOUVER", "comp": "WINDOW"}, "faces": "front_wall"}],
     "expect": {"groups": ["window_louvers"]}},
    {"id": "fill-bar", "scenario": "wall", "steps": [
        {"feature": "fill", "options": {"fill_type": "BAR", "comp": "WINDOW"}, "faces": "front_wall"}],
     "expect": {"groups": ["window_bars"]}},
]
