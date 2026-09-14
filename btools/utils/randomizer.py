"""Seeded hierarchical RNG -- the "seedian" pattern.

Every random decision derives from a root seed plus a decision path, so:

- same seed + same inputs => identical buildings (reproducible batches,
  tests and reference-corpus runs)
- re-rolling one branch (e.g. the roof) never perturbs other branches:
  each decision node gets an independent ``random.Random`` stream keyed by
  ``"<seed>:<path>"``

Usage::

    rng = BToolsRandom(seed="block-7")
    fill = rng.choice(("facade", "window", 3, "fill"), ("BAR", "GLASS_PANES"))
    if rng.chance(("facade", "window", 3, "arch"), 0.3):
        ...
"""

import hashlib
import random

__all__ = ["BToolsRandom"]


def _subseed(seed, path):
    """Stable integer sub-seed for a decision path (blake2b hash; integer
    seeds keep random.Random behavior stable across Python versions)."""
    raw = "%s:%s" % (seed, "/".join(str(part) for part in path))
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _loggable(value):
    return value.value if hasattr(value, "value") else value


class BToolsRandom:
    """Root seeded RNG with per-path sub-streams and a decision log."""

    def __init__(self, seed):
        self.seed = seed
        self.decisions = []

    def rng(self, *path):
        """Independent Random stream for a decision path."""
        if not path:
            raise ValueError("a decision path is required (avoid the root stream)")
        return random.Random(_subseed(self.seed, path))

    # ---------------------------------------------------------------- logging

    def log(self, path, decision, value):
        self.decisions.append(("/".join(map(str, path)), decision, _loggable(value)))

    # ---------------------------------------------------------------- helpers

    def choice(self, path, seq):
        value = self.rng(*path).choice(seq)
        self.log(path, "choice", value)
        return value

    def weighted_choice(self, path, choices, weights):
        value = self.rng(*path).choices(choices, weights=weights, k=1)[0]
        self.log(path, "weighted_choice", value)
        return value

    def chance(self, path, probability):
        value = self.rng(*path).random() < probability
        self.log(path, "chance", value)
        return value

    def jitter(self, path, value, amount):
        """Scale ``value`` by a uniform factor within ``1 +/- amount``."""
        jittered = value * (1.0 + self.rng(*path).uniform(-amount, amount))
        self.log(path, "jitter", jittered)
        return jittered
