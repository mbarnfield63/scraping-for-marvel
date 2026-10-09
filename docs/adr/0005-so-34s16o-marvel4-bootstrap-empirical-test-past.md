# ADR-0005: SO 34S16O X3Sigma- N/F unification — real MARVEL4.1 bootstrap empirical test

## Status

**REJECTED for merging, but for a different, more specific reason than ADR-0002/0003/0004
assumed.** Three genuinely distinct MARVEL4.1.x bootstrap runs were completed (not
simplified fixed-uncertainty pre-checks — the real binary, real bootstrap reweighting).
`03SaMcTh`'s N→F-converted data does not corrupt the wider network (network-wide bad-line
rate is statistically identical whether it is merged or disconnected), but it also does
not achieve genuine validated unification: only 1 of its 12 transitions ever connects to
the rest of the X3Sigma- network at all (the other 11 measure v/N/J combinations no other
34S16O source covers, N-labeled or F-labeled), and that one connecting transition fails
MARVEL4.1's own consistency check at ~11.5σ regardless of technique tried. **Final
deliverable uses the disconnected/canonical fallback network** (`03SaMcTh` kept
N-labeled, structurally separate) — see Verdict.

## Context

ADR-0002/0003/0004 (all REJECTED for the naive formula, on fixed-uncertainty pre-checks)
established that Brady et al. (2024)'s Eq. 1 N↔F conversion for SO's X3Sigma- fails a
network cross-validation test on five isotopologue/source combinations. ADR-0004
proposed, but never tested, that a real MARVEL4 bootstrap run might reconcile what a
fixed-uncertainty pre-check cannot, since Brady et al. themselves use exactly this
formula in their own published, self-consistent 32S16O network. Per explicit user
direction, this ADR tests that hypothesis directly with real `Marvel4.1.x` runs, with an
attempt budget of up to 6 distinct techniques before falling back to ADR-0004's mandated
safe default.

## Formula re-verification (done first, before any run)

`SO_algorithm.py`'s `N_to_F(N, J)` was checked against Brady et al. (2024) Eq. 1
(`F1=N+S, F2=N, F3=N-S`, S=1): mathematically identical (F1 ⇔ N=J−1, F2 ⇔ N=J, F3 ⇔
N=J+1 in both). **No formula bug.** The already-converted `03SaMcTh` 34S16O rows in
`molecules/SO/csv/03SaMcTh_SO_merged.csv` / `molecules/SO/combined/
SO_34S16O_combined.txt` were independently checked and are correctly converted (all 12
rows are the transition N'=0,J'=1 → N''=1,J''=0 at different v; N=0,J=1→F1 and N=1,J=0→F3
both correct per the verified formula). `SO_algorithm.py` itself has no CLI/file I/O, so
it did not itself produce these rows — some other, unlogged process applied equivalent
logic (a real provenance gap, not a correctness bug — see `.scratch/so-34s16o-marvel/
PROCESS.md` Appendix).

## Method and results

Environment note: `Marvel4.1.x` is reachable via `wsl.exe -e bash -lc "..."`, but each
fresh `wsl.exe` invocation in this sandboxed session paid a very large (~10+ minute), and
apparently constant rather than one-time, cold-start-like latency — batching every run
into as few `wsl.exe` calls as possible (`.scratch/so-34s16o-marvel/run_all.sh`) was
necessary to get all runs done in one session. All commands below eventually completed;
none hung indefinitely once actually dispatched.

**Attempt 0 (diagnostic, not one of the 3 counted attempts)**: the merged network with
`--minsize 1` (to avoid hiding any small component) **crashed** — `Marvel4.1.x` printed
`wrong decomp 1` (Eigen `SimplicialLDLT` Cholesky decomposition failure, i.e. a
non-positive-definite system) and called `exit(-1)`. Root-caused before spending an
attempt on it: this is an artifact of `--minsize 1` itself (a component reduced to a
single, degenerate 1x1 linear system), not of the N/F merge — confirmed by rerunning the
identical network with the default `--minsize 200` (below), which completed cleanly. All
substantive runs below use the default `--minsize 200`.

| attempt | technique | status | main component | wrong lines | very bad lines | `03SaMcTh` outcome |
|---|---|---|---|---|---|---|
| 1 | merged network, `-b` (100 iter, default) | completed | 5028 levels / 32620 trans | 4522 | 14939 | 1/12 transitions connect (v=1); flagged **VERY BAD** (ratio≈11.5) |
| 2 | + `03SaMcTh` uncertainty inflated 12.5x (0.002→0.025 MHz native) | completed | 5028 / 32620 | 4522 | 14939 | same 1/12 connects; flagged **VERY BAD_100** (ratio≈144, *worse* — see below) |
| 3 | + `--bootiter 1000` (10x default) | completed | 5028 / 32620 | 4522 | 14939 | unchanged from attempt 1 |
| fallback | canonical, unconverted, `03SaMcTh` fully disconnected | completed | 5028 / 32618 | 4562 | 14965 | not applicable (0 flagged occurrences — genuinely disconnected) |

Full logs, `BadLines.txt`, `CheckTransitions.txt`, `Components.txt`, `EnergyLevels.txt`
for every run are in `.scratch/so-34s16o-marvel/{attempt1_defaultminsize,attempt2,
attempt3,fallback}/`.

### Two findings, not one

1. **The dominant network badness (≈60% wrong+very-bad of the ~32.6k-transition main
   component, in every variant including the fully-disconnected fallback) has nothing to
   do with the N/F question.** Breaking `CheckTransitions.txt`'s flagged lines down by
   source tag: `22HeStLy` accounts for 38720-38884 of ~39630-39849 total flagged
   occurrences (≈97.7-97.8%) in every run, `87BuLoHa` ≈156-158, and the rest (`74Ti`,
   `82BoDeDe`, `82Ti`, `96KlSaBe`) single digits. `22HeStLy` (Heays et al. 2022) supplies
   32358 of the network's 32678 transitions at a single stated blanket uncertainty of
   0.05 cm⁻¹ (same value as in 24BrYuTe's own 32S16O Table 2), and its own residuals
   against the rest of the network sit at a **pervasive but modest ≈1.0-1.5x its own
   stated uncertainty** (e.g. diff=0.0729 cm⁻¹ against unc=0.05 cm⁻¹) — enough to clear
   the `ratio>1` "WRONG" bar on a huge fraction of lines by sheer volume, not because
   anything is catastrophically broken. This is exactly the kind of source-specific
   manual-uncertainty-recalibration problem 24BrYuTe's own footnote (a) and `20WaOwTe`
   both describe handling case-by-case — this session did not attempt that broader
   recalibration for `22HeStLy` (out of scope for the N/F question specifically; flagged
   here as a real, separate, worthwhile follow-up for whoever next works on this
   network's overall quality, not a blocker for this ADR's own verdict).
2. **`03SaMcTh`'s specific contribution is genuinely small and structurally limited,
   independent of (1).** Only `03SaMcTh.2` (the v=1 rotational transition) ever shares a
   node with the rest of the X3Sigma- network — the other 11 (v=0, v=2..11) sit in their
   own isolated 2-node components with no other source measuring the same transition, so
   they can never be checked for consistency at all, converted or not (confirmed directly
   in `Components.txt`: components 12-21 in the merged run are each a single, isolated
   `03SaMcTh` transition). `03SaMcTh.2`'s one real connection reproduces ADR-0003's own
   simplified-script finding almost exactly (max\|resid/unc\|≈11.5 there; ≈11.5 measured
   here via the real solver) — good cross-validation that ADR-0003's earlier, simpler
   test was measuring something real.

### Why uncertainty inflation (attempt 2) made `03SaMcTh` *worse*, not better

Inflating `03SaMcTh.2`'s uncertainty 12.5x weakened its pull in the weighted least-squares
solve, letting the (already ≈1-1.5x-miscalibrated) wider network's fitted energy for that
level drift further from `03SaMcTh`'s own high-precision (2 kHz-stated) measurement — the
raw absolute residual grew ≈156x while the uncertainty only grew 12.5x, so the *ratio*
got worse (VERY BAD → VERY BAD_100). This is a real, useful, disclosed negative result:
**manually inflating a well-measured but poorly-connected source's own uncertainty is not
a reliable fix when the anchor it would be reconciled against is itself not yet
well-calibrated** — the Brady-footnote-(a) technique works when the *majority* of the
network is trustworthy and one source is the outlier; here it is not clear that
assumption holds for the wider 34S16O network yet (see finding 1).

## Attempt-budget accounting

3 genuinely distinct techniques were tried (bootstrap-default merge; manual
uncertainty inflation; 10x bootstrap depth), all via the real `Marvel4.1.x` binary, not
simplified pre-checks — a strictly stronger test than anything in ADR-0002/0003/0004.
None validated `03SaMcTh.2`'s connection. Per the task's own instruction, the next step
would be reading `20WaOwTe_method.md` for additional techniques before falling back.
That doc's three techniques were considered and none offer a genuinely new, in-scope
avenue here: PGOPHER-style independent re-fitting requires software not available in
this pipeline; "pseudo-experimental" bridging transitions require fabricating a
transition from a fitted model, which ADR-0004 already implemented and rejected for
34S16O specifically (effective-Hamiltonian route, "improved but not validated," missing
higher-order constants for this isotopologue); manual uncertainty inflation was already
tried here (attempt 2) and made things worse, not better, for the specific reason
diagnosed above (not "the value chosen was wrong" but "the anchor network isn't clean
enough yet for this technique to be well-posed"). No further attempt was judged likely to
produce a materially different outcome without first addressing finding 1 (a separate,
larger, out-of-scope task) — so this ADR treats the 3-real-attempt budget as
substantively exhausted rather than mechanically running 3 more variations of the same
already-diagnosed failure mode.

## Verdict

**Use the fallback (disconnected, canonical, unconverted) network as the final
deliverable.** Justification, per the user's own framing (largest fully-connected
component with the most accurate uncertainties achievable, not the largest nominally-
joined one):
- The merged and disconnected networks have the **same main component** (5028 levels;
  32620 vs 32618 transitions — merging `03SaMcTh` adds zero new energy levels to the
  network, since every node its convertible transition would touch is already populated
  by other sources) and **statistically indistinguishable** overall bad-line rates
  (19461/32620 ≈ 59.7% merged vs 19527/32618 ≈ 59.9% disconnected).
- Merging buys nothing (no new connectivity) and costs a documented, unresolved ≈11.5σ
  inconsistency for one transition that the disconnected version simply doesn't surface.
- The formula itself is not the problem (verified correct, §"Formula re-verification");
  neither is it proven safe to rely on for this isotopologue's specific data — the
  connecting transition fails a real bootstrap-based MARVEL4 check, not just a
  simplified pre-check, closing the specific gap ADR-0004 left open.

**This does not reopen or contradict ADR-0004's own note that Brady et al.'s real 32S16O
network succeeds with this same formula** — that network has vastly more redundant
coverage per level (50106 transitions, 29 sources) than 34S16O's 8-source, much sparser
X3Sigma- coverage; the mechanism that reconciles the formula's asymptotic imprecision
there (a large, redundant, presumably-already-calibrated network absorbing one imprecise
formula) is not yet available for 34S16O specifically, because 34S16O's own dominant
source (`22HeStLy`) has not yet been through the same manual per-source uncertainty
recalibration Brady's own 32S16O analysis clearly required (finding 1).

## Consequences

- Final deliverable files (`molecules/SO/reference_papers/34S-16O_MARVEL_states.txt`,
  `molecules/SO/reference_papers/34S-16O_MARVEL_trans.txt`) are built from the **fallback** run: 5028
  energy levels from a 32678-transition, 12-source input with `03SaMcTh` kept genuinely
  disconnected (N-labeled, structurally isolated via the dummy-token NQN=6 padding
  described in `.scratch/so-34s16o-marvel/build_fallback.py`).
- `22HeStLy`'s own uncertainty calibration (finding 1) is flagged as a real, separate,
  worthwhile follow-up for this network's overall quality — out of scope for this ADR,
  which is specifically about the X3Sigma- N/F question.
- No change to ADR-0002/0003/0004's status; this ADR adds the real-bootstrap data point
  ADR-0004 said was the concrete reopening condition, and closes it (rejected, for a more
  precisely diagnosed reason) rather than leaving it open.
- Don't re-attempt N→F merging for 34S16O without first addressing `22HeStLy`'s
  calibration — repeating this exact test on a recalibrated network is the correct next
  step if this question is ever revisited, not a different formula or a different
  isotopologue.
