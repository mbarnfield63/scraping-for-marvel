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
Uncertainty   : [UNCERTAINTY — e.g. 0.0001 cm⁻¹ for unblended lines (Section 2);
                 0.001 cm⁻¹ for blended lines]
Expected count: [EXPECTED — transitions expected in this batch, per isotopologue if known]

━━ QUANTUM NUMBER COLUMNS ━━
[QUANTUM_COLS — insert the correct set for this molecule type, e.g.:
  Linear triatomic: v1_upper, v2_upper, l2_upper, v3_upper, J_upper, v1_lower, v2_lower, l2_lower, v3_lower, J_lower
  Diatomic: v_upper, J_upper, v_lower, J_lower
  Asymmetric top: v1_upper, v2_upper, v3_upper, J_upper, Ka_upper, Kc_upper, v1_lower, v2_lower, v3_lower, J_lower, Ka_lower, Kc_lower
  Symmetric top: v_upper, J_upper, K_upper, v_lower, J_lower, K_lower]

━━ KNOWN HAZARDS ━━
[HAZARDS — paper-specific issues discovered during pre-screening:
  - OCR error patterns (colon-for-period, digit fragmentation)
  - Isotopologue misassignments or caption errors with proof and corrected labels
  - Dual-column table layouts: which tables, and which band is left vs. right
  - Whether J in table headers is J″ (lower state, standard) or J′ (upper state)
  - Nuclear spin statistics (even-J-only for symmetric isotopologues of linear molecules)
  - Any missing or illegible table sections
  - Δ or residual columns that must NOT be extracted as wavenumbers]

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
