#!/usr/bin/env python3
"""Resume check for an extraction fan-out: which papers lack csv/<paperID>.done.

    python3 scripts/batch_status.py <mol> [paperID ...]

Without paper IDs it checks every OCR'd paper (each folder under molecules/<mol>/markdown/).
Prints one line: done N/M · todo: <paperIDs>. See the marvel-pipeline skill, Fan-out.
"""
import sys
from pathlib import Path

mol = Path(__file__).resolve().parent.parent / "molecules" / sys.argv[1]
papers = sys.argv[2:] or sorted(p.name for p in (mol / "markdown").iterdir() if p.is_dir())
todo = [p for p in papers if not (mol / "csv" / f"{p}.done").exists()]
print(f"done {len(papers) - len(todo)}/{len(papers)} · todo: {' '.join(todo) or '-'}")
