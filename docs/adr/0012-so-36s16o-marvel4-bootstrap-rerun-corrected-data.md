# ADR-0012: SO 36S16O X3Sigma- N/F unification — real MARVEL4.1 bootstrap rerun on corrected data

## Status

**ACCEPTED for merging** — reverses `docs/adr/0006-so-36s16o-marvel4-bootstrap-empirical-test-past.md`'s
REJECTED verdict. That ADR is marked "-past" precisely because it ran on data with a real
bug: `molecules/SO/papers/parse_22hestly_lines.py` derived `F_upper`/`F_lower` from a
wrong fixed Sigma->F formula instead of reading them directly from the source data
file's own `branch` column digits. The bug has since been fixed, mechanically validated,
and reviewer-signed-off (see task context). Rerunning ADR-0006's exact 3-attempt +
fallback method on the corrected data with the real `Marvel4.1.x` binary gives:
**merging 22HeStLy and 96KlSaBe now achieves 0% wrong+very-bad lines** (down from the
buggy data's 36.3%) across every technique tried, and connects all 28/28 of 96KlSaBe's
transitions (up from 11/28). ADR-0006's "36.3% branch-to-branch miscalibration" finding
was the F-labeling bug's own signature, not a genuine physical measurement
inconsistency — it is an **ARTIFACT**, not confirmed. **Final deliverable is now the
merged network** (`molecules/SO/reference_papers/36S-16O_MARVEL_states.txt`, 5366 levels;
`molecules/SO/reference_papers/36S-16O_MARVEL_trans.txt`, 35696 transitions, one connected component) —
the prior fallback-based deliverable is archived as `molecules/SO/reference_papers/36S-16O_MARVEL_states_past.txt`
/ `36S-16O_MARVEL_trans_past.txt`.

## Context

This ADR follows `docs/agents/marvel4-bootstrap-runbook.md` exactly, on the same
isotopologue and source pair ADR-0006 tested (22HeStLy, F-labeled electronic
B3Sigma--X3Sigma-/C3Pi-X3Sigma- bands; 96KlSaBe, N,J-labeled microwave pure-rotational
data within X3Sigma- v=0). 36S16O has only these two X3Sigma- sources — no `03SaMcTh`
data at all — so, per ADR-0006, no incremental-attribution study was needed or done (too
few sources for that to be meaningful); this is a fallback-vs-merged test only, same as
before.

**Why this rerun was needed**: earlier today, a real bug was found and fixed in
`parse_22hestly_lines.py`. `F_upper`/`F_lower` are now read directly from the source
file's own `branch` column digits (e.g. branch `"P22ff"` -> F_upper=F2, F_lower=F2)
instead of a wrong fixed Sigma->F formula. This is especially relevant here: the whole
point of merging in this isotopologue is to test whether 22HeStLy's own F1 and F2
branches connect and cross-validate consistently — if the old F-labels were wrong, the
"36.3% branch-to-branch miscalibration" finding in ADR-0006 could have been comparing the
wrong branches against each other entirely, not a real physical miscalibration. This ADR
answers that question directly.

`ef_upper`/`ef_lower` were **never** affected by this bug — `parse_22hestly_lines.py`
always took them directly from the source file's own `efp`/`efpp` columns (lines 15-16,
91), independent of the F-derivation logic. This turns out to matter (see Step 0/1
below).

## Step 0/1 — confirm what actually changed, before any run

- `molecules/SO/output/SO_36S16O_22HeStLy_SO_20260918_132255.txt` (new, corrected, 35668
  rows) replaces the buggy `..._20260916_154325.txt` (also 35668 rows — same row count,
  only the F-digit differs). Spot check: transition `22HeStLy.1` (wavenumber
  43757.523247 cm-1) was `F2/F2` under the old (buggy) labeling and is `F1/F1` under the
  corrected labeling — same transition, corrected label.
- `molecules/SO/output/SO_36S16O_96KlSaBe_20260916_161022.txt` is **byte-identical**
  (md5 `f4fef1d38c6c2939a0167e99c86a59a0`) to what ADR-0006 used — same filename,
  confirmed unaffected by the bug fix (96KlSaBe was never processed by the buggy
  22HeStLy parser).
- `molecules/SO/combined/SO_36S16O_combined.csv` (35696 data rows, current) is the
  regenerated combined file reflecting the fix.

### New finding: the fallback's "F1-branch vs F2-branch" split was itself mislabeled

Rebuilding 22HeStLy's own network **alone** (native F,ef, no 96KlSaBe at all, corrected
data) still gives **two components of exactly 2683 nodes each** (17742 + 17926
transitions) — the same sizes ADR-0006 found. But the mechanism is different from what
ADR-0006 described. ADR-0006 attributed the split to "22HeStLy's own F1-branch and
F2-branch are naturally disconnected... a ΔF=0 selection rule". On corrected data, **both
components contain a near-even mix of F1/F2/F3** (component 0: F1=892/F2=900/F3=891;
component 1: F1=894/F2=883/F3=906) — not split by F-branch at all. The real invariant is
**N-parity, equivalently e/f**: every F2 node has ef=f, every F1/F3 node has ef=e
(confirmed directly), and since ef was never touched by the F-labeling bug, this is a
real, bug-independent parity-conservation selection rule in the electric-dipole
B3Sigma-/C3Pi-X3Sigma- transitions — not an artifact of either the old bug or the fix.

**ADR-0006's topological finding (two disconnected 2683-node components, 0% internal
badness within each) reproduces exactly. Its causal narrative ("F1-branch vs F2-branch")
was itself an artifact of the old mislabeling** and is corrected here to the real
mechanism (N-parity / e-f parity conservation). This reframes what the merge test is
actually probing: not "does 22HeStLy's F1 data agree with its own F2 data" but "does
22HeStLy's even-N data agree with its own odd-N data" — the same structural test,
correctly described.

### Bridged pre-check on corrected data (fixed-uncertainty pre-check, before the real binary)

A from-scratch weighted combination-difference LS solve (same method as ADR-0006's own
Step 0, `.scratch/so-36s16o-marvel/step0_check.py`) on the bridged network:

- **28/28** of 96KlSaBe's transitions now connect into a single main component (vs.
  11/28 on the buggy data) — 5366 nodes, 35696 edges, **one** component (vs. 12
  components before, only one of which was large).
- RMS(resid/unc) = 3.07, max|resid/unc| = 36.82 overall (vs. buggy-data 11.17 / 78.64).
  96KlSaBe's own 28 connecting transitions: RMS = 3.96, max = 18.38 (vs. buggy-data's 11
  connecting transitions: RMS = 2.82, max = 6.05).

Still a real, non-trivial pre-check inconsistency (satisfying the runbook's §0
precondition), but smaller and not apples-to-apples with the old pre-check (connects
28/28, not 11/28, of 96KlSaBe's data). **Attempt-2 inflation factor: 18.38x**, sourced
from this session's own corrected-data pre-check (96KlSaBe's own max|resid/unc|) — not
invented, not carried over from the now-superseded buggy-data 6.05x (that number was
itself derived from the buggy F-labels).

## Method and results

Environment: `Marvel4.1.x` reachable via `wsl.exe -e bash -lc "..."` at
`/mnt/c/Code/versions_MARVEL/Marvel4.1.x/Marvel4.1.x`. Binary copied into a dedicated
`so-36s16o-rerun/` subdirectory (distinct from ADR-0006's `so-36s16o/`, to avoid any
collision with leftover state) and every run executed from there. All four runs batched
into a single `wsl.exe` call (`.scratch/so-36s16o-marvel/run_all.sh`), exit code 0 for
all four. `--minsize 200` (default) used throughout — never `--minsize 1`.

| attempt | technique | main component | wrong | very bad | wrong+verybad % | 96KlSaBe outcome |
|---|---|---|---|---|---|---|
| 1 | default bootstrap merge (`-b`, 100 iter) | 5366 EL / 35696 TR, **one** component (all data) | 0 | 0 | **0%** | 28/28 connect; resid scatter 3.296e-11 to 7.498e-06 cm-1 (AVTable.txt) |
| 2 | + 96KlSaBe unc inflated 18.38x (this session's own corrected-data pre-check, not invented) | 5366 / 35696, identical topology | 0 | 0 | **0%** (no change) | 28/28 connect |
| 3 | + `--bootiter 1000` (10x default) | 5366 / 35696, identical topology | 0 | 0 | **0%** (no change) | 28/28 connect |
| fallback | disconnected canonical (22HeStLy F,ef + 96KlSaBe N, NQN=6 dummy-padded) | **two** components: 2683 EL/17742 TR + 2683 EL/17926 TR (now confirmed split by N-parity/e-f, not F1-vs-F2 — see Step 0/1) + 96KlSaBe's own 16 tiny (2-5 node, 44 EL total) isolated components | 0 | 0 | **0%** | not applicable — genuinely disconnected |

Full logs and raw `Marvel4.1.x` output for every run are in
`.scratch/so-36s16o-marvel/{attempt1,attempt2,attempt3,fallback}/`. `BadLines.txt` used
as authoritative for wrong/very-bad counts throughout (not `CheckTransitions.txt`, which
uses bootstrap-adjusted, not stated, uncertainty — per the runbook's explicit warning).

### Comparison against ADR-0006 (buggy data)

| | ADR-0006 (buggy F-labels) | ADR-0012 (corrected F-labels) |
|---|---|---|
| Merged main component | 5366 EL / 35679 TR (17 of 96KlSaBe's transitions excluded/orphaned) | 5366 EL / 35696 TR (**all** data included) |
| 96KlSaBe transitions connecting | 11/28 (pre-check) | 28/28 (pre-check and real run) |
| Wrong + very bad lines (merged, attempt 1) | 8045 wrong + 4916 very bad = **36.3%** | 0 wrong + 0 very bad = **0%** |
| Effect of unc. inflation (attempt 2) | No material change (36.3%) | No change (already 0%) |
| Effect of 10x bootstrap depth (attempt 3) | Byte-identical to attempt 1 | Byte-identical to attempt 1 |
| Fallback (disconnected) badness | 0% (verified 22HeStLy-alone self-consistency) | 0% (same, but now correctly attributed to N-parity/e-f split, not F1-vs-F2) |
| Fallback main-component sizes | 2683+2683 (attributed to F1/F2 branches) | 2683+2683 (identical sizes; real cause is N-parity/e-f) |

The fallback's topology (component sizes) is numerically identical between the two runs
— expected, since `ef` was never affected by the bug and turns out to be the real split
driver. The merged network's behavior is where the two runs diverge completely: buggy
data forced two genuinely different, mislabeled sets of rows into false agreement/false
conflict; corrected data merges them cleanly.

## Attempt-budget accounting

3 genuinely distinct techniques were tried via the real `Marvel4.1.x` binary (default
bootstrap merge; manual uncertainty inflation, factor sourced from this session's own
corrected-data pre-check; 10x bootstrap depth), plus the disconnected fallback prepared
regardless, per runbook §2-3 — same budget ADR-0006 used. All three converged on the same
result (0% wrong+very-bad); attempts 2 and 3 are confirmatory rather than diagnostic here
(there was nothing left in the network to fix), unlike ADR-0006 where they were probing
an unresolved 36.3% badness.

## Verdict

**The ~36.3% branch-to-branch miscalibration is an ARTIFACT of the old F-labeling bug —
not a genuine physical measurement inconsistency.** It does not survive on corrected
data: merging 22HeStLy and 96KlSaBe now achieves 0% wrong+very-bad lines across three
independent techniques (default bootstrap, 18.38x uncertainty inflation, 10x bootstrap
depth), with per-source residual scatter (AVTable.txt: 7.498e-06 cm-1 for 22HeStLy,
3.296e-11 cm-1 for 96KlSaBe on attempt 1) four to fifteen orders of magnitude below the
stated measurement uncertainties — not a borderline pass.

Justification for calling this an artifact rather than a coincidental improvement:

- Nothing else changed between ADR-0006's attempts and this rerun except the F-label bug
  fix (Step 0/1 verified identical row counts, identical wavenumbers/ids for both
  sources).
- The fallback's own topology (which sub-networks of 22HeStLy are naturally
  disconnected) is numerically unchanged (2683+2683) between the buggy and corrected
  runs, because it is actually driven by `ef` (untouched by the bug), not `F`
  (the buggy quantity). This rules out "the bug happened to also fix some unrelated
  measurement issue" — the bug's blast radius was exactly the F-digit, and fixing exactly
  that digit is what flips the merge outcome from 36.3% to 0%.
- ADR-0006's own causal story ("F1-branch and F2-branch are naturally disconnected... but
  bridging exposes their relative miscalibration") is now known to have mischaracterized
  even the disconnected topology itself (it is not an F1-vs-F2 split at all) — so its
  conclusion about what the bridge exposed inherits the same mischaracterization.

**This does not reopen or contradict ADR-0002/0003/0004's broader rejection of the naive
Brady et al. Eq. 1 N<->F formula for other isotopologue/source pairs** — those findings
were never about 36S16O's 22HeStLy/96KlSaBe pair specifically, and this ADR does not
retest them. It also does not imply the formula itself was ever wrong here (it wasn't —
ADR-0006 independently re-verified it, and this rerun did not touch the N->F formula at
all, only the F-digit assignment for 22HeStLy's own native data).

## Consequences

- **Final deliverable changes**: `molecules/SO/reference_papers/36S-16O_MARVEL_states.txt` (5366
  levels) and `molecules/SO/reference_papers/36S-16O_MARVEL_trans.txt` (35696 transitions), now built
  from the **merged** network (attempt 1: default bootstrap merge) — one connected
  component, 0% wrong+very-bad, both sources' native F/N schemes unified via the same
  N->F conversion ADR-0002-0005 established as row-level-lossless. This **replaces**
  ADR-0006's fallback-based deliverable, archived as
  `molecules/SO/reference_papers/36S-16O_MARVEL_states_past.txt` /
  `molecules/SO/reference_papers/36S-16O_MARVEL_trans_past.txt`.
- **Retroactive implication for ADR-0006**: its REJECTED verdict and "genuinely
  perfect-but-mutually-inconsistent branches" framing should be read as describing a data
  bug's symptom, not 36S16O's real physics. ADR-0006 remains historically accurate for
  what it tested (it correctly diagnosed a 0-cost-vs-high-cost tradeoff *given the data it
  had*) but its finding does not describe the real, corrected dataset. This ADR
  supersedes it as the operative decision for 36S16O.
- **Open question for a future agent, not resolved here**: whether other SO
  isotopologue/source pairs previously rejected on N/F-merging grounds
  (ADR-0002/0003/0004/0005, e.g. 34S16O's 22HeStLy/03SaMcTh pair) were tested on data
  from the same buggy `parse_22hestly_lines.py` parser, and would similarly reverse if
  rerun on corrected data. **Flagged as a real, separate, out-of-scope follow-up** — not
  retested in this ADR, which is chartered narrowly to 36S16O per the task. Given the
  magnitude of the reversal found here (36.3% -> 0%), this is worth prioritizing.
- The pipeline-tooling gap ADR-0006 flagged (`csv_to_marvel.py so_convert` unconditionally
  dropping `N_upper`/`N_lower`) is unaffected by this ADR and remains open, unrelated to
  the F-labeling bug this ADR addresses.
- Don't re-derive 22HeStLy's F-labels from any Sigma-based formula in the future — the
  branch-column digit is the file's own unambiguous, already-stated label (per
  `parse_22hestly_lines.py`'s own docstring) and any regression back toward formula-based
  derivation would reintroduce exactly the failure mode this ADR diagnoses.
