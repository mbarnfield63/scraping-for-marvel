# MARVEL Input Creation Pipeline

## Project Purpose

This repository automates the extraction of measured rotational-vibrational transitions from spectroscopic research papers and formats them as **MARVEL** (Measured Active Rotational-Vibrational Energy Levels) input files.

The MARVEL algorithm (Furtenbacher, Császár & Tennyson 2007; Furtenbacher & Császár 2012) inverts experimentally measured transition data to yield empirical energy levels with well-defined uncertainties. It builds a spectroscopic network where vertices are energy levels and edges are measured transitions. The pipeline in this repository collects, parses, and formats transitions from literature sources into the input format required by the MARVEL code.

## Operating Rules

### 1. Initialize
When the user says **"get up to speed"**, immediately read the Obsidian state file at:
`C:/Obsidian/Claude_State/MARVEL scraping.md` to reconstruct full context.

### 2. Log & Save
When reaching a milestone or when the user says **"save state"**, overwrite the Obsidian state file (`C:/Obsidian/Claude_state/MARVEL scraping.md`) with a clean update (see Rule 3 format) and append a summary of work done to the log file (`C:/Obsidian/Logs/MARVEL scraping Log.md`). Never change any other files within `C:/Obsidian/`.

### 3. Obsidian State File Format
When writing to `C:/Obsidian/Claude_State/MARVEL scraping.md`, always overwrite with:

```
# MARVEL scraping — Claude State

**Last Modified:** YYYY-MM-DD HH:MM

**Completed:**
- Molecule: 
- Isotopologues:
- Transitions: 

**Next Steps / Blockers:**
- Exactly what needs to be tackled next session or the papers required to be analysed by the user for potential further scraping.
```

## Directory Structure

```
C:\Code\MARVEL\
├── docs\                         # Reference PDFs and agent docs
├── molecules\
│   └── <molecule>\               # One folder per molecule (e.g. CS2, CO, H2O)
│       ├── papers\               # Source PDFs and supplementary files
│       ├── markdown\             # MinerU cloud output, one folder per paper (see Step 2)
│       ├── csv\                  # Batch CSVs, merged CSV, reviewer reports
│       └── output\               # Final MARVEL .txt files
├── scripts\
│   ├── mineru_cloud.py           # Batch OCR via MinerU cloud API → markdown + bbox JSON
│   ├── csv_to_marvel.py          # Merge batch CSVs and format to MARVEL
│   └── templates\
│       └── scraper_template.md   # Extraction-brief skeleton (anti-fabrication rules, QN columns, hazards)
├── archive\
│   └── ocr-pipeline-v1\          # Retired self-hosted OCR pipeline — see Pipeline Workflow note
└── CLAUDE.md                     # This file
```

Molecule subdirectories are created on demand. A `briefs/` folder may appear under a molecule holding per-paper extraction notes — optional working scratch, not a required stage.

## Reference Papers (Context Only — Not for Extraction)

These PDFs live in `docs/` and serve as reference material for the MARVEL format. They are **not** targets for the extraction pipeline.

| File | Description |
|------|-------------|
| `07FuCsTe_Marvel.pdf` | Original MARVEL methodology paper (J. Mol. Spectrosc. 245, 2007). Defines the algorithm, spectroscopic networks, and robust reweighting. |
| `2012FuCs_Marvel_improved.pdf` | MARVEL algorithmic improvements (JQSRT 113, 2012). Hash-based input, conjugate gradient least-squares. |
| `2026GrDaPo_COisos_Marvel.pdf` | MARVEL analysis of CO minor isotopologues (ApJS 283, 2026). Diatomic — quantum numbers (v, J). |
| `24AzAzAb_CO2isos_Marvel.pdf` | MARVEL analysis of rare CO₂ isotopologues (J. Mol. Spectrosc. 405, 2024). Linear triatomic, Herzberg notation. |

## MARVEL Input Format

Tab-separated. Column scheme depends on molecular type.

### Diatomics (e.g. CO, CS)
```
transition_wavenumber   uncertainty   v_upper   J_upper   v_lower   J_lower   ID
```

### Linear Triatomics (e.g. CO₂, CS₂) — Herzberg notation
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   l2_upper   v3_upper   J_upper   v1_lower   v2_lower   l2_lower   v3_lower   J_lower   ID
```

### Asymmetric Tops (e.g. H₂O)
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   v3_upper   J_upper   Ka_upper   Kc_upper   v1_lower   v2_lower   v3_lower   J_lower   Ka_lower   Kc_lower   ID
```

### ID Construction Rules
Format: `YYAuthAuth.N`
- **YY** — 2-digit publication year
- **Auth** — first 2 letters of each of up to 3 authors' surnames, concatenated
- **N** — integer starting at 1, **resetting to 1 for each new isotopologue** within the same paper

### Output Filename Convention
```
<molecule>_<isotopologue>_<paperID>_YYYYMMDD_HHMMSS.txt
```
Saved in `molecules/<molecule>/output/`.

---

## Pipeline Workflow

### Overview

Two-stage pipeline: **MinerU cloud API** (OCR → markdown + bounding-box JSON) → **Claude** (validate, extract, review — interactive in this session).

```
mineru_cloud.py (cloud OCR) → Claude validate+extract → csv_to_marvel.py merge → reviewer agent (hard gate) → csv_to_marvel.py format
```

> **Why cloud, not self-hosted.** Self-hosting the OCR model was built and rejected. The open MinerU-2.5 1.2B model, run locally/on HPC, silently corrupts ~8% of values on hard scanned papers (digit misreads like `2186→2189`, high-J column drops, decimal-comma confusion) — unacceptable when a single wrong wavenumber silently corrupts the spectroscopic network. The cloud **`vlm`** model is the one whose quality was validated cell-by-cell against ground truth. The entire retired self-hosted pipeline (Gemini pre-screener, HPC OCR models, SLURM scripts) lives in `archive/ocr-pipeline-v1/`. Do not re-litigate self-hosting without new evidence that the local model has closed that gap.

1. **OCR** (cloud): `python scripts/mineru_cloud.py molecules/<mol>/papers --out-dir molecules/<mol>/markdown`
2. **Validate + extract** (Claude, interactive): read each paper's `full.md` + `content_list.json`, verify suspect cells against bbox crops of the page, write batch CSVs to `csv/`
3. **Merge**: `python scripts/csv_to_marvel.py merge <mol> <paperID>`
4. **Reviewer agent** → `molecules/<mol>/csv/<paperID>_review.md` — **HARD GATE**
5. **Format**: `python scripts/csv_to_marvel.py format <mol> <paperID>`

---

### Step 1: Set Up Molecule Directory

```bash
mkdir -p molecules/<mol>/papers molecules/<mol>/markdown molecules/<mol>/csv molecules/<mol>/output
```

Place source PDFs (and supplementary files, if any) in `papers/`. If a paper's transitions live only in an online supplement, add the supplement to `papers/` — the OCR stage handles the main PDF, but supplementary data files are often clean text/CSV that can be parsed directly without OCR.

---

### Step 2: OCR via MinerU Cloud API

```bash
python scripts/mineru_cloud.py molecules/<mol>/papers --out-dir molecules/<mol>/markdown
```

Submits every PDF in one batch to the MinerU v4 API (model `vlm`, OCR on), polls, and unzips one result folder per paper into `markdown/<paperID>/`:

- `full.md` — **source of truth for table bodies.** MinerU emits tables as HTML `<table>` blocks (not pipe markdown), with dual/triple-column layouts correctly unpacked.
- `<paperID>_content_list.json` — **source of truth for structure**: per-block `type`, `bbox`, `page_idx`, `table_caption`, `table_footnote`, `table_body`. Use this for captions, page mapping, and bbox crops.
- `images/`, `layout.json`, `<paperID>_origin.pdf` — page renders and layout data for the validation crops. (MinerU emits these with an internal UUID prefix; `mineru_cloud.py` renames them to the paper stem.)

**Token**: resolved from `--token`, then `$MINERU_API_TOKEN`, then the desktop client's `config.json` (`C:/Users/Marco/MinerU/config.json`, field `state.client_api_token`). Free tier: 2000 pages/day at top priority (more at reduced priority), 10,000 files/day. Data egress is fine — these are published papers.

**Known gotcha**: on a multi-page table, continuation pages register a caption block in `content_list.json` but often **no `table_body`** — the body is only in `full.md`. Always reconcile the two; never trust `content_list.json` alone for row counts.

---

### Step 3: Validate + Extract (Interactive — Claude)

One Claude pass per paper does reasoning **and** extraction (there is no separate pre-screener API call — that reasoning is folded in here). For each paper:

1. Read `markdown/<paperID>/full.md` and `<paperID>_content_list.json`. Read the paper's Experimental section (from `full.md`) for the stated measurement uncertainty and band assignments.
2. **Validate before extracting.** MinerU cloud is strong but not infallible on hard scans. For any cell that looks off — broken monotonicity in a branch, a header-span flattened into left-packed cells, a suspiciously short row — crop the table's `bbox` from the page image and read the value visually. Fix obvious OCR errors (header-span misalignment, decimal punctuation) against the crop. Where the crop is genuinely illegible, mark the cell **UNREADABLE** — never guess a digit.
3. Apply quantum-number assignments, the paper's uncertainty, and band/isotopologue labels to parse the HTML tables into the correct CSV column structure (see MARVEL Input Format + Quantum Number Reference).
4. Emit batch CSVs to `molecules/<mol>/csv/<paperID>_batch<N>.csv`, columns:
   `transition_wavenumber, uncertainty, <QN columns>, id, iso, notes`
   Use `notes` to record table/band/branch provenance and any OCR fix or UNREADABLE flag.

**Anti-fabrication rule**: a wrong value silently corrupts the spectroscopic network — there is no downstream physical check. Never invent, interpolate, or "smooth" a value. An UNREADABLE flag is always correct over a guess. See `scripts/templates/scraper_template.md` for the full extraction-brief skeleton.

---

### Step 4: Merge

```bash
python scripts/csv_to_marvel.py merge <mol> <paperID>
```

Merges all `<paperID>_batch*.csv` files into `<paperID>_merged.csv` in the same `csv/` directory. Errors if batch files are missing or have mismatched column headers.

---

### Step 5: Reviewer Agent

Spawn one reviewer agent with the path to `<paperID>_merged.csv`. **The reviewer must not modify any data.**

**Validation checks:**
1. **ID format** — every entry matches `YYAuthAuth.N`; N resets to 1 per isotopologue
2. **Uncertainty** — all values positive, non-blank (N/A only if `notes` explains why)
3. **Wavenumber range** — positive, physically plausible for the molecule and band
4. **Quantum numbers** — J ≥ 0, v ≥ 0, |l₂| ≤ v₂ for linear triatomics
5. **Isotopologue labels** — consistent notation throughout
6. **Transition counts** — extracted vs. expected; flag if <80% of expected for any isotopologue
7. **UNREADABLE rows** — list all, grouped by table
8. **Cross-batch duplicates** — same wavenumber (±0.002 cm⁻¹) + same quantum numbers but different ID

**Report** (written to `molecules/<mol>/csv/<paperID>_review.md`):
- Section 1: check-by-check PASS / FAIL / PARTIAL with specifics
- Section 2: all flagged rows with location and reason
- Section 3: UNREADABLE row inventory
- Section 4: final recommendation — one of:
  - `READY FOR MARVEL CONVERSION`
  - `READY WITH CAVEATS` (list caveats — acceptable gaps that do not block conversion)
  - `REQUIRES MANUAL REVIEW` (list specific blockers)

**Hard gate**: if the recommendation is `REQUIRES MANUAL REVIEW`, do not proceed to Step 6. Surface the blockers to the user.

---

### Step 6: Format

```bash
python scripts/csv_to_marvel.py format <mol> <paperID>
```

Reads `<paperID>_merged.csv`, splits by `iso` column, and writes one MARVEL `.txt` file per isotopologue to `molecules/<mol>/output/`. Drops the `iso` and `notes` columns; all other columns are written tab-separated with a header row.

---

## Quantum Number Reference

| Molecule Type | Examples | Upper QNs | Lower QNs |
|---|---|---|---|
| Diatomic | CO, CS, SiS | v′, J′ | v″, J″ |
| Linear triatomic | CO₂, CS₂, N₂O | v₁′, v₂′, ℓ₂′, v₃′, J′ | v₁″, v₂″, ℓ₂″, v₃″, J″ |
| Symmetric top | NH₃ | v′, J′, K′ | v″, J″, K″ |
| Asymmetric top | H₂O, SO₂ | v₁′, v₂′, v₃′, J′, Ka′, Kc′ | v₁″, v₂″, v₃″, J″, Ka″, Kc″ |

## Isotopologue Shorthand

Papers often use a 3-digit shorthand where each digit is the mass number of the relevant atoms:
- **CO₂**: 626 = ¹²C¹⁶O₂, 828 = ¹⁸O¹²C¹⁸O, 728 = ¹⁷O¹²C¹⁸O, 838 = ¹⁸O¹³C¹⁸O
- **CS₂**: digits represent the two S atoms (C implicit) — 323 = ³²S¹²C³²S (parent), 324 = ³²S¹²C³⁴S, 534 = ¹³C³²S₂

Follow the same pattern for other molecules.

---

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/` in this repo (local-markdown, no external CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
