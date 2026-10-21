---
name: student-handoff
description: Package a molecule's raw extraction for a student as molecules/<mol>/student_handoff/ (one shared papers/ folder, one CSV folder per isotopologue, a README of open issues). Use when asked for a student hand-off, or to update one.
---

The hand-off is the raw, unmerged extraction plus the sources needed to check it, nothing else. Reference
layout: `molecules/CN/student_handoff/` (2026-10-21).

```
student_handoff/
  README.md     what each folder holds, open issues per paper, decisions needed before merging
  papers/       sources shared by every isotopologue: PDFs, supplements, publisher XML/TXT of text-native papers
  <iso>/        <paperID>_batch<N>.csv, one folder per isotopologue
```

Left out on purpose, because they stay in `molecules/<mol>/`: MinerU output (`markdown/`, `markdown_cloud/`,
`ocr_diff.md`, `ocr_3way.csv`), superseded extractions, `.done` markers, and the sources of papers with
nothing extracted. Every OCR fix and review flag already lives in the CSV `notes` column.

## Steps

1. **Settle the user checks.** Collect every row whose `notes` carries `OCR 3-way: user check` into one
   table (paper, PDF page, location, the readings) and hand it to the user. Apply their values, then set
   the note to `OCR 3-way: user-confirmed against PDF` in `molecules/<mol>/csv/`. Done when
   `grep -l "OCR 3-way: user check" molecules/<mol>/csv/*.csv` prints nothing.
2. **Clear the target.** `scripts/student_handoff.py` refuses to write over anything but `README.md`. Move
   an older hand-off's other contents to `molecules/<mol>/archive/student_handoff_<YYYYMMDD_HHMMSS>/`;
   move, never delete.
3. **Build.** `python3 scripts/student_handoff.py molecules/<mol> --extra <paperID> ...`. `--extra` names
   each paper with no rows that the README cites as a correction source (CN: 84ItOzNa fixes 28Je). Done
   when it prints the row total with no assertion error, and every paper it reports as skipped (no `.done`)
   is one the user agreed to leave out.
4. **Missing PDFs.** Give the user the `doi.org` links the script prints. Once they add a PDF, copy it to
   both `student_handoff/papers/` and `molecules/<mol>/papers/<folder>/`, refusing to overwrite.
5. **README.** Write or update `README.md`, keeping the CN README's sections:
   - one bullet per folder, naming any paper split across isotopologue folders and any source oddity
     (rows from a supplement, a paper split into several PDFs, a text-native paper);
   - **Papers with data**: paper, rows, isotopologue(s), open issues, one row per paper the script printed;
   - **Papers with nothing extracted**: paper and reason, every finished paper without rows;
   - **Decisions needed before merging**, numbered, each naming its papers, then the pipeline pointer
     (`csv_to_marvel.py merge → split-parity → validate → reviewer → reconcile → format`).
   Done when every paper in the script's table and every row-less `.done` paper appears exactly once, the
   row counts match the script, and every path the README names exists inside the hand-off (anything else
   is described as "in `molecules/<mol>/` of the pipeline repo").
