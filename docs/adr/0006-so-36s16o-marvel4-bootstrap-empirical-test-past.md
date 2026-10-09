# ADR-0006: SO 36S16O X3Sigma- N/F unification — real MARVEL4.1 bootstrap empirical test

## Status

**REJECTED for merging**, for a cleaner and more directly attributable reason than
ADR-0005 found for 34S16O. Three genuinely distinct MARVEL4.1.x bootstrap runs were
completed (not simplified fixed-uncertainty pre-checks — the real binary, real bootstrap
reweighting). `96KlSaBe`'s N->F-converted data does genuinely connect the network
(unlike 34S16O's `03SaMcTh`, it unites two otherwise-disconnected sub-networks of
`22HeStLy`'s own data into one), but doing so takes a verified **0%**-wrong-line network
to **36.3%** wrong+very-bad — a large, real degradation directly and exclusively
attributable to the bridge, since nothing else differs between the merged and
disconnected builds. **Final deliverable uses the disconnected/canonical fallback
network** (`96KlSaBe` kept N-labeled, structurally separate) — see Verdict.

## Context

ADR-0002/0003/0004 (all REJECTED for the naive Brady et al. 2024 Eq. 1 N<->F formula, on
fixed-uncertainty pre-checks) established that this conversion fails a network
cross-validation test for SO's X3Sigma- state on multiple isotopologue/source
combinations, including a qualitative ("extends the rejection") mention of 36S16O in
ADR-0004. ADR-0005 then tested the real-binary hypothesis for 34S16O per explicit user
direction (a real MARVEL4 bootstrap might reconcile what a fixed-uncertainty pre-check
cannot, since Brady et al. themselves use exactly this formula in their own published,
self-consistent 32S16O network) and found: rejected, but for a specific, previously
undiagnosed reason (34S16O's dominant network badness is `22HeStLy`'s own uncertainty
miscalibration, unrelated to the N/F question). This ADR runs the same real-binary test
for **36S16O**, the isotopologue `docs/agents/marvel4-bootstrap-runbook.md` (distilled
from ADR-0005) was written to make repeatable.

36S16O has only two X3Sigma- sources in this pipeline's corpus — `22HeStLy` (F-labeled,
electronic B3Sigma--X3Sigma-/C3Pi-X3Sigma- bands) and `96KlSaBe` (microwave, pure
rotational within X3Sigma- v=0) — and **no `03SaMcTh` data at all** for this isotopologue
(unlike 34S16O). The disputed pair here is 22HeStLy vs 96KlSaBe, per ADR-0004's section
"1. Extra Option-B data point: 33S16O and 36S16O via 22HeStLy".

## Step 0 — verifying the conflict actually exists in current data (mandatory, done first)

Both sources' native labeling schemes were independently re-verified against their own
source papers, not assumed from the ADR chain's prior description:

- **`22HeStLy` is genuinely F-labeled**: confirmed directly against
  `molecules/SO/output/SO_36S16O_22HeStLy_SO_20260916_154325.txt` (35668 rows, real
  populated F1/F2/F3 + e/f for every row).
- **`96KlSaBe` is genuinely N,J-labeled in its own paper** (`molecules/SO/markdown/
  96KlSaBe_SO/full.md` Table 2, "Observed and Calculated Rotational Transitions for
  36SO", uses `N' J' <- N'' J''` directly) — matching ADR-0004's description — **but the
  canonical `molecules/SO/output/SO_<iso>_96KlSaBe_*.txt` / `csv/96KlSaBe_merged.csv`
  files have already silently discarded N and kept only the derived F**, with no
  disclosure note, unlike `03SaMcTh`'s 34S16O treatment (which keeps `N_upper`/`N_lower`
  populated *and* discloses "F/ef derived from N,J per X3Sigma- N-to-F convention
  (SO_algorithm.py)" in its notes). Root cause identified: `scripts/csv_to_marvel.py`'s
  `so_convert` command (line 399) treats an N,J->F,ef relabeling as unconditionally
  "safe" (true, at the row level — a lossless 1:1 map, verified below) and
  **unconditionally drops `N_upper`/`N_lower`** afterward (line 510), regardless of
  whether another source for the same isotopologue is independently F-labeled — the
  exact situation this ADR chain separately tests and has repeatedly rejected for
  network merging. `96KlSaBe` was evidently run through `so_convert`; `03SaMcTh` was not
  (a different, more careful extraction path). **This is flagged as a separate,
  out-of-scope pipeline-tooling gap**, not fixed this session: `so_convert` should not
  unconditionally discard N when a molecule/isotopologue also carries an independently
  F-labeled X3Sigma- source. N was recovered here via the exact (verified lossless)
  inverse of the same formula.
- **Formula re-verification** (runbook step 1): `SO_algorithm.py`'s `N_to_F`/
  `F_to_parity`, already verified correct for 34S16O in ADR-0005, reproduces 96KlSaBe's
  stored F,ef exactly for all 28 rows via round-trip, and was independently hand-checked
  against 3 of Table 2's raw rows. **No formula bug.**
- **The task's cited fixed-uncertainty pre-check number for 36S16O (RMS(resid/unc)~317,
  max~1358) does not reproduce and appears to be a mislabeled citation of ADR-0004's
  33S16O result** (that ADR's only numeric pre-check table row is explicitly labeled
  33S16O; no 36S16O-specific number exists anywhere in its text, and the script that
  would have produced one, `optionB_nf_validation_22hestly.py`, does not exist in this
  repository). Per the runbook's explicit instruction not to fabricate an attempt table
  if a cited pre-check doesn't reproduce, a new equivalent pre-check was built this
  session (`step0_check.py`) instead of assuming the cited number: it found a real, but
  much smaller, conflict — bridged-network RMS(resid/unc)=11.17/max=78.64 overall,
  and RMS=2.82/max=6.05 for 96KlSaBe's own 11 connecting transitions specifically. This
  independently satisfies the runbook's own §0 precondition (a real conflict worth
  testing with the real solver) on its own merits, just via a different route and a
  different magnitude than the task's framing suggested. See `.scratch/so-36s16o-marvel/
  PROCESS.md` §0 for full detail.

## Method and results

Environment: `Marvel4.1.x` reachable via `wsl.exe -e bash -lc "..."` at
`/mnt/c/Code/versions_MARVEL/Marvel4.1.x/Marvel4.1.x`. A sibling agent was concurrently
running a 32S18O bootstrap test on the same machine; to avoid clobbering its output, the
binary was copied into a dedicated `so-36s16o/` subdirectory and every run executed from
there. All four runs were batched into a single `wsl.exe` call
(`.scratch/so-36s16o-marvel/run_all.sh`) per the runbook's documented latency warning.
`--minsize 200` (default) used throughout — never `--minsize 1`.

| attempt | technique | main component | wrong | very bad | wrong+verybad % | 96KlSaBe outcome |
|---|---|---|---|---|---|---|
| 1 | default bootstrap merge (`-b`, 100 iter) | 5366 EL / 35679 TR, one component | 8045 | 4916 | 36.3% | 0 flagged lines |
| 2 | + 96KlSaBe unc inflated 6.05x (sourced from Step 0's own max\|resid/unc\|, not invented) | 5366 / 35679, identical topology | 8055 | 4916 | 36.3% (no material change) | ~90 lines flagged at trivial (~1e-4-1e-5) ratios |
| 3 | + `--bootiter 1000` (10x default) | 5366 / 35679, identical topology | 8045 | 4916 | 36.3% (byte-identical to attempt 1) | 0 flagged lines |
| fallback | disconnected canonical (22HeStLy F,ef + 96KlSaBe N, NQN=6 dummy-padded) | **two** components: 2683 EL/17742 TR + 2683 EL/17926 TR (22HeStLy's own F1- and F2-branches) + 96KlSaBe's 16 tiny (2-5 node) isolated components | 0 | 0 | **0%** | not applicable — genuinely disconnected |

Full logs and raw `Marvel4.1.x` output for every run are in
`.scratch/so-36s16o-marvel/{attempt1,attempt2,attempt3,fallback}/`.

### Two findings

1. **22HeStLy's own 36S16O data is, by itself, perfectly self-consistent** (0 wrong/very
   bad lines across 17742+17926 highly redundant transitions) — unlike 34S16O, where
   `22HeStLy`'s own uncertainty miscalibration caused ~97.7% of that network's badness
   even fully disconnected from `03SaMcTh` (ADR-0005). Whatever affects 34S16O's
   `22HeStLy` dataset does not reproduce here.
2. **`22HeStLy`'s own F1-branch and F2-branch are naturally disconnected from each other**
   (a ΔF=0 selection rule in these electronic bands): the fallback's two main components
   sum to exactly 2683+2683=5366, matching attempt 1's single merged component exactly.
   **`96KlSaBe`'s 11 real connecting transitions are the only thing tying these two
   branches into one network** — a genuine connectivity gain 34S16O's `03SaMcTh` did not
   provide (ADR-0005: merging it added zero new energy levels). But bridging them exposes
   that the two branches' *relative* energy-scale calibration disagrees far beyond either
   branch's own stated uncertainty — almost all of the 36.3% wrong+very-bad lines in the
   merged network are `22HeStLy` transitions themselves (not `96KlSaBe`'s few connecting
   lines), because the bridge forces one global fit onto two otherwise-independently-
   perfect branches whose relative offset it cannot resolve at their stated precision.

This is a **more directly attributable rejection** than ADR-0005's 34S16O finding: there,
the ~60% badness existed with or without the disputed source, so the merge itself
couldn't be blamed; here, the network goes from a measured, verified 0% to 36.3% *solely
because of* the N->F bridge, with nothing else in the network changed.

## Attempt-budget accounting

3 genuinely distinct techniques were tried via the real binary (default bootstrap merge;
manual uncertainty inflation, factor sourced from this session's own Step 0 pre-check;
10x bootstrap depth). Uncertainty inflation made no material difference (weakening
`96KlSaBe`'s pull cannot fix a disagreement that lives entirely within `22HeStLy`'s own
data once bridged); 10x bootstrap depth reproduced attempt 1 byte-for-byte (not the
bottleneck). No further attempt was judged likely to change the outcome without first
re-examining `22HeStLy`'s F1-vs-F2 relative calibration directly — a separate,
out-of-scope literature/re-fitting question, not a MARVEL4-run variation — so this ADR
treats the 3-attempt budget as substantively exhausted, per the same judgment ADR-0005
used.

## Verdict

**Use the fallback (disconnected, canonical, unconverted) network as the final
deliverable.** Justification:

- Merging genuinely buys real new connectivity (unlike 34S16O) — but at the cost of
  taking a verified 0%-wrong network to 36.3%-wrong, a degradation directly and
  exclusively attributable to the N->F bridge.
- The formula itself is not the problem (re-verified correct, independently, a third
  time across three isotopologue/source pairs); the failure is a real physical
  branch-to-branch calibration disagreement the bridge exposes, not a bug.
- Neither manual uncertainty inflation nor deeper bootstrapping resolves it, for
  diagnosed, disclosed reasons (not merely "wasn't tried hard enough").

**This does not reopen or contradict ADR-0004's note that Brady et al.'s real 32S16O
network succeeds with this same formula** — same reasoning as ADR-0005: that network has
vastly more redundant, presumably-already-cross-calibrated coverage (50106 transitions,
29 sources) than 36S16O's sparse 2-source X3Sigma- coverage.

## Consequences

- Final deliverable: `molecules/SO/reference_papers/36S-16O_MARVEL_states.txt` (5366 levels) and
  `molecules/SO/reference_papers/36S-16O_MARVEL_trans.txt` (35696 transitions), built from the
  **fallback** run — `96KlSaBe` kept genuinely N-labeled and structurally disconnected
  via NQN=6 dummy-padding (`.scratch/so-36s16o-marvel/build_fallback.py`).
- **New, separate, out-of-scope pipeline-tooling finding**: `scripts/csv_to_marvel.py`'s
  `so_convert` command unconditionally discards `N_upper`/`N_lower` after deriving F —
  correct and safe at the row level, but it silently removes the only information a
  later agent would need to keep a genuinely N-labeled source properly disconnected from
  an independently F-labeled one, without any disclosure note (unlike whatever process
  produced `03SaMcTh`'s more careful, N-preserving 34S16O rows). Flagged as a real,
  scoped follow-up for whoever next touches `so_convert` or processes another SO
  isotopologue through it — not fixed this session (out of scope: a tooling-behavior
  change, not this ADR's own N/F-unification question).
- **New, separate finding for a future `22HeStLy` re-calibration effort**: 36S16O's
  `22HeStLy` F1-branch and F2-branch are each internally perfect but mutually
  inconsistent by an amount `96KlSaBe`'s bridge exposes at ~36% of the merged network.
  This is a real, disclosed, out-of-scope-for-this-ADR data-quality question about
  `22HeStLy`'s own relative branch calibration (not the N/F conversion question this ADR
  was chartered to answer) — flagged for whoever next wants a genuinely unified,
  validated 36S16O X3Sigma- network.
- No change to ADR-0002/0003/0004's status; this ADR adds the real-bootstrap data point
  for 36S16O ADR-0004 left open, and closes it (rejected, for a cleanly diagnosed reason)
  rather than leaving it unresolved.
- Don't re-attempt N->F merging for 36S16O without first resolving `22HeStLy`'s
  F1-vs-F2 relative branch calibration — repeating this test unchanged would reproduce
  the same 36.3% badness.
