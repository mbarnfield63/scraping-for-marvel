"""OCR a directory of PDFs with self-hosted MinerU and write the cloud API's layout.

Runs on Hypatia inside the job (see ocr.sh), never locally. Per paper, <out-dir>/<stem>/
gets the files pipeline Steps 3-9 read from scripts/mineru_cloud.py output:
  full.md, <stem>_content_list.json (+ .slim.json), layout.json, <stem>_origin.pdf, images/

Usage: python ocr.py <in-dir> <out-dir> [--tier standard|advanced]
"""
import argparse
import json
import shutil
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from mineru_cloud import write_slim_content_list  # noqa: E402

from mineru.parser import MinerUParser, ParseResult  # noqa: E402
from mineru.parser.writer import FileBasedDataWriter  # noqa: E402
from mineru.render.content_list import render_content_list  # noqa: E402
import docvortex.render._internal.markdown.table as _md_table  # noqa: E402

# MinerU 4.x writes "simple" tables to full.md as GFM pipe tables; the cloud output and the
# extractor expect HTML <table> for every table. No setting for it, so disable the conversion.
# ponytail: private API, pinned by mineru==4.0.10; recheck on upgrade.
_md_table._convert_simple_table = lambda *a, **k: None


def ocr_one(parser, pdf, dest):
    dest.mkdir(parents=True, exist_ok=True)
    parser.parse(pdf).save(FileBasedDataWriter(str(dest)))
    # Local MinerU 4.x names its outputs differently from the cloud zip; map them back.
    (dest / "markdown.md").rename(dest / "full.md")
    (dest / "middle_json.json").rename(dest / "layout.json")
    # Render the content list from the saved middle JSON so img_path matches images/ on disk.
    saved = ParseResult.from_json((dest / "layout.json").read_text(encoding="utf-8"))
    cl = dest / f"{pdf.stem}_content_list.json"
    cl.write_text(json.dumps(render_content_list(saved.middle_json), ensure_ascii=False), encoding="utf-8")
    write_slim_content_list(cl)
    shutil.copy(pdf, dest / f"{pdf.stem}_origin.pdf")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("in_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--tier", default="standard", choices=["standard", "advanced"])
    args = ap.parse_args()

    pdfs = sorted(args.in_dir.glob("*.pdf"))
    # parse_mode="ocr" matches the cloud script's is_ocr=True.
    parser = MinerUParser(tier=args.tier, parse_mode="ocr")
    failed = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf.name}", flush=True)
        try:
            ocr_one(parser, pdf, args.out_dir / pdf.stem)
        except Exception:
            # One bad PDF must not lose the rest of the batch.
            traceback.print_exc()
            failed.append(pdf.name)
    print(f"done: {len(pdfs) - len(failed)}/{len(pdfs)} ok")
    if failed:
        sys.exit("FAILED: " + ", ".join(failed))


if __name__ == "__main__":
    main()
