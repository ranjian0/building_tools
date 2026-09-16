"""The btools command line (pip-package phase 2).

    btools run house.py --render confirm.png --export house.glb --json
    btools preset apartment-block --floors 4 --render out.png
    btools list-presets --json
    btools smoke

Conventions for agents: exit code 0 iff every step succeeded, machine
summaries go to stdout with --json, human text to stderr/stdout.
"""

import argparse
import importlib.util
import json
import os
import sys

import btools

_RULE_CTX = None


def _ctx(options=None):
    global _RULE_CTX
    if _RULE_CTX is None:
        from btools.rules import RuleContext

        _RULE_CTX = RuleContext
    return _RULE_CTX(options)


def _add_render_args(parser):
    parser.add_argument("--render", metavar="PNG", help="render a confirmation image")
    parser.add_argument(
        "--views",
        default="front,iso",
        help="comma-separated render views (front,right,top,iso)",
    )
    parser.add_argument("--engine", help="render engine override")
    parser.add_argument("--res", default="1280x1280", help="render resolution")
    parser.add_argument("--ascii", metavar="VIEW", help="print an ASCII elevation")
    parser.add_argument(
        "--export",
        metavar="PATH",
        action="append",
        help="export path (.glb/.glb/.fbx); repeatable",
    )


def _finish(args, ctx):
    outputs = []
    if args.get("render"):
        views = [
            v.strip() for v in args.get("views", "front,iso").split(",") if v.strip()
        ]
        res_x, _, res_y = args.get("res", "1280x1280").partition("x")
        out = ctx.render(
            args.get("render"),
            engine=args.get("engine"),
            views=views,
            resolution=(int(res_x), int(res_y)),
        )
        outputs.extend(
            [path for *_rest, path in out] if isinstance(out, list) else [out]
        )
    if args.get("export"):
        for path in args.get("export"):
            ok, out = ctx.export(path)
            outputs.append(out if ok else path)
    if args.get("ascii"):
        obj = ctx.object_data()
        print(ctx.ascii(args.get("ascii")) if obj else "(no object)")
    return outputs


def cmd_run(args):
    rule_path = args["rule"]
    if not rule_path.endswith(".py"):
        rule_path += ".py"

    ctx = _ctx()
    mod = _load_rule_module(rule_path)
    if hasattr(mod, "build"):
        res = mod.build(ctx)
        if res is not None and hasattr(res, "status"):
            ctx._record(res)

    failures = [r for r in ctx.results if not r.ok]
    if args.get("json"):
        print(json.dumps(_summary(ctx, failures), indent=2))
    outputs = _finish(args, ctx)
    if args.get("json") and outputs:
        print(json.dumps({"outputs": outputs}, indent=2))
    return 1 if failures else 0


def cmd_preset(args):
    ctx = _ctx()
    kwargs = {}
    if args["floors"] is not None:
        kwargs["floors"] = args["floors"]
    if args["width_scale"] is not None:
        kwargs["width_scale"] = args["width_scale"]
    if args["depth_scale"] is not None:
        kwargs["depth_scale"] = args["depth_scale"]
    ctx.preset(args["preset_id"], **kwargs)
    failures = [r for r in ctx.results if not r.ok]
    if args.get("json"):
        print(json.dumps(_summary(ctx, failures), indent=2))
    outputs = _finish(args, ctx)
    if args.get("json") and outputs:
        print(json.dumps({"outputs": outputs}, indent=2))
    return 1 if failures else 0


def cmd_list_presets(args):
    from btools.api.presets import preset_items

    items = preset_items()
    if args.get("json"):
        print(json.dumps([{"id": i[0], "label": i[1]} for i in items], indent=2))
    else:
        for pid, label, description in items:
            print(f"{pid:24s} {label:24s} {description}")
    return 0


def cmd_examples(args):
    from btools.examples import discover, write_manifest

    if args.get("examples_command") == "index":
        path, manifest = write_manifest()
        print("manifest: %d examples -> %s" % (manifest["count"], path))
        return 0

    if args.get("examples_command") == "run":
        ex_id = args["example_id"]
        matches = [e for e in discover() if e.id == ex_id or e.id.endswith("." + ex_id)]
        if not matches:
            print("unknown example %r" % ex_id, file=sys.stderr)
            return 1
        ex = matches[0]
        ctx = _ctx()
        mod = _load_rule_module(ex.path)
        mod.build(ctx)
        failures = [r for r in ctx.results if not r.ok]
        if failures:
            for r in failures:
                print(r.object_name, r.errors[:1], file=sys.stderr)
            return 1
        print("%s built: %s" % (ex.id, ", ".join(ctx.objects)))
        return 0

    # -- list
    entries = []
    for ex in discover():
        if args.get("tag") and args["tag"] not in ex.tags:
            continue
        entries.append(
            {
                "id": ex.id,
                "title": ex.title,
                "tags": list(ex.tags),
                "tier": ex.tier,
                "path": os.path.relpath(ex.path),
            }
        )
    if args.get("json"):
        print(json.dumps(entries, indent=2))
    else:
        for e in entries:
            print("%-40s %s" % (e["id"], e["title"]))
    return 0


def cmd_smoke(args):
    """Headless preset smoke: build + validate every bundled preset."""
    from btools.api.checks import run_checks
    from btools.api.presets import PRESETS, build_preset

    failures = []
    for pid, preset in PRESETS.items():
        res = build_preset(preset)
        if not res.ok:
            failures.append((pid, ["build failed: %s" % res.status]))
            print(f"{pid:28s} BUILD-FAIL")
            continue
        import bpy

        obj = bpy.data.objects.get(res.created_object or "")
        report = run_checks(obj, preset.checks) if obj else {"ok": False, "results": []}
        status = "ok" if report["ok"] else "CHECK-FAIL"
        print(f"{pid:28s} {status}")
        if not report["ok"]:
            failures.append((pid, report.get("failures", [])))
    return 1 if failures else 0


def _load_rule_module(path):

    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    name = "btools_rule_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _summary(ctx, failures):
    summary = {
        "objects": list(ctx.objects),
        "results": [
            {"status": r.status, "warnings": r.warnings[:2]} for r in ctx.results
        ],
        "failures": [
            {"object": r.object_name, "errors": r.errors[:2]} for r in failures
        ],
        "decisions": len(ctx.decisions),
        "version": btools.__version__,
    }
    return summary


def main(argv=None):
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    parser = argparse.ArgumentParser(
        prog="btools", description="Procedural building generation headless"
    )
    parser.add_argument("--version", action="version", version=btools.__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="execute a rule file")
    run_p.add_argument("rule", help="path to the rule file (.py)")
    _add_render_args(run_p)
    run_p.add_argument("--json", action="store_true", help="machine summary on stdout")

    preset_p = sub.add_parser("preset", help="build a bundled preset")
    preset_p.add_argument("preset_id")
    preset_p.add_argument("--floors", type=int)
    preset_p.add_argument("--width-scale", type=float)
    preset_p.add_argument("--depth-scale", type=float)
    _add_render_args(preset_p)
    preset_p.add_argument("--json", action="store_true")

    list_p = sub.add_parser("list-presets", help="list bundled presets")
    list_p.add_argument("--json", action="store_true")

    sub.add_parser("smoke", help="build + validate every preset")

    ex_p = sub.add_parser("examples", help="bundled example rule files")
    ex_sub = ex_p.add_subparsers(dest="examples_command")
    ex_list = ex_sub.add_parser("list", help="list examples")
    ex_list.add_argument("--json", action="store_true")
    ex_list.add_argument("--tag", help="filter by tag")
    ex_run = ex_sub.add_parser("run", help="run one example by id")
    ex_run.add_argument("example_id")
    ex_run.add_argument("--render", action="store_true")
    ex_sub.add_parser("index", help="regenerate examples/manifest.json")

    args = parser.parse_args(argv)
    btools.ensure_registered()

    command = args.command
    args = vars(args)
    del args["command"]
    if command == "examples":
        return cmd_examples(args)
    handlers = {
        "run": cmd_run,
        "preset": cmd_preset,
        "list-presets": cmd_list_presets,
        "smoke": cmd_smoke,
    }
    return handlers[command](args)


if __name__ == "__main__":
    sys.exit(main())
