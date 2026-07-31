---
name: marvel-pipeline
description: Step-by-step MARVEL extraction pipeline for this repo — set up a molecule directory, OCR papers via MinerU cloud, validate + extract to CSV, merge, mechanically validate, run the reviewer sub-agent, and format to MARVEL .txt output. Use when processing a paper (or a new molecule) into MARVEL input, or when asked what the next pipeline step is.
---

## Overview

Two-stage pipeline: **MinerU cloud API** (OCR → markdown + bounding-box JSON) → **Claude** (validate + extract in an isolated `marvel-extractor` sub-agent, review in an isolated `marvel-reviewer` sub-agent, orchestration/scripts run in the main session).

```
mineru_cloud.py (cloud OCR) → Claude validate+extract → csv_to_marvel.py merge → csv_to_marvel.py split-parity → csv_to_marvel.py validate (script) → reviewer sub-agent (hard gate) → csv_to_marvel.py reconcile → csv_to_marvel.py format
```

Cloud OCR over self-hosted: see `docs/adr/0001-cloud-ocr-over-self-hosted.md`.

1. **Set up** molecule directory (`papers/`, `markdown/`, `csv/`, `reviews/`, `output/`)
2. **OCR** (cloud): `python scripts/mineru_cloud.py molecules/<mol>/papers --out-dir molecules/<mol>/markdown`
3. **Validate + extract** (`marvel-extractor` sub-agent, isolated): read each paper's `full.md` + `content_list.slim.json`, verify suspect cells against bbox crops of the page, write batch CSVs to `csv/`
4. **Merge**: `python scripts/csv_to_marvel.py merge <mol> <paperID>`
5. **Split unresolved parity pairs** (script, mechanical, electronic-transition papers only): `python scripts/csv_to_marvel.py split-parity <mol> <paperID>`
6. **Validate** (script, mechanical): `python scripts/csv_to_marvel.py validate <mol> <paperID>`
7. **Reviewer sub-agent** (judgment only) → `molecules/<mol>/reviews/<paperID>_review.md` — **HARD GATE**
8. **Reconcile units** (script, mechanical): `python scripts/csv_to_marvel.py reconcile <mol> <paperID>`
9. **Format**: `python scripts/csv_to_marvel.py format <mol> <paperID>`

---

### Step 1: Set Up Molecule Directory

```bash
mkdir -p molecules/<mol>/papers molecules/<mol>/markdown molecules/<mol>/csv molecules/<mol>/reviews molecules/<mol>/output
```

Place source PDFs (and supplementary files, if any) in `papers/`. If a paper's transitions live only in an online supplement, add the supplement to `papers/` — the OCR stage handles the main PDF, but supplementary data files are often clean text/CSV that can be parsed directly without OCR.

---

### Step 2: OCR via MinerU Cloud API

```bash
python scripts/mineru_cloud.py molecules/<mol>/papers --out-dir molecules/<mol>/markdown
```

Submits every PDF in one batch to the MinerU v4 API (model `vlm`, OCR on), polls, and unzips one result folder per paper into `markdown/<paperID>/`:

- `full.md` — **source of truth for table bodies.** MinerU emits tables as HTML `<table>` blocks (not pipe markdown), with dual/triple-column layouts correctly unpacked.
- `<paperID>_content_list.slim.json` — **source of truth for structure**: per-block `type`, `bbox`, `page_idx`, `table_caption`, `table_footnote`, and (for table blocks) `has_table_body`. Use this for captions, page mapping, and bbox crops. `table_body` is stripped from this file — it's a byte-for-byte duplicate of what's already in `full.md` (routinely >95% of the raw file's size) — so **read the `.slim.json`, never the full `<paperID>_content_list.json`**, for structure. The full (non-slim) file still exists on disk if a slim-file bug ever needs cross-checking, but should not be the default read.
- `images/`, `layout.json`, `<paperID>_origin.pdf` — page renders and layout data for the validation crops. (MinerU emits these with an internal UUID prefix; `mineru_cloud.py` renames them to the paper stem.)

**Token**: resolved from `--token`, then `$MINERU_API_TOKEN`, then the desktop client's `config.json` (`C:/Users/Marco/MinerU/config.json`, field `state.client_api_token`). Free tier: 2000 pages/day at top priority (more at reduced priority), 10,000 files/day. Data egress is fine — these are published papers.

**Known gotcha**: on a multi-page table, continuation pages register a caption block but often have `has_table_body: false` (or the key absent) in `content_list.slim.json` — the body is only in `full.md`. Always reconcile the two; never trust `content_list.slim.json` alone for row counts.

---

### Step 3: Validate + Extract (`marvel-extractor` sub-agent, isolated)

Spawn the `marvel-extractor` sub-agent (`.claude/agents/extractor.md`) per paper, passing the molecule dir + paperID. It runs isolated from the calling session — the OCR markdown/image context it reads never touches the main session's history, so it isn't replayed via cache-read through Steps 4-8 (validated: isolated per-paper extraction cut main-session cache-read from a ~60-66M/278-337-turn baseline to ~2.7M/51 turns for a comparable two-paper run). It works to completion and reports back one line per batch file — no back-and-forth needed. For each paper:

1. Reads `markdown/<paperID>/full.md` and `<paperID>_content_list.slim.json` (not the full, non-slim `content_list.json` — see Step 2), including the Experimental section for stated measurement uncertainty and band assignments.
2. **Validates before extracting.** MinerU cloud is strong but not infallible on hard scans. For any cell that looks off — broken monotonicity in a branch, a header-span flattened into left-packed cells, a suspiciously short row — it crops the table's `bbox` from the page image and reads the value visually. Fixes obvious OCR errors (header-span misalignment, decimal punctuation) against the crop. Where the crop is genuinely illegible, marks the cell **UNREADABLE** — never guesses a digit.
3. Applies quantum-number assignments, the paper's uncertainty, and band/isotopologue labels to parse the HTML tables into the correct CSV column structure (see MARVEL Input Format in CLAUDE.md + `docs/agents/reference.md` for the QN table).
4. Emits batch CSVs to `molecules/<mol>/csv/<paperID>_batch<N>.csv`, columns:
   `transition_wavenumber, uncertainty, <QN columns>, id, iso, notes`
   Using `notes` to record table/band/branch provenance and any OCR fix or UNREADABLE flag.

The **anti-fabrication**, **uncertainty**, and **unit** rules for this step live in the root `CLAUDE.md` ("Extraction Rules") and are mirrored in `extractor.md` — always apply them.

---

### Step 4: Merge

```bash
python scripts/csv_to_marvel.py merge <mol> <paperID>
```

Merges all `<paperID>_batch*.csv` files into `<paperID>_merged.csv` in the same `csv/` directory. Errors if batch files are missing or have mismatched column headers.

---

### Step 5: Split Unresolved Parity Pairs (script, mechanical, electronic-transition papers only)

```bash
python scripts/csv_to_marvel.py split-parity <mol> <paperID>
```

Extraction never duplicates rows itself (Parity rule, CLAUDE.md) — when a paper doesn't resolve which e/f parity component was measured for a state, the extractor leaves `ef_upper`/`ef_lower` blank and tags `notes` with `parity: unresolved`. This step scans `<paperID>_merged.csv` for that token (molecule-obliviously — it just looks for `ef_upper`/`ef_lower` columns and the token, no per-molecule logic) and, for each tagged row: sets that row's own `ef_upper`/`ef_lower` to `e` in place (same ID, no renumbering), and appends **one** new row at the tail of that isotopologue's ID block with `ef_upper`/`ef_lower` set to `f` and the identical wavenumber/uncertainty/other QNs. Only the new `f` row gets a fresh ID (append-only, no gaps, safe to rerun). The original row's `notes` gets marked consumed (`parity: unresolved (split -> .510)`) and the new row cross-references it (`parity-split: sibling of <original id>`), so rerunning is a no-op on already-split rows. No-op entirely for papers without the token (i.e. every non-electronic-transition paper).

---

### Step 6: Validate (script, mechanical)

```bash
python scripts/csv_to_marvel.py validate <mol> <paperID>
```

Runs every check that's pure logic against `<paperID>_merged.csv` — no LLM judgment needed: ID format/sequencing, uncertainty non-blank/positive, wavenumber positivity, generic QN arithmetic validity (J/v ≥ 0, K ≤ J, |l#| ≤ v#), isotopologue-label counts, UNREADABLE inventory, and cross-batch duplicates (same wavenumber ±0.002 cm⁻¹ + same QNs/iso, different ID). Prints a report; fixes nothing. Run this **before** spawning the reviewer sub-agent — it exists so the sub-agent doesn't re-derive mechanical checks by hand every time.

A flag here is not automatically an error — e.g. `|l#| > v#` is sometimes a legitimate Coriolis-perturbation-allowed transition, not a data bug. The script flags; the reviewer sub-agent (Step 7) judges.

Note: this includes checking uncertainty is non-blank/positive, but not unit consistency between wavenumber and uncertainty within a row — that's Step 8 (Reconcile). It also checks split-parity pair integrity for electronic-transition papers: every `e`/`f` pair produced by Step 5 must be wavenumber/QN-identical apart from the parity label; orphaned or mismatched pairs are flagged (most likely a Step 5 script bug, not a data error).

---

### Step 7: Reviewer Sub-Agent

Spawn the `marvel-reviewer` sub-agent (`.claude/agents/reviewer.md`) with the path to `<paperID>_merged.csv` and the Step 5 validate output. **The reviewer must not modify any data** — it runs with a restricted toolset (no `Edit`) by design.

The sub-agent's job is only what the script can't do: QN domain-validity judgment on flagged rows, and visual spot-check verification against source PDF pages. **Confidence-tiered, not exhaustive**: it flags genuinely uncertain rows rather than chasing full certainty through repeated re-derivation.

**Re-review scope**: if `molecules/<mol>/reviews/<paperID>_review.md` already exists, a re-review reads **only the rows that report flagged, plus any rows changed since** — never the whole file again. Only do a full re-review if the user explicitly asks for one.

If two independent passes disagree on a single value (a digit, a symmetry label, etc.), resolve it by directly rendering the source PDF page and reading it visually — ideally side-by-side against an unambiguous reference character on the same page — rather than trusting either pass's confidence language or an "objective" automated method (pixel/hole-counting has been shown to mis-read glyphs). Critically, **`full.md`'s OCR text is not independent ground truth** — it can misread the same glyph a disputed cell is arguing about. Always settle real disagreements against the rendered page image itself.

**Report** (written to `molecules/<mol>/reviews/<paperID>_review.md`) — compact template, no prose for passing checks:
- Judgment-checks table (QN domain-validity, visual spot-check) — PASS/FLAGGED + one-line detail
- Flagged-rows table: row id / field / confidence / reason — one line each
- One-line verdict: `READY FOR MARVEL CONVERSION` / `READY WITH CAVEATS` (list caveats) / `REQUIRES MANUAL REVIEW` (list blockers)

**Hard gate**: if the recommendation is `REQUIRES MANUAL REVIEW`, do not proceed to Step 8. Surface the blockers to the user.

---

### Step 8: Reconcile Units (script, mechanical)

```bash
python scripts/csv_to_marvel.py reconcile <mol> <paperID>
```

Extraction never converts units (Unit rule, CLAUDE.md) — a row's uncertainty is sometimes stated in a different native unit than its wavenumber (e.g. a global fit-uncertainty quoted in kHz for an MHz transition table). This step is the one place a conversion happens: it scans each row's `notes` for `unit:` mentions — the first is always the wavenumber's unit, any later *different* one is the uncertainty's unit — and converts the uncertainty into the wavenumber's unit, appending `unit-reconciled: <old> <unit> -> <new> <unit>` to `notes` so the conversion stays auditable. No-op for rows where both columns already share a unit. Currently handles `Hz`/`kHz`/`MHz`/`GHz`; extend `FREQ_TO_HZ` in `csv_to_marvel.py` if a paper needs another unit pair.

---

### Step 9: Format

```bash
python scripts/csv_to_marvel.py format <mol> <paperID>
```

Reads `<paperID>_merged.csv`, splits by `iso` column, and writes one MARVEL `.txt` file per isotopologue to `molecules/<mol>/output/`. Drops the `iso` and `notes` columns; all other columns are written tab-separated with a header row.
