"""Self-check for marvel_steps.load overrides: python scripts/test_marvel_steps.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import marvel_steps as m

ov = Path(tempfile.mkdtemp()) / "overrides.tsv"
ov.write_text("action\ttarget\tvalue\treason\n"
              "negate\t09WaLiPe.1\t-\tt\nscale\t19LiHuWa\t2\tt\n"
              "assume_unc\t69MaRaJo\t0.01\tt\nrelabel\t09WaLiPe.2\tupper=9 9 9 e 9\tt\n"
              "double\t09WaLiPe.3\t-\tt\nwn_scale\t09WaLiPe\t1.00001\tt\n")
(ov.parent / "vx.txt").write_text("0.8 1e-5 1e-5 0 0 1 e 1 0 0 1 e 0 VGS_X.1\n")
ov.write_text(ov.read_text() + "extra\tvx.txt\tcm-1\tt\n")  # extra files resolve next to overrides.tsv
L, seg, held = m.load("548", ov)
assert "VGS_X.1" in {t[-1] for t in L} and seg["VGS_X"] == "cm-1"
b = {t[-1]: t for t in L}
assert b["09WaLiPe.1"][0].startswith("-")
assert m.up(b["09WaLiPe.2"]) == "9 9 9 e 9"
assert held == ["69MaRaJo", "VGS_X"] and sum(m.src(t) == "69MaRaJo" for t in L) == 43 and seg["69MaRaJo"] == "cm-1"
base = [l.split() for l in open(m.ROOT / "marvel4_input" / "N2O_548_trans_marvel4.txt")]
x = next(t for t in base if m.src(t) == "19LiHuWa")
assert abs(float(b[x[-1]][2]) - 2 * float(x[2])) < 1e-12
assert len(m.load("548", ov.with_name("none.tsv"))[0]) == len(base)  # no overrides -> base unchanged
y = {t[-1]: t for t in base}
assert abs(float(b["09WaLiPe.3"][2]) - 2 * float(y["09WaLiPe.3"][2])) < 1e-12
assert abs(float(b["09WaLiPe.3"][0]) - 1.00001 * float(y["09WaLiPe.3"][0])) < 1e-6
assert float(b["09WaLiPe.1"][0]) < 0  # wn_scale keeps the negation
# validation: loop 0-1-2-0 validated, dangling 3 tree, 4 only via virtual line model-anchored
g, a1, a2, a3, a4 = "0 0 1 e 0", "0 0 1 e 1", "1 1 1 e 1", "1 1 1 e 2", "0 0 1 e 2"
mk = lambda u, l, i: ["1.0", "0.1", "0.1"] + u.split() + l.split() + [i]
V = m.validation([mk(a1, g, "X.1"), mk(a2, a1, "X.2"), mk(a2, g, "X.3"), mk(a3, a2, "X.4"), mk(a4, a1, "VGS_X.1")])
assert V == {g: "validated", a1: "validated", a2: "validated", a3: "tree"}, V
assert len(m.prune([mk(a1, g, "X.1"), mk(a1, g, "X.2"), mk(a2, a1, "X.3")])) == 2  # repeat counts as loop
print("ok")
