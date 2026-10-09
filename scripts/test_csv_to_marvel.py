"""Self-check for csv_to_marvel.py on a synthetic molecule: python3 scripts/test_csv_to_marvel.py"""
import contextlib, csv, io, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import csv_to_marvel as c

c.BASE = Path(tempfile.mkdtemp())
d = c.BASE / "XY" / "csv"
d.mkdir(parents=True)


def run(f, *a):
    """Call f quietly; return what it printed."""
    o = io.StringIO()
    with contextlib.redirect_stdout(o):
        f(*a)
    return o.getvalue()


head = "transition_wavenumber,uncertainty,state_upper,v_upper,J_upper,F_upper,ef_upper,state_lower,v_lower,J_lower,F_lower,ef_lower,id,iso,notes\n"
(d / "26AbCd_batch1.csv").write_text(
    "# 26AbCd provenance line\n" + head +
    "1000.5,0.01,A2Pi,1,1.5,,,X2Pi,0,0.5,,,26AbCd.1,32S16O,unit: cm-1; parity: unresolved\n"
    "30000,17,A2Pi,1,2.5,,e,X2Pi,0,1.5,,e,26AbCd.2,32S16O,unit: MHz; fit 17 kHz (unit: kHz)\n")
(d / "26AbCd_batch2.csv").write_text(head + "1001.5,,A2Pi,1,2.5,,e,X2Pi,0,1.5,,e,26AbCd.1,34S16O,unit: cm-1\n")

try:  # merge refuses a paper without its .done marker
    c.merge("XY", "26AbCd")
    raise AssertionError("merge ran without .done")
except SystemExit as e:
    assert ".done" in str(e)
(d / "26AbCd.done").touch()
run(c.merge, "XY", "26AbCd")
rows = list(csv.DictReader(open(d / "26AbCd_merged.csv")))
assert len(rows) == 3 and not any(r["transition_wavenumber"].startswith("#") for r in rows)

run(c.split_parity, "XY", "26AbCd")
rows = {r["id"]: r for r in csv.DictReader(open(d / "26AbCd_merged.csv")) if r["iso"] == "32S16O"}
assert rows["26AbCd.1"]["ef_upper"] == "e" and rows["26AbCd.3"]["ef_upper"] == "f"
assert rows["26AbCd.3"]["transition_wavenumber"] == "1000.5"
assert "sibling of 26AbCd.1" in rows["26AbCd.3"]["notes"]
run(c.split_parity, "XY", "26AbCd")  # idempotent
assert len(list(csv.DictReader(open(d / "26AbCd_merged.csv")))) == 4

out = run(c.validate, "XY", "26AbCd")
assert "FLAGGED ROWS" in out and "uncertainty" in out  # the blank 34S16O uncertainty

run(c.reconcile_units, "XY", "26AbCd")
r2 = next(r for r in csv.DictReader(open(d / "26AbCd_merged.csv")) if r["id"] == "26AbCd.2")
assert abs(float(r2["uncertainty"]) - 0.017) < 1e-12 and "unit-reconciled: 17 kHz -> 0.017 MHz" in r2["notes"]

run(c.format_marvel, "XY", "26AbCd")
outs = sorted((c.BASE / "XY" / "output").glob("*.txt"))
assert [p.name.split("_")[1] for p in outs] == ["32S16O", "34S16O"], outs
lines = outs[0].read_text().splitlines()
assert lines[0].split("\t")[-1] == "id" and "notes" not in lines[0] and len(lines) == 4
print("ok")
