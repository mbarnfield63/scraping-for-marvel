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
out = run(c.count, "XY")
assert "26AbCd" in out and "32S16O 3" in out and "= 4 rows" in out, out
assert c.ID_RE.match("99IsNaMib.450") and c.ID_RE.match("26PeLeSuRu.12") and not c.ID_RE.match("99IsNaMiBcDe.1")
# split-parity follows the dipole rule: P/R pair e-e/f-f, Q pairs e-f/f-e, a printed side always wins
dz = c.BASE / "XZ" / "csv"
dz.mkdir(parents=True)
(dz / "26EfGh_batch1.csv").write_text(head +
    "1002.5,0.01,B2Pi,2,3.5,,f,X2Pi,2,2.5,,,26EfGh.1,15N18O,unit: cm-1; parity: unresolved\n"   # R, upper printed
    "1003.5,0.01,B2Pi,2,2.5,,,X2Pi,2,2.5,,,26EfGh.2,15N18O,unit: cm-1; parity: unresolved\n"    # Q, both blank
    "1004.5,0.01,B2Pi,2,2.5,,,X2Pi,2,2.5,,e,26EfGh.3,15N18O,unit: cm-1; parity: unresolved\n"   # Q, lower printed
    "1005.5,0.01,B2Pi,2,1.5,,,X2Pi,2,2.5,,,26EfGh.4,15N18O,unit: cm-1; parity: unresolved\n")   # P, both blank
(dz / "26EfGh.done").touch()
run(c.merge, "XZ", "26EfGh")
run(c.split_parity, "XZ", "26EfGh")
z = {r["id"]: (r["ef_upper"], r["ef_lower"]) for r in csv.DictReader(open(dz / "26EfGh_merged.csv"))}
assert z == {"26EfGh.1": ("f", "f"), "26EfGh.2": ("e", "f"), "26EfGh.3": ("f", "e"), "26EfGh.4": ("e", "e"),
             "26EfGh.5": ("f", "e"), "26EfGh.6": ("f", "f")}, z
run(c.split_parity, "XZ", "26EfGh")  # idempotent
assert len(list(csv.DictReader(open(dz / "26EfGh_merged.csv")))) == 6
assert "FLAGGED" not in run(c.validate, "XZ", "26EfGh").split("Split-parity")[1].splitlines()[0]
print("ok")
