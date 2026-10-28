# MARVEL input format, paper IDs and output names

The pipeline's **canonical** format: `csv_to_marvel.py format` output in
`molecules/<mol>/output/*.txt`. Tab-separated, with a header row; the column scheme depends on the
molecule type. The compiled MARVEL4.1.x binary needs one more column (a duplicated `uncorig`); see
the skill's Step 10 (`scripts/to_marvel4_input.py`).

## Column schemes

### Diatomics (e.g. CO, CS)
```
transition_wavenumber   uncertainty   v_upper   J_upper   v_lower   J_lower   ID
```

### Linear triatomics (e.g. CO₂, CS₂): Herzberg notation
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   l2_upper   v3_upper   J_upper   v1_lower   v2_lower   l2_lower   v3_lower   J_lower   ID
```

HCP adds rotationless parity after each `l2` (user decision 2026-10-21):
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   l2_upper   ef_upper   v3_upper   J_upper   v1_lower   v2_lower   l2_lower   ef_lower   v3_lower   J_lower   ID
```
`ef` comes from a printed label, else l=0 → e, else the dipole rule from the other side (P/R keep
e/f, Q flips), logged in `notes`. Rows still blank with l>0 carry `REQUIRES MANUAL REVIEW: ef_<side>
unresolved`, never `parity: unresolved` (`split-parity` would add a wrong second row). Bent-state
rows (99IsNaMib, 96IsChOh C̃–X̃, 93MaLe) are formatted into `output/bent/`, apart from the linear network files.

### Asymmetric tops (e.g. H₂O)
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   v3_upper   J_upper   Ka_upper   Kc_upper   v1_lower   v2_lower   v3_lower   J_lower   Ka_lower   Kc_lower   ID
```

### C2H4: 12 normal modes + J Ka Kc
```
transition_wavenumber   uncertainty   v1_upper ... v12_upper   J_upper   Ka_upper   Kc_upper   v1_lower ... v12_lower   J_lower   Ka_lower   Kc_lower   ID
```
Mode numbering ν1..ν12 as in Herzberg and TheoReTS (ν7 ≈ 949, ν8 ≈ 943, ν10 ≈ 826, ν12 ≈ 1443
cm-1). C2H4 v1 only: papers labelled in tensorial (J, C, n) / (J, C, α) went through
`scripts/c2h4_labels.py` into `molecules/C2H4/convert/`. From v2 they take the copy path
("Copied sources" below) and MARVEL_network converts them.

## Copied sources

Machine-readable sources (SKILL.md, "Copy path") are copied, not extracted, to
`molecules/<mol>/copy/<tag>.tsv`:
```
src_file   src_row   <source columns, unchanged>
```
- `src_file`: the copied file's name in `papers/<folder>/`; for a spreadsheet, `<file>:<sheet>`.
- `src_row`: the 1-based line number in that file (spreadsheet: the sheet row). The network line ID
  is `<tag>.<src_row>` (ADR-0002 D2), so it never changes when other rows are removed.
- Source columns keep the source's header names, else `c1`, `c2`, .... Values are copied as
  printed: no unit change, no relabel, no sign change, no dropped row.

## Source metadata

`molecules/<mol>/sources.tsv`, one row per source tag (ADR-0002 D3), tab-separated with a header:

| column | content |
|---|---|
| `tag` | the source tag, as in line IDs |
| `file` | data file(s) under `molecules/<mol>/`, `;`-separated; the paper PDF when the lines were OCR'd |
| `kind` | `IR`, `Raman`, `term values` or `levels` (a calculated or fitted level list) |
| `wn_min`, `wn_max` | range of the absolute line positions in cm-1 |
| `stated_unc` | the position uncertainty the paper states, in cm-1; blank when the paper states none or it is not yet read |
| `unc_basis` | where `stated_unc` comes from: the paper's words or table, short |
| `notation` | the label scheme: axis convention, counter definition, anything a converter must know |
| `notes` | row count, fidelity check, known defects |

Network reads this file and does not read the paper again for the same facts.

### Diatomics with electronic transitions (e.g. SO bands crossing electronic states)
```
transition_wavenumber   uncertainty   state_upper   v_upper   J_upper   F_upper   ef_upper   state_lower   v_lower   J_lower   F_lower   ef_lower   ID
```
Only when a paper's transitions span more than one electronic state; a single-state diatomic paper
stays on the plain diatomic scheme. `state_*` is a plain term-symbol string (`X3Sigma-`,
`a1Delta`). `F_*` and `ef_*` are blank for singlet states, and filled only when the paper resolves
the fine-structure sublevel or parity. For other molecule types, prepend
`state_upper`/`state_lower` to that type's QN block.

### Diatomics with hyperfine structure (e.g. CS isotopologues with resolved nuclear-spin splitting)
```
transition_wavenumber   uncertainty   v_upper   J_upper   F_upper   v_lower   J_lower   F_lower   ID
```
Only when a paper reports individually resolved hyperfine components (nuclear spin I > 0:
quadrupole and/or spin-rotation coupling). An isotopologue with no resolved hyperfine splitting in
that paper stays on the plain diatomic scheme, even when other isotopologues in the same paper need
this one. Here `F` is the **nuclear hyperfine** quantum number (for example `F=5/2,3/2,1/2` for
I=3/2). That is a different quantity from the electronic fine-structure `F` of the scheme above.
The two schemes are never combined in one paper's output, and column meaning comes from the scheme
a file uses, not from the column name. Fitted hyperfine constants (`eQq`, `C_I`, hyperfine-free
`v0`) are fit outputs, not transitions: never extract them. For other molecule types, append
`F_upper`/`F_lower` right after `J_upper`/`J_lower`.

### N2O: polyad scheme (24TeFuYu)
```
transition_wavenumber   uncertainty   P_upper   l_upper   N_upper   ef_upper   J_upper   P_lower   l_lower   N_lower   ef_lower   J_lower   ID
```
N2O uses the 24TeFuYu polyad labels instead of Herzberg ones:
- `P = 2v1+v2+4v3`;
- `l` is the vibrational angular momentum;
- `N` is the polyad counting number (canonical 24TeFuYu numbering, carried to minor isotopologues
  via Ames-1 levels);
- `ef` is the rotationless parity.

Herzberg labels live only in `molecules/N2O/states/<iso>_states.tsv`. Two N2O-only exceptions to
the extraction rules are applied in the mechanical apply step (`scripts/n2o_apply.py`), never
during extraction:
- **Uncertainty**: for 24TeFuYu source papers, use 24TeFuYu's per-source choice (Appendix A /
  Table 2), logged in `notes`. Other papers keep the manual-review rule.
- **Parity**: e/f follows the linear-molecule dipole selection rule (l=0 → e; with one side l=0,
  P/R → e and Q → f). Both sides l>0 and unlabelled → `parity: unresolved`, then split.

Full plan, decisions and the per-paper brief: `molecules/N2O/polyad_plan.md`.

## Paper IDs and line IDs

The paper ID is the paper's `key` in `MARVEL_literature/<mol>/<mol>_handoff.tsv`: a published
MARVEL/ExoMol tag if one exists, else `YY` (print year) + the first two letters of up to four
surnames. Use it as given; don't derive it again. Line IDs are `<paperID>.N`, with `N` starting at 1
and **restarting at 1 for each isotopologue** within the paper.

## Output file names

```
<molecule>_<isotopologue>_<paperID>_YYYYMMDD_HHMMSS.txt
```
Saved in `molecules/<molecule>/output/`.
