"""Validate an engine run directory against the writer's input bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from paperwriter.contracts import INPUT_BUNDLE


@dataclass
class BundleReport:
    run_dir: Path
    present: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_required

    @property
    def has_results(self) -> bool:
        return "results/" in self.present


def _exists(run_dir: Path, rel: str) -> bool:
    p = run_dir / rel
    if rel.endswith("/"):
        return p.is_dir() and any(p.iterdir())
    return p.is_file() and p.stat().st_size > 0


def validate_bundle(run_dir: str | Path) -> BundleReport:
    root = Path(run_dir)
    report = BundleReport(run_dir=root)
    for item in INPUT_BUNDLE:
        if _exists(root, item.path):
            report.present.append(item.path)
        elif item.required:
            report.missing_required.append(item.path)
        else:
            report.missing_optional.append(item.path)
    return report
