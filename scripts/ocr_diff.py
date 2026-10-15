#!/usr/bin/env python3
"""Page-by-page disagreements between two MinerU OCRs of one paper (Hypatia vs cloud).

  python3 scripts/ocr_diff.py markdown/<paperID> markdown_cloud/<paperID>   # writes markdown/<paperID>/ocr_diff.md
  python3 scripts/ocr_diff.py --selftest

Compares the ordered numbers inside each page's <table> blocks; tables are matched by page, not by index,
because the two OCRs split and merge tables differently. Only formatting is normalized (unicode minus,
decimal comma); a digit that differs is a disagreement. Neither OCR is ground truth: on an old scan both
agree on a wrong value about as often as either is right alone, so every listed page is settled on the crop.
"""
import difflib
import json
import re
import sys
import tempfile
from pathlib import Path

NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")
CONTEXT = 3  # numbers shown either side of a disagreement
MAX_SHOWN = 40  # disagreements listed per page; the rest are counted


def page_numbers(run_dir):
    """{page (1-based): [number tokens in reading order]} over the run's table blocks."""
    cl = next(p for p in Path(run_dir).glob("*_content_list.json") if not p.name.endswith(".slim.json"))
    pages = {}
    for item in json.loads(cl.read_text(encoding="utf-8")):
        if item.get("type") != "table":
            continue
        text = re.sub(r"<[^>]+>", " ", item.get("table_body") or "")
        text = text.replace("−", "-").replace("–", "-")
        text = re.sub(r"(\d),(\d)", r"\1.\2", text)
        pages.setdefault(item["page_idx"] + 1, []).extend(NUM.findall(text))
    return pages


def diff(local_dir, cloud_dir):
    """Markdown report and the number of pages with disagreements."""
    a, b = page_numbers(local_dir), page_numbers(cloud_dir)
    lines, bad = [], 0
    for page in sorted(set(a) | set(b)):
        x, y = a.get(page, []), b.get(page, [])
        ops = [o for o in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes() if o[0] != "equal"]
        if not ops:
            continue
        bad += 1
        lines.append(f"## Page {page}: {len(ops)} disagreement(s) (Hypatia {len(x)} numbers, cloud {len(y)})")
        for op, i1, i2, j1, j2 in ops[:MAX_SHOWN]:
            before = " ".join(x[max(0, i1 - CONTEXT):i1])
            after = " ".join(x[i2:i2 + CONTEXT])
            lines.append(f"- {op}: Hypatia `{' '.join(x[i1:i2]) or '-'}` vs cloud `{' '.join(y[j1:j2]) or '-'}`"
                         f" (after `{before}`, before `{after}`)")
        if len(ops) > MAX_SHOWN:
            lines.append(f"- ... {len(ops) - MAX_SHOWN} more on this page")
        lines.append("")
    head = [f"# OCR disagreements: {Path(local_dir).name}", "",
            f"Hypatia `{local_dir}` vs cloud `{cloud_dir}`. {bad} page(s) disagree."
            " Settle each listed value on the page crop; neither OCR is ground truth.", ""]
    return "\n".join(head + lines), bad


def selftest():
    tmp = Path(tempfile.mkdtemp())

    def run(name, tables):
        d = tmp / name
        d.mkdir()
        items = [{"type": "table", "page_idx": p, "table_body": body} for p, body in tables]
        (d / f"x_content_list.json").write_text(json.dumps(items))
        (d / f"x_content_list.slim.json").write_text("[]")  # must be ignored
        return d

    loc = run("loc", [(0, "<table><tr><td>818.879</td><td>2020.024</td></tr></table>"),
                      (1, "<table><tr><td>944.476</td><td>−1</td></tr></table>")])
    cld = run("cld", [(0, "<table><tr><td>818,879</td></tr></table><table><tr><td>2020.024</td></tr></table>"),
                      (1, "<table><tr><td>944.976</td><td>-1</td></tr></table>")])
    report, bad = diff(loc, cld)
    assert bad == 1, report  # page 1: comma and the table split are formatting; page 2: a real digit
    assert "## Page 2" in report and "`944.476` vs cloud `944.976`" in report and "## Page 1" not in report
    print("ocr_diff selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit()
    local, cloud = sys.argv[1:3]
    report, bad = diff(local, cloud)
    (Path(local) / "ocr_diff.md").write_text(report, encoding="utf-8")
    print(f"DIFF {Path(local).name}: {bad} page(s) where Hypatia and cloud disagree -> {Path(local) / 'ocr_diff.md'}")
