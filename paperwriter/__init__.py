"""PaperWriter: attach ResearchClaw's paper-writing stages to any project.

    from paperwriter import write_paper
    result = write_paper({"topic": ..., "hypotheses": [...], "literature": [...]},
                         "out/", config="config.yaml")
"""

from paperwriter.models import PaperInput, PaperResult, Reference, StageOutcome
from paperwriter.pipeline import write_paper

__version__ = "0.1.0"

__all__ = ["PaperInput", "PaperResult", "Reference", "StageOutcome", "write_paper"]
