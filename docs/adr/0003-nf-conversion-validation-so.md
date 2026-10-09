# ADR-0003: X3Sigma- N<->F magnitude conversion (Brady et al. 2024 Eq.1) — REJECTED for SO

## Status

REJECTED. `csv_to_marvel.py`'s `harmonize` subcommand and the `marvel-combiner` agent
must never apply this (or any other) N<->F remap for SO's X3Sigma- (or B3Sigma-) state.
Sources on incompatible QN schemes for the same isotopologue stay reported as separate
networks (per `marvel-combiner`'s SO X3Sigma- precedent) until either a validated
conversion exists or a new bridging source removes the need for one.

## Context

This is "Option B" from `.scratch/so-multi-isotopologue-combination/issues/03-nqn-
schema-harmonization.md` — the real combination-difference / level-chain test that two
earlier, weaker attempts (both recorded in ADR-0002) explicitly deferred:

- ADR-0002's own test used the derived rule to predict `ef_lower` *within* `22HeStLy`'s
  own already-resolved rows (a parity/label check, Σ=0 vs Σ=+1 branches) — F2 (Σ=0)
  passed trivially (N=J always, no ambiguity regardless of coupling), F1 (Σ=+1) failed
  at a ~51/49 uncorrelated split.
- A same-session follow-up cross-referenced `87BuLoHa`'s F-labeled rows against
  independent N from microwave sources at matching `(v,J)` — failed methodologically,
  `(v,J)` is a 3-way degenerate key for a triplet state, so the comparison was circular
  before it could produce a real answer.

Neither built an actual energy-level network from independently-labeled data and
checked whether the two networks agree once merged — the real test the issue scoped as
"Option B" and explicitly left unbuilt.

## Method

Script: `.scratch/so-multi-isotopologue-combination/optionB_nf_validation.py <ISO>`
(read-only, prints a report, never writes MARVEL input). Run for 32S16O and, in a
follow-up pass the same day, 34S16O.

1. Load the isotopologue's directly-measured N,J pure-rotational transitions from its
   N-only microwave/FIR sources — real N,J labels, no conversion involved. (32S16O:
   `15DrHiMo`, `74Ti`, `82BoDeDe`, `82Ti`, `92LoSuOg`, `96KlSaBe` — 285 transitions.
   34S16O: the same six plus `03SaMcTh`, whose `F` column is genuinely blank for this
   isotopologue since both 34S and 16O have I=0 — no hyperfine possible, unlike its
   real nuclear-hyperfine `F` for 33S16O — 134 transitions.)
2. Load `87BuLoHa`'s X3Sigma- IR band data for that isotopologue, relabeled to (N,J)
   via the candidate map **N = J-1 (F1), J (F2), J+1 (F3)** — Brady et al. 2024 Eq.1
   (F1=N+S, F2=N, F3=N-S, S=1), the standard asymptotic Hund's-case-b triplet-Sigma
   correlation. (32S16O: v=1,2<-0, 444 transitions after excluding 116 a1Delta rows
   and 1 unresolved-F row. 34S16O: v=1<-0 only, 148 transitions, no a1Delta rows in
   this source for this isotopologue.)
3. Unit rule compliance: microwave sources are native MHz, `87BuLoHa` is native cm-1
   (`output/segments/<iso>_segment.txt`, read per-source at runtime, not hardcoded) —
   converted to a common cm-1 scale before any energy comparison.
4. Build one graph over both datasets, nodes = (state, v, N, J), edges = transitions.
   Find connected components. Where relabeling bridges a microwave node and an
   `87BuLoHa` node onto the same (v,N,J), do a weighted least-squares level-energy
   solve (`minimize sum(((E_upper-E_lower-wn)/unc)^2)`, same principle MARVEL itself
   uses) and inspect residuals.
5. **Sanity control, run first**: solve each network alone, under its own native labels
   (no cross-source relabeling), to confirm any blow-up in step 4 is caused by the
   conversion and not a bug in the unit handling or solver.

## Results — 32S16O (2026-09-16)

Sanity control — each network alone:

| network (native labels) | components | RMS(resid/unc) range | max\|resid/unc\| |
|---|---|---|---|
| microwave (N,J) | 72 | 0.00-0.43 | 1.19 |
| `87BuLoHa` (F,J, no relabel) | 9 | 0.87-12.12 | 52.42 |

Microwave data is essentially internally perfect (as expected — mature rotational
spectroscopy). `87BuLoHa`'s own internal band combination differences already show up
to ~50 sigma scatter under its own native labels — likely a few underestimated
uncertainties on blended/weak lines, a separate, narrower finding worth a follow-up
uncertainty-review of that source, but not this ADR's question.

Bridged network (candidate N<->F relabeling applied, 386 nodes, 649 edges: 205
microwave + 444 `87BuLoHa`):

| source | n | RMS(resid/unc) | max\|resid/unc\| |
|---|---|---|---|
| 15DrHiMo | 99 | 1.70 | 16.91 |
| 74Ti | 13 | 34.72 | 117.42 |
| 82BoDeDe | 42 | 10.10 | 45.47 |
| 82Ti | 9 | 3.14 | 6.04 |
| 96KlSaBe | 41 | 0.39 | 1.05 |
| **87BuLoHa (F1)** | 153 | **39.32** | — |
| **87BuLoHa (F2)** | 149 | **350.68** | — |
| **87BuLoHa (F3)** | 142 | **50.27** | — |

`87BuLoHa` absolute residuals: RMS = 0.0454 cm-1, max = 0.9122 cm-1 — 200-4000x its
stated ~0.0002 cm-1 uncertainty, and far beyond even the ~50 sigma ceiling the native-
label sanity control already showed is attributable to `87BuLoHa`'s own data quality.

**F2 (the branch ADR-0002 found trivially exact for the *parity* question) is the
worst-fit branch here for the *magnitude* question** — opposite pattern from ADR-0002,
confirming this is a genuinely different test, not a restatement of the same result.

## Results — 34S16O (2026-09-16, follow-up pass)

Sanity control — each network alone: microwave max\|resid/unc\| = 2.85 (largest
component, 20 nodes); `87BuLoHa` native-label max\|resid/unc\| = 0.00 across all 9
components (this isotopologue's IR data has no internal redundant loops flagging any
scatter at all, unlike 32S16O's). Both clean — no script bug.

Bridged network (134 microwave + 148 `87BuLoHa`, merged to 188 nodes / 262 edges):

| source | n | RMS(resid/unc) | max\|resid/unc\| |
|---|---|---|---|
| 15DrHiMo | 48 | 0.05 | 0.32 |
| 74Ti | 10 | 26.85 | 60.07 |
| 82BoDeDe | 17 | 198.89 | 519.07 |
| 82Ti | 10 | 132.90 | 288.54 |
| 03SaMcTh | 2 | 8.16 | 11.54 |
| 96KlSaBe | 26 | 0.15 | 0.51 |
| **87BuLoHa (F1)** | 51 | **1685.38** | — |
| **87BuLoHa (F2)** | 48 | **2.01** | — |
| **87BuLoHa (F3)** | 49 | **5437.31** | — |

`87BuLoHa` absolute residuals: RMS = 0.72 cm-1, max = 8.37 cm-1 — an order of magnitude
worse in absolute terms than 32S16O's bridged result.

**F2 comes back nearly clean here (RMS 2.01 sigma)** — matching ADR-0002's original
"Sigma=0/F2 is trivially unambiguous" finding — while **F1 and F3 both fail
catastrophically** (1685 and 5437 sigma RMS respectively). This is a different failure
signature than 32S16O (where all three branches failed, F2 worst), but the same
underlying qualitative conclusion: the map is not safe to apply, and which branch fails
worst is not even consistent between isotopologues — reinforcing that this needs a real
per-isotopologue, per-v/J-range treatment, not a single global formula, if it's ever
revisited.

## Verdict

**Rejected, on two independent isotopologues (32S16O and 34S16O).** The candidate map
produces residuals two-to-four orders of magnitude larger than measurement
uncertainty, even after controlling for `87BuLoHa`'s own baseline internal scatter
(verified via the native-label sanity control on both isotopologues — no script bug).
This is the real intermediate-coupling mixing `22HeStLy` §3 already describes in prose
("states of common parity within each Fi manifold become mixed with increasing
molecular rotation"), now quantified directly against independent data. Which branch
fails worst differs between the two isotopologues (32S16O: all three fail, F2 worst;
34S16O: F2 nearly clean, F1/F3 catastrophic) — the map isn't just offset by a fixable
constant, its failure mode itself isn't stable across isotopologues.

This is a fourth independent failure of the same underlying formula across two
molecules'-worth of tests (after ADR-0002's two attempts on 33S16O and this ADR's own
32S16O + 34S16O runs). **Recommend downgrading ADR-0002 from DRAFT to REJECTED** —
four independent angles across three isotopologues, zero successes beyond the
trivially-unambiguous Sigma=0/F2 case, and even that "clean" case isn't reliable
(32S16O's F2 was the worst-failing branch).

## Consequences

- `csv_to_marvel.py harmonize` keeps its blank-pad-only behavior and its refusal to
  auto-union electronic-F and hyperfine-F sources — this ADR adds the specific,
  numeric evidence for why a real N<->F magnitude conversion isn't a safe alternative
  either, for this molecule.
- SO's X3Sigma- ground state stays split across genuinely separate networks (N-labeled
  microwave/FIR vs. F-labeled IR/UV) per isotopologue, per CLAUDE.md's Project Purpose
  section (a real, unvalidated-conversion case, not a permanently-unresolvable one —
  see that section for the distinction from truly disconnected parity ladders).
- Don't retry this exact map without new evidence. A future attempt would need either
  an independent source that resolves the intermediate-coupling mixing directly (e.g.
  an effective-Hamiltonian re-fit, out of scope for this pipeline), or a v/J-dependent
  correction derived and validated the same way (network cross-check, not a formula
  guess) — not a repeat of Brady's asymptotic Eq.1.
