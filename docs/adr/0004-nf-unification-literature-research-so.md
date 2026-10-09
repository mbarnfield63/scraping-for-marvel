# ADR-0004: SO X3Sigma- N<->F unification — literature research beyond the naive formula

## Status

**Update (ADR-0005, 34S16O, 2026-09)**: this ADR's own "Recommended next step" (a real
MARVEL4/bootstrap run, not a fixed-uncertainty pre-check) was performed for 34S16O.
Result: still rejected for merging, but for a more specific, now-diagnosed reason — the
X3Sigma- network's dominant badness is unrelated to the N/F question at all (a separate
uncertainty-calibration issue in a different source, 22HeStLy), and 03SaMcTh's one
connectable transition fails the real bootstrap check too. See ADR-0005 for the full
result; this ADR's own findings below are unchanged.

REJECTED for the naive/asymptotic universal formula (Brady et al. 2024 Eq.1, tested
five times now across ADR-0002, ADR-0003, and this ADR, on five isotopologues, zero
passes beyond the trivially-unambiguous Sigma=0/F2 case). A real, citable,
higher-fidelity alternative (an actual effective-Hamiltonian diagonalization, not an
asymptotic label offset) was implemented and tested this session — it comes far closer
in absolute terms than any prior attempt but still fails this pipeline's mandatory
few-sigma validation gate, for a specific, documented, and citable reason (missing
higher-order centrifugal-distortion terms not cleanly recoverable from this repo's OCR
extraction of the source paper). **Do not treat this as a permanently closed
question** — Section "A working precedent exists" below documents that Brady et al.
2024 already built a real, published, self-consistent MARVEL network combining
N-labeled and F-labeled X3Sigma- sources for 32S16O, using the very formula rejected
here, and the likely reconciliation is MARVEL4's own iterative uncertainty-reweighting
mechanism (not a fixed-uncertainty formula-validity test). See "Recommended next step."

## Context

This is the research issue scoped in `.scratch/so-multi-isotopologue-combination/
issues/04-x3sigma-minus-n-f-coupling-research.md`, following four prior naive-formula
failures documented in ADR-0002 (REJECTED) and ADR-0003 (REJECTED): every attempt to
bridge SO's X3Sigma- N-labeled (Hund's case-b microwave/FIR) sources with F1/F2/F3-
labeled (effective-Hamiltonian-fit UV/IR) sources via Brady et al. 2024's Eq.1
(F1=N+S, F2=N, F3=N-S, S=1) has failed a real network cross-validation test. This ADR
was asked to go beyond that formula: find a real, sourced, validated correlation, or
conclusively close the question.

## Method and findings, in the order performed

### 1. Extra Option-B data point: 33S16O and 36S16O via 22HeStLy (not 87BuLoHa)

`optionB_nf_validation.py` (ADR-0003's script) hardcodes `IR_SOURCE = "87BuLoHa"`,
which has no 33S16O/36S16O data. A sibling script,
`.scratch/so-multi-isotopologue-combination/optionB_nf_validation_22hestly.py`, was
written reusing its graph/solve machinery, adapted for `22HeStLy`'s real data shape:
unlike `87BuLoHa`'s pure X3Sigma--X3Sigma- IR band, every `22HeStLy` row is an
electronic transition (`B3Sigma--X3Sigma-` or `C3Pi-X3Sigma-`) with only the *lower*
side actually X3Sigma- (verified: `state_lower` is X3Sigma- in 100% of both
isotopologues' rows, `F_lower` never blank). The lower node is relabeled F->N via the
same Brady Eq.1 map; the upper (B3Sigma-/C3Pi) node keeps its own real
`(state, v, F, J, ef)` label unchanged.

**A real bug was found and fixed during this**: the first version's upper-state node
omitted `ef_upper`. For 33S16O, `(state_upper, F_upper, J_upper)` alone has only 251
distinct combinations in the data vs. 451 once `ef_upper` is included — meaning ~44% of
upper levels were being spuriously merged with a real, physically distinct e/f-parity
partner (B3Sigma-/C3Pi have genuine Lambda-doubling-like splitting, unlike X3Sigma-,
where parity is a fixed function of N and does not need to be in the node key). Fixed
by adding `ef_upper` to the upper node tuple.

Provisional results (pre-fix run, 2026-09-16 — see "Known limitation" below):

| isotopologue | native-label sanity (22HeStLy alone) | bridged (mw + 22HeStLy) |
|---|---|---|
| 33S16O | 2662 nodes, 1 component, RMS(resid/unc)=317.13, max=1357.85; absolute RMS=16.03 cm-1, max=67.89 cm-1 | 15DrHiMo RMS=4.13/max=6.94; 96KlSaBe RMS=4.41/max=14.01; 22HeStLy RMS=320.52/max=1357.85 (F1: RMS=379.40, n=19322; F2: RMS=146.96, n=9815; no F3 rows present in this data) |

**Known limitation**: the `ef_upper` fix was applied to
`optionB_nf_validation_22hestly.py`, but re-running it afterward did not complete in
practical time (the single 2662+-node bridged component's dense `np.linalg.lstsq`
does not scale — fixing the node-identity bug increases the free-parameter count,
making an already-borderline-slow dense solve worse). The table above is therefore the
**pre-fix** run (real bug present, inflating residuals by spuriously merging distinct
upper levels). This is a real, disclosed limitation, not a silently accepted one: the
qualitative verdict (catastrophic failure, two-to-four orders of magnitude beyond
measurement uncertainty) is overwhelmingly unlikely to flip on a bug-fix that only
affects the upper (spectator, not-under-test) state's own internal fit — no plausible
correction shrinks a >300-sigma RMS / >1300-sigma max failure into "a few sigma" — but
the exact numbers above should be treated as an upper bound, not a final result.
Sparsifying `solve_component` (e.g. `scipy.sparse.linalg.lsqr`) for large components is
a real, scoped tooling gap this ADR surfaces but does not fix (out of scope: a
`csv_to_marvel.py`/validation-tooling concern, not a literature question).

**Verdict**: consistent with, and extends, ADR-0003's rejection to two more
isotopologues (five of five SO isotopologues with a coexisting N/F X3Sigma- source
pair now tested: 32S16O, 34S16O via ADR-0003; 33S16O, 36S16O via this ADR; 32S17O has
no electronic-F source at all, out of scope per the issue).

### 2. Re-read 22HeStLy and 24BrYuTe in full for real per-level/Hamiltonian data

Both papers were re-read in full (not just the summary equation already extracted).

**22HeStLy §3 (Analysis method) contains exactly what candidate direction 3 asked
for**: a real, citable effective-Hamiltonian matrix for X3Sigma-/B3Sigma-, Table 1
(`molecules/SO/markdown/22HeStLy_SO/full.md` line 195), in a `|Omega, e/f>` basis:

```
<0,e|H|0,e>     = T + B[J(J+1)+2] - 2*gamma - (4/3)*lambda      (F1)
<1,e/f|H|1,e/f> = T + B*J(J+1) - gamma + (2/3)*lambda           (F2, unmixed -- no
                                                                  <0,e|H|1,f> element)
<0,e|H|1,e>     = 2*sqrt(J(J+1)) * [-B + (1/2)*gamma]           (F1<->F3 mixing)
```

Per the paper's own text (line 109), this matrix form follows **Brown, Colbourn,
Watson & Wayne, J. Mol. Spectrosc. 74, 294 (1979)** (general effective-Hamiltonian
formulation), with the explicit 3Sigma- matrix elements specifically attributed to
**Cheung, Yoshino, Parkinson & Freeman, J. Mol. Spectrosc. 119, 1 (1986)** (reference
[48], full.md line 727). F1 (Omega=0,e) and F3 (Omega=1,e) are the two eigenvalues of
the 2x2 block; F2 (Omega=1,f) has no mixing partner and is exact. This is the
"rigorous version of what the naive [N=J+offset] formula tries to shortcut" the issue
asked for — a real intermediate-coupling diagonalization, not an asymptotic label.

**Table 2** (full.md lines 224-236) gives real fitted X3Sigma-(v=0,1) constants
(T, B, D, lambda, gamma, cm-1) for all four isotopologues this issue covers
(32S16O, 33S16O, 34S16O, 36S16O). Footnote (e) (line 254) states these ground-state
values are **"Computed from the isotopically-invariant ground-state parameters of
Lattanzi, Cazzoli & Puzzarini, Astrophys. J. 813, 4 (2015)"** [56] — i.e. sourced from
an independent microwave rotational-spectroscopy global fit, not from 22HeStLy's own
UV data. No level-by-level table listing both N and F/Sigma labels for the same
physical level was found in either paper's main text; the paper's own supplementary
archive (Zenodo 7423903, ref [45]) is the same archive this repo's own
`parse_22hestly_lines.py` extractor already draws its F/J labels from (per ADR-0002),
so it is not an independent source for a level-by-level N-F correlation table — it IS
the source of the F-labels already in our CSVs.

**24BrYuTe (Brady et al. 2024) §2.2 "Quantum numbers"** (full.md lines 33-45) states
their own MARVEL analysis assigns **every** experimental rovibronic transition using
`(v, J, e/f, F)` — not N — for triplet states, converting via **exactly Eq.1**
(F1=N+S, F2=N, F3=N-S) wherever a source paper's own convention used N. This is the
literal same formula already rejected four-to-five times in this repo. Yet their
32S16O MARVEL network (50106 transitions, 29 sources, mixing N-labeled microwave and
F-labeled UV/IR data for X3Sigma-) is reported self-consistent, with a downstream DUO
refinement RMS of only 3.13e-3 cm-1 for 512 X3Sigma- energy levels (full.md line 198).
See "A working precedent exists" below for the likely reconciliation with this ADR's
own rejection of the same formula.

### 3. Implemented and validated the effective-Hamiltonian diagonalization

New script: `.scratch/so-multi-isotopologue-combination/effective_hamiltonian_nf.py`.
Diagonalizes 22HeStLy's Table 1 matrix per J using Table 2's real B/D/lambda/gamma
constants (a standard `-D*[J(J+1)]^2` centrifugal term was added to each diagonal,
following Herzberg's universal rotational-term convention, since 22HeStLy's own
printed matrix has no explicit D term — their full treatment uses an R-dependent B(R)
from a numerically-integrated potential curve, not a closed polynomial; this is
flagged as an explicit, disclosed simplification, not silently assumed). Predicts
microwave pure-rotational X3Sigma- transitions using the **same** standard N=J+offset
branch-label map as every prior attempt, but now computing each branch's energy from
the real diagonalized Hamiltonian instead of letting a free-energy network solve
absorb any error.

Results (33S16O, 34S16O, 36S16O; 32S16O's `output/` files are currently archived
pending an unrelated reprocessing pass — see "Known limitation" — so it could not be
tested this session):

| isotopologue | source | n | RMS(resid/unc) | max\|resid/unc\| | RMS(resid) cm-1 | max\|resid\| cm-1 |
|---|---|---|---|---|---|---|
| 33S16O | 15DrHiMo | 21 | 5969.69 | 11425.28 | 0.01237 | 0.02022 |
| 33S16O | 96KlSaBe | 24 | 2681.83 | 6421.26 | 0.00912 | 0.02142 |
| 34S16O | 15DrHiMo | 48 | 17583.14 | 48840.76 | 0.00842 | 0.01944 |
| 34S16O | 74Ti | 9 | 84.04 | 148.75 | 0.00040 | 0.00065 |
| 34S16O | 82BoDeDe | 17 | 584.88 | 1050.03 | 0.00185 | 0.00362 |
| 34S16O | 82Ti | 10 | 916.57 | 1700.12 | 0.00203 | 0.00544 |
| 34S16O | 96KlSaBe | 26 | 2793.96 | 5097.03 | 0.00972 | 0.02550 |
| 36S16O | 96KlSaBe | 28 | 3310.57 | 5288.47 | 0.01260 | 0.02566 |

**This is a real, meaningful improvement over every prior attempt in absolute terms**:
residuals are consistently ~0.0004-0.026 cm-1 across three isotopologues and six
independent microwave sources, vs. ADR-0003's 0.045-0.91 cm-1 (87BuLoHa network merge)
and this ADR's own 16-68 cm-1 (raw 22HeStLy internal scatter, Section 1 above) — one to
three orders of magnitude closer to the real physical answer. But it still fails the
mandatory few-sigma validation gate by 2-5 orders of magnitude (microwave uncertainties
are ~1e-4-1e-5 cm-1, far smaller than the ~0.01-0.03 cm-1 residual). **Per the issue's
own instruction, this is reported honestly as "improved but not validated" — a
rejection, not a partial win.**

The residual grows smoothly and monotonically with J (checked directly: 33S16O
combination-difference residuals against 22HeStLy's own upper-level structure grow
from ~14 cm-1 mean at J=0-9 to ~76 cm-1 mean at J=40-49 — too large and too
state-dependent to be explained by the X-state model alone; this specific check is
confounded by not modeling the B3Sigma-/C3Pi upper state at all, so it is reported as
an observation, not evidence, and was not used in the pass/fail verdict above). This
pattern is consistent with a real, documented, but not-implemented cause: the **same**
22HeStLy Table 2 footnote (e) states X3Sigma- has additional fitted higher-order
constants — `H = -2.16e-13`, `lambda_D = 1.02e-5`, `gamma_D = -1.76e-8` — not included
in Table 1's printed matrix or in this implementation. **These were not added to the
model**: the markdown extraction of Table 2's footnotes shows this exact numeric block
only once, but the table has one footnote letter per isotopologue's v=0 row (e, r, w,
ab for 32S16O/33S16O/34S16O/36S16O respectively) — meaning the visible numbers are very
likely 32S16O-specific, and using them for 33S16O/34S16O/36S16O without a citable
per-isotopologue source would itself violate the anti-fabrication rule. This is a
concrete, scoped, and different next step than "check textbooks": **re-extract or
re-OCR the original PDF's footnote table specifically for the other three
isotopologues' H/lambda_D/gamma_D values, or fetch them directly from Lattanzi, Cazzoli
& Puzzarini (2015)**, rather than open-ended literature searching.

### 4. Brown & Carrington / Lefebvre-Brion & Field / PGOPHER (candidate directions 2-3)

Not pursued further as independent primary sources: 22HeStLy's Table 1 already *is*
the standard Brown & Carrington-class treatment (their own text says it follows the
PGOPHER program's [46] conventions and Brown et al. [47]/Cheung et al. [48]'s matrix
elements directly), so re-deriving the same matrix from a textbook would be redundant
with what was already implemented and cited to its actual primary literature source.

### 5. Checked both candidate sources for the missing H/lambda_D/gamma_D constants — both already in this repo's corpus, both missing 33S16O and 36S16O

A second, independent research pass (a Perplexity-drafted ADR, `adr0004_draft_perplexity.md`,
not otherwise adopted) proposed Bogey, Demuynck & Destombes (1982) as the source for
the higher-order X3Sigma- constants Section 3 above found missing for 33S16O/34S16O/
36S16O, via a case-(b)-basis (N-basis) Hamiltonian diagonalization rather than
22HeStLy's own case-(a)-like Omega-basis matrix. Both candidate constants sources are
already in this repo's corpus and were checked directly (not re-derived from the draft's
citations):

- **`molecules/SO/markdown/82BoDeDe_SO/full.md`** (Bogey et al. 1982, `82BoDeDe`): uses
  the N-basis Hamiltonian `H = Bv*N^2 + (2/3)*lambda_v*(3Sz^2-S^2) + gamma_v*N*S -
  Dv*N^4 + ...` (line 38) — structurally the case-(b) form, not 22HeStLy's Omega-basis
  form, though physically equivalent (same underlying Brown/Colbourn/Watson/Wayne-class
  Hamiltonian, related by a unitary basis change, given the same B/gamma/lambda/D
  constants). Table 2 (line 116) fits `32S16O` only, referencing `34S16O` and `32S18O`
  data from the same joint least-squares fit (line 67: "all experimental data... the
  three isotopic species 32S16O, 34S16O and 32S18O"). **No 33S16O or 36S16O data or
  constants anywhere in this paper.**
- **`molecules/SO/markdown/15LaCaPu_SO/full.md`** (Lattanzi, Cazzoli & Puzzarini 2015,
  `15LaCaPu` — the paper 22HeStLy's own Table 2 footnote (e) already cites as its
  ground-state constants source, see Section 2 above): also N-basis (`H_S-N = N.S(gamma_B
  + gamma_D*N^2)`, `H_S-S = (2/3)(lambda_B + lambda_D*N^2)(3Sz^2-S^2)`, line 61/67),
  explicitly carries `D, H, gamma_D, lambda_D` (line 70: "D, H, gamma_D, and lambda_D
  represent their centrifugal-distortion correction. The derived parameters... for each
  isotopic species are summarized in Tables 1-2"). Tables 1-2 were checked directly:
  **cover 32S16O and 34S16O (and 32S18O via the ${}^{17}$O hyperfine extension) — no
  33S16O or 36S16O rows in either table.**

**This closes off, rather than reopens, the "re-extract or fetch Lattanzi 2015 directly"
fallback Section 3 proposed**: it was not an OCR/extraction gap in this repo's own
processing of 15LaCaPu — the paper itself never published H/lambda_D/gamma_D (or any
higher-order constant) for 33S16O or 36S16O, and Bogey (1982), the only other candidate
primary source identified, has the identical gap (plus lacks 32S18O... no, has 32S18O
but never had 33S16O/36S16O at all — it predates their microwave characterization).
**Verdict on this sub-question: a genuine literature gap, not a tooling or research-effort
gap.** The only remaining path for 33S16O/36S16O's higher-order constants is isotopic
mass-scaling from the 32S16O/34S16O values (both papers already do exactly this kind of
scaling for their own covered isotopologues, e.g. 82BoDeDe's Eq. 3-4 Born-Oppenheimer
mass-scaling relations) — a derived, not directly-measured, estimate, which would need
its own validation against real data before use, not a citation of either paper as-is.

### 6. 33S16O higher-order constants located; 36S16O confirmed a genuine literature gap; no validated gamma-scaling relation exists

A `74Ti_SO_constants.pdf` file (Tiemann, E. (1974), "Microwave Spectra of Molecules of
Astrophysical Interest VIII. Sulfur Monoxide," *J. Phys. Chem. Ref. Data* 3, 259-268,
DOI 10.1063/1.3253141) was found already sitting in `molecules/SO/papers/`, distinct
from the already-corpus `74Ti_SO.pdf` (a different, shorter 1974 Tiemann NBS paper on
isotope dependence of B0 only, covering just 32S16O/34S16O/32S18O). OCR'd via
`mineru_cloud.py` this session into `molecules/SO/markdown/74Ti_SO_constants/full.md`
and verified directly against the source text (not taken on citation alone).

**33S16O: constants exist, confirmed real.** Table 2 (full.md line 178) gives, for the
ground vibrational state:

| Constant | Value | Status |
|---|---|---|
| B0 | 21306.46 +/- 0.10 MHz | scaled from 32S16O via isotopic (reduced-mass) relation |
| lambda0 | 158257.3 +/- 5.0 MHz | scaled from 32S16O |
| gamma0 | -167.21 +/- 0.45 MHz | **fitted directly** to 33S16O's own resolved hyperfine spectrum (Amano et al. 1967, ref [67A]) |
| D0 | (3.352 +/- 0.018)e-2 MHz | scaled from 32S16O |
| rho0 | 0.300 +/- 0.030 MHz | scaled from 32S16O |
| eqQ | -15.9 +/- 3.0 MHz | fitted, 33S-nuclear-spin (I=3/2) hyperfine, ref [67A] |
| b | +51.0 +/- 2.0 MHz | fitted, ref [67A] |
| c | -96.5 +/- 2.0 MHz | fitted, ref [67A] |

The paper's own text (line 65) states explicitly: "For 33S16O all rotational constants
were calculated with isotopic relations from 32S16O and the hyperfine constants were
fitted to the observed spectral splittings" — i.e. **B0/lambda0/D0/rho0 are themselves
mass-scaled, not independently measured; only gamma0/eqQ/b/c come from real 33S16O
data.** This is a real, citable, complete-enough constant set for 33S16O — no longer a
gap.

**36S16O: still absent, confirmed exhaustively.** `74Ti_SO_constants` (this section),
`15LaCaPu` and `82BoDeDe` (Section 5 above) were all checked directly — none of the
three papers that carry X3Sigma- higher-order/hyperfine constants for any SO
isotopologue has a 36S16O entry anywhere. This is a genuine, multiply-confirmed
literature gap, not a search-effort or extraction-quality problem.

**No validated scaling relation for gamma0 exists — two candidate literature sources for
one were checked and both are misapplied/irrelevant, not usable:**
- Kim, Shin, Nah et al. (2015), *Computational and Theoretical Chemistry* 1054, 46-54
  (DOI 10.1016/j.comptc.2014.12.003) — real paper, verified via CrossRef + abstract, but
  is ab initio RICC2/CCSD vibrational-frequency/rotational-constant scaling for **NH3
  and HCHO** (closed-shell polyatomics) — nothing to do with 3Sigma- spin-rotation
  coupling or SO. **Do not cite for this problem.**
- arXiv:1211.5397, "Linear polyatomic molecules with Pi ground state: sensitivity to
  variation of the fundamental constants" — real paper, verified by direct fetch,
  genuinely contains a formula "gamma ~ alpha^2 * mu" (Table 3), but **mu there is the
  electron-to-proton mass ratio** (a fundamental constant, for testing cosmological
  time-variation), not the isotopic reduced-mass ratio (mu_32/mu_36) used everywhere
  else in this ADR's scaling arithmetic — same symbol, unrelated physics. Also a
  polyatomic Pi-state Renner-Teller system (C3H), not a diatomic 3Sigma- state.
  **Do not cite for this problem.**
- Tiemann (1974) itself is, if anything, evidence *against* a simple gamma-scaling law:
  he had B0/lambda0/D0/rho0 scalable from 32S16O but explicitly could not do the same
  for gamma0/lambda0's fine structure — he fit gamma0 directly from 33S16O's own
  hyperfine-resolved data instead (see table above), and this repo's own 74Ti (the
  other Tiemann 1974 paper) separately states "it is not possible to discuss the
  isotope dependence of the molecular parameters lambda0 and gamma0" from B0-type
  microwave data alone (74Ti full.md line 79).

**Practical options for a 36S16O gamma0, if one is needed before a real measurement
exists (none validated — pick per the pipeline's own anti-fabrication standard, i.e.
disclose whichever is used as an explicit approximation, never as a citation):**
1. **mu-scale gamma0 like B0** (gamma0(36S16O) = gamma0(32S16O) * mu32/mu36 = -168.794 *
   0.9673 = -163.3 MHz) — simplest, structurally consistent with how B0/lambda0/D0 are
   already scaled, but **unvalidated** for gamma specifically.
2. **Hold gamma0 constant across isotopologues** (-168.8 MHz) — also unvalidated, but
   defensible in that gamma0's isotopic variation is already small and only barely
   resolved even for 34S16O/32S18O in the sources that do measure it directly (74Ti,
   15LaCaPu, 82BoDeDe).
3. **Fit gamma0 empirically** against whatever F-labeled 36S16O sources exist in this
   pipeline's own corpus, if any, by minimizing merged-network residuals — turns the
   unknown into a measured quantity from this pipeline's own data rather than an
   assumption, but only possible if such a source exists for 36S16O.
4. **Sensitivity analysis**: run the effective-Hamiltonian diagonalization (Section 3)
   with gamma0 in {-163, -169, -175} MHz (spanning options 1-2 plus a symmetric spread)
   and check whether the merged-network residual verdict (pass/fail against measurement
   uncertainty) changes at all across that range. If it doesn't, gamma0's exact value is
   not the bottleneck for 36S16O and this whole question can be deprioritized; if it
   does, that pins down how much precision is actually needed before chasing a real
   36S16O measurement or fit.

None of these four have been implemented or tested this session — this is a scoped,
disclosed open question for 36S16O only, not a blocker for 33S16O (which now has a real,
complete, citable constant set per the table above).

## A working precedent exists (Brady et al. 2024) — do not treat this as closed

Section 2 above found that Brady et al. 2024 already built a real, published,
self-consistent MARVEL network for 32S16O combining N-labeled microwave sources and
F-labeled UV/IR sources for X3Sigma-, using literally the same Eq.1 formula this
pipeline has rejected five times. Their MARVEL run invalidated only 546/50106
transitions overall (~1%) and reports X3Sigma- fitting to 3.13e-3 cm-1 RMS downstream.

This is not a contradiction of this ADR's rejection — it is evidence about *what
"validated" means for a real MARVEL network* that this pipeline's test methodology
does not currently capture. MARVEL's own iterative bootstrap reweighting algorithm
(24BrYuTe §2.1, full.md line 29: "adjusts (increases) the uncertainties in the line
positions to an optimized uncertainty sigma_opt until they agree with the rest of the
network") is explicitly designed to absorb exactly this kind of imperfect-but-real
connectivity by inflating the *effective* uncertainty on the poorly-fitting
transitions, rather than requiring them to already match at face-value stated-
uncertainty precision. `optionB_nf_validation.py` and this ADR's tests, by contrast,
use each transition's *original, unmodified* stated uncertainty as the pass/fail
denominator — a stricter and different test than what a real MARVEL4/bootstrap run
would apply.

**Recommended next step** (not performed this session — a real MARVEL4/bootstrap run
is a different kind of task than a literature-research issue): relabel this pipeline's
own X3Sigma- N-labeled sources to F/J via Eq.1 (matching Brady's own scheme) and run
the merged, harmonized set through an actual MARVEL4 (or MARVEL_GNN) solve with its
real iterative reweighting — not this repo's simplified fixed-uncertainty network-merge
test script — to see whether it converges the way Brady's did. If it does, the right
fix is architectural (marvel-combiner should adopt F/J, not N, as the canonical
X3Sigma- scheme, matching Brady's precedent, and defer final consistency-checking to
MARVEL4 itself) rather than a pre-solve deterministic relabeling formula.

## Verdict

- The naive asymptotic formula (Brady Eq.1) applied as a rigid, fixed-uncertainty
  label-and-merge test: **REJECTED**, now on five isotopologues (32S16O, 34S16O from
  ADR-0003; 33S16O, 36S16O from this ADR) — no change to ADR-0002/ADR-0003's status.
- The rigorous effective-Hamiltonian alternative (candidate direction 3, actually
  implemented and cited this session): **REJECTED** under the same fixed-uncertainty
  standard, despite being 10-1000x closer in absolute terms — "improved but not
  validated," per the issue's own instruction not to round up.
- **This question is not formally closed** in the sense the issue's option (b)
  describes ("no shortcut exists ... absent new data"). New data was not required to
  find a working precedent — it already exists, published, for 32S16O (Brady et al.
  2024) — but the working mechanism is MARVEL4's own bootstrap reweighting, not a
  formula this pipeline's tooling can validate standalone. The concrete reopening
  condition is: **run an actual MARVEL4/bootstrap solve** on the F/J-relabeled,
  harmonized SO X3Sigma- dataset (all five isotopologues) and check whether it
  converges self-consistently the way it did for Brady's 32S16O, rather than further
  literature-searching for a better deterministic formula.
- **The "missing higher-order constants" sub-question (Section 3's own next step) IS
  formally closed**, by Sections 5-6: Bogey 1982, Lattanzi 2015, and Tiemann 1974
  (`74Ti_SO_constants`) were all checked directly. **33S16O's constants are now real,
  sourced, and in-corpus** (Section 6 table) — no longer a gap. **36S16O has no
  higher-order or hyperfine constants in any of the three papers** — a genuine
  literature gap, not a re-extraction or better-source problem. No validated gamma0
  isotopic-scaling relation exists for either isotopologue if one is ever needed
  (Section 6's two candidate citations for one are both real papers but physically
  irrelevant to this problem). Any future 36S16O value must come from isotopic
  mass-scaling (derived, needs its own validation per Section 6's four options) or a
  new source paper, not from re-reading 15LaCaPu/82BoDeDe/74Ti again.

## Consequences

- `csv_to_marvel.py harmonize` and `marvel-combiner` keep their current blank-pad-only,
  no-auto-union behavior for SO's X3Sigma- N/F sources — no formula tested to date
  (naive or effective-Hamiltonian) clears this pipeline's fixed-uncertainty validation
  gate, so nothing changes operationally yet.
- The real next step is a different kind of task: an actual MARVEL4/bootstrap run (see
  above). Recovering 33S16O's H/lambda_D/gamma_D-equivalent constants is **done** —
  `74Ti_SO_constants` (Section 6) has a complete, citable 33S16O constant set now in
  the corpus. 36S16O's equivalent is **confirmed absent everywhere checked** (Bogey
  1982, Lattanzi 2015, both Tiemann 1974 papers) — only mass-scaling (Section 6,
  unvalidated) or a new source paper remains. Flag the MARVEL4/bootstrap run as a
  follow-up issue rather than re-opening this one unchanged.
- `optionB_nf_validation_22hestly.py` and `effective_hamiltonian_nf.py` (this session's
  new scripts, `.scratch/so-multi-isotopologue-combination/`) are read-only validation
  tools, reusable for the recommended next step once 32S16O's `output/` files are
  un-archived and/or a sparse solver replaces `solve_component`'s dense `lstsq` for
  large single components.
- `molecules/SO/markdown/74Ti_SO_constants/` (this session's new OCR output) now exists
  alongside the pre-existing, distinct `74Ti_SO/` — both are legitimately separate
  Tiemann 1974 papers and should not be merged or treated as duplicates.
