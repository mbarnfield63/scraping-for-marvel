"""Apply a per-paper N2O bandmap: relabel extracted rows to the 24TeFuYu (P l N e/f J) scheme.

Reads molecules/N2O/bandmap/<paper>.tsv, whose first line is
    # spec: {"files": [...], "key_cols": [...], "key_note_regex": "...", "branch_col": "...",
    #        "J_col": "...", "J_kind": "lower"|"upper", "J_upper_col": "...", "J_lower_col": "...",
    #        "unc": {"mode": "as_extracted"|"set", "value": x, "blended_value": y, "blended_regex": "...",
#                "blended_factor": f (as_extracted only), "blended_base": b (as_extracted only:
    #                 a blended row with a blank uncertainty gets b * f), "base": b0 (any row with a
    #                 blank uncertainty gets b0, x f if blended), "reason": "..."},
    #        "recal": 1.0, "isos": ["456", ...] (optional filter), "J_abs": true (optional: J_col holds -J for P),
    #        "branch_cell_regex": "^([PQR])\\s*(\\d+)\\s*([ef])$" (optional: branch, J and ef in one cell),
    #        "wn_from_note_regex": "..." (optional: one capture group in notes, e.g. a printed
    #        "1277.208(7)"; parentheses are stripped and the result replaces the wavenumber)}
followed by a TSV with columns
    key  P_u l_u N_u ef_u  P_l l_l N_l ef_l  action  evidence
(ef = e | f | auto; action = keep | drop:<reason>). `key` is the row's key_cols values joined by '|'
(plus the key_note_regex capture, if given). Optional columns: `branch` (P/Q/R: the line applies
to that branch only; blank = all branches), `note` (text appended to every matched row's notes),
and `J_shift` + `J_shift_range` (integer added to both J_upper and J_lower for a misprinted J;
range "a-b" of the J as printed in J_col/J_upper_col, inclusive; blank = all rows of that key).
Re-running replaces this paper's earlier output/*.txt for the same isotopologue.

Optional spec "unit": "kHz" | "MHz" | "GHz" (default "cm-1"), and "unc_unit" when the extracted
uncertainty is in a different unit (converted into "unit", logged). Wavenumber and uncertainty stay in that unit in
every output; only the obs-Ames check converts (c = 29979.2458 MHz per cm-1). Each run records
"<paper> <unit>" in segments/N2O_<iso>_segment.txt (the MARVEL segment file).

Optional bandmap/<paper>_fixes.tsv (columns iso, orig_id, wn, evidence): replaces the printed wavenumber of
proven typos (e.g. a dropped digit), logged in notes. csv/ stays untouched.

Optional bandmap/<paper>_rows.tsv (columns iso, orig_id, efu, efl, action, evidence): per-row overrides.
efu/efl select which output copy of that extracted row the line applies to (blank = any). action is
`ef:XY` (replace the parity pair with upper X, lower Y; the row is then never removed as a reprint) or
`drop:<reason>` (row stays in csv_polyad with flag DROP and the reason in notes, but not in output/).

Optional spec "wn_shift": {"value": d, "min": a, "max": b, "reason": "..."}: adds d to printed wavenumbers
in [a, b] (a published recalibration of part of a paper's range), logged in notes.
Optional unc "label" (mode "set"): text for the notes entry (default "24TeFuYu adopted").

csv/ is read-only. Writes csv_polyad/<paper>_<iso>.csv (new labels + original labels + obs-Ames)
and output/N2O_<iso>_<paper>_<stamp>.txt (canonical MARVEL: wn unc P l N ef J P l N ef J ID).

Usage: python scripts/n2o_apply.py <paper>
"""
import csv
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "molecules" / "N2O"
AMES = ROOT / "reference_papers" / "Ames1_levels"
DJ = {"P": -1, "Q": 0, "R": 1}
OUTLIER = 0.03  # cm-1 from the per-band fit; ponytail: fixed threshold, scale with stated uncertainty if needed  # J_upper - J_lower


def read_rows(path, delimiter=","):
    with open(path, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader((l for l in f if not l.startswith("#")), delimiter=delimiter))


def load_bandmap(paper):
    lines = (ROOT / "bandmap" / f"{paper}.tsv").read_text(encoding="utf-8").splitlines()
    spec = json.loads(lines[0].split("spec:", 1)[1])
    body = [l for l in lines[1:] if l and not l.startswith("#")]
    head = body[0].split("\t")
    bm = {}
    for l in body[1:]:
        r = dict(zip(head, l.split("\t")))
        k = (r["key"], r.get("branch", "").strip().upper())
        if k in bm:
            print("WARNING duplicate bandmap key", k)
        bm[k] = r
    return spec, bm


def row_key(row, spec):
    parts = [row[c].strip() for c in spec["key_cols"]]
    if spec.get("key_note_regex"):
        m = re.search(spec["key_note_regex"], row.get("notes", ""))
        if not m:
            print("WARNING key_note_regex no match:", row.get("id"))
        parts.append(m.group(1) if m else "")
    return "|".join(parts)


def row_J(row, spec):
    """(branch letter, J_upper, J_lower)."""
    if spec.get("J_kind") == "pair":
        Ju, Jl = int(row[spec["J_upper_col"]]), int(row[spec["J_lower_col"]])
        return {-1: "P", 0: "Q", 1: "R"}[Ju - Jl], Ju, Jl
    br = row[spec["branch_col"]].strip().upper()[:1]
    J = int(row[spec["J_col"]])
    if spec.get("J_abs"):  # some tables store P(J) as -J
        J = abs(J)
    elif J < 0:
        print("WARNING negative J (set spec J_abs?):", row.get("id"))
    if spec["J_kind"] == "lower":
        return br, J + DJ[br], J
    return br, J, J - DJ[br]


def parities(ef_u, ef_l, l_u, l_l, br):
    """e/f rules (marvel-pipeline format.md, N2O section). Returns list of (ef_u, ef_l) pairs and a note."""
    if ef_u != "auto" and ef_l != "auto":
        return [(ef_u, ef_l)], ""
    flip = {"e": "f", "f": "e"}
    same = br in "PR"
    if l_l == 0 or l_u == 0:
        known = "e"
        other = known if same else flip[known]
        return ([(other, "e")] if l_l == 0 else [("e", other)]), "ef: selection rule"
    # both l > 0, parity not labelled: unresolved, duplicate as both components
    pairs = [("e", "e"), ("f", "f")] if same else [("e", "f"), ("f", "e")]
    return pairs, "parity: unresolved"


class AmesTracker:
    """Ames-1 level of a (P,l,N) state at any J, tracked upward from J=l in its parity block."""

    def __init__(self, iso, states):
        self.states = {(r["P"], r["l"], r["N"]): float(r["Eiso"]) for r in states}
        self.lev = {}
        f = next((AMES / iso).glob("*.dat"))
        with open(f) as fh:
            for line in fh:
                t = line.split()
                self.lev.setdefault((int(t[0]), int(t[1])), []).append(float(t[3]))
        for v in self.lev.values():
            v.sort()
        self.cache = {}

    def block(self, J, ef):
        e = 2 if J % 2 == 0 else 1
        return (J, e if ef == "e" else 3 - e)

    def energy(self, P, l, N, ef, J):
        key = (P, l, N, ef)
        if key not in self.cache:
            E0 = self.states.get((str(P), str(l), str(N)))
            if E0 is None:
                return None
            track, E, B = {l: E0}, E0, 0.42
            # ponytail: nearest-level tracking; jumps at avoided crossings show up as obs-Ames outliers
            for j in range(l + 1, 151):
                cands = self.lev.get(self.block(j, ef))
                if not cands:
                    break
                pred = E + 2 * B * j
                E_new = min(cands, key=lambda x: abs(x - pred))
                B = max(0.3, min(0.5, (E_new - E) / (2 * j)))
                E = track[j] = E_new
            if ef == "f" and l > 0:
                track[l] = min(self.lev[self.block(l, "f")], key=lambda x: abs(x - E0))
            self.cache[key] = track
        return self.cache[key].get(J)


def write_segment(iso, paper, unit):
    """Upsert '<paper> <unit>' in segments/N2O_<iso>_segment.txt (MARVEL segment file)."""
    path = ROOT / "segments" / f"N2O_{iso}_segment.txt"
    path.parent.mkdir(exist_ok=True)
    seg = dict(l.split() for l in path.read_text().splitlines() if l.strip()) if path.exists() else {}
    seg[paper] = unit
    path.write_text("".join(f"{k} {v}\n" for k, v in sorted(seg.items())))


def is_own_output(path):
    """True only for this script's format: 13 columns, no header, e/f in columns 6 and 11."""
    f = path.read_text().split("\n", 1)[0].split("\t")
    return len(f) == 13 and f[5] in ("e", "f") and f[10] in ("e", "f")


def main(paper):
    spec, bm = load_bandmap(paper)
    rows = []
    for fn in spec["files"]:
        rows += read_rows(ROOT / "csv" / fn)
    if spec.get("branch_cell_regex"):  # e.g. "R  8e" in one cell: groups (branch, J[, ef]) -> branch_col, J_col[, "ef"]
        for r in rows:
            m = re.match(spec["branch_cell_regex"], r[spec["branch_col"]].strip())
            if not m:
                print("WARNING branch_cell_regex no match:", r.get("id"))
                continue
            r[spec["branch_col"]], r[spec["J_col"]] = m.group(1), m.group(2)
            if m.lastindex >= 3:
                r["ef"] = m.group(3)
    if spec.get("isos"):  # optional: only these isotopologues (e.g. skip 446, covered by 24TeFuYu)
        rows = [r for r in rows if r["iso"] in spec["isos"]]
    unc = spec.get("unc", {"mode": "as_extracted"})
    recal = float(spec.get("recal", 1.0))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unit = spec.get("unit", "cm-1")
    in_mhz = {"kHz": 1e-3, "MHz": 1.0, "GHz": 1e3, "cm-1": 29979.2458}
    to_cm = in_mhz[unit] / in_mhz["cm-1"]
    unc_unit = spec.get("unc_unit", unit)
    fx_path = ROOT / "bandmap" / f"{paper}_fixes.tsv"
    fixes = {(r["iso"], r["orig_id"]): r for r in read_rows(fx_path, "\t")} if fx_path.exists() else {}
    fix_used = set()
    rw_path = ROOT / "bandmap" / f"{paper}_rows.tsv"
    overrides = {}
    for r in (read_rows(rw_path, "\t") if rw_path.exists() else []):
        overrides.setdefault((r["iso"], r["orig_id"]), []).append(r)
    ov_used = set()
    shift = spec.get("wn_shift")
    by_iso, log = {}, {"unmapped": 0, "dropped": 0, "J<l": 0, "split_added": 0, "reprint_removed": 0}
    seen, dup_ids = {}, set()
    for row in rows:
        key = row_key(row, spec)
        br0 = row_J(row, spec)[0]
        m = bm.get((key, br0)) or bm.get((key, ""))
        if m is None:
            log["unmapped"] += 1
            print("UNMAPPED", key, row.get("id"))
            continue
        if m["action"] != "keep":
            log["dropped"] += 1
            continue
        br, Ju, Jl = row_J(row, spec)
        j_note = ""
        if m.get("J_shift", "").strip():
            jp = int(row[spec.get("J_col") or spec["J_upper_col"]])
            rng = m.get("J_shift_range", "").strip()
            lo, hi = (int(x) for x in rng.split("-")) if rng else (jp, jp)
            if lo <= jp <= hi:
                d = int(m["J_shift"])
                Ju, Jl = Ju + d, Jl + d
                j_note = f"J: shifted {d:+d} (printed J {jp}; bandmap evidence: {m.get('evidence', '')})"
        ovs = overrides.get((row["iso"], row.get("id", "")), [])
        ef_ov = next((o for o in ovs if o["action"].startswith("ef:")), None)
        dk = (row["iso"], key, br, Ju, Jl, ef_ov["action"] if ef_ov else "")
        dup_of = seen.get(dk)
        if dup_of and abs(float(dup_of["transition_wavenumber"]) - float(row["transition_wavenumber"])) < 1e-9:
            log["reprint_removed"] += 1  # same measurement printed twice: keep the first
            print(f"REPRINT removed {key} {br} Ju={Ju}: {row.get('id')} = {dup_of.get('id')}")
            continue
        if dup_of:
            print(f"DUPLICATE {key} {br} Ju={Ju}: {dup_of.get('id')} and {row.get('id')} (different wavenumbers, both kept)")
            dup_ids.update((dup_of.get("id"), row.get("id")))
        else:
            seen[dk] = row
        Pu, lu, Nu, Pl, ll, Nl = (int(m[k]) for k in ("P_u", "l_u", "N_u", "P_l", "l_l", "N_l"))
        if Ju < lu or Jl < ll:
            log["J<l"] += 1
            continue
        pairs, efnote = parities(m["ef_u"], m["ef_l"], lu, ll, br)
        if ef_ov:
            ov_used.add(id(ef_ov))
            pairs = [(ef_ov["action"][3], ef_ov["action"][4])]
            efnote = f"ef: set to {pairs[0][0]}<-{pairs[0][1]} (rows file: {ef_ov['evidence']})"
        log["split_added"] += len(pairs) - 1
        wn = float(row["transition_wavenumber"])
        wn_note = ""
        if spec.get("wn_from_note_regex"):
            mt = re.search(spec["wn_from_note_regex"], row.get("notes", ""))
            if not mt:
                print(f"WARNING wn_from_note_regex miss: {row.get('id')}")
            else:
                wn_new = float(mt.group(1).replace("(", "").replace(")", ""))
                wn_note = f"wn: {wn_new} from printed {mt.group(1)!r} (extracted {row['transition_wavenumber']})"
                wn = wn_new
        fx = fixes.get((row["iso"], row.get("id", "")))
        if fx:
            fix_used.add((fx["iso"], fx["orig_id"]))
            wn_note = f"wn: {fx['wn']} replaces printed {row['transition_wavenumber']} (fixes file: {fx['evidence']})"
            wn = float(fx["wn"])
        if shift and shift["min"] <= wn <= shift["max"]:
            wn = round(wn + shift["value"], 9)
            wn_note = (wn_note + "; " if wn_note else "") + f"wn: {shift['value']:+g} recalibration ({shift['reason']})"
        wn *= recal
        u_orig = row["uncertainty"]
        u = u_orig
        if u and unc_unit != unit:
            u = "%g" % (float(u) * in_mhz[unc_unit] / in_mhz[unit])
            notes_unit = f"unc: {u_orig} {unc_unit} = {u} {unit}"
        else:
            notes_unit = ""
        u_base = u  # extracted uncertainty in the output unit
        blended = unc.get("blended_regex") and re.search(unc["blended_regex"], row.get("notes", ""))
        if unc["mode"] == "set":
            u = str(unc["value"])
            if blended:
                u = str(unc["blended_value"])
        elif blended and unc.get("blended_factor") and u:
            u = "%g" % (float(u) * float(unc["blended_factor"]))
        elif blended and unc.get("blended_factor") and unc.get("blended_base"):
            u = "%g" % (float(unc["blended_base"]) * float(unc["blended_factor"]))
        if not u and unc.get("base"):  # paper states no per-line value: paper-derived base (reason in spec)
            u = "%g" % (float(unc["base"]) * (float(unc.get("blended_factor", 1)) if blended else 1))
        notes = [row.get("notes", "")]
        if j_note:
            notes.append(j_note)
        if notes_unit:
            notes.append(notes_unit)
        if efnote:
            notes.append(efnote)
        if m.get("note"):
            notes.append(m["note"])
        if unc["mode"] != "as_extracted":
            notes.append(f"unc: {unc.get('label', '24TeFuYu adopted')} {u} (extracted: {u_orig or 'blank'})")
        elif u != u_base and not u_orig and unc.get("base"):
            notes.append(f"unc: {u} from paper-derived base {unc['base']}{' x' + str(unc.get('blended_factor')) + ' blended' if blended else ''} ({unc.get('reason', '')}; extracted: blank)")
        elif u != u_base:
            notes.append(f"unc: x{unc['blended_factor']} for blended/overlapped line ({unc.get('reason', 'user decision')}; extracted: {u_orig or 'blank'})")
        if wn_note:
            notes.append(wn_note)
        if recal != 1.0:
            notes.append(f"recal: x{recal} (24TeFuYu)")
        for efu, efl in pairs:
            drop = next((o for o in ovs if o["action"].startswith("drop:") and o["efu"] in ("", efu)
                         and o["efl"] in ("", efl)), None)
            nts = "; ".join(n for n in notes if n)
            if drop:
                ov_used.add(id(drop))
                nts += f"; {drop['action']} (rows file: {drop['evidence']})"
            by_iso.setdefault(row["iso"], []).append(dict(
                wn=wn, unc=u, u_orig=u_orig, Pu=Pu, lu=lu, Nu=Nu, efu=efu, Ju=Ju,
                Pl=Pl, ll=ll, Nl=Nl, efl=efl, Jl=Jl, key=key, branch=br, drop=bool(drop),
                orig_id=row.get("id", ""), notes=nts))

    for out in by_iso.values():
        for r in out:
            if r["orig_id"] in dup_ids:
                r["notes"] += "; DUP_DIFF: same (band, branch, J) printed twice with different wavenumbers in source"
    states_dir = ROOT / "states"
    for iso in {r["iso"] for r in rows} - set(by_iso):  # every row of this iso dropped: clear stale outputs
        (ROOT / "csv_polyad" / f"{paper}_{iso}.csv").unlink(missing_ok=True)
        for old in (ROOT / "output").glob(f"N2O_{iso}_{paper}_*.txt"):
            if is_own_output(old):
                old.unlink()
        print(f"{paper} {iso}: 0 rows kept, stale outputs removed")
    for iso, out in by_iso.items():
        lines = [l for l in open(states_dir / f"{iso}_states.tsv") if not l.startswith("#")]
        st = list(csv.DictReader(lines, delimiter="\t"))
        tr = AmesTracker(iso, st)
        for r in out:
            Eu = tr.energy(r["Pu"], r["lu"], r["Nu"], r["efu"], r["Ju"])
            El = tr.energy(r["Pl"], r["ll"], r["Nl"], r["efl"], r["Jl"])
            r["oma"] = r["wn"] * to_cm - (Eu - El) if Eu is not None and El is not None else None
        # per-band spread of obs-Ames
        bands = {}
        for r in out:
            if r["oma"] is not None:
                bands.setdefault(r["key"], []).append(r["oma"])
        # per-band linear fit of obs-Ames in x = Ju(Ju+1): removes Ames-1's smooth J drift
        fit = {}
        for k in bands:
            band = [r for r in out if r["key"] == k and r["oma"] is not None]
            pts = [(r["Ju"] * (r["Ju"] + 1), r["oma"]) for r in band if not r["drop"]] or \
                  [(r["Ju"] * (r["Ju"] + 1), r["oma"]) for r in band]
            xs, ys = zip(*pts)
            if len(set(xs)) > 2:
                slope, icpt = statistics.linear_regression(xs, ys)
            else:
                slope, icpt = 0.0, statistics.median(ys)
            fit[k] = (icpt, slope)
        med = {k: statistics.median(v) for k, v in bands.items()}
        for r in out:
            r["flag"] = ""
            if r["drop"]:
                r["flag"] = "DROP"
                if r["oma"] is not None:
                    r["fit_res"] = r["oma"] - fit[r["key"]][0] - fit[r["key"]][1] * r["Ju"] * (r["Ju"] + 1)
            elif r["oma"] is None:
                r["flag"] = "NO_AMES"
            else:
                a, b = fit[r["key"]]
                r["fit_res"] = r["oma"] - a - b * r["Ju"] * (r["Ju"] + 1)
                if abs(r["fit_res"]) > OUTLIER:
                    r["flag"] = "OMA_OUTLIER"
        out.sort(key=lambda r: r["wn"])
        for i, r in enumerate(out, 1):
            r["id"] = f"{paper}.{i}"
        cols = ["wn", "unc", "Pu", "lu", "Nu", "efu", "Ju", "Pl", "ll", "Nl", "efl", "Jl", "id",
                "oma", "fit_res", "flag", "u_orig", "key", "branch", "orig_id", "notes"]
        (ROOT / "csv_polyad").mkdir(exist_ok=True)
        with open(ROOT / "csv_polyad" / f"{paper}_{iso}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, cols)
            w.writeheader()
            for r in out:
                w.writerow({c: ("%.5f" % r[c] if c in ("oma", "fit_res") and r.get(c) is not None else r.get(c, ""))
                            for c in cols})
        (ROOT / "output").mkdir(exist_ok=True)
        for old in (ROOT / "output").glob(f"N2O_{iso}_{paper}_*.txt"):
            if is_own_output(old):  # never touch older outputs (e.g. Herzberg format)
                old.unlink()
        out_path = ROOT / "output" / f"N2O_{iso}_{paper}_{stamp}.txt"
        if not any(r["unc"] and not r["drop"] for r in out):
            out_path = "(no output file: every row lacks an uncertainty)"
        else:
            with open(out_path, "w") as f:
                for r in out:
                    if not r["unc"] or r["drop"]:
                        continue  # no uncertainty (manual review) or dropped by the rows file: stays in csv_polyad only
                    f.write("\t".join(str(r[c]) for c in
                                      ["wn", "unc", "Pu", "lu", "Nu", "efu", "Ju", "Pl", "ll", "Nl", "efl", "Jl", "id"]) + "\n")
        n_out = sum(1 for r in out if r["flag"] == "OMA_OUTLIER")
        print(f"{paper} {iso}: {len(out)} rows, {n_out} OMA_OUTLIER, {sum(1 for r in out if not r['unc'])} no-unc, "
              f"{sum(1 for r in out if r['drop'])} dropped (rows file)")
        print(f"  wrote {out_path}\n  wrote {ROOT / 'csv_polyad' / f'{paper}_{iso}.csv'}")
        if not isinstance(out_path, str):  # only sources that reach output/
            write_segment(iso, paper, unit)
        print(f"  {'band key':45s} {'n':>5s} {'median':>8s} {'min':>8s} {'max':>8s} {'fit_rms':>7s} {'slope/J(J+1)':>12s} out")
        for k in sorted(bands):
            v = bands[k]
            res = [r["fit_res"] for r in out if r["key"] == k and "fit_res" in r]
            rms = (sum(x * x for x in res) / len(res)) ** 0.5
            nout = sum(1 for r in out if r["key"] == k and r["flag"] == "OMA_OUTLIER")
            print(f"  {k:45s} {len(v):5d} {med[k]:+8.4f} {min(v):+8.4f} {max(v):+8.4f} {rms:7.4f} {fit[k][1]:+12.2e} {nout}")
    for fid in set(fixes) - fix_used:
        print("WARNING fixes row matched no extracted row:", fid)
    for o in (o for v in overrides.values() for o in v if id(o) not in ov_used):
        print("WARNING rows-file line matched nothing:", o["iso"], o["orig_id"], o["efu"], o["efl"], o["action"])
    print("log:", log)


if __name__ == "__main__":
    main(sys.argv[1])
