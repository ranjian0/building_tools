"""Structured result type for api operations."""

from dataclasses import dataclass, field


@dataclass
class OpResult:
    """Outcome of a building-tools api operation.

    All fields are JSON-serializable via to_dict(); agents and batch tooling
    should branch on `status` and read `errors`/`warnings` for diagnostics.
    """

    status: str  # "ok" | "cancelled" | "error"
    feature: str
    object_name: str | None = None
    created_object: str | None = None
    matgroup_counts: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    # -- seeded-randomization trace: [(path, decision, value), ...]
    decisions: list = field(default_factory=list)

    @property
    def ok(self):
        return self.status == "ok"

    def to_dict(self):
        return {
            "status": self.status,
            "ok": self.ok,
            "feature": self.feature,
            "object": self.object_name,
            "created_object": self.created_object,
            "matgroup_counts": self.matgroup_counts,
            "errors": self.errors,
            "warnings": self.warnings,
            "decisions": self.decisions,
        }
