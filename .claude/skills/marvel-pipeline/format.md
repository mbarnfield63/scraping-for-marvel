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

### Asymmetric tops (e.g. H₂O)
```
transition_wavenumber   uncertainty   v1_upper   v2_upper   v3_upper   J_upper   Ka_upper   Kc_upper   v1_lower   v2_lower   v3_lower   J_lower   Ka_lower   Kc_lower   ID
```

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
MARVEL/ExoMol tag if one exists, else `YY` (print year) + the first two letters of up to three
surnames. Use it as given; don't derive it again. Line IDs are `<paperID>.N`, with `N` starting at 1
and **restarting at 1 for each isotopologue** within the paper.

## Output file names

```
<molecule>_<isotopologue>_<paperID>_YYYYMMDD_HHMMSS.txt
```
Saved in `molecules/<molecule>/output/`.
