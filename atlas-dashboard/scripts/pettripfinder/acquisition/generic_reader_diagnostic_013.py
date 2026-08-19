"""PTF-GENERIC-READER-FIRECRAWL-DIAGNOSTIC-013 -- provider, or reader?

Four brands have been decided. Three moved to Firecrawl carrying a brand reader
built for their markup. Motel 6 was rejected, and its two "successes" were the
string "Pets Allowed Coin Laundry" -- an amenity checkbox. Motel 6, Red Roof and
every Milwaukee independent share one thing: they all use the ``generic``
reader. So the Motel 6 rejection cannot distinguish "Firecrawl did not bring the
policy" from "the generic reader could not find it".

This work order measures that distinction and changes nothing.

WHY THE LAYERS MUST BE MEASURED SEPARATELY
-------------------------------------------
The trap is to run the reader, see nothing, and conclude the provider failed.
So LAYER B searches the RAW DOCUMENT for policy language WITHOUT using the
reader at all -- its own concept scan over the whole page text, not the reader's
locator. Only then does LAYER C run the reader on the same bytes and ask
whether it recovered what Layer B proved was there.

A document where Layer B finds a fee, a weight and a count, and the reader finds
nothing, is a READER_MISS. A document where Layer B finds nothing is
PROVIDER_LIMITED, and no reader work would recover it. Averaging those two into
one "Firecrawl success rate" is precisely the misleading number this exists to
prevent.

DIAGNOSTIC ACQUISITION IS DELIBERATELY GATE-FREE
------------------------------------------------
``capture_property`` persists an artifact only for a VALID capture, which is why
two of the four Motel 6 properties left no document behind: the very failures
worth diagnosing are the ones that erase their own evidence. So diagnostic mode
calls ``firecrawl_capture.fetch`` directly and keeps the document whatever the
gates would have said about it. The gates are then applied as ANALYSIS rather
than as a filter.

Nothing here touches routes.json, and both Bright Data providers are
unreachable by construction: this module never imports a Bright Data capture
path and a test asserts it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY         # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR          # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC        # noqa: E402

WORK_ORDER = "PTF-GENERIC-READER-FIRECRAWL-DIAGNOSTIC-013"
MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "generic-reader-diagnostic-013"
QUEUE = REPORTS / "milwaukee-wi_policy_acquisition_queue_001.json"

#: The cap this work order set. The universe is larger, so it binds.
COHORT_CAP = 15
MAX_INDEPENDENTS = 10

#: Documents already on disk that can be reused rather than re-bought.
REUSABLE = REPO / "data" / "acquisition" / "motel6-firecrawl-decision-012"

PRIOR_JOURNALS = (
    "milwaukee-router-001/milwaukee-router-001/journal.jsonl",
    "milwaukee-resume-007/milwaukee-resume-007/journal.jsonl",
    "milwaukee-resume-007/milwaukee-wyndham-008/journal.jsonl",
    "milwaukee-ihg-009/milwaukee-ihg-009/journal.jsonl",
)


# --------------------------------------------------------------------------- #
# Cohort
# --------------------------------------------------------------------------- #

def generic_universe() -> List[Dict]:
    """Every remaining Milwaukee property whose route uses the generic reader."""
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    routable = [r for r in doc["items"]
                if r["queue_state"] == "QUEUED" and not r.get("brand_excluded")]
    done = set()
    for rel in PRIOR_JOURNALS:
        path = REPO / "data" / "acquisition" / rel
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    done.add(json.loads(line)["identity_key"])
    out = []
    for row in routable:
        if row["identity_key"] in done:
            continue
        route = REGISTRY.resolve(brand=row["brand"], url=row["official_url"],
                                 identity_key=row["identity_key"])
        if route.reader != "generic":
            continue
        entry = dict(row)
        entry["reader"] = route.reader
        entry["class"] = classify(row["brand"])
        entry["domain"] = urlparse(row["official_url"]).netloc.lower()
        out.append(entry)
    return sorted(out, key=lambda r: (r["class"], r["identity_key"]))


def classify(brand: str) -> str:
    if brand in ("MOTEL6", "RED_ROOF"):
        return brand
    if brand.startswith("INDEP:"):
        return "INDEPENDENT"
    return brand


def cohort() -> Dict:
    """The diagnostic cohort, chosen by a rule fixed before any result is seen.

    Motel 6 and Red Roof enter whole -- they are the brands with a decision
    behind them. Independents are taken in identity-key order up to the cap.
    Every independent sits on its own domain, so any subset of ten carries ten
    distinct domains and no ordering choice can maximise domain variation more
    than another; the rule is therefore chosen for determinism rather than for
    a selection effect it cannot have.
    """
    universe = generic_universe()
    motel6 = [r for r in universe if r["class"] == "MOTEL6"]
    redroof = [r for r in universe if r["class"] == "RED_ROOF"]
    independents = [r for r in universe if r["class"] == "INDEPENDENT"]

    chosen_independents = independents[:MAX_INDEPENDENTS]
    excluded = independents[MAX_INDEPENDENTS:]
    selected = motel6 + redroof + chosen_independents
    if len(selected) > COHORT_CAP:
        raise SystemExit("cohort %d exceeds the cap %d" % (len(selected), COHORT_CAP))
    return {
        "universe_total": len(universe),
        "universe_by_class": dict(Counter(r["class"] for r in universe)),
        "selection_method": (
            "MOTEL6 and RED_ROOF enter whole. INDEPENDENT rows are sorted by "
            "identity_key ascending and the first %d are taken, to respect the "
            "%d-property cap. Every independent is on a distinct domain, so "
            "any subset of that size carries the same domain variation and the "
            "ordering cannot select for expected success."
            % (MAX_INDEPENDENTS, COHORT_CAP)),
        "selected": selected,
        "excluded_by_cap": [r["identity_key"] for r in excluded],
        "distinct_domains": len({r["domain"] for r in selected}),
    }


# --------------------------------------------------------------------------- #
# LAYER B -- what the RAW DOCUMENT contains, independent of the reader
# --------------------------------------------------------------------------- #

#: Concept classes. A policy is a statement with terms; a chip is a label.
_CONCEPTS: Dict[str, re.Pattern] = {
    "allow_signal": re.compile(
        r"\bpets?\s+(?:are\s+)?(?:allowed|welcome|permitted)\b|\bpet[-\s]?friendly\b",
        re.IGNORECASE),
    "refuse_signal": re.compile(
        r"\bno\s+pets?\b|\bpets?\s+(?:are\s+)?not\s+(?:allowed|permitted)\b"
        r"|\bpets?\s+allowed\s*:?\s*no\b", re.IGNORECASE),
    "fee": re.compile(
        r"\bpet\s+(?:fee|charge|rate)\b|\bfee\s+(?:of\s+)?\$?\d|\$\s*\d+"
        r"|\b\d+(?:\.\d{2})?\s*(?:usd|dollars?)\b", re.IGNORECASE),
    "basis": re.compile(r"\bper\s+(?:night|stay|day|week)\b|\bnightly\b",
                        re.IGNORECASE),
    "weight": re.compile(r"\b\d+\s*(?:lbs?|pounds?|kgs?)\b|\bweight\s+limit\b",
                         re.IGNORECASE),
    "count": re.compile(r"\b\d+\s*pets?\s+(?:max|maximum|per)\b"
                        r"|\bmax(?:imum)?\s+(?:of\s+)?\d+\s*pets?\b"
                        r"|\bpet\s+limit\b", re.IGNORECASE),
    "species": re.compile(r"\bdogs?\b|\bcats?\b", re.IGNORECASE),
    "breed": re.compile(r"\bbreed\s+restrict|\baggressive\s+breed", re.IGNORECASE),
    "unattended": re.compile(r"\bunattended\b|\bleft\s+alone\s+in\s+the\s+room\b",
                             re.IGNORECASE),
    "deposit": re.compile(r"\b(?:non-?\s?refundable|refundable)\b|\bdeposit\b",
                          re.IGNORECASE),
    "service_animal": re.compile(r"\bservice\s+animals?\b|\bada\b", re.IGNORECASE),
}

#: Concepts that make a statement actionable. ``species`` and
#: ``service_animal`` are excluded: a page mentioning dogs, or stating the legal
#: service-animal position, has not thereby stated a pet policy.
_SUBSTANTIVE = ("fee", "basis", "weight", "count", "breed", "unattended", "deposit")


#: How close a term must sit to a pet word to be ABOUT pets.
_PET_WORD_RE = re.compile(r"\bpets?\b|\bdogs?\b|\bcats?\b|\banimals?\b",
                          re.IGNORECASE)
_PET_PROXIMITY_CHARS = 120


def _in_pet_context(text: str, start: int, end: int) -> bool:
    """Is this term about a pet, or merely on the same page as one?

    Added after the first run of this diagnostic reported PARTIAL_POLICY_PRESENT
    for two Motel 6 pages and one independent whose only "fee" was a ROOM RATE
    -- "Best rate", "My6 member rate", a bare $NN in a booking widget. That is
    the guest-room-rate mistake this corpus has made before, reproduced inside
    the tool built to detect misreadings. A term with no pet word within reach
    is not evidence of a pet policy.
    """
    window = text[max(0, start - _PET_PROXIMITY_CHARS):end + _PET_PROXIMITY_CHARS]
    return bool(_PET_WORD_RE.search(window))


def scan_document(text: str) -> Dict:
    """What policy language exists in this document, reader or no reader.

    Substantive terms must sit in pet context; signal concepts need not, since
    they contain the pet word themselves.
    """
    hits: Dict[str, List[str]] = {}
    for name, pattern in _CONCEPTS.items():
        needs_context = name in _SUBSTANTIVE
        found = []
        for match in pattern.finditer(text):
            if needs_context and not _in_pet_context(text, match.start(), match.end()):
                continue
            start = max(0, match.start() - 70)
            end = min(len(text), match.end() + 70)
            found.append(" ".join(text[start:end].split()))
            if len(found) >= 3:
                break
        if found:
            hits[name] = found
    return hits


def classify_presence(text: str, *, identity_ok: bool) -> Dict:
    """FULL / PARTIAL / AMENITY_ONLY / NO_POLICY / UNUSABLE, with the snippets.

    An amenity label alone is never FULL. That is the whole point: "Pets
    Allowed" next to "Coin Laundry" satisfies an allow signal and nothing else,
    and treating it as a policy is the error this diagnostic was opened for.
    """
    if not identity_ok or not text.strip():
        return {"presence": "UNUSABLE_DOCUMENT", "concepts": {},
                "substantive_concepts": [],
                "why": "identity, navigation or hydration prevents a determination"}

    hits = scan_document(text)
    substantive = [c for c in _SUBSTANTIVE if c in hits]
    has_signal = "allow_signal" in hits or "refuse_signal" in hits

    if not has_signal and not substantive:
        presence, why = "NO_POLICY_PRESENT", "no pet-policy language of any kind"
    elif has_signal and len(substantive) >= 2:
        presence, why = ("FULL_POLICY_PRESENT",
                         "an allow/refuse signal plus %d actionable terms: %s"
                         % (len(substantive), ", ".join(substantive)))
    elif has_signal and len(substantive) == 1:
        presence, why = ("PARTIAL_POLICY_PRESENT",
                         "an allow/refuse signal plus one actionable term: %s"
                         % substantive[0])
    elif has_signal:
        presence, why = ("AMENITY_ONLY",
                         "a pets-allowed signal with no actionable term "
                         "anywhere in the document")
    else:
        presence, why = ("PARTIAL_POLICY_PRESENT",
                         "actionable terms (%s) with no explicit allow or "
                         "refuse statement" % ", ".join(substantive))
    return {"presence": presence, "concepts": hits,
            "substantive_concepts": substantive, "why": why}


# --------------------------------------------------------------------------- #
# LAYER C -- what the GENERIC READER recovers from the same bytes
# --------------------------------------------------------------------------- #

def read_generically(html: str) -> Dict:
    """The generic reader's own path: static walk, then parse."""
    hit = UC.locate_policy_in_html(html)
    block = hit.text if hit.found else ""
    reading = PR.parse(block, strategy="generic_diagnostic") if block else None
    extraction = (dict(PR.to_extraction(reading, location="").extraction)
                  if reading else {})
    return {"block_found": bool(block), "block": block,
            "block_chars": len(block), "strategy": hit.strategy,
            "candidates_considered": hit.candidates_considered,
            "extraction": extraction}


_POLICY_FIELDS = ("pet_fee", "fee_amount", "fee_basis", "weight_limit",
                  "pet_count_limit", "species_allowed", "deposit", "fee_cap")


#: A URL that was never going to carry a policy. Fetching a site root
#: successfully and finding no pet policy is not a provider limitation -- the
#: provider returned exactly what it was asked for.
_NON_POLICY_PATH_RE = re.compile(r"^/?$|^/(?:contact|hotel|home|about)/?$",
                                 re.IGNORECASE)


def limitation_cause(url: str, presence: Dict) -> str:
    """Why the policy is absent: the page, or the URL that chose the page."""
    if presence["presence"] not in ("NO_POLICY_PRESENT", "AMENITY_ONLY"):
        return ""
    path = urlparse(url).path or "/"
    if _NON_POLICY_PATH_RE.match(path):
        return ("URL_IS_NOT_A_POLICY_PAGE: the census URL points at a site root "
                "or contact page. The provider fetched it successfully; no "
                "provider or reader can recover a policy from a page that does "
                "not state one. This is a URL-discovery gap.")
    return ("DOCUMENT_LACKS_POLICY: the property's own policy-bearing page was "
            "fetched and states no actionable pet terms")


def compare(presence: Dict, reader: Dict) -> Dict:
    """Where the loss happened, if it happened."""
    p = presence["presence"]
    extraction = reader["extraction"]
    fields = [f for f in _POLICY_FIELDS if f in extraction]
    amenity_shaped = (reader["block_found"] and reader["block_chars"] <= 60
                      and not fields
                      and set(extraction) <= {"pets_allowed"}
                      and extraction.get("pets_allowed") is True)

    if p == "UNUSABLE_DOCUMENT":
        verdict, why = "IDENTITY_FAILURE", "the page could not be evaluated"
    elif p in ("NO_POLICY_PRESENT", "AMENITY_ONLY"):
        if amenity_shaped:
            verdict, why = ("READER_FALSE_POSITIVE",
                            "the document carries no actionable policy and the "
                            "reader emitted a policy from an amenity label")
        else:
            verdict, why = ("PROVIDER_LIMITED",
                            "the document does not contain policy any reader "
                            "could recover")
    elif p == "FULL_POLICY_PRESENT":
        if not fields:
            verdict, why = ("READER_MISS",
                            "the document states %d actionable terms and the "
                            "reader recovered none"
                            % len(presence["substantive_concepts"]))
        elif len(fields) < len(presence["substantive_concepts"]):
            verdict, why = ("READER_PARTIAL",
                            "the document states %d actionable terms and the "
                            "reader recovered %d"
                            % (len(presence["substantive_concepts"]), len(fields)))
        else:
            verdict, why = "READER_CORRECT", "the reader recovered what was there"
    else:   # PARTIAL_POLICY_PRESENT
        if not fields and not extraction:
            verdict, why = ("READER_MISS",
                            "the document states an actionable term and the "
                            "reader recovered nothing")
        elif amenity_shaped:
            verdict, why = ("READER_FALSE_POSITIVE",
                            "richer text exists but the reader bound an "
                            "amenity label instead")
        else:
            verdict, why = "READER_CORRECT", "the reader represented what was available"
    return {"verdict": verdict, "why": why, "reader_fields": fields}


# --------------------------------------------------------------------------- #
# Acquisition -- gate-free, Firecrawl only
# --------------------------------------------------------------------------- #

def reusable_document(slug_fragment: str) -> Optional[Path]:
    hits = sorted(REUSABLE.rglob("*%s*/attempt-*/rendered.html" % slug_fragment))
    return hits[-1] if hits else None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def acquire(entry: Dict, run_dir: Path) -> Dict:
    """One diagnostic document. Reused when possible, fetched when not."""
    slug = _slug(entry["canonical_name"])
    out_dir = run_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "rendered.html"

    if target.is_file():
        html = target.read_text(encoding="utf-8", errors="replace")
        return {"source": "CACHED_THIS_RUN", "html": html, "status": 200,
                "final_url": entry["official_url"], "credits": 0}

    existing = reusable_document(slug)
    if existing is not None:
        html = existing.read_text(encoding="utf-8", errors="replace")
        target.write_bytes(html.encode("utf-8"))
        return {"source": "REUSED_%s" % existing.parts[-4], "html": html,
                "status": 200, "final_url": entry["official_url"], "credits": 0}

    try:
        result = FC.fetch(entry["official_url"], profile=FC.ROUTED_PROFILE)
    except Exception as exc:                                     # noqa: BLE001
        return {"source": "FETCH_FAILED", "html": "", "status": None,
                "final_url": "", "credits": 1,
                "error": "%s: %s" % (type(exc).__name__, FC.redact(str(exc)))}
    html = result.get("html") or ""
    if html:
        target.write_bytes(html.encode("utf-8"))
    return {"source": "FIRECRAWL", "html": html, "status": result.get("status"),
            "final_url": result.get("final_url") or entry["official_url"],
            "credits": 1}


def identity_layer(entry: Dict, acquired: Dict) -> Dict:
    """LAYER A. Right page, right domain, hydrated enough to judge?"""
    requested = urlparse(entry["official_url"])
    final = urlparse(acquired.get("final_url") or "")
    html = acquired.get("html") or ""
    text = UC.html_to_text(html) if html else ""
    redirected_off_domain = bool(final.netloc and final.netloc != requested.netloc)

    if not html:
        state = "NAVIGATION_FAILED"
    elif redirected_off_domain:
        state = "UNEXPECTED_PAGE"
    elif len(text) < 500:
        state = "UNHYDRATED"
    else:
        state = "IDENTITY_OK"
    return {"state": state, "requested_domain": requested.netloc,
            "final_domain": final.netloc, "redirected_off_domain": redirected_off_domain,
            "status": acquired.get("status"), "text_chars": len(text),
            "document_sha256": (hashlib.sha256(html.encode("utf-8")).hexdigest()
                                if html else ""),
            "text": text}


def run(args) -> Dict:
    selection = cohort()
    subjects = selection["selected"]
    print("cohort: %d (universe %d, cap %d) | %d distinct domains"
          % (len(subjects), selection["universe_total"], COHORT_CAP,
             selection["distinct_domains"]))

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    credits_before = FC.credits_remaining()
    rows, spent = [], 0
    began = time.monotonic()

    for entry in subjects:
        acquired = acquire(entry, run_dir)
        spent += acquired["credits"]
        layer_a = identity_layer(entry, acquired)
        presence = classify_presence(layer_a["text"],
                                     identity_ok=layer_a["state"] == "IDENTITY_OK")
        reader = read_generically(acquired.get("html") or "")
        verdict = compare(presence, reader)
        row = {
            "identity_key": entry["identity_key"],
            "property_name": entry["canonical_name"],
            "class": entry["class"],
            "domain": entry["domain"],
            "url": entry["official_url"],
            "document_source": acquired["source"],
            "layer_a_identity": {k: v for k, v in layer_a.items() if k != "text"},
            "layer_b_presence": presence,
            "layer_c_reader": {k: v for k, v in reader.items() if k != "block"},
            "reader_block": reader["block"][:300],
            "verdict": verdict,
            "limitation_cause": limitation_cause(entry["official_url"], presence),
        }
        rows.append(row)
        print("  %-44s %-12s %-22s %-22s"
              % (row["property_name"][:44], row["class"],
                 presence["presence"], verdict["verdict"]), flush=True)
        if acquired["source"] == "FIRECRAWL":
            time.sleep(args.pace)

    credits_after = FC.credits_remaining()
    return report(rows, selection, spent=spent,
                  credits_before=credits_before, credits_after=credits_after,
                  elapsed=round(time.monotonic() - began, 1))


def report(rows: List[Dict], selection: Dict, *, spent, credits_before,
           credits_after, elapsed: float) -> Dict:
    presence = Counter(r["layer_b_presence"]["presence"] for r in rows)
    verdicts = Counter(r["verdict"]["verdict"] for r in rows)
    identity = Counter(r["layer_a_identity"]["state"] for r in rows)

    recoverable = [r for r in rows
                   if r["layer_b_presence"]["presence"] in
                   ("FULL_POLICY_PRESENT", "PARTIAL_POLICY_PRESENT")]
    reader_lost = [r for r in recoverable
                   if r["verdict"]["verdict"] in
                   ("READER_MISS", "READER_PARTIAL", "READER_FALSE_POSITIVE")]
    provider_limited = [r for r in rows
                        if r["verdict"]["verdict"] == "PROVIDER_LIMITED"]

    n = len(rows) or 1
    reader_opportunity = (round(100.0 * len(reader_lost) / len(recoverable), 1)
                          if recoverable else 0.0)
    provider_limit = round(100.0 * len(provider_limited) / n, 1)

    # By class, because averaging different failure modes is the thing the
    # work order specifically forbids.
    by_class: Dict[str, Dict] = {}
    for cls in sorted({r["class"] for r in rows}):
        subset = [r for r in rows if r["class"] == cls]
        rec = [r for r in subset if r["layer_b_presence"]["presence"] in
               ("FULL_POLICY_PRESENT", "PARTIAL_POLICY_PRESENT")]
        lost = [r for r in rec if r["verdict"]["verdict"] in
                ("READER_MISS", "READER_PARTIAL", "READER_FALSE_POSITIVE")]
        by_class[cls] = {
            "documents": len(subset),
            "presence": dict(Counter(x["layer_b_presence"]["presence"] for x in subset)),
            "verdicts": dict(Counter(x["verdict"]["verdict"] for x in subset)),
            "recoverable": len(rec),
            "reader_lost": len(lost),
        }

    if reader_opportunity >= 60 and provider_limit < 50:
        decision = "READER_HARDENING_JUSTIFIED"
    elif reader_opportunity < 30:
        decision = "PROVIDER_IS_PRIMARY_LIMIT"
    else:
        decision = "MIXED"

    doc = {
        "schema": "ptf-generic-reader-diagnostic/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": ("Diagnostic only. No route changed, nothing published, and "
                 "both Bright Data providers are unreachable by construction: "
                 "this module imports no Bright Data capture path."),
        "cohort": {k: v for k, v in selection.items() if k != "selected"},
        "cohort_members": [{"identity_key": r["identity_key"],
                            "class": r["class"], "domain": r["domain"],
                            "document_source": r["document_source"]} for r in rows],
        "layer_a_identity": dict(identity),
        "layer_b_presence": dict(presence),
        "layer_c_reader_verdicts": dict(verdicts),
        "rates": {
            "documents": len(rows),
            "recoverable_documents": len(recoverable),
            "reader_opportunity_rate_pct": reader_opportunity,
            "reader_opportunity_note": (
                "of documents that DO contain policy language, the share the "
                "generic reader failed to represent. This is the number that "
                "says whether reader work would pay."),
            "provider_limitation_rate_pct": provider_limit,
            "provider_limitation_note": (
                "share of documents containing no policy any reader could "
                "recover."),
        },
        "by_class": by_class,
        "architectural_decision": decision,
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "cost": {"new_firecrawl_credits": spent,
                 "credits_before": credits_before, "credits_after": credits_after,
                 "bright_data_attempts": 0, "bright_data_usd": 0.0},
        "total_elapsed_seconds": elapsed,
        "properties": rows,
    }
    out = REPORTS / "ptf_generic_reader_diagnostic_013.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="generic-diagnostic-013")
    parser.add_argument("--pace", type=float, default=8.0)
    args = parser.parse_args(argv)
    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2
    doc = run(args)
    print()
    print("identity :", doc["layer_a_identity"])
    print("presence :", doc["layer_b_presence"])
    print("reader   :", doc["layer_c_reader_verdicts"])
    r = doc["rates"]
    print("reader opportunity %.1f%% of %d recoverable | provider limit %.1f%%"
          % (r["reader_opportunity_rate_pct"], r["recoverable_documents"],
             r["provider_limitation_rate_pct"]))
    print("credits: %d" % doc["cost"]["new_firecrawl_credits"])
    print()
    print("DECISION: %s" % doc["architectural_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
