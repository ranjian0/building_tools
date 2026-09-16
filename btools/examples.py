"""Discovery and execution for the bundled example rule files.

Every example is a complete-building rule file with the standard
contract: module docstring (title), optional TAGS/TIER/RENDER, and a
``build(ctx)`` entry point. The manifest (examples/manifest.json) is
generated from these and doubles as the agent-facing index.
"""

import json
import os
from dataclasses import dataclass

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "examples")


@dataclass
class Example:
    id: str
    path: str
    title: str
    tags: tuple
    tier: str
    render: bool


def _examples_root(explicit=None):
    if explicit is not None:
        return explicit
    return os.path.normpath(EXAMPLES_DIR)


def discover(root=None):
    """All example modules under `root` (default: bundled examples/)."""
    root = _examples_root(root)
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in sorted(files):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            path = os.path.join(dirpath, fname)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            out.append(
                Example(
                    id=rel[:-3].replace("/", "."),
                    path=path,
                    title="",
                    tags=(),
                    tier="standard",
                    render=False,
                )
            )
    out.sort(key=lambda e: e.id)
    return out


def load_metadata(ex, mod):
    """Read TAGS/TIER/RENDER + title from a loaded example module."""
    ex.title = (mod.__doc__ or "").strip().splitlines()[0] if mod.__doc__ else ex.id
    ex.tags = tuple(getattr(mod, "TAGS", ()))
    ex.tier = getattr(mod, "TIER", "standard")
    ex.render = bool(getattr(mod, "RENDER", False))
    return ex


def build_manifest(root=None):
    """Run every example's metadata pass and return the manifest dict."""
    entries = []
    for ex in discover(root):
        entries.append(
            {
                "id": ex.id,
                "title": ex.title,
                "tags": list(ex.tags),
                "tier": ex.tier,
                "render": ex.render,
            }
        )
    return {"version": 1, "count": len(entries), "examples": entries}


def write_manifest(root=None):
    root = _examples_root(root)
    manifest = build_manifest(root)
    path = os.path.join(root, "manifest.json")
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    return path, manifest
