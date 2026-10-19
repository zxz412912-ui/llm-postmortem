"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyze
from .report import render_html, render_markdown


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("expected a JSON object")
            records.append(item)
        except (json.JSONDecodeError, ValueError) as error:
            errors.append(f"Line {number}: {error}")
    return records, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Find recurring LLM failures in JSONL call logs.")
    parser.add_argument("input", type=Path, help="Path to JSONL logs")
    parser.add_argument("--output", "-o", type=Path, help="Write the Markdown report to this path")
    args = parser.parse_args()
    records, errors = load_jsonl(args.input)
    analysis = analyze(records, errors)
    report = render_html(analysis) if args.output and args.output.suffix.lower() == ".html" else render_markdown(analysis)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
