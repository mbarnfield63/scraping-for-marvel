"""
csv_to_marvel.py — Merge scraper batch CSVs and convert to MARVEL tab-separated format.

Commands:
    merge  <mol> <paper_id>   Merge molecules/<mol>/csv/<paper_id>_batch*.csv
                               -> molecules/<mol>/csv/<paper_id>_merged.csv
    format <mol> <paper_id>   Split merged CSV by isotopologue
                               -> molecules/<mol>/output/<mol>_<iso>_<paper_id>_YYYYMMDD_HHMMSS.txt
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent / "molecules"


def merge(mol: str, paper_id: str) -> None:
    csv_dir = BASE / mol / "csv"
    batches = sorted(csv_dir.glob(f"{paper_id}_batch*.csv"))
    if not batches:
        raise SystemExit(f"No batch CSVs found for {paper_id} in {csv_dir}")

    header = None
    rows = []
    for batch in batches:
        with open(batch, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            h = next(reader)
            if header is None:
                header = h
            elif h != header:
                raise SystemExit(f"Column mismatch in {batch.name}:\n  expected: {header}\n  got:      {h}")
            rows.extend(reader)

    out = csv_dir / f"{paper_id}_merged.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Merged {len(batches)} batch(es) -> {out.name}  ({len(rows)} rows)")


def format_marvel(mol: str, paper_id: str) -> None:
    csv_dir = BASE / mol / "csv"
    out_dir = BASE / mol / "output"
    out_dir.mkdir(exist_ok=True)

    merged = csv_dir / f"{paper_id}_merged.csv"
    if not merged.exists():
        raise SystemExit(f"Merged CSV not found: {merged}\nRun 'merge' first.")

    with open(merged, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    # MARVEL output: all columns except 'iso' and 'notes'
    marvel_cols = [c for c in fieldnames if c not in ("iso", "notes")]

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
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="Merge batch CSVs into one merged CSV")
    m.add_argument("mol", help="Molecule name (e.g. CS2)")
    m.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    f = sub.add_parser("format", help="Convert merged CSV to MARVEL .txt files per isotopologue")
    f.add_argument("mol", help="Molecule name (e.g. CS2)")
    f.add_argument("paper_id", help="Paper ID (e.g. 01BlWaBr)")

    args = p.parse_args()
    if args.cmd == "merge":
        merge(args.mol, args.paper_id)
    else:
        format_marvel(args.mol, args.paper_id)


if __name__ == "__main__":
    main()
