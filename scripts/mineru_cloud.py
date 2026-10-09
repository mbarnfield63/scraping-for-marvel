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
  python3 scripts/mineru_cloud.py molecules/CS2/papers --out-dir molecules/CS2/markdown
  python3 scripts/mineru_cloud.py molecules/CS2/papers/46/a.pdf molecules/CS2/papers/b.pdf --out-dir /tmp/out
  python3 scripts/mineru_cloud.py molecules/CS2/papers --dry-run          # no network
  python3 scripts/mineru_cloud.py molecules/CS2/markdown/74MaSa --tidy    # desktop/web app export

Folders are searched recursively; all PDFs go in one batch. --tidy takes result folders already
unzipped (from the MinerU desktop or web app), renames the UUID-prefixed files to the folder name
and writes the slim content list, as a cloud download does.

Token resolution order: --token, $MINERU_API_TOKEN, then the desktop client's config.json
(--config, else $MINERU_CONFIG, else C:/Users/Marco/MinerU/config.json).
"""
import argparse
import functools
import http.client
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://mineru.net/api/v4"
# the desktop client lives on the Windows side; Path.home() under WSL is /home/<user>
DEFAULT_CONFIG = Path(os.environ.get("MINERU_CONFIG", "/mnt/c/Users/Marco/MinerU/config.json"))
POLL_SECONDS = 10
print = functools.partial(print, flush=True)  # progress shows up live in a background run


def resolve_token(cli_token, config_path):
    if cli_token:
        return cli_token
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


def poll(batch_id, token, expected, timeout):
    deadline = time.time() + timeout
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
    sys.exit(f"timeout: only {len(done)}/{expected} files finished in {timeout}s (rerun with a larger --timeout)")


def download_and_extract(name, zip_url, out_dir):
    dest = out_dir / name
    dest.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(zip_url, timeout=300) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    z.extractall(dest)
    tidy(dest, name)
    print(f"  [saved] {dest}  ({len(z.namelist())} files)")


def tidy(dest, name):
    """MinerU prefixes several files with an internal UUID; rename them to the paper's stem so
    downstream steps get a predictable <paperID>_content_list.json, then write the slim copy."""
    cl = next((f for f in dest.glob("*_content_list.json") if not f.name.startswith(name + "_")), None)
    if cl:
        uuid = cl.name[: -len("_content_list.json")]
        for f in dest.glob(f"{uuid}_*"):
            f.rename(f.with_name(name + f.name[len(uuid):]))
    cl = dest / f"{name}_content_list.json"
    if cl.exists():
        write_slim_content_list(cl)


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


def collect_pdfs(targets):
    pdfs = []
    for target in targets:
        t = Path(target)
        if t.is_dir():
            pdfs += sorted(t.rglob("*.pdf"))  # papers/ has one subfolder per isotopologue
        elif t.suffix.lower() == ".pdf":
            pdfs.append(t)
        else:
            sys.exit(f"not a PDF or directory: {target}")
    return pdfs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="+", help="PDF files and/or directories of PDFs (searched recursively)")
    ap.add_argument("--out-dir", default="mineru_out", help="where to unzip results (default: mineru_out)")
    ap.add_argument("--language", default="en", help="document language hint (default: en)")
    ap.add_argument("--token", help="API token (else $MINERU_API_TOKEN, else config.json)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to MinerU client config.json")
    ap.add_argument("--dry-run", action="store_true", help="resolve token + list PDFs, no network")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds to wait for results (default 3600)")
    ap.add_argument("--tidy", action="store_true", help="targets are unzipped app exports: rename + slim only")
    args = ap.parse_args()
    if args.tidy:
        for t in map(Path, args.target):
            tidy(t, t.name)
            print(f"  [tidied] {t}")
        return

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
    for name, zip_url in poll(batch_id, token, len(pdfs), args.timeout).items():
        if zip_url:
            download_and_extract(name, zip_url, out_dir)
    print("done.")


if __name__ == "__main__":
    main()
