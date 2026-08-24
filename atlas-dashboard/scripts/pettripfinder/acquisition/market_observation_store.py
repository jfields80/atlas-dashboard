"""PTF-ST-LOUIS-MARKET-001 -- the current-state observation store, offline.

Input: a capture run directory whose attempts already persisted their artifact
set (``rendered.html``, ``page-text.txt``, ``policy-block.txt``, ``locator.json``)
plus the pilot report that says which attempt each identity ended on.

Output: one ``ptf-policy-observation/1.0`` record per acquired identity, each
with its reader provenance, its publication-grade verdict, its withheld fields
and its membrane/readiness result -- and a store document that says, per row,
why it is or is not publishable.

RE-PARSE THE BLOCK, NEVER RE-LOCATE THE DOCUMENT
------------------------------------------------
PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 established this the expensive way:
re-locating from a persisted document runs TODAY'S locator, which can bound a
different block than the locator that actually ran, and a different block is a
record about a different thing. It flipped two of nine records and would have
published one of two stated fee bases.

So this module reads ``policy-block.txt`` -- the bytes the capture itself
bounded -- and checks it against ``locator.json``'s ``block_sha256`` before
parsing. A block that does not match its own locator record is refused, not
repaired. ``rendered.html`` is read only to be hashed and to hold the quotes,
which is exactly what the evidence contract attests.

ZERO NETWORK. ZERO SPEND. Nothing here fetches anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC       # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS      # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS        # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG     # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC      # noqa: E402
from scripts.pettripfinder.discovery.property_identity import street_identity  # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MEMBRANE     # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO        # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS          # noqa: E402

SCHEMA = "ptf-market-observation-store/1.0"

# Why a captured identity produced no usable observation.
BLOCK_MISSING = "PERSISTED_BLOCK_MISSING"
BLOCK_HASH_MISMATCH = "PERSISTED_BLOCK_DOES_NOT_MATCH_ITS_LOCATOR_RECORD"
READER_FOUND_NOTHING = "READER_FOUND_NOTHING_IN_THE_PERSISTED_BLOCK"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _identity_check(html_path: Path, result: Mapping) -> "OrderedDict":
    """The page's own identity signals, re-read from the persisted document.

    The membrane's M10 gate reads ``name_on_page``. A document <title> is not
    an identity: Extended Stay America titles every property page "Explore Our
    Nationwide Hotel Locations", which M10 correctly refuses as neither a
    subset nor a superset of the property it is supposed to name -- and the
    capture's own identity gate had already confirmed those properties on
    street, postal code and telephone. Read what the capture read.
    """
    check = OrderedDict()
    try:
        html = _read(html_path)
        title = MS.collapse(html.split("<title", 1)[1].split(">", 1)[1]
                            .split("</title", 1)[0]) if "<title" in html else ""
        signals = PS.read_identity(html, final_url=result.get("final_url", ""),
                                   title=title,
                                   brand=(result.get("brand") or "")
                                   if not str(result.get("brand", "")).startswith("INDEP:")
                                   else "")
        raw = signals.to_dict()
    except Exception:                                            # noqa: BLE001
        raw = {}
    check["name_on_page"] = (str(raw.get("name_on_page") or "").strip()
                             or result.get("title") or result["canonical_name"])
    for source_key, target_key in (("address_on_page", "address_on_page"),
                                   ("property_code_on_page", "property_code"),
                                   ("phone_on_page", "phone_on_page")):
        value = str(raw.get(source_key) or "").strip()
        if value:
            check[target_key] = value
    return check


#: Lanes that drive a real browser. ``policy_observation.CAPTURE_METHODS``
#: already distinguishes these from a fetch, and the distinction is not
#: cosmetic: a record captured through a managed browser was produced by
#: something that could have interacted with the page, and a reviewer reading
#: the provenance is entitled to know which of the two produced the quote.
_BROWSER_PROVIDERS = frozenset({"brightdata_browser"})


def _capture_method(result: Mapping) -> str:
    return ("browser_assisted" if result.get("provider") in _BROWSER_PROVIDERS
            else "deterministic_fetch")


def _hotel_ref(result: Mapping, *, market_id: str,
               census_row: Optional[Mapping],
               corrected_name: str = "") -> "OrderedDict":
    """The reference into the identity authority, INCLUDING its street guard.

    ``policy_observation`` calls hotel_ref "a reference into the existing
    identity authority (market_id + normalized_name, GUARDED BY
    street_identity)", and this builder had been leaving that guard empty. The
    consequence was silent: ``policy_membrane``'s M10 escapes both need a street
    on the reference side, so neither could ever fire for a market built on this
    path, and twelve St. Louis captures whose identity the capture gate had
    already confirmed were refused as the wrong property with no way back.

    The street comes from the CENSUS, which is the identity authority. It is not
    read off the page -- that is the value being checked against.
    """
    row = census_row or {}
    street = row.get("address", "") or ""
    postal = row.get("postal_code", "") or ""
    ref = OrderedDict((
        ("market_id", market_id),
        ("canonical_name", corrected_name or result["canonical_name"]),
        ("normalized_name", result["identity_key"]),
        ("official_url", result["source_url"]),
        ("property_code", ""),
    ))
    if street:
        ref["street_identity"] = street_identity(street, postal)
    return ref


def _apply_allowance_override(observation: Dict, override: Mapping) -> None:
    """Write a founder's allowance ruling onto an observation, and cite it.

    The reader withholds ``pets_allowed`` as SOURCE_SILENT when a page states
    pet terms without ever writing an allowance, because reading one out of a
    price is an inference. A founder may make that reading; this records that
    they did, on the named row only.

    The quote cited is the property's OWN text -- the fee or the count the
    ruling rests on -- never the ruling's words. An evidence quote must remain
    something a reader can find on the page.
    """
    extraction = observation.setdefault("extraction", {})
    extraction["pets_allowed"] = bool(override.get("set_pets_allowed"))
    species = list(override.get("species_supported_by_the_text") or ())
    if species:
        extraction["species_allowed"] = species
    quotes = [q for q in (override.get("cited_quotes") or ())
              if any(q == item.get("quote") for item in observation["evidence"])]
    for quote in quotes:
        for item in observation["evidence"]:
            if item.get("quote") == quote and "pets_allowed" not in item["field_refs"]:
                item["field_refs"] = list(item["field_refs"]) + ["pets_allowed"]
                break
    observation.setdefault("founder_overrides", []).append(OrderedDict((
        ("kind", "ALLOWANCE"),
        ("field", "pets_allowed"),
        ("set_to", extraction["pets_allowed"]),
        ("decided_by", override.get("decided_by", "")),
        ("decided_at", override.get("decided_at", "")),
        ("work_order", override.get("work_order", "")),
        ("ruling", override.get("founder_ruling", "")),
        ("cited_quotes", quotes),
        ("was_withheld_as", "SOURCE_SILENT"),
    )))


def observation_for(result: Mapping, *, run_id: str, market_id: str,
                    census_row: Optional[Mapping] = None,
                    corrected_name: str = "",
                    allowance: Optional[Mapping] = None,
                    identity_override: Optional[Mapping] = None
                    ) -> Tuple[Optional[Dict], Optional[Dict], str]:
    """``(observation, publication_grade, refusal_reason)`` for one result."""
    attempt_dir = Path(result.get("artifact_dir") or "")
    if not attempt_dir.is_dir():
        return (None, None, BLOCK_MISSING)
    block_path = attempt_dir / "policy-block.txt"
    html_path = attempt_dir / "rendered.html"
    text_path = attempt_dir / "page-text.txt"
    locator_path = attempt_dir / "locator.json"
    if not (block_path.is_file() and html_path.is_file()):
        return (None, None, BLOCK_MISSING)

    block_text = _read(block_path)
    locator: Dict = {}
    if locator_path.is_file():
        locator = json.loads(_read(locator_path))
        recorded = str(locator.get("block_sha256") or "")
        if recorded and BC.sha256_file(block_path) != recorded:
            return (None, None, BLOCK_HASH_MISMATCH)

    strategy = str(locator.get("strategy") or result.get("locator_strategy") or "")
    reading = PR.parse(block_text, strategy=strategy)
    if not reading.found:
        return (None, None, READER_FOUND_NOTHING)

    extraction_result = PR.to_extraction(
        reading,
        location="bounded policy container (%s / %s)"
                 % (strategy, locator.get("selector") or "no path"))

    html_sha = BC.sha256_file(html_path)
    observation = OrderedDict((
        ("obs_id", "%s::%s" % (run_id, result["identity_key"])),
        ("contract_version", PO.CONTRACT_VERSION),
        ("hotel_ref", _hotel_ref(result, market_id=market_id,
                                 census_row=census_row,
                                 corrected_name=corrected_name)),
        ("identity_check", _identity_check(html_path, result)),
        ("source_url", result.get("final_url") or result["source_url"]),
        ("source_type", "official_property_page"),
        ("authority_tier", PO.PT1_OFFICIAL_PROPERTY),
        ("observed_at", "2026-08-23"),
        ("retrieved_at", "2026-08-23"),
        ("capture_method", _capture_method(result)),
        ("evidence", [dict(item) for item in extraction_result.evidence]),
        ("extraction", dict(extraction_result.extraction)),
        ("extraction_confidence", "EXACT_QUOTE"),
        ("flags", [dict(flag) for flag in extraction_result.flags]),
        ("snapshot_hash", html_sha),
        ("raw_pointer", str(attempt_dir)),
        ("capture_artifacts", OrderedDict((
            ("rendered.html", str(html_path)),
            ("page-text.txt", str(text_path)),
            ("policy-block.txt", str(block_path)),
            ("locator.json", str(locator_path) if locator_path.is_file() else ""),
        ))),
    ))
    if extraction_result.parser_warnings:
        observation["parser_warnings"] = list(extraction_result.parser_warnings)

    grade = PG.assess(
        evidence_items=observation["evidence"],
        extraction=observation["extraction"],
        source_url=observation["source_url"],
        captured_at="2026-08-23",
        ref_prefix="%s::%s" % (run_id, result["identity_key"]),
        artifact_path=html_path,
        recorded_sha256=html_sha,
        page_text_path=text_path if text_path.is_file() else None,
        identity_confirmed=bool(result.get("identity_confirmed")))

    if identity_override is not None:
        observation["identity_adjudication"] = OrderedDict((
            ("approved_by", identity_override.get("decided_by", "")),
            ("approved_at", identity_override.get("decided_at", "")),
            ("work_order", identity_override.get("work_order", "")),
            ("census_canonical_name",
             identity_override.get("census_canonical_name", "")),
            ("page_name", identity_override.get("page_name", "")),
            ("signals_agreeing", identity_override.get("signals_agreeing", 0)),
            ("street", identity_override.get("street", {})),
            ("telephone", identity_override.get("telephone", {})),
            ("property_code", identity_override.get("property_code", {})),
            ("contradicting_evidence",
             identity_override.get("contradicting_evidence", "")),
            ("founder_verdict", identity_override.get("founder_verdict", "")),
            ("rule", identity_override.get("founder_ruling", "")),
        ))
    if allowance is not None:
        _apply_allowance_override(observation, allowance)
    membrane = MEMBRANE.evaluate(observation)
    readiness = READINESS.derive([observation], blocked=False,
                                 all_surfaces_reached=True)
    record = OrderedDict((
        ("identity_key", result["identity_key"]),
        ("canonical_name", corrected_name or result["canonical_name"]),
        ("census_canonical_name", result["canonical_name"]),
        ("corridor", result.get("corridor", "")),
        ("brand", result.get("brand", "")),
        # Read from the row, defaulted to what the only lane that existed when
        # this module was written would have said. A paid run carries its own
        # provider and reader per property -- Firecrawl with the Choice reader
        # on one row, the Browser API with the Marriott reader on the next --
        # and asserting "direct_http / generic" over that would put a false
        # provenance on a record whose whole value is its provenance.
        ("provider", result.get("provider") or "direct_http"),
        ("reader", result.get("reader") or "generic"),
        ("reader_provenance", OrderedDict((
            ("module", "scripts/pettripfinder/brightdata/policy_reading.py"),
            ("entrypoint", "parse -> to_extraction"),
            ("locator_walk", str(locator.get("walk") or "")),
            ("locator_strategy", strategy),
            ("locator_contract", str(locator.get("contract") or "")),
            ("block_sha256", str(locator.get("block_sha256") or "")),
            ("document_sha256", html_sha),
        ))),
        ("observation", observation),
        ("publication_grade", grade.to_dict()),
        ("withheld_fields", dict(extraction_result.withheld)),
        ("non_inferences", list(extraction_result.non_inferences)),
        ("membrane", membrane.to_dict()),
        ("readiness", readiness.to_dict()),
        ("review_state", "AWAITING_FOUNDER_REVIEW"),
    ))
    return (record, grade.to_dict(), "")


def build(pilot: Mapping, *, run_id: str,
          census: Optional[Mapping] = None,
          name_corrections: Optional[Mapping] = None,
          founder_overrides: Optional[Mapping] = None
          ) -> Tuple[List[Dict], List[Dict]]:
    """``(records, refusals)``. Every VALID capture is accounted for."""
    market_id = pilot["market_id"]
    rows = {h["identity_key"]: h for h in (census or {}).get("hotels") or ()}
    # A census name is what DISCOVERY observed. Where that is a bare chain word,
    # an evidence-cited overlay supplies the name the property's own page
    # states. The census file itself is never edited: a derivation and an
    # observation must stay distinguishable.
    corrected = {r["identity_key"]: r["corrected_canonical_name"]
                 for r in (name_corrections or {}).get("records") or ()}
    overrides = founder_overrides or {}
    stamp = {"decided_by": overrides.get("decided_by", ""),
             "decided_at": overrides.get("decided_at", ""),
             "work_order": overrides.get("work_order", "")}
    allowance_block = overrides.get("allowance_overrides") or {}
    identity_block = overrides.get("identity_overrides") or {}
    allowances = {r["identity_key"]: dict(r, **stamp,
                  founder_ruling=allowance_block.get("founder_ruling", ""))
                  for r in allowance_block.get("records") or ()}
    identities = {r["identity_key"]: dict(r, **stamp,
                  founder_ruling=identity_block.get("founder_ruling", ""))
                  for r in identity_block.get("records") or ()}
    records: List[Dict] = []
    refusals: List[Dict] = []
    for result in pilot["results"]:
        if result["outcome"] != "VALID":
            continue
        record, _grade, refusal = observation_for(
            result, run_id=run_id, market_id=market_id,
            census_row=rows.get(result["identity_key"]),
            corrected_name=corrected.get(result["identity_key"], ""),
            allowance=allowances.get(result["identity_key"]),
            identity_override=identities.get(result["identity_key"]))
        if record is None:
            refusals.append(OrderedDict((
                ("identity_key", result["identity_key"]),
                ("canonical_name", result["canonical_name"]),
                ("reason", refusal),
                ("artifact_dir", result.get("artifact_dir", "")),
            )))
            continue
        records.append(record)
    records.sort(key=lambda r: r["identity_key"])
    refusals.sort(key=lambda r: r["identity_key"])
    return (records, refusals)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--census", default="",
                        help="the market census; supplies hotel_ref's "
                             "street_identity guard, which the membrane's "
                             "identity escapes need on the reference side")
    parser.add_argument("--name-corrections", default="",
                        help="a ptf-canonical-name-correction report; replaces "
                             "a bare-chain census name with the one the "
                             "property's own captured page states")
    parser.add_argument("--founder-overrides", default="",
                        help="a ptf-founder-override report; carries a human's "
                             "allowance and identity rulings, which no reader "
                             "may make for itself")
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", default="ptf-st-louis-direct-http-001")
    args = parser.parse_args(argv)

    pilot = json.loads(Path(args.pilot).read_text(encoding="utf-8"))
    census = (json.loads(Path(args.census).read_text(encoding="utf-8"))
              if args.census else None)
    corrections = (json.loads(Path(args.name_corrections)
                              .read_text(encoding="utf-8"))
                   if args.name_corrections else None)
    overrides = (json.loads(Path(args.founder_overrides)
                            .read_text(encoding="utf-8"))
                 if args.founder_overrides else None)
    records, refusals = build(pilot, run_id=args.run_id, census=census,
                              name_corrections=corrections,
                              founder_overrides=overrides)

    grades = Counter(r["publication_grade"]["verdict"] for r in records)
    readiness_states = Counter(r["readiness"].get("state", "") for r in records)
    membrane_states = Counter(str(r["membrane"].get("verdict", "")) for r in records)
    pets = Counter(str(r["observation"]["extraction"].get("pets_allowed"))
                   for r in records)

    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "The current-state policy observation store for this market, derived "
         "offline from persisted capture artifacts. Every row carries its "
         "source, its capture, its locator, its evidence, its reader "
         "provenance, its current facts, its withheld fields and its review "
         "state. No row here is an authority; every row is AWAITING_FOUNDER_"
         "REVIEW until a human decides it."),
        ("market_id", pilot["market_id"]),
        ("work_order", pilot.get("work_order", "")),
        ("run_id", args.run_id),
        ("derived_from", args.pilot),
        ("network_calls", 0),
        ("usd_spent", 0.0),
        ("count", len(records)),
        ("publication_grade_counts", OrderedDict(sorted(grades.items()))),
        ("readiness_counts", OrderedDict(sorted(readiness_states.items()))),
        ("membrane_counts", OrderedDict(sorted(membrane_states.items()))),
        ("pets_allowed_counts", OrderedDict(sorted(pets.items()))),
        ("refusals", refusals),
        ("records", records),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("observations   : %d" % len(records))
    print("refusals       : %d" % len(refusals))
    print("grades         : %s" % dict(sorted(grades.items())))
    print("readiness      : %s" % dict(sorted(readiness_states.items())))
    print("pets_allowed   : %s" % dict(sorted(pets.items())))
    print("written        : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
