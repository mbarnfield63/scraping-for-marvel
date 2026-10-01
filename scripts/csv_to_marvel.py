"""
csv_to_marvel.py — Merge scraper batch CSVs and convert to MARVEL tab-separated format.

Commands:
    merge    <mol> <paper_id>   Merge molecules/<mol>/csv/<paper_id>_batch*.csv
                                  -> molecules/<mol>/csv/<paper_id>_merged.csv
    validate <mol> <paper_id>   Mechanical checks on <paper_id>_merged.csv (ID format,
                                  uncertainty, wavenumber range, QN validity, isotopologue
                                  labels, UNREADABLE inventory, cross-batch duplicates).
                                  Prints a report; fixes nothing. Run before the reviewer agent.
    split-parity <mol> <paper_id> Expand rows tagged "parity: unresolved" in notes (electronic-
                                  transition papers only, see CLAUDE.md Parity rule) into an e/f
                                  pair: the original row becomes the "e" copy in place (same ID),
                                  and one new "f" copy is appended at the tail of that isotopologue's
                                  ID block. No-op for papers without ef_upper/ef_lower columns, and
                                  idempotent -- already-split rows are marked consumed. Run after
                                  merge, before validate.
    reconcile <mol> <paper_id>   Convert any row whose uncertainty is stated in a different
                                  native unit than its wavenumber (flagged in notes as
                                  "unit: X, differs from wavenumber's Y") into the wavenumber's
                                  unit, logging the conversion in notes. Run after the reviewer,
                                  before format -- extraction never converts units (see CLAUDE.md
                                  Unit rule); this is the one place a conversion is allowed.
    format   <mol> <paper_id>   Split merged CSV by isotopologue
                                  -> molecules/<mol>/output/<mol>_<iso>_<paper_id>_YYYYMMDD_HHMMSS.txt
"""

import argparse
import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent / "molecules"
ID_RE = re.compile(r"^(\d{2}(?:[A-Za-z]{2}){1,3})\.(\d+)$")
NON_QN_COLS = ("transition_wavenumber", "uncertainty", "id", "iso", "notes")
DUP_TOLERANCE = 0.002
FREQ_TO_HZ = {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
UNIT_RE = re.compile(r"unit:\s*(Hz|kHz|MHz|GHz)")
PARITY_UNRESOLVED_RE = re.compile(r"parity:\s*unresolved(?!\s*\(split)")
PARITY_SIBLING_RE = re.compile(r"parity-split: sibling of (\S+?),")


def merge(mol: str, paper_id: str) -> None:
    csv_dir = BASE / mol / "csv"
    batches = sorted(csv_dir.glob(f"{paper_id}_batch*.csv"))
    if not batches:
        raise SystemExit(f"No batch CSVs found for {paper_id} in {csv_dir}")

    header = None
    rows = []
    for batch in batches:
        with open(batch, newline="", encoding="utf-8") as f:
            # Batch files may start with '#' provenance lines (bib code, DOI, uncertainty, notes).
            reader = csv.reader(line for line in f if not line.startswith("#"))
            h = next(reader)
            if header is None:
                header = h
            elif h != header:
                raise SystemExit(
                    f"Column mismatch in {batch.name}:\n  expected: {header}\n  got:      {h}"
                )
            rows.extend(reader)

    out = csv_dir / f"{paper_id}_merged.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Merged {len(batches)} batch(es) -> {out.name}  ({len(rows)} rows)")


def _num(s: str):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _load_merged(mol: str, paper_id: str):
    merged = BASE / mol / "csv" / f"{paper_id}_merged.csv"
    if not merged.exists():
        raise SystemExit(f"Merged CSV not found: {merged}\nRun 'merge' first.")
    with open(merged, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames)


def split_parity(mol: str, paper_id: str) -> None:
    merged = BASE / mol / "csv" / f"{paper_id}_merged.csv"
    rows, fieldnames = _load_merged(mol, paper_id)

    if "ef_upper" not in fieldnames or "ef_lower" not in fieldnames:
        print(
            f"SPLIT-PARITY {paper_id}  (no ef_upper/ef_lower columns -- not an electronic-transition paper, no-op)"
        )
        return

    max_n: dict[tuple[str, str], int] = {}
    for r in rows:
        m = ID_RE.match(r.get("id", ""))
        if m:
            key = (m.group(1), r.get("iso", ""))
            max_n[key] = max(max_n.get(key, 0), int(m.group(2)))

    to_split = [r for r in rows if PARITY_UNRESOLVED_RE.search(r.get("notes", ""))]
    new_rows = []
    for r in to_split:
        m = ID_RE.match(r["id"])
        key = (m.group(1), r.get("iso", ""))
        max_n[key] += 1
        new_id = f"{m.group(1)}.{max_n[key]}"

        clean_notes = PARITY_UNRESOLVED_RE.sub("", r.get("notes", ""))
        clean_notes = re.sub(r";\s*;", ";", clean_notes).strip("; ").strip()

        new_row = dict(r)
        new_row["ef_upper"] = "f"
        new_row["ef_lower"] = "f"
        new_row["id"] = new_id
        sibling_note = f"parity-split: sibling of {r['id']}, degenerate e/f pair"
        new_row["notes"] = (
            f"{clean_notes}; {sibling_note}" if clean_notes else sibling_note
        )
        new_rows.append(new_row)

        r["ef_upper"] = "e"
        r["ef_lower"] = "e"
        r["notes"] = PARITY_UNRESOLVED_RE.sub(
            f"parity: unresolved (split -> {new_id})", r.get("notes", "")
        )

    rows.extend(new_rows)

    with open(merged, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(
        f"SPLIT-PARITY {paper_id}  ({len(to_split)} row(s) split, {len(new_rows)} new row(s) appended, {len(rows)} total)"
    )


def validate(mol: str, paper_id: str) -> None:
    rows, fieldnames = _load_merged(mol, paper_id)
    qn_cols = [c for c in fieldnames if c not in NON_QN_COLS]
    issues: list[tuple[str, str, str]] = []  # (row_id, field, reason)

    # ID format + per-(prefix, iso) N-sequencing (must reset to 1, no gaps/dupes)
    by_prefix_iso: dict[tuple[str, str], list[int]] = {}
    for r in rows:
        m = ID_RE.match(r.get("id", ""))
        if not m:
            issues.append((r.get("id", "<blank>"), "id", "does not match YYAuthAuth.N"))
            continue
        by_prefix_iso.setdefault((m.group(1), r.get("iso", "")), []).append(
            int(m.group(2))
        )
    for (prefix, iso), ns in by_prefix_iso.items():
        expected = set(range(1, len(ns) + 1))
        got = set(ns)
        if got != expected:
            missing, dupes_n = sorted(expected - got), sorted(
                n for n in set(ns) if ns.count(n) > 1
            )
            detail = ", ".join(
                p
                for p in (
                    f"missing {missing}" if missing else "",
                    f"duplicated {dupes_n}" if dupes_n else "",
                )
                if p
            )
            issues.append((f"{prefix}.* (iso={iso})", "id", detail))

    # Uncertainty: non-blank, positive
    for r in rows:
        u = _num(r.get("uncertainty"))
        if u is None or u <= 0:
            issues.append(
                (
                    r["id"],
                    "uncertainty",
                    f"{r.get('uncertainty')!r} (notes: {r.get('notes', '')!r})",
                )
            )

    # Wavenumber: non-blank, positive
    for r in rows:
        w = _num(r.get("transition_wavenumber"))
        if w is None or w <= 0:
            issues.append(
                (
                    r["id"],
                    "transition_wavenumber",
                    f"{r.get('transition_wavenumber')!r}",
                )
            )

    # QN validity: v*/J* non-negative integers, 0<=K<=J per suffix, |l#|<=v# per suffix
    for r in rows:
        for c in qn_cols:
            val = r.get(c, "")
            if val == "":
                continue
            n = _num(val)
            low = c.lower()
            if (low.startswith("v") or low.startswith("j") or low.startswith("k")) and (
                n is None or n < 0 or n != int(n)
            ):
                issues.append(
                    (r["id"], c, f"expected non-negative integer, got {val!r}")
                )
        for c in qn_cols:
            if c.lower().startswith("k"):
                suffix = c.split("_", 1)[1] if "_" in c else ""
                jcol = next(
                    (
                        x
                        for x in qn_cols
                        if x.lower().startswith("j") and x.endswith(suffix)
                    ),
                    None,
                )
                kv, jv = _num(r.get(c, "")), _num(r.get(jcol, "")) if jcol else None
                if kv is not None and jv is not None and kv > jv:
                    issues.append((r["id"], c, f"{c}={kv:g} > {jcol}={jv:g}"))
            if c.lower().startswith("l") and len(c) > 1 and c[1].isdigit():
                vcol = "v" + c[1:]
                if vcol in qn_cols:
                    lv, vv = _num(r.get(c, "")), _num(r.get(vcol, ""))
                    if lv is not None and vv is not None and abs(lv) > vv:
                        issues.append(
                            (r["id"], c, f"|{c}|={abs(lv):g} > {vcol}={vv:g}")
                        )

    # UNREADABLE inventory
    unreadable = [
        (r["id"], r.get("notes", ""))
        for r in rows
        if "unreadable" in r.get("notes", "").lower()
    ]

    # Split-parity: no unconsumed tokens, and every split pair is wavenumber/QN-identical
    # apart from the ef_upper/ef_lower label (electronic-transition papers only)
    unconsumed = [
        r["id"] for r in rows if PARITY_UNRESOLVED_RE.search(r.get("notes", ""))
    ]
    for rid in unconsumed:
        issues.append(
            (
                rid,
                "parity",
                "unconsumed 'parity: unresolved' token -- run split-parity before validate",
            )
        )

    if "ef_upper" in fieldnames and "ef_lower" in fieldnames:
        by_id = {(r["id"], r.get("iso", "")): r for r in rows}
        other_label = {"e": "f", "f": "e"}
        for r in rows:
            m = PARITY_SIBLING_RE.search(r.get("notes", ""))
            if not m:
                continue
            sib = by_id.get((m.group(1), r.get("iso", "")))
            if sib is None:
                issues.append((r["id"], "parity", f"sibling {m.group(1)} not found"))
                continue
            if sib.get("ef_upper") != other_label.get(r.get("ef_upper", ""), None):
                issues.append(
                    (
                        r["id"],
                        "parity",
                        f"sibling {sib['id']} ef_upper={sib.get('ef_upper')!r}, expected opposite",
                    )
                )
            diff_cols = [
                c
                for c in qn_cols
                if c not in ("ef_upper", "ef_lower") and r.get(c, "") != sib.get(c, "")
            ]
            if (
                r.get("transition_wavenumber") != sib.get("transition_wavenumber")
                or diff_cols
            ):
                issues.append(
                    (
                        r["id"],
                        "parity",
                        f"sibling {sib['id']} mismatched: {diff_cols or 'wavenumber'}",
                    )
                )

    # Cross-batch duplicates: same QN tuple + iso, wavenumber within tolerance, different id
    by_qn: dict[tuple, list] = {}
    for r in rows:
        by_qn.setdefault(
            tuple(r.get(c, "") for c in qn_cols) + (r.get("iso", ""),), []
        ).append(r)
    dupes = []
    for group in by_qn.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                w1, w2 = _num(group[i]["transition_wavenumber"]), _num(
                    group[j]["transition_wavenumber"]
                )
                if (
                    w1 is not None
                    and w2 is not None
                    and abs(w1 - w2) <= DUP_TOLERANCE
                    and group[i]["id"] != group[j]["id"]
                ):
                    dupes.append((group[i]["id"], group[j]["id"], w1, w2))

    iso_counts = Counter(r.get("iso", "") for r in rows)

    # ---- report ----
    def cat(field_prefix):
        return [i for i in issues if i[1] == field_prefix]

    id_issues, unc_issues, wave_issues, parity_issues = (
        cat("id"),
        cat("uncertainty"),
        cat("transition_wavenumber"),
        cat("parity"),
    )
    qn_issues = [
        i
        for i in issues
        if i[1] not in ("id", "uncertainty", "transition_wavenumber", "parity")
    ]

    print(f"VALIDATE {paper_id}  ({len(rows)} rows)")
    print(f"{'CHECK':<24}{'RESULT':<10}DETAIL")
    checks = [
        ("ID format/sequencing", not id_issues, f"{len(id_issues)} issue(s)"),
        ("Uncertainty", not unc_issues, f"{len(unc_issues)} row(s)"),
        ("Wavenumber range", not wave_issues, f"{len(wave_issues)} row(s)"),
        ("QN validity", not qn_issues, f"{len(qn_issues)} row(s)"),
        ("Isotopologue labels", True, dict(iso_counts)),
        ("Transition counts", True, f"{len(rows)} total"),
        ("UNREADABLE inventory", not unreadable, f"{len(unreadable)} row(s)"),
        ("Split-parity integrity", not parity_issues, f"{len(parity_issues)} issue(s)"),
        ("Cross-batch duplicates", not dupes, f"{len(dupes)} pair(s)"),
    ]
    for name, ok, detail in checks:
        print(f"{name:<24}{'PASS' if ok else 'FLAGGED':<10}{detail}")

    if issues or unreadable or dupes:
        print("\nFLAGGED ROWS")
        for rid, field, reason in issues:
            print(f"  {rid}\t{field}\t{reason}")
        for rid, notes in unreadable:
            print(f"  {rid}\tUNREADABLE\t{notes}")
        for id1, id2, w1, w2 in dupes:
            print(
                f"  {id1} / {id2}\tduplicate\twavenumbers {w1:g} / {w2:g} within {DUP_TOLERANCE}, same QNs+iso"
            )
    else:
        print("\nNo flags from mechanical checks.")


def reconcile_units(mol: str, paper_id: str) -> None:
    merged = BASE / mol / "csv" / f"{paper_id}_merged.csv"
    rows, fieldnames = _load_merged(mol, paper_id)

    changed = 0
    for row in rows:
        notes = row.get("notes", "")
        if "unit-reconciled:" in notes:
            continue
        units = UNIT_RE.findall(notes)
        if len(units) < 2:
            continue
        to_unit = units[0]  # wavenumber's unit, always stated first
        from_unit = next((u for u in units[1:] if u != to_unit), None)
        if from_unit is None:
            continue
        val = _num(row["uncertainty"])
        if val is None:
            continue
        new_val = val * FREQ_TO_HZ[from_unit] / FREQ_TO_HZ[to_unit]
        new_val_str = f"{new_val:.9g}"
        row["uncertainty"] = new_val_str
        row["notes"] = (
            f"{notes}; unit-reconciled: {val:g} {from_unit} -> {new_val_str} {to_unit}"
        )
        changed += 1

    with open(merged, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"RECONCILE {paper_id}  ({changed} row(s) converted, {len(rows)} total)")


def so_convert(mol: str, paper_id: str) -> None:
    """
    SO-specific mechanical step (SO_algorithm.py logic): resolve a paper's fine-structure
    labeling into the F_upper/ef_upper + F_lower/ef_lower columns.

    - N_upper/N_lower present, no F_upper: Hund's case-(b) triplet -- map N,J -> F1/F2/F3
      deterministically (N=J-1->F1, N=J->F2, N=J+1->F3), parity f for F2 else e. Safe:
      1:1 per-row mapping, no fabricated rows.
    - 'branch' column present: decode existing branch label (e.g. R33ee) into F/parity.
      Safe: decodes data already in the row, no fabrication.
    - F_upper and ef_upper both already present: already in target scheme, no-op.
    - No N_upper and no F_upper: singlet-state paper -- duplicate each row into an F1 e/f
      pair (SO_algorithm.py singlet branch): original row becomes the "e" copy in place
      (same id), one new "f" copy appended at the tail of that isotopologue's id block.
    - F_upper present without ef_upper/branch: no data source to resolve parity from --
      fails safe (CSV left unchanged); run 'format' as-is and flag for manual correction.
    """
    merged = BASE / mol / "csv" / f"{paper_id}_merged.csv"
    rows, fieldnames = _load_merged(mol, paper_id)
    has = lambda c: c in fieldnames

    if has("F_upper") and has("ef_upper"):
        print(f"SO-CONVERT {paper_id}  already has F_upper/ef_upper -- no-op")
        return
    if has("N_upper") and not has("F_upper"):
        source_type = "triplet_N"
    elif has("branch"):
        source_type = "branch"
    elif has("F_upper") and not has("ef_upper"):
        print(
            f"SO-CONVERT {paper_id}  FAILED -- F_upper present without ef_upper/branch column, "
            f"no data source to resolve parity. Skipping conversion; merged CSV left unchanged. "
            f"Flag for manual QN-scheme correction."
        )
        return
    elif not has("N_upper") and not has("F_upper"):
        source_type = "singlet"
    else:
        print(
            f"SO-CONVERT {paper_id}  FAILED -- unrecognized column scheme: {fieldnames}. "
            f"Skipping conversion; merged CSV left unchanged. Flag for manual QN-scheme correction."
        )
        return

    try:
        if source_type == "singlet":
            max_n: dict[tuple[str, str], int] = {}
            for r in rows:
                m = ID_RE.match(r.get("id", ""))
                if m:
                    key = (m.group(1), r.get("iso", ""))
                    max_n[key] = max(max_n.get(key, 0), int(m.group(2)))

            new_rows = []
            for r in rows:
                m = ID_RE.match(r.get("id", ""))
                if not m:
                    raise ValueError(
                        f"row {r.get('id')!r}: does not match YYAuthAuth.N"
                    )
                r["F_upper"], r["ef_upper"] = "F1", "e"
                r["F_lower"], r["ef_lower"] = "F1", "e"

                key = (m.group(1), r.get("iso", ""))
                max_n[key] += 1
                new_row = dict(r)
                new_row["F_upper"], new_row["ef_upper"] = "F1", "f"
                new_row["F_lower"], new_row["ef_lower"] = "F1", "f"
                new_row["id"] = f"{m.group(1)}.{max_n[key]}"
                sibling_note = f"parity-split: sibling of {r['id']}, degenerate e/f pair (singlet duplication, SO_algorithm.py)"
                new_row["notes"] = (
                    f"{r.get('notes', '')}; {sibling_note}"
                    if r.get("notes")
                    else sibling_note
                )
                new_rows.append(new_row)
            rows.extend(new_rows)

        elif source_type == "triplet_N":
            for r in rows:
                for suf in ("upper", "lower"):
                    n, j = _num(r.get(f"N_{suf}")), _num(r.get(f"J_{suf}"))
                    if n is None or j is None:
                        raise ValueError(f"row {r['id']}: blank N_{suf}/J_{suf}")
                    if n == j:
                        f_label = "F2"
                    elif n == j - 1:
                        f_label = "F1"
                    elif n == j + 1:
                        f_label = "F3"
                    else:
                        raise ValueError(
                            f"row {r['id']}: invalid N_{suf}={n:g}, J_{suf}={j:g} for triplet state"
                        )
                    r[f"F_{suf}"] = f_label
                    r[f"ef_{suf}"] = "f" if f_label == "F2" else "e"

        else:  # branch
            for r in rows:
                b = r.get("branch", "")
                if len(b) < 5:
                    raise ValueError(f"row {r['id']}: malformed branch label {b!r}")
                r["F_upper"], r["F_lower"] = f"F{b[1]}", f"F{b[2]}"
                r["ef_upper"], r["ef_lower"] = b[3], b[4]
    except ValueError as e:
        print(
            f"SO-CONVERT {paper_id}  FAILED -- {e}\n  Skipping conversion; merged CSV left unchanged. "
            f"Run 'format' as-is and flag for manual QN-scheme correction."
        )
        return

    drop = {"N_upper", "N_lower", "branch"}
    new_fieldnames = []
    for c in fieldnames:
        if c in drop:
            continue
        new_fieldnames.append(c)
        if c == "J_upper" and "F_upper" not in fieldnames:
            new_fieldnames += ["F_upper", "ef_upper"]
        if c == "J_lower" and "F_lower" not in fieldnames:
            new_fieldnames += ["F_lower", "ef_lower"]

    with open(merged, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(
        f"SO-CONVERT {paper_id}  converted {len(rows)} row(s) ({source_type}) -> F_upper/ef_upper, F_lower/ef_lower added"
    )


def combine_isotopologues(mol: str, exclude: tuple[str, ...] = ()) -> None:
    """
    Combine every formatted <mol>_<iso>_<paperID>_<timestamp>.txt in molecules/<mol>/output/
    (top-level only, not archive_* subdirs) into one CSV per isotopologue, written to
    molecules/<mol>/combined/. Columns are the union across all contributing papers -- a
    paper whose QN scheme lacks a column (e.g. no state_upper) gets that cell left blank,
    never fabricated. paperID files containing any string in `exclude` are skipped entirely.
    """
    out_dir = BASE / mol / "output"
    combined_dir = BASE / mol / "combined"
    combined_dir.mkdir(exist_ok=True)
    files = sorted(out_dir.glob(f"{mol}_*.txt"))
    if exclude:
        skipped = [f for f in files if any(e in f.name for e in exclude)]
        files = [f for f in files if f not in skipped]
        for f in skipped:
            print(f"  Excluding {f.name}")

    by_iso: dict[str, list[Path]] = {}
    for f in files:
        iso = f.name.split("_")[1]
        by_iso.setdefault(iso, []).append(f)

    for iso, iso_files in sorted(by_iso.items()):
        fieldnames: list[str] = []
        rows = []
        for f in iso_files:
            with open(f, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh, delimiter="\t")
                for c in reader.fieldnames:
                    if c not in fieldnames:
                        fieldnames.append(c)
                rows.extend(reader)

        front = [c for c in ("transition_wavenumber", "uncertainty") if c in fieldnames]
        back = [c for c in ("id",) if c in fieldnames]
        middle = [c for c in fieldnames if c not in front + back]
        ordered = front + middle + back

        out_path = combined_dir / f"{mol}_{iso}_combined.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=ordered, restval="")
            w.writeheader()
            w.writerows(rows)
        print(
            f"  {out_path.name}  ({len(rows)} rows, {len(iso_files)} paper(s), {len(ordered)} cols)"
        )


def format_marvel(mol: str, paper_id: str) -> None:
    out_dir = BASE / mol / "output"
    out_dir.mkdir(exist_ok=True)

    rows, fieldnames = _load_merged(mol, paper_id)

    # MARVEL output: all columns except 'iso' and 'notes'
    marvel_cols = [c for c in fieldnames if c not in ("iso", "notes")]

    # Skip rows with an UNREADABLE cell -- MARVEL input must be all-numeric;
    # these need manual resolution and stay out of the .txt output.
    skipped = [
        r for r in rows if any(r.get(c, "") == "UNREADABLE" for c in marvel_cols)
    ]
    rows = [r for r in rows if r not in skipped]
    if skipped:
        print(
            f"  Skipped {len(skipped)} row(s) with UNREADABLE cells: {', '.join(r['id'] for r in skipped)}"
        )

    # Group by isotopologue, preserving order of first appearance
    iso_order: list[str] = []
    by_iso: dict[str, list] = {}
    for row in rows:
        iso = row["iso"]
        if iso not in by_iso:
            iso_order.append(iso)
            by_iso[iso] = []
        by_iso[iso].append(row)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for iso in iso_order:
        iso_rows = by_iso[iso]
        out_path = out_dir / f"{mol}_{iso}_{paper_id}_{ts}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\t".join(marvel_cols) + "\n")
            for row in iso_rows:
                f.write("\t".join(row[c] for c in marvel_cols) + "\n")
        print(f"  {out_path.name}  ({len(iso_rows)} lines)")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="Merge batch CSVs into one merged CSV")
    m.add_argument("mol", help="Molecule name (e.g. CS2)")
    m.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    sp = sub.add_parser(
        "split-parity", help="Expand 'parity: unresolved' rows into e/f pairs"
    )
    sp.add_argument("mol", help="Molecule name (e.g. SO)")
    sp.add_argument("paper_id", help="Paper ID (e.g. 87BuLoHa)")

    v = sub.add_parser("validate", help="Run mechanical checks on the merged CSV")
    v.add_argument("mol", help="Molecule name (e.g. CS2)")
    v.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    r = sub.add_parser(
        "reconcile", help="Convert cross-unit uncertainty rows to the wavenumber's unit"
    )
    r.add_argument("mol", help="Molecule name (e.g. CS2)")
    r.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    sc = sub.add_parser(
        "so-convert",
        help="SO-specific: resolve N/branch labels into F_upper/ef_upper columns",
    )
    sc.add_argument("mol", help="Molecule name (e.g. SO)")
    sc.add_argument("paper_id", help="Paper ID (e.g. 74Ti)")

    f = sub.add_parser(
        "format", help="Convert merged CSV to MARVEL .txt files per isotopologue"
    )
    f.add_argument("mol", help="Molecule name (e.g. CS2)")
    f.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    c = sub.add_parser(
        "combine",
        help="Combine all papers' formatted .txt outputs into one CSV per isotopologue",
    )
    c.add_argument("mol", help="Molecule name (e.g. SO)")
    c.add_argument(
        "--exclude",
        nargs="*",
        default=(),
        help="Paper-ID substrings to skip (e.g. 82CaDeFa)",
    )

    args = p.parse_args()
    if args.cmd == "merge":
        merge(args.mol, args.paper_id)
    elif args.cmd == "split-parity":
        split_parity(args.mol, args.paper_id)
    elif args.cmd == "validate":
        validate(args.mol, args.paper_id)
    elif args.cmd == "reconcile":
        reconcile_units(args.mol, args.paper_id)
    elif args.cmd == "so-convert":
        so_convert(args.mol, args.paper_id)
    elif args.cmd == "combine":
        combine_isotopologues(args.mol, tuple(args.exclude))
    else:
        format_marvel(args.mol, args.paper_id)


if __name__ == "__main__":
    main()
