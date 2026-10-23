"""Input and output types of the paper-writing library."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class Reference:
    """One paper the manuscript may cite. ``cite_key`` is generated when empty."""

    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    venue: str = ""
    doi: str = ""
    url: str = ""
    arxiv_id: str = ""
    abstract: str = ""
    citation_count: int = 0
    cite_key: str = ""

    @classmethod
    def from_value(cls, value: "Reference | Mapping[str, Any]") -> "Reference":
        if isinstance(value, Reference):
            return value
        title = str(value.get("title", "")).strip()
        if not title:
            raise ValueError("literature entry has no title")
        authors = value.get("authors") or ()
        if isinstance(authors, str):
            authors = [a.strip() for a in re.split(r"\s+and\s+|;", authors) if a.strip()]
        names = tuple(
            str(a.get("name", "")) if isinstance(a, Mapping) else str(a) for a in authors
        )
        year = value.get("year")
        try:
            year = int(year) if year not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        return cls(
            title=title,
            authors=tuple(n for n in names if n),
            year=year,
            venue=str(value.get("venue", "") or ""),
            doi=str(value.get("doi", "") or ""),
            url=str(value.get("url", "") or ""),
            arxiv_id=str(value.get("arxiv_id", "") or ""),
            abstract=str(value.get("abstract", "") or ""),
            citation_count=int(value.get("citation_count", 0) or 0),
            cite_key=str(value.get("cite_key", "") or ""),
        )


@dataclass(frozen=True)
class PaperInput:
    """Everything the writer needs from the host project.

    The paper is a literature-first manuscript (survey / systematic review /
    proposal): it is grounded in ``literature`` and ``hypotheses`` only. No
    experimental numbers are accepted, so none can appear in the output.
    """

    topic: str
    hypotheses: tuple[str, ...]
    literature: tuple[Reference, ...]
    goal: str = ""  # research goal / problem statement; defaults to the topic
    synthesis: str = ""  # optional literature synthesis or reviewer notes (markdown)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PaperInput":
        topic = str(data.get("topic", "")).strip()
        if not topic:
            raise ValueError("input needs a non-empty 'topic'")
        hyps: list[str] = []
        for h in data.get("hypotheses") or ():
            text = (h.get("text") or h.get("statement") or "") if isinstance(h, Mapping) else h
            if str(text).strip():
                hyps.append(str(text).strip())
        lit = tuple(Reference.from_value(r) for r in data.get("literature") or ())
        return cls(
            topic=topic,
            hypotheses=tuple(hyps),
            literature=lit,
            goal=str(data.get("goal", "") or ""),
            synthesis=str(data.get("synthesis", "") or ""),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "PaperInput":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(frozen=True)
class StageOutcome:
    stage: str
    number: int
    status: str
    error: str | None = None
    artifacts: tuple[str, ...] = ()


@dataclass
class PaperResult:
    ok: bool
    run_dir: Path
    stages: list[StageOutcome] = field(default_factory=list)
    error: str | None = None
    paper_markdown: Path | None = None
    paper_tex: Path | None = None
    references_bib: Path | None = None
    verification_report: Path | None = None
    citations: dict[str, Any] = field(default_factory=dict)  # verified / suspicious / hallucinated counts

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("run_dir", "paper_markdown", "paper_tex", "references_bib", "verification_report"):
            d[k] = str(d[k]) if d[k] else None
        return d
