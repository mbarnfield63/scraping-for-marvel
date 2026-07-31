#!/usr/bin/env python3
"""Batch OCR PDFs through the MinerU cloud API (v4) and download the results.

Flow (https://mineru.net/doc/docs/index_en/):
  1. POST /api/v4/file-urls/batch  -> batch_id + one signed upload URL per file
  2. PUT each PDF to its signed URL
  3. GET /api/v4/extract-results/batch/{batch_id}  -> per-file state + full_zip_url
  4. download + unzip each result into <out-dir>/<pdf-stem>/

Uses the "vlm" model (the one whose output we validated) with OCR on. Stdlib
only — no requests, no SDK.

Usage:
  python scripts/mineru_cloud.py molecules/CS2/papers --out-dir molecules/CS2/markdown
  python scripts/mineru_cloud.py molecules/CS2/papers/74MaSa_CS2.pdf --out-dir /tmp/out
  python scripts/mineru_cloud.py molecules/CS2/papers --dry-run   # no network

Token resolution order: --token, $MINERU_API_TOKEN, then the desktop client's
config.json (C:/Users/Marco/MinerU/config.json or --config).
"""
import argparse
import http.client
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://mineru.net/api/v4"
DEFAULT_CONFIG = Path.home() / "MinerU" / "config.json"
POLL_SECONDS = 10
POLL_TIMEOUT = 60 * 60  # 1h; a big scanned paper on the free queue can be slow


def resolve_token(cli_token, config_path):
    if cli_token:
        return cli_token
    import os
    if os.environ.get("MINERU_API_TOKEN"):
        return os.environ["MINERU_API_TOKEN"]
    # The client stores its token as a JSON string inside the "config" field.
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return json.loads(cfg["config"])["state"]["client_api_token"]


def _req(url, token, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"API {method} {url} -> {e.code}: {e.read().decode(errors='replace')}")


def request_upload_urls(pdfs, token, language):
    body = {
        "model_version": "vlm",
        "is_ocr": True,
        "enable_table": True,
        "enable_formula": True,
        "language": language,
        "files": [{"name": p.name, "data_id": p.stem} for p in pdfs],
    }
    resp = _req(f"{BASE}/file-urls/batch", token, "POST", body)
    d = resp["data"]
    return d["batch_id"], d["file_urls"]


def put_file(url, path):
    # Signed OSS URL: raw bytes, no auth header, and crucially NO Content-Type
    # (the URL is signed without one). urllib forces a Content-Type on any body,
    # which breaks the signature -> 403, so PUT via http.client for exact headers.
    u = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(u.netloc, timeout=900)
    try:
        path_qs = u.path + ("?" + u.query if u.query else "")
        body = path.read_bytes()
        conn.putrequest("PUT", path_qs, skip_host=False, skip_accept_encoding=True)
        conn.putheader("Content-Length", str(len(body)))
        conn.endheaders()
        conn.send(body)
        resp = conn.getresponse()
        resp.read()
        if resp.status not in (200, 201):
            sys.exit(f"upload {path.name} -> HTTP {resp.status}: {resp.reason}")
    finally:
        conn.close()


def poll(batch_id, token, expected):
    deadline = time.time() + POLL_TIMEOUT
    done = {}
    while time.time() < deadline:
        results = _req(f"{BASE}/extract-results/batch/{batch_id}", token)["data"]["extract_result"]
        for r in results:
            name = r.get("data_id") or r.get("file_name", "?")
            state = r.get("state")
            if state == "done" and name not in done:
                done[name] = r["full_zip_url"]
                print(f"  [done] {name}")
            elif state == "failed":
                print(f"  [FAILED] {name}: {r.get('err_msg', 'unknown error')}")
                done[name] = None
        if len(done) >= expected:
            return done
        time.sleep(POLL_SECONDS)
    sys.exit(f"timeout: only {len(done)}/{expected} files finished in {POLL_TIMEOUT}s")


def download_and_extract(name, zip_url, out_dir):
    dest = out_dir / name
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(zip_url, timeout=300) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    z.extractall(dest)
    # MinerU prefixes several files with an internal UUID; rename them to the
    # paper's stem so downstream steps get a predictable <paperID>_content_list.json.
    cl = next(dest.glob("*_content_list.json"), None)
    if cl:
        uuid = cl.name[: -len("_content_list.json")]
        for f in dest.glob(f"{uuid}_*"):
            f.rename(f.with_name(name + f.name[len(uuid):]))
        cl = dest / f"{name}_content_list.json"
        write_slim_content_list(cl)
    print(f"  [saved] {dest}  ({len(z.namelist())} files)")


def write_slim_content_list(content_list_path):
    # table_body duplicates full.md (the source of truth for table bodies) and
    # is routinely >95% of this file's bytes; strip it so downstream steps can
    # read structure (bbox/page_idx/captions) without re-paying for the tables.
    blocks = json.loads(content_list_path.read_text(encoding="utf-8"))
    for b in blocks:
        if b.get("type") == "table" and "table_body" in b:
            b["has_table_body"] = bool(b["table_body"].strip())
            del b["table_body"]
    slim_path = content_list_path.with_name(content_list_path.stem + ".slim.json")
    slim_path.write_text(json.dumps(blocks), encoding="utf-8")


def collect_pdfs(target):
    t = Path(target)
    if t.is_dir():
        return sorted(t.glob("*.pdf"))
    if t.suffix.lower() == ".pdf":
        return [t]
    sys.exit(f"not a PDF or directory: {target}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a PDF file or a directory of PDFs")
    ap.add_argument("--out-dir", default="mineru_out", help="where to unzip results (default: mineru_out)")
    ap.add_argument("--language", default="en", help="document language hint (default: en)")
    ap.add_argument("--token", help="API token (else $MINERU_API_TOKEN, else config.json)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to MinerU client config.json")
    ap.add_argument("--dry-run", action="store_true", help="resolve token + list PDFs, no network")
    args = ap.parse_args()

    pdfs = collect_pdfs(args.target)
    if not pdfs:
        sys.exit(f"no PDFs found in {args.target}")
    token = resolve_token(args.token, args.config)

    print(f"{len(pdfs)} PDF(s); token …{token[-6:]}; out-dir {args.out_dir}")
    for p in pdfs:
        print(f"  - {p.name}")
    if args.dry_run:
        print("dry-run: nothing submitted.")
        return

    print("requesting upload URLs…")
    batch_id, urls = request_upload_urls(pdfs, token, args.language)
    print(f"batch_id {batch_id}; uploading…")
    # file_urls come back in the same order as the files we submitted.
    for p, url in zip(pdfs, urls):
        put_file(url, p)
        print(f"  [up] {p.name}")

    print("polling for results…")
    out_dir = Path(args.out_dir)
    for name, zip_url in poll(batch_id, token, len(pdfs)).items():
        if zip_url:
            download_and_extract(name, zip_url, out_dir)
    print("done.")


if __name__ == "__main__":
    main()
