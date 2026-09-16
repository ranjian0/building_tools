"""Preset baseline — build a bundled preset through the rule context."""
TAGS = ("pipeline", "preset", "simple")


def build(ctx):
    ctx.preset("suburban-house")
