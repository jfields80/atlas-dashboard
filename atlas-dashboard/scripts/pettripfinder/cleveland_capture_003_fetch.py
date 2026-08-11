"""PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003 -- deterministic fetch pass.

Fetches every ROUTED_AWAITING_CAPTURE target's official_url with the
existing SSRF-safe, honestly-identified ``RequestsPageFetcher``
(``scripts/pettripfinder/importer/fetch.py``) -- the same fetcher and the
same disclosed ``AtlasImporter/1.0`` user agent every other importer job in
this repository uses. No browser automation, no stealth headers, no
CAPTCHA/Kasada interaction: a blocked or challenge response is recorded as
exactly that, never retried past the bound below.

Writes one raw capture file per target under
``data/worker_runs/pettripfinder/cleveland-policy-capture-003/raw/<n>-<slug>.json``
(gitignored) carrying the final URL, HTTP status, decoded visible text,
html_sha256/text_sha256, and outcome. This module performs NO extraction and
asserts NO pet-policy fact -- it only proves what a plain GET returned.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.importer.fetch import RequestsPageFetcher  # noqa: E402

MANIFEST_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                  / "cleveland_unresolved_manifest.json")
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "cleveland-policy-capture-003")
RAW_DIR = RUN_DIR / "raw"

_TAG_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript|template)\b.*?</\1>")
_TAG = re.compile(r"(?s)<[^>]+>")
_WS = re.compile(r"\s+")
_JSONLD = re.compile(r'(?is)<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')


def visible_text(raw_html: str) -> str:
    """A crude but deterministic HTML->text reduction: strip script/style,
    strip tags, unescape entities, collapse whitespace. Not a renderer --
    content that only exists behind client-side JS stays absent, honestly."""
    no_script = _TAG_SCRIPT_STYLE.sub(" ", raw_html)
    no_tags = _TAG.sub(" ", no_script)
    unescaped = html.unescape(no_tags)
    normalized = unicodedata.normalize("NFKC", unescaped)
    return _WS.sub(" ", normalized).strip()


def jsonld_blocks(raw_html: str):
    out = []
    for m in _JSONLD.finditer(raw_html):
        chunk = html.unescape(m.group(1))
        try:
            out.append(json.loads(chunk))
        except Exception:  # noqa: BLE001
            continue
    return out


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    targets = [i for i in manifest["items"] if i["classification"] == "ROUTED_AWAITING_CAPTURE"]
    assert len(targets) == 74, "expected 74 ROUTED_AWAITING_CAPTURE targets, found %d" % len(targets)
    names = [t["normalized_name"] for t in targets]
    assert len(set(names)) == 74, "target set is not 74 mutually unique identities"

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fetcher = RequestsPageFetcher(min_domain_interval_seconds=2.0)

    index = []
    for n, item in enumerate(targets, start=1):
        slug = slugify(item["normalized_name"])
        out_path = RAW_DIR / ("%02d-%s.json" % (n, slug))
        if out_path.exists():
            print("%02d SKIP (already fetched) %s" % (n, slug))
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            index.append({"n": n, "slug": slug, "ok": existing["ok"],
                          "reason": existing.get("reason", ""),
                          "http_status": existing.get("http_status", 0)})
            continue

        url = item["official_url"]
        started = time.time()
        result = fetcher.fetch(url)
        elapsed = time.time() - started

        record = {
            "n": n,
            "slug": slug,
            "normalized_name": item["normalized_name"],
            "canonical_name": item["canonical_name"],
            "expected_city": item.get("city", ""),
            "expected_postal_code": item.get("postal_code", ""),
            "expected_phone": item.get("phone", ""),
            "requested_url": url,
            "ok": result.ok,
            "final_url": result.final_url,
            "http_status": result.http_status,
            "content_type": result.content_type,
            "reason": result.reason,
            "redirect_chain": list(result.redirect_chain),
            "elapsed_seconds": round(elapsed, 2),
        }
        if result.ok and result.body:
            raw_html = result.body.decode("utf-8", errors="replace")
            text = visible_text(raw_html)
            record["html_sha256"] = hashlib.sha256(result.body).hexdigest()
            record["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            record["text"] = text
            record["text_len"] = len(text)
            record["jsonld"] = jsonld_blocks(raw_html)
            has_pet_word = bool(re.search(r"\bpet", text, re.I))
            record["has_pet_word"] = has_pet_word

        out_path.write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")
        index.append({"n": n, "slug": slug, "ok": result.ok,
                      "reason": result.reason, "http_status": result.http_status})
        print("%02d %-6s status=%-4s reason=%-20s %s"
              % (n, "OK" if result.ok else "FAIL", record["http_status"] or "-",
                 record["reason"] or "-", slug))

    (RUN_DIR / "fetch_index.json").write_text(
        json.dumps(index, indent=1), encoding="utf-8")

    ok_count = sum(1 for r in index if r["ok"])
    print("\nfetched %d/%d ok" % (ok_count, len(index)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
