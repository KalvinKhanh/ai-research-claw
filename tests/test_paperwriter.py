"""PaperWriter library: input seeding, config forcing, and an offline end-to-end run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperwriter import PaperInput, write_paper
from paperwriter.pipeline import build_config
from paperwriter.seed import assign_cite_keys, seed_run_dir
from researchclaw.literature import verify as verify_mod
from researchclaw.llm.client import LLMResponse
from researchclaw.pipeline.stages import GATE_ROLLBACK, NEXT_STAGE, Stage

LLM_CFG = {
    "llm": {
        "provider": "openai-compatible",
        "base_url": "http://localhost:1/v1",
        "api_key": "k",
        "api_key_env": "UNUSED",
        "primary_model": "fake",
    }
}

INPUT = {
    "topic": "A survey of topic modelling for journal trend forecasting",
    "hypotheses": ["H1: topic models surface emerging topics earlier than citation counts"],
    "literature": [
        {"title": "Deep learning for trend forecasting", "authors": ["John Smith"], "year": 2024},
        {"title": "Deep learning for trend analysis", "authors": ["Jane Smith"], "year": 2024},
    ],
}


class FakeLLM:
    """Returns a quality report for judge prompts and a short markdown paper otherwise."""

    def __init__(self, score: float = 7.0) -> None:
        self.score = score
        self.prompts: list[str] = []

    def chat(self, messages, **kwargs):
        text = " ".join(m["content"] for m in messages)
        self.prompts.append(text)
        if "score_1_to_10" in text:
            body = json.dumps(
                {"score_1_to_10": self.score, "verdict": "proceed", "strengths": [], "weaknesses": []}
            )
        else:
            body = (
                "# A Survey\n\n## Abstract\nTopic models help [smith2024deep] and "
                "[smith2024deepb].\n\n## Introduction\nText."
            )
        return LLMResponse(content=body, model="fake")


def _patch_verifier(monkeypatch, hallucinated: frozenset[str] = frozenset()):
    """Replace Crossref/OpenAlex lookups.

    Keys in ``hallucinated`` pass the first call (stage 17 pre-verification) and fail
    later ones, so the draft cites them and only stage 23 catches them.
    """
    calls = {"n": 0}

    def fake_verify(bib_text, **kwargs):
        calls["n"] += 1
        results = []
        for e in verify_mod.parse_bibtex_entries(bib_text):
            bad = calls["n"] > 1 and e["key"] in hallucinated
            results.append(
                verify_mod.CitationResult(
                    cite_key=e["key"], title=e.get("title", ""),
                    status=verify_mod.VerifyStatus.HALLUCINATED if bad else verify_mod.VerifyStatus.VERIFIED,
                    confidence=1.0, method="test",
                )
            )
        n_bad = sum(r.status is verify_mod.VerifyStatus.HALLUCINATED for r in results)
        return verify_mod.VerificationReport(
            total=len(results), verified=len(results) - n_bad, hallucinated=n_bad, results=results
        )

    monkeypatch.setattr(verify_mod, "verify_citations", fake_verify)


@pytest.fixture()
def offline_verification(monkeypatch):
    _patch_verifier(monkeypatch)


def test_cite_keys_are_unique_and_stable():
    refs = assign_cite_keys(PaperInput.from_dict(INPUT).literature)
    assert [r.cite_key for r in refs] == ["smith2024deep", "smith2024deepb"]


def test_input_requires_topic_and_normalises_hypotheses():
    with pytest.raises(ValueError):
        PaperInput.from_dict({"hypotheses": []})
    paper = PaperInput.from_dict({**INPUT, "hypotheses": [{"text": "H1"}, "H2", ""]})
    assert paper.hypotheses == ("H1", "H2")


def test_seed_writes_artifacts_stage_16_reads(tmp_path: Path):
    paper = PaperInput.from_dict(INPUT)
    seed_run_dir(paper, tmp_path)
    assert "H1" in (tmp_path / "stage-08" / "hypotheses.md").read_text(encoding="utf-8")
    assert "@article{smith2024deep," in (tmp_path / "stage-04" / "references.bib").read_text(encoding="utf-8")
    rows = (tmp_path / "stage-04" / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[0])["cite_key"] == "smith2024deep"


def test_config_is_forced_docs_first_with_input_topic(tmp_path: Path):
    paper = PaperInput.from_dict(INPUT)
    cfg = build_config(paper, tmp_path, {**LLM_CFG, "project": {"name": "x", "mode": "full-auto"}})
    assert cfg.project.mode == "docs-first"
    assert cfg.research.topic == paper.topic


def test_writing_state_machine_is_closed():
    assert NEXT_STAGE[Stage.PAPER_OUTLINE] is Stage.PAPER_DRAFT
    assert NEXT_STAGE[Stage.EXPORT_PUBLISH] is Stage.CITATION_VERIFY
    assert NEXT_STAGE[Stage.CITATION_VERIFY] is None
    assert set(GATE_ROLLBACK.values()) <= set(Stage)


def test_end_to_end_without_experiments(tmp_path: Path, offline_verification):
    llm = FakeLLM()
    result = write_paper(INPUT, tmp_path, config=LLM_CFG, llm=llm)

    assert result.ok, result.error
    assert [s.number for s in result.stages] == [16, 17, 18, 19, 20, 22, 23]
    assert result.paper_markdown and result.paper_markdown.parent.name == "final"
    assert result.paper_tex and result.paper_tex.is_file()
    assert "smith2024deep" in result.references_bib.read_text(encoding="utf-8")
    assert result.citations["total"] == 2
    assert result.citations["verified"] == result.citations["total"]
    assert result.citations["hallucinated"] == 0
    assert "NeurIPS" not in result.paper_tex.read_text(encoding="utf-8")
    assert json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))["ok"] is True


def test_rejected_quality_gate_rewrites_once_then_fails(tmp_path: Path, offline_verification):
    config = {**LLM_CFG, "research": {"graceful_degradation": False, "quality_threshold": 8.0}}
    result = write_paper(INPUT, tmp_path, config=config, llm=FakeLLM(score=2.0), max_rewrites=1)

    assert not result.ok
    assert "QUALITY_GATE" in result.error
    outlines = [s for s in result.stages if s.stage == "PAPER_OUTLINE"]
    assert len(outlines) == 2  # first pass + one rewrite
    assert result.paper_markdown is None or result.citations == {}


def test_hallucinated_citation_is_removed_from_every_deliverable(tmp_path: Path, monkeypatch):
    _patch_verifier(monkeypatch, hallucinated=frozenset({"smith2024deepb"}))
    result = write_paper(INPUT, tmp_path, config=LLM_CFG, llm=FakeLLM())

    assert result.ok, result.error
    assert result.citations["hallucinated"] == 1
    for path in (result.paper_markdown, result.paper_tex, result.references_bib):
        text = path.read_text(encoding="utf-8")
        assert "smith2024deepb" not in text, path.name
    assert "smith2024deep" in result.paper_tex.read_text(encoding="utf-8")
    assert "smith2024deep" in result.references_bib.read_text(encoding="utf-8")


def test_rerun_starts_fresh_and_ignores_stale_degradation(tmp_path: Path, offline_verification):
    (tmp_path / "degradation_signal.json").write_text("{}", encoding="utf-8")
    (tmp_path / "stage-17").mkdir()
    (tmp_path / "stage-17" / "stale.txt").write_text("old", encoding="utf-8")

    result = write_paper(INPUT, tmp_path, config=LLM_CFG, llm=FakeLLM())

    assert result.ok, result.error
    assert not (tmp_path / "degradation_signal.json").exists()
    assert not (tmp_path / "stage-17" / "stale.txt").exists()


def test_rewrite_passes_review_feedback_to_outline(tmp_path: Path, offline_verification):
    config = {**LLM_CFG, "research": {"graceful_degradation": False, "quality_threshold": 8.0}}
    llm = FakeLLM(score=2.0)
    write_paper(INPUT, tmp_path, config=config, llm=llm, max_rewrites=1)

    ctx = json.loads((tmp_path / "iteration_context.json").read_text(encoding="utf-8"))
    assert ctx["iteration"] == 2 and ctx["quality_score"] == 2.0
    assert any("Iteration 2 Feedback" in p for p in llm.prompts)


def test_requires_llm_or_config(tmp_path: Path):
    with pytest.raises(ValueError, match="config"):
        write_paper(INPUT, tmp_path)
