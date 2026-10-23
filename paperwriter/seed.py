"""Turn a :class:`PaperInput` into the artifacts stage 16 expects in a run dir.

Layout mirrors the original pipeline so the unchanged stage code finds them:
``stage-01/goal.md``, ``stage-04/{candidates.jsonl,references.bib}``,
``stage-07/synthesis.md``, ``stage-08/hypotheses.md``.
"""

from __future__ import annotations

import dataclasses
import json
import re
import unicodedata
from pathlib import Path

from paperwriter.models import PaperInput, Reference


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def _letters(n: int) -> str:
    """2 -> 'b', 3 -> 'c', ... 26 -> 'z', 27 -> 'ba' (n >= 2)."""
    out = ""
    n -= 1
    while True:
        out = chr(ord("a") + n % 26) + out
        n = n // 26
        if n == 0:
            return out


def assign_cite_keys(refs: tuple[Reference, ...]) -> tuple[Reference, ...]:
    """Give every reference a unique ``authorYYYYword`` key (explicit keys win)."""
    used: set[str] = {r.cite_key for r in refs if r.cite_key}
    out: list[Reference] = []
    for r in refs:
        key = r.cite_key
        if not key:
            surname = _slug(r.authors[0].split()[-1]) if r.authors else "anon"
            first = next(iter(re.findall(r"[A-Za-z]{4,}", r.title)), "paper")
            base = f"{surname or 'anon'}{r.year or ''}{_slug(first)}"
            key, n = base, 1
            while key in used:  # letter suffixes only: stage 23's text matcher wants [a-z]+YYYY[a-z]*
                n += 1
                key = base + _letters(n)
            used.add(key)
        out.append(dataclasses.replace(r, cite_key=key))
    return tuple(out)


def _bib_escape(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}")


def references_to_bibtex(refs: tuple[Reference, ...]) -> str:
    entries = []
    for r in refs:
        fields = [
            ("title", "{" + _bib_escape(r.title) + "}"),
            ("author", "{" + " and ".join(r.authors) + "}" if r.authors else ""),
            ("year", f"{{{r.year}}}" if r.year else ""),
            ("journal", "{" + _bib_escape(r.venue) + "}" if r.venue else ""),
            ("doi", "{" + r.doi + "}" if r.doi else ""),
            ("url", "{" + r.url + "}" if r.url else ""),
            ("eprint", "{" + r.arxiv_id + "}" if r.arxiv_id else ""),
        ]
        body = ",\n".join(f"  {k} = {v}" for k, v in fields if v)
        entries.append(f"@article{{{r.cite_key},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def seed_run_dir(paper: PaperInput, run_dir: Path) -> tuple[Reference, ...]:
    """Write the input artifacts into ``run_dir``; returns the keyed references."""
    refs = assign_cite_keys(paper.literature)

    _write(
        run_dir / "stage-01" / "goal.md",
        f"# Goal\n\n{paper.goal or paper.topic}\n\n## Topic\n\n{paper.topic}\n",
    )
    _write(
        run_dir / "stage-08" / "hypotheses.md",
        "# Hypotheses\n\n"
        + "\n".join(f"{i}. {h}" for i, h in enumerate(paper.hypotheses, 1))
        + "\n",
    )
    if paper.synthesis.strip():
        _write(run_dir / "stage-07" / "synthesis.md", paper.synthesis)

    rows = [
        {
            "cite_key": r.cite_key,
            "title": r.title,
            "authors": [{"name": a} for a in r.authors],
            "year": r.year,
            "venue": r.venue,
            "doi": r.doi,
            "url": r.url,
            "arxiv_id": r.arxiv_id,
            "abstract": r.abstract,
            "citation_count": r.citation_count,
        }
        for r in refs
    ]
    _write(
        run_dir / "stage-04" / "candidates.jsonl",
        "\n".join(json.dumps(x) for x in rows) + ("\n" if rows else ""),
    )
    _write(run_dir / "stage-04" / "references.bib", references_to_bibtex(refs))

    return refs
