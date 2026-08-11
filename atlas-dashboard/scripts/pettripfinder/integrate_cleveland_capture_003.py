"""PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 -- worker 003 evidence into
Cleveland authority.

Worker ``worker/ptf-cleveland-policy-capture-003`` (86d6f04) fetched the 74
ROUTED_AWAITING_CAPTURE Cleveland targets, reached 10, and proposed six
candidates. This module is the integrator's side of that handback: it does not
trust the worker's conclusions, it re-derives them.

WHAT IS PUBLISHED AND WHAT IS NOT
---------------------------------
Only the two Drury properties publish. Both state a complete, formal pet policy
in the property's own words on the property's own domain, and both reach
``readiness.POLICY_CONFIRMED``.

The three Wyndham properties do NOT publish. Their evidence is genuine and is
retained, but it is marketing copy ("our pet-friendly hotel ...") with no fee,
species, weight or count anywhere on the fetched surface -- the brand's own
Pet & Service Animal Policy accordion is client-side and never rendered. The
readiness layer states them POLICY_PARTIAL, and ``PUBLISHABLE_STATES`` does not
contain POLICY_PARTIAL: a partial shape publishes only on an explicit operator
ruling, which this integration does not have. Inventing the missing fields, or
publishing ``pets_allowed`` alone off marketing language, is exactly the
erosion the membrane exists to stop.

The sixth candidate (Super 8 Akron South/Green/Uniontown) is retained
UNRESOLVED. See ``HELD`` below.

THE FACT TABLE IS HAND-AUTHORED, AND MATCHES ITS COLUMBUS SIBLING
-----------------------------------------------------------------
Both Drury pages carry one identical brand sentence, and Columbus already
publishes that exact sentence for ``drury plaza hotel columbus downtown`` in
the frozen 404c4ff5 bundle. This module reuses that record's field shape
verbatim rather than inventing a second encoding of one policy:

  * ``weight_limit`` + ``weight_limit_operator = "combined"`` -- the older
    combined form, which ``hotel_profile`` reads as authoritative and renders.
    The newer ``weight_limit_combined`` pair is deliberately NOT used here:
    ``weight_conflict_reason()`` accepts only ``("", "lt", "lte")`` for
    ``weight_limit_combined_operator``, so the shape used elsewhere for this
    same Drury sentence publishes no weight limit at all.
  * ``fee_basis = "per room per night"`` -- "a daily fee of $50 per room",
    stated as one basis rather than split across a ``fee_scope`` whose
    published spelling ("per room") is not the one the renderer tests for
    ("per_room").

WITHHELD, AND WHY IT IS WITHHELD
--------------------------------
  * ``service_animal_exception``: the page does say service animals are free of
    charge, and the field is in the observation contract -- but no renderer
    reads it, so publishing it would record a fact the site cannot state. It
    stays in the observation, where it is true and inert, and out of the
    published facts.
  * ``fee_scope``: the fee's room scope is carried inside ``fee_basis``, and
    asserting it twice would let the two drift apart.
  * The page says "$50 per room plus tax". Tax is not modelled anywhere in the
    published fact vocabulary and is not invented here; the published fee is
    the fee the page states.

Run:  python -m scripts.pettripfinder.integrate_cleveland_capture_003 [--apply]
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD          # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MB              # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO           # noqa: E402
from scripts.pettripfinder.policy import readiness as RD                    # noqa: E402
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name  # noqa: E402

MARKET = "cleveland-akron-canton-oh"
RUN_ID = "cleveland-policy-capture-003"
AS_OF = "2026-08-11"
REVIEWER = "jfields80"

PROPOSAL_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                 / "cleveland-policy-capture-003-proposed-authority.json")
CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / ("%s.json" % MARKET))
FACTS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
              / ("hotel_policy_facts_%s.json" % MARKET))
ROUTING_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                / "identity_routing.json")
RAW_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID / "raw")
OBS_PATH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID
            / "observations.json")

#: The one sentence both Drury pages state, verbatim. Asserted to be a literal
#: substring of each property's own capture before anything derives from it.
DRURY_QUOTE = (
    "Pet Policy Dogs and cats accepted. Rooms with pets will be charged a "
    "daily fee of $50 per room plus tax. Service animals are free of charge. "
    "Limit of two pets per room with a combined weight of 80 pounds.")

#: slug -> {facts: field -> (published value, exact supporting sub-quote),
#:          withheld: field -> reason}
#: Every sub-quote must appear inside that property's own captured evidence.
PUBLISH: Dict[str, Dict] = {
    "drury-plaza-hotel": {
        "facts": {
            "pets_allowed": ("true", "Dogs and cats accepted."),
            "species_allowed": ("dogs and cats", "Dogs and cats accepted."),
            "pet_fee": ("$50.00", "a daily fee of $50 per room"),
            "fee_basis": ("per room per night", "a daily fee of $50 per room"),
            "pet_count_limit": ("2", "Limit of two pets per room"),
            "pet_count_scope": ("room", "Limit of two pets per room"),
            "weight_limit": ("80 pounds", "a combined weight of 80 pounds"),
            "weight_limit_operator": ("combined", "a combined weight of 80 pounds"),
        },
        "withheld": {
            "service_animal_exception":
                "the page states service animals are free of charge, but no "
                "renderer reads this field, so publishing it would record a "
                "fact the site cannot state",
            "fee_scope":
                "the fee's room scope is already carried inside fee_basis "
                "('per room per night'); asserting it twice lets the two drift",
        },
    },
    "drury-inn-suites-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Dogs and cats accepted."),
            "species_allowed": ("dogs and cats", "Dogs and cats accepted."),
            "pet_fee": ("$50.00", "a daily fee of $50 per room"),
            "fee_basis": ("per room per night", "a daily fee of $50 per room"),
            "pet_count_limit": ("2", "Limit of two pets per room"),
            "pet_count_scope": ("room", "Limit of two pets per room"),
            "weight_limit": ("80 pounds", "a combined weight of 80 pounds"),
            "weight_limit_operator": ("combined", "a combined weight of 80 pounds"),
        },
        "withheld": {
            "service_animal_exception":
                "the page states service animals are free of charge, but no "
                "renderer reads this field, so publishing it would record a "
                "fact the site cannot state",
            "fee_scope":
                "the fee's room scope is already carried inside fee_basis "
                "('per room per night'); asserting it twice lets the two drift",
        },
    },
}

#: Candidates whose evidence is real and retained but which do NOT publish.
#: slug -> (readiness state this integration re-derived, decision, next action)
HELD: Dict[str, Tuple[str, str, str]] = {
    "la-quinta-inn-cleveland-independence": (
        RD.POLICY_PARTIAL,
        "marketing-only: the page affirms 'our pet-friendly hotel' and states "
        "no fee, species, weight or count anywhere in the fetched surface",
        "attended capture of wyndhamhotels.com's client-side Pet & Service "
        "Animal Policy accordion, or an operator phone call to the property",
    ),
    "la-quinta-inn-suites-cleveland-airport-north": (
        RD.POLICY_PARTIAL,
        "marketing-only: the page affirms 'Our pet-friendly hotel' and states "
        "no fee, species, weight or count anywhere in the fetched surface",
        "attended capture of wyndhamhotels.com's client-side Pet & Service "
        "Animal Policy accordion, or an operator phone call to the property",
    ),
    "super-8-by-wyndham-richfield-cleveland": (
        RD.POLICY_PARTIAL,
        "marketing-only: the page affirms 'our pet-friendly, non-smoking "
        "hotel' and states no fee, species, weight or count. Identity holds on "
        "name and street address, which agree exactly; the page's own phone "
        "(+1-330-344-9040) disagrees with the CVB census phone "
        "((330) 659-6888) and that contradiction is preserved, not resolved",
        "attended capture of the Pet Policy accordion; separately, reconcile "
        "the two telephone numbers against a third identity-grade source",
    ),
    "super-8-by-wyndham-akron-south-green-uniontown": (
        RD.POLICY_NOT_FOUND,
        "membrane REJECT_WRONG_PROPERTY on M10: the brand's own JSON-LD names "
        "the property 'Super 8 by Wyndham Akron S/Green/Uniontown OH', whose "
        "token set is neither a subset nor a superset of the census identity "
        "'Super 8 by Wyndham Akron South/Green/Uniontown' ('S' vs 'south'). "
        "M10's conjunctive code+address override cannot fire: the routing "
        "record carries property_code '' and the only source for the page's "
        "code (10475) is the page under question, which would make the "
        "override self-certifying. Not forced through; M10 not relaxed. The "
        "retained evidence is marketing-only in any case, so resolving the "
        "identity would yield a POLICY_PARTIAL hold, never a publication",
        "establish the Wyndham property code for this census record from an "
        "identity-grade source independent of this capture and record it on "
        "route-cleveland-akron-canton-oh-super-8-by-wyndham-akron-south-green-"
        "uniontown, THEN re-emit the observation with property_code on both "
        "hotel_ref and identity_check and address_on_page as the STREET ALONE "
        "in the census's 'street|zip' form -- street_identity() folds a full "
        "comma-formatted address into different tokens, so the override fails "
        "on the address half even when the code half agrees. Both halves are "
        "required; neither weakens M10",
    ),
}


def _norm(text: str) -> str:
    """Whitespace-collapsed. The capture keeps the page's own line breaks."""
    return " ".join((text or "").split())


def _comma_fold(text: str) -> str:
    """Whitespace-collapsed with commas treated as whitespace.

    The Drury header prints its address as "1380 East 6th Street Cleveland ,
    OH 44114" -- the comma floats. A record that writes the same address with
    ordinary punctuation is the SAME string to a reader and a different one to
    ``in``, so identity is checked with the punctuation folded rather than by
    hand-copying the page's spacing and calling that verification.
    """
    return " ".join((text or "").replace(",", " ").split())


def verified_identity(observation: Dict, page: str) -> Dict[str, str]:
    """The worker's ``identity_check``, re-verified against the raw capture.

    The values are the worker's, which is the point: M10 must compare our
    record against what the PAGE says, and deriving the page's side from our
    own census would make the gate self-certifying. What is not taken on trust
    is that the page says them -- every value here is proven present in the
    bytes before it reaches the membrane.
    """
    check = observation["identity_check"]
    out: Dict[str, str] = {}
    for field in ("name_on_page", "address_on_page", "phone_on_page"):
        value = check.get(field)
        if not value:
            continue
        if _comma_fold(value) not in _comma_fold(page):
            raise ValueError("%s: %s %r is not present in the capture"
                             % (observation["obs_id"], field, value))
        out[field] = value
    return out


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_raw_by_url() -> Dict[str, Dict]:
    """The worker's raw captures, keyed by the URL each one actually fetched.

    Gitignored and regenerable via
    ``python scripts/pettripfinder/cleveland_capture_003_fetch.py``. Absent
    captures are not fatal here -- the committed proposal carries the hashes
    and the observation carries the quote -- but when the bytes ARE present
    every hash and every quote is re-verified against them.
    """
    out: Dict[str, Dict] = {}
    if not RAW_DIR.is_dir():
        return out
    for path in sorted(RAW_DIR.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("ok") and doc.get("text") is not None:
            out[doc["final_url"]] = doc
    return out


def routing_property_codes() -> Dict[str, str]:
    """Property codes from the ROUTING records, never from the captured page.

    The same reason ``integrate_cleveland_authority.expected_property_codes``
    gives: sourcing the expected side from the page under question would make
    M10's override self-certifying.
    """
    from scripts.pettripfinder.identity_routing import load_routes

    out: Dict[str, str] = {}
    for route in load_routes():
        if route.get("market_id") != MARKET:
            continue
        code = (route.get("property_code") or "").strip()
        if code:
            out[route["hotel_ref"]["normalized_name"]] = code
    return out


def routing_official_urls() -> Dict[str, str]:
    from scripts.pettripfinder.identity_routing import load_routes

    return {r["hotel_ref"]["normalized_name"]: r.get("official_property_url") or ""
            for r in load_routes() if r.get("market_id") == MARKET}


def build_observation(census_row: Dict, evidence: List[Dict], extraction: Dict,
                      source_url: str, raw: Dict, identity: Dict[str, str],
                      codes: Dict[str, str],
                      official_urls: Dict[str, str]) -> Dict:
    """A ptf-policy-observation/1.0 record for the membrane to judge.

    ``street_identity`` is the STREET ALONE, not the census's "street|zip"
    composite: ``street_identity()`` folds the postal code into the street
    token set, and the composite then stops matching the page's own address.
    """
    key = census_row["normalized_name"]
    return OrderedDict([
        ("obs_id", "cle003-%s" % census_row["slug"]),
        ("contract_version", PO.CONTRACT_VERSION),
        ("hotel_ref", OrderedDict([
            ("market_id", MARKET),
            ("canonical_name", census_row["canonical_name"]),
            ("normalized_name", key),
            ("street_identity", census_row["address"]),
            ("official_url", official_urls.get(key, "")),
            ("property_code", codes.get(key, "")),
        ])),
        # What the capture READ off the page, never what we expected -- and
        # every value re-proven present in the bytes by verified_identity().
        ("identity_check", OrderedDict(sorted(identity.items()))),
        ("source_url", source_url),
        ("source_type", "official_property_page"),
        ("authority_tier", PO.PT1_OFFICIAL_PROPERTY),
        ("observed_at", AS_OF),
        ("retrieved_at", AS_OF + "T00:00:00Z"),
        ("capture_method", "deterministic_fetch"),
        ("evidence", evidence),
        ("extraction", extraction),
        ("extraction_confidence", "EXACT_QUOTE"),
        ("flags", []),
        ("capture_artifacts", [raw["html_sha256"], raw["text_sha256"]]),
    ])


def build() -> Dict:
    """Re-derive everything. Returns the full decision record."""
    proposal = _load(PROPOSAL_PATH)
    census = {h["slug"]: h for h in _load(CENSUS_PATH)["hotels"]}
    worker_obs = {o["obs_id"]: o for o in _load(OBS_PATH)} if OBS_PATH.is_file() else {}
    raws = load_raw_by_url()
    codes = routing_property_codes()
    official_urls = routing_official_urls()

    candidates = {c["slug"]: c for c in proposal["candidates"]}
    accepted, observations, refused = [], [], []
    evidence_status: List[Dict] = []

    for slug, spec in sorted(PUBLISH.items()):
        cand = candidates[slug]
        row = census[slug]
        url = cand["source_urls"][0]
        claimed = cand["source_hashes"][0]
        raw = raws.get(url)

        # ---- durable evidence: the committed hash must match real bytes ---- #
        status = OrderedDict([("slug", slug), ("source_url", url),
                              ("html_sha256", claimed["html_sha256"]),
                              ("text_sha256", claimed["text_sha256"])])
        if raw is None:
            status["raw_bytes"] = "ABSENT"
            refused.append("%s: raw capture absent; cannot verify the committed "
                           "hashes against real bytes" % slug)
            evidence_status.append(status)
            continue
        import hashlib
        recomputed = hashlib.sha256(raw["text"].encode("utf-8")).hexdigest()
        status["raw_bytes"] = "PRESENT"
        status["text_sha256_recomputed"] = recomputed
        status["hashes_agree"] = bool(
            raw["html_sha256"] == claimed["html_sha256"]
            and raw["text_sha256"] == claimed["text_sha256"]
            and recomputed == claimed["text_sha256"])
        evidence_status.append(status)
        if not status["hashes_agree"]:
            refused.append("%s: committed hashes do not match the raw capture" % slug)
            continue
        if raw.get("http_status") != 200:
            refused.append("%s: capture is not an HTTP 200" % slug)
            continue

        page = _norm(raw["text"])

        # ---- the brand sentence itself must be literal in THIS capture ----- #
        if _norm(DRURY_QUOTE) not in page:
            refused.append("%s: the policy quote is not a literal substring of "
                           "its own capture" % slug)
            continue

        # ---- every field's sub-quote must be literal in THIS capture ------- #
        facts, evidence, bad = OrderedDict(), [], []
        for field, (value, quote) in spec["facts"].items():
            if _norm(quote) not in page:
                bad.append("%s: %r is not in the capture" % (field, quote))
                continue
            if _norm(quote) not in _norm(DRURY_QUOTE):
                bad.append("%s: %r is outside the cited policy statement"
                           % (field, quote))
                continue
            facts[field] = value
            evidence.append(OrderedDict([
                ("field", field), ("quote", quote), ("source_url", url),
                ("value", value)]))
        for field in spec["withheld"]:
            if field in facts:
                bad.append("%s is both withheld and published" % field)
        if bad:
            refused.append("%s: %s" % (slug, "; ".join(bad)))
            continue

        # ---- observation -> membrane -> readiness, independently ----------- #
        worker_record = worker_obs.get(cand["observations"][0])
        if worker_record is None:
            refused.append("%s: the worker's observation batch is absent; the "
                           "page-side identity cannot be re-verified" % slug)
            continue
        try:
            identity = verified_identity(worker_record, page)
        except ValueError as exc:
            refused.append(str(exc))
            continue

        obs = build_observation(
            row,
            [OrderedDict([("quote", DRURY_QUOTE), ("location", "Hotel Policies section"),
                          ("field_refs", sorted({
                              "pets_allowed", "species_allowed", "pet_fee",
                              "fee_currency", "fee_basis", "pet_count_limit",
                              "pet_count_scope", "weight_limit_combined",
                              "weight_limit_combined_operator",
                              "service_animal_exception"})),
                          ("artifact_ref", raw["html_sha256"])])],
            OrderedDict([
                ("pets_allowed", "true"),
                ("species_allowed", "dogs_and_cats"),
                ("pet_fee", 5000),
                ("fee_currency", "USD"),
                ("fee_basis", "per_night"),
                ("pet_count_limit", 2),
                ("pet_count_scope", "room"),
                ("weight_limit_combined", 80),
                ("weight_limit_combined_operator", "max"),
                ("service_animal_exception", "true"),
            ]),
            url, raw, identity, codes, official_urls)
        PO.validate_observation(obs)
        verdict = MB.evaluate(obs)
        state = RD.derive([obs], all_surfaces_reached=True)
        if not verdict.may_establish:
            refused.append("%s: membrane %s / %s -- %s"
                           % (slug, verdict.verdict, verdict.rule, verdict.detail))
            continue
        if state.state not in RD.PUBLISHABLE_STATES:
            refused.append("%s: readiness %s is not publishable" % (slug, state.state))
            continue

        observations.append(obs)
        accepted.append(OrderedDict([
            ("key", row["normalized_name"]),
            ("name", row["canonical_name"]),
            ("facts", facts),
            ("evidence", evidence),
            ("evidence_count", len(evidence)),
            ("evidence_quote", _norm(DRURY_QUOTE)),
            ("source_url", url),
            ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", AS_OF), ("verified_at", AS_OF),
            ("approval", OrderedDict([("approval_date", AS_OF),
                                      ("decision", "APPROVED"),
                                      ("operator", REVIEWER)])),
            ("withheld_fields", OrderedDict(sorted(spec["withheld"].items()))),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash", "sha256:%s" % raw["html_sha256"]),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
        ]))

    # ---- the held set is re-derived, not copied from the worker ----------- #
    held = []
    for slug, (expected_state, decision, next_action) in sorted(HELD.items()):
        cand = candidates[slug]
        obs = worker_obs.get(cand["observations"][0]) if worker_obs else None
        rederived = ""
        membrane = ""
        if obs is not None:
            v = MB.evaluate(obs)
            membrane = "%s%s" % (v.verdict, "/%s" % v.rule if v.rule else "")
            rederived = RD.derive([obs], all_surfaces_reached=True).state
        held.append(OrderedDict([
            ("slug", slug), ("canonical_name", cand["canonical_name"]),
            ("worker_state", cand["state"]),
            ("integrator_state", rederived or cand["state"]),
            ("membrane", membrane),
            ("published", False),
            ("decision", decision),
            ("next_action", next_action),
            ("source_url", cand["source_urls"][0]),
            ("source_hashes", cand["source_hashes"][0]),
        ]))
        if rederived and rederived != expected_state:
            refused.append("%s: re-derived readiness %s does not match the "
                           "reviewed %s" % (slug, rederived, expected_state))

    return {"accepted": accepted, "observations": observations, "held": held,
            "refused": refused, "evidence_status": evidence_status,
            "census": census, "proposal": proposal}


def seed_rows(accepted: List[Dict], census: Dict) -> List[Dict]:
    """One inventory row per published hotel.

    ``pet_policy`` carries the property's own captured words. PTF-INVENTORY-001's
    renderability boundary reads this field: an empty value filters the listing
    out before the WGE.
    """
    by_key = {row["normalized_name"]: row for row in census.values()}
    rows = []
    for rec in accepted:
        row = by_key[rec["key"]]
        rows.append({
            "name": rec["name"], "category": "pet-friendly-hotels",
            "address": row["address"], "city": row["city"], "state": row["state"],
            "postal_code": row["postal_code"], "phone": row["phone"],
            "website_url": rec["source_url"], "source_url": rec["source_url"],
            "source_type": "OFFICIAL_PROPERTY", "observed_at": AS_OF,
            "rating": "", "amenities": "",
            "pet_policy": rec["evidence_quote"],
            "canonical": "", MARKET_ID_FIELD: MARKET,
        })
    return rows


def apply_changes(accepted: List[Dict], census: Dict) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    # ---- policy facts ----------------------------------------------------- #
    facts = _load(FACTS_PATH)
    have = {h["key"] for h in facts["hotels"]}
    new_facts = [r for r in accepted if r["key"] not in have]
    facts["hotels"] = facts["hotels"] + new_facts
    FACTS_PATH.write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8", newline="\n")
    counts["facts_added"] = len(new_facts)

    # ---- inventory -------------------------------------------------------- #
    rows = seed_rows(accepted, census)
    with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        existing = list(reader)
        fields = list(reader.fieldnames)
    by_name = {normalize_name(r["name"]): r for r in rows}
    merged, seen = [], set()
    for row in existing:
        key = normalize_name(row["name"])
        if key in by_name and row.get(MARKET_ID_FIELD) == MARKET:
            merged.append(by_name[key])
            seen.add(key)
        else:
            merged.append(row)
    new_rows = [r for k, r in by_name.items() if k not in seen]
    merged += new_rows
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in merged:
        writer.writerow({k: row.get(k, "") for k in fields})
    PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8", newline="")
    counts["seed_rows_added"] = len(new_rows)

    # ---- retire the routing records now owned by the seed ----------------- #
    routing = _load(ROUTING_PATH)
    done = {normalize_name(r["name"]) for r in rows}
    before = len(routing["routes"])
    routing["routes"] = [r for r in routing["routes"]
                         if not (r.get("market_id") == MARKET
                                 and r["hotel_ref"]["normalized_name"] in done)]
    routing["count"] = len(routing["routes"])
    ROUTING_PATH.write_text(json.dumps(routing, indent=1, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
    counts["routes_retired"] = before - len(routing["routes"])
    return counts


def main() -> int:
    apply = "--apply" in sys.argv
    result = build()

    print("=== CLEVELAND CAPTURE-003 INTEGRATION ===")
    print("  worker candidates      : %d" % len(result["proposal"]["candidates"]))
    print("  durable evidence       :")
    for status in result["evidence_status"]:
        print("      %-32s raw=%-8s hashes_agree=%s"
              % (status["slug"], status["raw_bytes"],
                 status.get("hashes_agree", "n/a")))
    print("  accepted for publish   : %d" % len(result["accepted"]))
    for rec in result["accepted"]:
        print("      %-32s %d facts / %d withheld"
              % (rec["key"][:32], len(rec["facts"]), len(rec["withheld_fields"])))
    print("  held, not published    : %d" % len(result["held"]))
    for rec in result["held"]:
        print("      %-46s %-16s %s"
              % (rec["slug"][:46], rec["integrator_state"], rec["membrane"]))
    print("  refused                : %d" % len(result["refused"]))
    for line in result["refused"]:
        print("      %s" % line)

    if result["refused"]:
        print("  mode                   : REFUSED")
        return 1
    if apply:
        counts = apply_changes(result["accepted"], result["census"])
        print("  APPLIED: %(facts_added)d facts, %(seed_rows_added)d seed rows, "
              "%(routes_retired)d routes retired" % counts)
    else:
        print("  mode                   : DRY RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
