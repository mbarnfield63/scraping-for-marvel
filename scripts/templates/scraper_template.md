You are extracting measured rotational-vibrational transition wavenumbers from a
spectroscopic research paper for use in the MARVEL algorithm. Your output is
scientific data used directly for energy level calculations — accuracy is critical.
A wrong value is worse than a missing one.

━━ PAPER DETAILS ━━
Citation      : [CITATION — Authors (Year), Journal, Vol, Pages]
PDF path      : [PDF_PATH — absolute path to PDF in papers/]
Supplementary : [SUPP_PATH — absolute path to supplementary file, or "None"]
ID prefix     : [ID_PREFIX — e.g. 01BlWaBr]
Molecule      : [MOLECULE — e.g. CS₂ — linear triatomic, Herzberg notation]
Batch         : [BATCH_N] of [BATCH_TOTAL]
Isotopologues : [ISO_LIST — standard notation, e.g. 12C32S2, 13C32S2]
Tables        : [TABLE_RANGE — e.g. Tables 2–5 as they appear in the PDF]
Uncertainty   : [UNCERTAINTY — the paper's EXPLICITLY STATED value only. Either
                 (a) a global measurement uncertainty/resolution quoted in the
                 text (e.g. "resolution of 0.030 cm⁻¹"), applied to every line, OR
                 (b) a per-transition uncertainty COLUMN in the tables, applied
                 row by row. Never infer, average, split blended-vs-clean, or
                 derive from obs-calc/residuals. If the paper states neither,
                 do NOT guess — flag REQUIRES MANUAL REVIEW.]
Expected count: [EXPECTED — transitions expected in this batch, per isotopologue if known]

━━ QUANTUM NUMBER COLUMNS ━━
[QUANTUM_COLS — insert the correct set for this molecule type, e.g.:
  Linear triatomic: v1_upper, v2_upper, l2_upper, v3_upper, J_upper, v1_lower, v2_lower, l2_lower, v3_lower, J_lower
  Diatomic: v_upper, J_upper, v_lower, J_lower
  Asymmetric top: v1_upper, v2_upper, v3_upper, J_upper, Ka_upper, Kc_upper, v1_lower, v2_lower, v3_lower, J_lower, Ka_lower, Kc_lower
  Symmetric top: v_upper, J_upper, K_upper, v_lower, J_lower, K_lower
  Diatomic with electronic transitions: state_upper, v_upper, J_upper, F_upper, ef_upper, state_lower, v_lower, J_lower, F_lower, ef_lower
    (state_* is a term-symbol string, e.g. X3Sigma-; F_* stays blank unless the
    paper itself resolves fine-structure sublevels — see docs/agents/reference.md
    for term-symbol notation. Only use this scheme when the paper's transitions
    span more than one electronic state.
    ef_*: if the paper states/labels which parity component was measured, record
    it directly. If parity doesn't apply to that state, leave ef_* blank, no note.
    If the paper does NOT resolve parity for that state (components unmeasured/
    degenerate), leave ef_* blank AND add "parity: unresolved" to notes — a later
    mechanical pipeline step (csv_to_marvel.py split-parity) expands that row into
    an e/f pair automatically. Never derive e/f from J-value parity or branch type
    yourself — see CLAUDE.md's Parity (e/f) rule.)]
  Diatomic with hyperfine structure: v_upper, J_upper, F_upper, v_lower, J_lower, F_lower
    (F_* is the nuclear hyperfine quantum number, NOT the electronic fine-structure
    F above — different physical quantity, same column name. Only use this scheme
    for isotopologues where the paper reports individually resolved hyperfine
    components (nuclear spin I>0); an isotopologue with unresolved/no hyperfine
    splitting in the same paper stays on the plain Diatomic scheme. Never extract
    derived/fitted hyperfine constants (eQq, C_I, v0) — only raw resolved-component
    frequencies. See docs/agents/reference.md for F range (|J-I| to J+I).)]

━━ KNOWN HAZARDS ━━
[HAZARDS — paper-specific issues discovered during pre-screening:
  - OCR error patterns (colon-for-period, digit fragmentation)
  - Isotopologue misassignments or caption errors with proof and corrected labels
  - Dual-column table layouts: which tables, and which band is left vs. right
  - Whether J in table headers is J″ (lower state, standard) or J′ (upper state)
  - Nuclear spin statistics (even-J-only for symmetric isotopologues of linear molecules)
  - Any missing or illegible table sections
  - Δ or residual columns that must NOT be extracted as wavenumbers
  - Electronic-transition papers only: e/f-parity and F-sublevel misassignment
    risk, and per-band J-numbering conventions that can differ within one paper]

━━ PROCEDURE ━━

STEP 1 — Read the PDF (path above). Focus on the tables listed in this brief.
  Use the `pages` parameter when calling Read — supply the specific page range for
  each table. Maximum 20 pages per Read call.
  - Confirm units are cm⁻¹ (or note if MHz/GHz — extract original values, flag in notes).
  - Confirm whether J in table headers is J″ (lower state, standard for branch-notation
    tables) or J′ (upper state).
  - If a supplementary file is listed: read it directly. Parse the column headers to
    identify the wavenumber, branch, J, and band columns before extracting rows.

STEP 2 — For each data table in scope:
  - Read the caption or annotation immediately above the table to confirm the vibrational
    band and isotopologue before reading any data rows.
  - Read the table header: (a) vibrational band QNs for upper and lower states,
    (b) isotopologue, (c) branch columns present (R, P, Q).
  - Extract all legible rows. Apply Anti-Fabrication Rules strictly.
  - Dual-column tables (two band datasets side-by-side): if repeating column patterns are
    detected, the table caption names both bands left→right. Unpack as two sequential
    datasets — left columns = first band, right columns = second band.
  - Produce one CSV line per branch column per row (a row with both R and P columns
    yields two CSV lines).
  - If a table is missing or illegible in the pages read: flag it in the discrepancy
    report — do not silently omit.

STEP 3 — Output a single CSV code block with columns in this exact order:

  transition_wavenumber, uncertainty, [QUANTUM_COLS], id, iso, notes

  - id: [ID_PREFIX].N — N starts at 1 and resets to 1 for each new isotopologue
    within this paper.
  - iso: standard chemical notation (e.g. 12C32S2).
  - notes: source table number, branch (R/P/Q), any OCR corrections applied,
    UNREADABLE flag with raw cell content if applicable.

STEP 4 — After the CSV, report:
  Transitions extracted : count per isotopologue and band
  UNREADABLE rows       : count and which tables
  vs. expected          : comparison against expected count in this brief
  Discrepancies         : tables not extracted, systematic gaps, or illegible sections

━━ ANTI-FABRICATION RULES — NON-NEGOTIABLE ━━

1. Never invent values. If a number is not clearly legible, write UNREADABLE and
   continue. Do not guess.

2. Never interpolate. Do not fill in missing wavenumbers or J values from surrounding
   rows. Tables routinely skip J values due to blended lines, missing assignments, or
   nuclear spin statistics (even-J-only for symmetric isotopologues of linear molecules).

3. OCR colon-for-period: correct silently only if the substitution is systematic
   throughout the table and the corrected value is physically plausible (correct order
   of magnitude for this band). Record every correction in notes as "colon→period corrected".

4. OCR digit-fragmentation: do not reconstruct fragmented numbers (e.g. "3 4 4 9 . 0 0 1 3").
   Write UNREADABLE if reconstruction is not certain.

5. Merged cells: if a cell contains multiple J values mixed with wavenumber fragments,
   mark the entire row UNREADABLE and record the raw cell content in notes. Do not
   attempt to disentangle which wavenumber belongs to which J value.

6. Blank cells mean N/A — never propagate a value from the row above.

7. Branch notation derivation is permitted and required:
   - R(J″): J_upper = J″ + 1, J_lower = J″
   - P(J″): J_upper = J″ − 1, J_lower = J″
   - Q(J″): J_upper = J″,     J_lower = J″
   Record the branch in notes (e.g. "R-branch, Table 3").

8. Count your output. Report totals vs. expected after the CSV. If your count is more
   than 10% below expected, identify which tables you could not extract from.

9. When in doubt, omit. A missing value is recoverable by re-reading the paper.
   A silently wrong value corrupts the MARVEL spectroscopic network and is
   undetectable downstream.

10. UNCERTAINTY IS NEVER INFERRED. Use only the paper's explicitly stated value:
    a global measurement uncertainty/resolution (applied to every transition) or
    a per-transition uncertainty column (applied row by row). Do NOT derive it
    from obs-calc residuals, do NOT split blended vs. clean with made-up numbers,
    do NOT "estimate" it. Record a blended flag in `notes` if useful, but it must
    not change the uncertainty. If the paper states no uncertainty at all, flag
    REQUIRES MANUAL REVIEW rather than guessing. (obs-calc may still be used to
    VALIDATE/repair a misread wavenumber digit per technique A below — that is a
    value check, not an uncertainty source.)

━━ RECURRING OCR / TABLE HAZARDS & TECHNIQUES (general — apply to every paper) ━━
These patterns recur across papers (first catalogued on 74MaSa, Maki & Sams 1974).
Encode them into every extraction, not just the paper where they were found.

A. THE obs-calc COLUMN IS YOUR DIGIT-CHECKER (most important technique).
   Line-list tables almost always print an obs-calc residual next to each
   wavenumber (headed "σ-C", "M-C", "θ-C", "o-c" — all the same thing). This
   residual is small (|x| ≲ 0.01). Since obs = calc + residual, and calc lies on
   the *smooth* branch, the residual PINS the true value. Use it two ways:
     - Alignment sanity: a residual-position cell must hold a residual-magnitude
       number (or be blank). If it holds a wavenumber-magnitude number, the row
       is mis-parsed — flag it, do not extract.
     - Single-digit repair: OCR on faint scans routinely misreads ONE digit of a
       wavenumber (e.g. 2194.91→2188.91, 2176.37→2179.37, 2142.5694→2142.9694).
       Detect via a branch-monotonicity break; confirm the misread digit is the
       one that makes obs = (smooth-branch calc) + (printed residual). If the
       printed residual is small AND the corrected value falls on the branch, the
       fix is determined (not a guess) — apply it and record the raw value, the
       corrected value, and the residual in notes. If the residual is instead
       INCONSISTENT with every plausible branch value, mark UNREADABLE.

B. COLLAPSED CELLS + REPEATED J-LABEL in MinerU multi-band HTML tables.
   Multi-band tables put a J column on BOTH ends and one (wavenumber, residual)
   pair per band per branch. MinerU drops *trailing* empty <td>s and often
   appends the row's J as the last cell (sometimes itself OCR-misread, e.g.
   59→55), so row length varies. Parse defensively: first cell = J; drop a
   trailing bare-integer cell if it equals J or the row is over-length (a real
   wavenumber always has a decimal point); right-pad the value region to the
   fixed column count; THEN map columns. Validate every residual slot per (A).

C. BRANCH HEADERS LIE — ASSIGN BY PHYSICS. A printed "P(J)"/"R(J)" header can be
   wrong (74MaSa labelled a 22°1-12°0 R-branch column "P(J)"). Decide branch by
   monotonic direction: R increases with J, P decreases. Only fall back to the
   header when a column is too sparse to tell.

D. MULTI-PAGE TABLES: a table continued across pages ("TABLE X (continued)") is
   merged by MinerU into ONE <table> in full.md but the continuation page yields
   a caption block with NO table_body in content_list.json. Trust full.md for row
   completeness; never derive row counts from content_list.json alone.

E. VISUAL VALIDATION when the MinerU origin.pdf render is password-protected
   (the Read tool will refuse it): the SOURCE PDF in papers/ usually opens fine.
   Render the specific table pages to PNG with PyMuPDF (`fitz`) or pikepdf and
   read those, or crop a tight region at high DPI (~400-500) for a single cell.
