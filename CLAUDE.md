# MARVEL Input Creation Pipeline

## Project Purpose

This repository automates the extraction of measured rotational-vibrational transitions from spectroscopic research papers and formats them as **MARVEL** (Measured Active Rotational-Vibrational Energy Levels) input files.

The MARVEL algorithm (Furtenbacher, Császár & Tennyson 2007; Furtenbacher & Császár 2012) inverts experimentally measured transition data to yield empirical energy levels with well-defined uncertainties. It builds a spectroscopic network where vertices are energy levels and edges are measured transitions. The pipeline in this repository collects, parses, and formats transitions from literature sources into the input format required by the MARVEL code.

## Operating Rules

### 1. Initialize
When the user says **"get up to speed"**, immediately read the Obsidian state file at:
`C:/Obsidian/Claude_State/MARVEL scraping.md` to reconstruct full context.

### 2. Log & Save
When reaching a milestone or when the user says **"save state"**, overwrite the Obsidian state file (`C:/Obsidian/Claude_state/MARVEL scraping.md`) with a clean update (see Rule 4 format) and append a summary of work done to the log file (`C:/Obsidian/Logs/MARVEL scraping Log.md`). Never change any other files within `C:/Obsidian/`.

### 3. Never delete untracked files outside your own run
Never delete, move-as-cleanup, or overwrite an untracked file in this repo unless it was created by the current agent/session's own run (e.g. a temp file you just wrote to your own scratchpad). Untracked files (`git status`) are frequently in-progress user work, not junk — `git` gives no recovery path for them if deleted. This applies even to "obviously superfluous"-looking files (stray `.txt`/`.json` scratch files at the repo root, etc.) and even when doing routine cleanup. If a file looks like leftover clutter and you did not create it in this run, leave it alone or ask the user before touching it.

### 4. Obsidian State File Format
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

Molecule subdirectories are created on demand. A `briefs/` folder may appear under a molecule holding per-paper extraction notes — optional working scratch, not a required stage.

Reference PDFs list, the Quantum Number table, and Isotopologue Shorthand are lookup material, not needed to decide what to do next — see `docs/agents/reference.md`.

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

### Diatomics with electronic transitions (e.g. SO bands crossing electronic states)
```
transition_wavenumber   uncertainty   state_upper   v_upper   J_upper   F_upper   ef_upper   state_lower   v_lower   J_lower   F_lower   ef_lower   ID
```
Use only when a paper's transitions span more than one electronic state — a single-state diatomic paper stays on the plain Diatomics scheme above. `state_*` is a plain term-symbol string (e.g. `X3Sigma-`, `a1Delta`) — see `docs/agents/reference.md` for term-symbol notation. `F_*`/`ef_*` are blank for singlet states and populated only when the paper resolves fine-structure sublevel/parity. Generalizes to other molecular types by prepending `state_upper`/`state_lower` to that type's existing QN block whenever a paper includes electronic transitions.

### Diatomics with hyperfine structure (e.g. CS isotopologues with resolved nuclear-spin splitting)
```
transition_wavenumber   uncertainty   v_upper   J_upper   F_upper   v_lower   J_lower   F_lower   ID
```
Use only when a paper reports individually resolved hyperfine components (from nuclear spin I > 0 — quadrupole and/or spin-rotation coupling) rather than a single unresolved line per (v, J) pair — an isotopologue with no resolved hyperfine splitting in a given paper stays on the plain Diatomics scheme above, even if other isotopologues in the same paper do need this scheme. `F_upper`/`F_lower` here is the **nuclear hyperfine** quantum number (half-integer or integer depending on nuclear spin, e.g. `F=5/2,3/2,1/2` for I=3/2) — a distinct physical quantity from the `F_upper`/`F_lower` electronic fine-structure sublevel label used in the "Diatomics with electronic transitions" scheme above; the two schemes are never combined in the same paper's output, and column meaning is always inferred from which scheme a given CSV/file is using, not the column name alone. A paper's derived/fitted hyperfine constants (nuclear quadrupole coupling `eQq`, spin-rotation `C_I`, hypothetical hyperfine-free frequency `v0`, etc.) are fit outputs, not raw transition data — never extract them; only the individually resolved component frequencies belong in MARVEL input, per the anti-fabrication rule. Generalizes to other molecular types by appending `F_upper`/`F_lower` immediately after `J_upper`/`J_lower` in that type's existing QN block whenever a paper reports hyperfine-resolved lines.

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

Use the `marvel-pipeline` skill for the full step-by-step guide (set up molecule dir → OCR → validate + extract → merge → mechanical validate → reviewer sub-agent hard gate → format).

### Extraction Rules (always apply during extraction — Step 3 of the pipeline)

**Anti-fabrication rule**: a wrong value silently corrupts the spectroscopic network — there is no downstream physical check. Never invent, interpolate, or "smooth" a value. An UNREADABLE flag is always correct over a guess. See `scripts/templates/scraper_template.md` for the full extraction-brief skeleton.

**Uncertainty rule**: the uncertainty column comes **only** from what the paper explicitly states — either a **global measurement uncertainty/resolution** quoted in the text (applied to every transition) or a **per-transition uncertainty column** in the tables (applied row by row). Never infer it, never split blended vs. clean with made-up values, never derive it from obs-calc/residuals. If the paper states no uncertainty at all, flag `REQUIRES MANUAL REVIEW` — do not guess.

**Parity (e/f) rule** (electronic-transition diatomics only — `ef_upper`/`ef_lower` columns): three cases, decided per row from what the paper states, molecule-oblivious.
- Paper explicitly states/labels which parity component was measured → record the real `e`/`f` value directly.
- Parity doesn't apply to that state at all (no Λ-doubling/parity-splitting concept for it) → leave `ef_upper`/`ef_lower` blank, no `notes` token.
- Paper doesn't resolve parity for that state (components are unmeasured/degenerate at its precision) → leave `ef_upper`/`ef_lower` blank **and** add `parity: unresolved` to `notes`. A later mechanical step (`csv_to_marvel.py split-parity`, pipeline Step 3.5) expands that row into an `e`/`f` pair with the identical wavenumber — extraction never does the duplication itself, same "extraction records, a later mechanical step transforms" pattern as the Unit rule's `reconcile` step.
Never derive e/f from J-value parity or branch type — that mapping is genuinely Hund's-case- and molecule-dependent, not a general rule (out of scope for this pipeline; treated as a known limitation, not something to infer).

**Unit rule**: never convert units during extraction. Record `transition_wavenumber` and `uncertainty` exactly as printed in the paper's native unit (cm⁻¹, MHz, GHz, etc.) and note the unit explicitly in `notes` for every row (e.g. `unit: MHz`). If a row's uncertainty is stated in a *different* native unit than its wavenumber (e.g. a global fit-uncertainty quoted in kHz for an MHz transition table), state the wavenumber's unit first in `notes` (`unit: MHz`) and the uncertainty's unit afterward wherever it's mentioned (`... 17 kHz ... (unit: kHz)`) — `csv_to_marvel.py reconcile` (Step 6.5, before Format) parses first-vs-later `unit:` mentions to convert the uncertainty into the wavenumber's unit mechanically, logging the conversion in `notes`. Extraction itself never converts; reconciliation across units is a single later, mechanical, logged step — not a judgment call made during extraction.

---

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/` in this repo (local-markdown, no external CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
