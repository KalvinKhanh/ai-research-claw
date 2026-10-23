"""``paperwriter`` command line: write a paper from a JSON input file."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from paperwriter.models import PaperInput
from paperwriter.pipeline import write_paper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paperwriter",
        description="Write a literature-first paper from topic + hypotheses + literature.",
    )
    parser.add_argument("input", help="JSON file: {topic, hypotheses[], literature[], goal?, synthesis?}")
    parser.add_argument("-o", "--output", required=True, help="output directory (previous stage outputs in it are replaced)")
    parser.add_argument("-c", "--config", required=True, help="YAML config with at least an 'llm' section")
    parser.add_argument("--max-rewrites", type=int, default=1, help="outline rewrites after a rejected quality gate")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)
    result = write_paper(
        PaperInput.from_json(args.input),
        args.output,
        config=args.config,
        max_rewrites=args.max_rewrites,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
