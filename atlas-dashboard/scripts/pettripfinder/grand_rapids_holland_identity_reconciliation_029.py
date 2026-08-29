# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029 -- settle six identities, spend nothing.

028 fetched twenty pages and the identity gate refused six of them. Every one
of those six came back from a page that NAMES the property and was declined on
a street suffix -- "4155 28th St., S.E." against "4155 28th Street". The bytes
are on disk. This order asks whether those six are the same buildings the
census means, and reads the policy of the ones that are.

No provider is called. Nothing is fetched, discovered, or acquired.

THE IDENTITY RULE, AND WHY IT IS NOT "THE ADDRESSES LOOK CLOSE"
---------------------------------------------------------------
A row is confirmed only on TWO AGREEING SIGNALS of which AT LEAST ONE IS NOT A
TELEPHONE. That second clause is the whole point: a switchboard is shared by
every hotel in a building, and this market has three pairs that prove it --
019 held two open on exactly that evidence and 025 named the third. A shared
telephone alone may never confirm an identity here.

Six signals are available and each is read from a committed artifact:

    STREET_NUMBER      the number the page prints against the census's
    STREET_NAME        token containment after the census's own normalisation,
                       so "Lake Eastbrook" and "Lake Eastbrook Blvd SE" agree
                       and "Lake Eastbrook" and "Clyde Park" do not
    NAME               the same token-containment rule the census uses
                       everywhere else, widened by presentation_key
    PROPERTY_CODE      a brand's own code in the URL -- mi121, grrpd, grrmi
    PLACES_PREMISES    the address Google returned, checked against the census
                       independently of what the fetched page says
    TELEPHONE          census against the Places result. NEVER sufficient alone.

THE POLICY RE-READ USES THE COMMITTED STACK, NOT A NEW READER
--------------------------------------------------------------
``unlocker_capture.locate_policy_in_html`` finds the block and
``policy_reading.parse`` reads it -- the same locator and the same reader that
produced the thirteen rows 028 already accepted. Re-locating from saved HTML is
the sanctioned move for a capture DECLINED AT THE IDENTITY GATE, because that
gate runs BEFORE the locator and no block was ever cut.

Nothing is inferred from a service-animal sentence, an amenity chip, or a fee
paragraph that is not a pet policy. That matters concretely here: the Comfort
Inn page prints "Pet Friendly*" in a list beside "Free WiFi" and "Fitness
Centre", and this pass does NOT read that. It reads the labelled block the
locator finds, which says "Pets are allowed. Dogs Only. 25.00 USD Per Night Per
Pet."

THE STOP RULE IS OBEYED LITERALLY
----------------------------------
One additional clean PET_FRIENDLY row takes this market to 43, and the order
says stop there rather than maximise. So the confirmed rows are read in
identity-key order and the reading STOPS at the first pet-friendly row. Rows
left unread are reported as unread -- with their identity settled, so a later
pass can take them if a founder ever wants more than the target.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR             # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC           # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC        # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP           # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "grand-rapids-holland-mi.json"
ACQUISITION = LP / "grand_rapids_holland_mi_market_acquisition_028.json"
RESULT_028 = LP / "grand_rapids_holland_mi_policy_acquisition_028.json"
PLACES_026 = LP / "grand_rapids_holland_mi_places_pilot_026.json"
PLACES_027 = LP / "grand_rapids_holland_mi_places_batch_027_run.json"
HOLDS_019 = LP / "grand_rapids_holland_mi_identity_holds_019.json"

REPORT_PATH = LP / "grand_rapids_holland_mi_identity_reconciliation_029.json"
PACKET_PATH = LP / "grand_rapids_holland_mi_founder_review_packet_029.json"

SCHEMA = "ptf-identity-reconciliation/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029"
MARKET = "grand-rapids-holland-mi"

PUBLISHED_TODAY = 35
CLEAN_FROM_028 = 7
TARGET = 43

SAME_PROPERTY = "SAME_PROPERTY_CONFIRMED"
DISTINCT_PROPERTY = "DISTINCT_PROPERTY"
HOLD_IDENTITY = "HOLD_IDENTITY"

PET_FRIENDLY = "PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
HOLD = "HOLD"
NOT_READ = "NOT_READ_THE_TARGET_WAS_REACHED"
WITHHELD_BRAND_PAGE = "WITHHELD_PAGE_IS_NOT_PROPERTY_SPECIFIC"

#: Two signals, and one of them may not be the telephone.
MIN_SIGNALS = 2

#: A brand's own property code, as it appears in the URLs this market routes.
_PROPERTY_CODE = re.compile(
    r"/(?:hotels?/)?(?P<code>[a-z]{2}\d{3,4}|[a-z]{5,6})(?:/hoteldetail|\?|$|/)",
    re.IGNORECASE)

#: Pages whose title says they describe MANY properties. A policy read off one
#: belongs to no single hotel, whatever address the page also prints.
_INDEX_TITLE = re.compile(
    r"\b(nationwide|all\s+locations|our\s+locations|explore\s+our)\b",
    re.IGNORECASE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _street_number(value: str) -> str:
    match = re.match(r"\s*(\d+)", value or "")
    return match.group(1) if match else ""


def _street_tokens(value: str) -> set:
    """Street words after the census's own normalisation, number dropped."""
    words = URC.normalise(value).split()
    return {URC._STREET_WORDS.get(w, w) for w in words if not w.isdigit()}


# --------------------------------------------------------------------------- #
# Gathering the evidence
# --------------------------------------------------------------------------- #

def mismatch_rows() -> List[Dict]:
    """The six IDENTITY_MISMATCH rows, with every artifact that speaks to them."""
    census = {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}
    places: Dict[str, Dict] = {}
    for path in (PLACES_026, PLACES_027):
        for row in _load(path)["rows"]:
            if row.get("requests_made"):
                places[row["identity_key"]] = row

    out: List[Dict] = []
    for result in _load(ACQUISITION)["results"]:
        if result["outcome"] != "IDENTITY_MISMATCH":
            continue
        key = result["identity_key"]
        folder = Path((result.get("declined_dir") or "").replace("\\", "/"))
        declined: Dict = {}
        if (folder / "declined.json").is_file():
            declined = json.loads(
                (folder / "declined.json").read_text(encoding="utf-8-sig"))
        signals = (declined.get("identity") or {}).get("signals") or {}
        out.append(OrderedDict((
            ("identity_key", key),
            ("census", census[key]),
            ("places", places.get(key, {})),
            ("page_name", signals.get("name_on_page", "")),
            ("page_address", signals.get("address_on_page", "")),
            ("page_postal", signals.get("postal_code_on_page", "") or ""),
            ("page_telephone", signals.get("telephone_on_page", "") or ""),
            ("page_title", declined.get("title", "")),
            ("source_url", result.get("source_url", "")),
            ("declined_directory",
             folder.as_posix() if str(folder) != "." else ""),
            ("gate_detail", result.get("detail", "")),
        )))
    return sorted(out, key=lambda r: r["identity_key"])


def prior_identity_rulings() -> Dict[str, str]:
    """Identity questions this market has already opened. None may be reopened
    here by a pass that was not asked to rule on them."""
    out: Dict[str, str] = {}
    for hold in _load(HOLDS_019)["holds"]:
        for key in hold["identity_keys"]:
            out[key] = ("019 holds this identity open against %r"
                        % [k for k in hold["identity_keys"] if k != key])
    return out


# --------------------------------------------------------------------------- #
# The identity rule
# --------------------------------------------------------------------------- #

def identity_signals(row: Mapping) -> List[Dict]:
    """Every signal that agrees, each labelled telephone or not."""
    census = row["census"]
    places = row["places"]
    found: List[Dict] = []

    census_number = _street_number(census.get("address", ""))
    page_number = _street_number(row["page_address"])
    if census_number and page_number and census_number == page_number:
        found.append(OrderedDict((
            ("signal", "STREET_NUMBER"), ("telephone", False),
            ("census", census_number), ("page", page_number))))

    census_street = _street_tokens(census.get("address", ""))
    page_street = _street_tokens(row["page_address"])
    if census_street and page_street and (page_street <= census_street
                                          or census_street <= page_street):
        found.append(OrderedDict((
            ("signal", "STREET_NAME"), ("telephone", False),
            ("census", " ".join(sorted(census_street))),
            ("page", " ".join(sorted(page_street))))))

    if row["page_name"] and DEDUP.names_compatible(
            URC.normalise(census.get("canonical_name", "")),
            URC.normalise(row["page_name"])):
        found.append(OrderedDict((
            ("signal", "NAME"), ("telephone", False),
            ("census", census.get("canonical_name", "")),
            ("page", row["page_name"]))))

    code = _PROPERTY_CODE.search(row["source_url"] or "")
    if code:
        found.append(OrderedDict((
            ("signal", "PROPERTY_CODE"), ("telephone", False),
            ("census", ""), ("page", code.group("code")))))

    premises = places.get("premises_agreement") or {}
    if premises.get("checked") and not premises.get("disagrees"):
        if premises.get("census_street_number") and premises.get("census_postal"):
            found.append(OrderedDict((
                ("signal", "PLACES_PREMISES"), ("telephone", False),
                ("census", "%s | %s" % (premises.get("census_street_number"),
                                        premises.get("census_postal"))),
                ("page", "%s | %s" % (premises.get("place_street_number"),
                                      premises.get("place_postal"))))))

    census_phone = URC.digits(census.get("phone", ""))
    places_phone = URC.digits(places.get("returned_phone", ""))
    page_phone = URC.digits(row["page_telephone"])
    other = places_phone or page_phone
    if census_phone and other and census_phone == other:
        found.append(OrderedDict((
            ("signal", "TELEPHONE"), ("telephone", True),
            ("census", census_phone), ("page", other))))
    return found


def rule_identity(row: Mapping, prior: Mapping[str, str]) -> Dict:
    """Exactly one of SAME_PROPERTY / DISTINCT_PROPERTY / HOLD_IDENTITY."""
    signals = identity_signals(row)
    non_telephone = [s for s in signals if not s["telephone"]]
    key = row["identity_key"]

    if key in prior:
        verdict = HOLD_IDENTITY
        why = ("%s; a pass asked to reconcile a capture may not close an "
               "identity question another order opened" % prior[key])
    elif len(signals) >= MIN_SIGNALS and non_telephone:
        verdict = SAME_PROPERTY
        why = ("%d signals agree (%s) and %d of them are not a telephone; the "
               "gate declined it on a street SUFFIX, which is a spelling and "
               "not a building"
               % (len(signals), ", ".join(s["signal"] for s in signals),
                  len(non_telephone)))
    elif signals and not non_telephone:
        verdict = HOLD_IDENTITY
        why = ("the only agreeing signal is a telephone, and a switchboard is "
               "shared by every hotel in a building; this market holds three "
               "pairs open on exactly that evidence")
    elif not signals:
        verdict = DISTINCT_PROPERTY
        why = ("nothing agrees: no street, no name, no code, no premises and "
               "no telephone")
    else:
        verdict = HOLD_IDENTITY
        why = ("%d signal agrees and the rule needs %d"
               % (len(signals), MIN_SIGNALS))

    return OrderedDict((
        ("identity_key", key),
        ("census_canonical_name", row["census"].get("canonical_name", "")),
        ("census_address", row["census"].get("address", "")),
        ("census_postal_code", row["census"].get("postal_code", "")),
        ("census_telephone", URC.digits(row["census"].get("phone", ""))),
        ("official_url", row["source_url"]),
        ("page_title", row["page_title"]),
        ("page_name", row["page_name"]),
        ("page_address", row["page_address"]),
        ("page_telephone", row["page_telephone"]),
        ("places_binding", row["places"].get("bind_method", "")),
        ("places_place_id", row["places"].get("place_id", "")),
        ("gate_declined_because", row["gate_detail"]),
        ("signals_agreeing", signals),
        ("signal_count", len(signals)),
        ("non_telephone_signal_count", len(non_telephone)),
        ("verdict", verdict), ("why", why),
    ))


# --------------------------------------------------------------------------- #
# The policy re-read
# --------------------------------------------------------------------------- #

def page_is_property_specific(row: Mapping) -> Tuple[bool, str]:
    """Does this page describe ONE hotel, or a directory of them?

    The two Extended Stay America captures print the right address and the
    right name and are titled "Explore Our Nationwide Hotel Locations". A
    policy read off a page that lists many properties belongs to none of them,
    and 028 already measured the consequence: both ESA rows returned the
    IDENTICAL sentence.
    """
    title = row.get("page_title") or ""
    if _INDEX_TITLE.search(title):
        return (False, "the page is titled %r, which describes a directory of "
                       "properties rather than this one" % title)
    return (True, "the page title names this property alone")


def read_saved_policy(directory: Path) -> Dict:
    """Locate and read a policy block in bytes already on disk.

    The COMMITTED locator and the COMMITTED reader, which is what makes this
    comparable with the thirteen rows 028 accepted. Re-locating is the
    sanctioned move for a capture declined at the IDENTITY gate, because that
    gate runs before the locator and no block was ever cut.
    """
    html_path = directory / "rendered.html"
    if not html_path.is_file():
        return OrderedDict((("located", False),
                            ("why", "no rendered.html on disk")))
    html = html_path.read_text(encoding="utf-8", errors="replace")
    located = UC.locate_policy_in_html(html)
    if not located.found:
        return OrderedDict((("located", False),
                            ("why", "the committed locator finds no policy "
                                    "block in the saved document")))
    reading = PR.parse(located.text, strategy=located.strategy)
    result = PR.to_extraction(reading, location=located.strategy)
    return OrderedDict((
        ("located", True),
        ("locator_strategy", located.strategy),
        ("block", located.text[:600]),
        ("block_chars", len(located.text)),
        ("reader_found", bool(reading.found)),
        ("pets_allowed", reading.pets_allowed),
        ("extraction", dict(result.extraction)),
        ("evidence_quotes", [e.get("quote", "")
                             for e in (result.evidence or ())]),
        ("non_inferences", list(result.non_inferences)),
    ))


def classify_policy(reading: Mapping) -> Tuple[str, str]:
    if not reading.get("located"):
        return (POLICY_NOT_FOUND, reading.get("why", ""))
    allowed = reading.get("pets_allowed")
    if allowed is True:
        return (PET_FRIENDLY, "the located block states pets are allowed")
    if allowed is False:
        return (VERIFIED_NO_PETS, "the located block states pets are not allowed")
    return (HOLD, "a block was located and states no pets_allowed value")


# --------------------------------------------------------------------------- #
# The pass
# --------------------------------------------------------------------------- #

def run() -> Dict:
    rows = mismatch_rows()
    prior = prior_identity_rulings()
    rulings = [rule_identity(row, prior) for row in rows]
    by_key = {row["identity_key"]: row for row in rows}

    confirmed = [r for r in rulings if r["verdict"] == SAME_PROPERTY]
    readings: List[Dict] = []
    recovered_pet_friendly = 0
    recovered_no_pets = 0
    stopped_after = ""

    for ruling in sorted(confirmed, key=lambda r: r["identity_key"]):
        key = ruling["identity_key"]
        row = by_key[key]
        entry = OrderedDict((("identity_key", key),
                             ("canonical_name", ruling["census_canonical_name"])))

        # THE BRAND-PAGE WITHHOLDING IS TESTED FIRST, BEFORE THE STOP RULE.
        # It is a property of the page and holds however the reading is
        # ordered; leaving it downstream of the stop would mean the two
        # Extended Stay America rows escaped classification by luck of the
        # alphabet rather than by rule, and a different stop point would have
        # classified them.
        specific, why_specific = page_is_property_specific(row)
        if not specific:
            entry.update((("classification", WITHHELD_BRAND_PAGE),
                          ("why", why_specific)))
            readings.append(entry)
            continue

        if stopped_after:
            entry.update((("classification", NOT_READ),
                          ("why", "the target was reached at %r and the order "
                                  "says stop rather than maximise; this row's "
                                  "identity is settled and its bytes are on "
                                  "disk" % stopped_after)))
            readings.append(entry)
            continue

        reading = read_saved_policy(Path(row["declined_directory"]))
        verdict, why = classify_policy(reading)
        entry.update((("classification", verdict), ("why", why),
                      ("page_is_property_specific", True),
                      ("reading", reading)))
        readings.append(entry)

        if verdict == PET_FRIENDLY:
            recovered_pet_friendly += 1
            stopped_after = key
        elif verdict == VERIFIED_NO_PETS:
            recovered_no_pets += 1

    clean_total = CLEAN_FROM_028 + recovered_pet_friendly
    projected = PUBLISHED_TODAY + clean_total

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("generated_at", _now()),
        ("provider_calls", 0), ("usd_spent", 0.0), ("plan_credits_spent", 0.0),
        ("nothing_was_fetched",
         "no Places lookup, no Bright Data fetch, no Firecrawl scrape, no "
         "discovery and no new acquisition. Every byte read here was already "
         "on disk and already paid for."),
        ("identity_review", OrderedDict((
            ("reviewed", len(rulings)),
            ("rule", "two agreeing signals, at least one of them not a "
                     "telephone; a shared switchboard may never confirm an "
                     "identity on its own"),
            ("counts", OrderedDict(sorted(Counter(
                r["verdict"] for r in rulings).items()))),
            ("same_property_confirmed",
             sum(1 for r in rulings if r["verdict"] == SAME_PROPERTY)),
            ("distinct_property",
             sum(1 for r in rulings if r["verdict"] == DISTINCT_PROPERTY)),
            ("hold_identity",
             sum(1 for r in rulings if r["verdict"] == HOLD_IDENTITY)),
            ("rows", rulings),
        ))),
        ("policy_reread", OrderedDict((
            ("stack", "unlocker_capture.locate_policy_in_html then "
                      "policy_reading.parse -- the same locator and reader "
                      "that produced the thirteen rows 028 accepted"),
            ("saved_captures_were_not_altered", True),
            ("counts", OrderedDict(sorted(Counter(
                r["classification"] for r in readings).items()))),
            ("rows", readings),
        ))),
        ("stop_rule", OrderedDict((
            ("rule", "one additional clean PET_FRIENDLY row reaches 43; stop "
                     "there rather than maximise the count"),
            ("stopped_after", stopped_after),
            ("rows_left_unread", sum(1 for r in readings
                                     if r["classification"] == NOT_READ)),
            ("their_identity_is_settled",
             "the unread rows are SAME_PROPERTY_CONFIRMED and their bytes are "
             "on disk, so a later order can take them if the founder ever "
             "wants more than the target"),
        ))),
        ("target", OrderedDict((
            ("published_today", PUBLISHED_TODAY),
            ("clean_pet_friendly_from_028", CLEAN_FROM_028),
            ("additional_pet_friendly_recovered", recovered_pet_friendly),
            ("additional_verified_no_pets_recovered", recovered_no_pets),
            ("clean_pet_friendly_candidates_total", clean_total),
            ("projected_final_published_pet_friendly", projected),
            ("target", TARGET),
            ("target_reached", projected >= TARGET),
            ("caveat", "PROJECTED, not published. Every candidate still needs "
                       "a founder record approval before it publishes: a FACT "
                       "ruling is not a RECORD approval."),
        ))),
        ("unresolved_remaining", OrderedDict((
            ("identity_holds", [r["identity_key"] for r in rulings
                                if r["verdict"] == HOLD_IDENTITY]),
            ("distinct_properties", [r["identity_key"] for r in rulings
                                     if r["verdict"] == DISTINCT_PROPERTY]),
            ("withheld_brand_pages", [r["identity_key"] for r in readings
                                      if r["classification"] == WITHHELD_BRAND_PAGE]),
            ("left_unread_by_the_stop_rule", [r["identity_key"] for r in readings
                                              if r["classification"] == NOT_READ]),
            ("unexpected_page_from_028",
             ["cityflatshotel grand rapids"]),
            ("why_cityflats_is_not_here",
             "028's UNEXPECTED_PAGE row kept no artifact: both lanes were "
             "tried and its property URL redirects to a site root serving "
             "Grand Rapids AND Holland. There are no saved bytes to review, "
             "so it is out of this pass's scope entirely."),
        ))),
        ("nothing_else_was_run", [
            "Places: not called", "Bright Data: not called",
            "Firecrawl: not called", "discovery: not run",
            "acquisition: not run",
            "no authority written, nothing assembled, nothing deployed",
        ]),
    ))


def founder_packet(document: Mapping) -> Dict:
    """The 7 from 028, whatever 029 recovered, and everything still open."""
    result_028 = _load(RESULT_028)
    clean_028 = [r for r in result_028["classification"]["rows"]
                 if r["classification"] == "PET_FRIENDLY"]
    no_pets_028 = [r for r in result_028["classification"]["rows"]
                   if r["classification"] == "VERIFIED_NO_PETS"]
    new_rows = [r for r in document["policy_reread"]["rows"]
                if r["classification"] in (PET_FRIENDLY, VERIFIED_NO_PETS)]
    target = document["target"]

    return OrderedDict((
        ("schema", "ptf-founder-review-packet/1.0"),
        ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("what_this_is",
         "every pet-friendly and verified-no-pets candidate this market now "
         "holds unpublished, from 028's acquisition and 029's identity "
         "reconciliation. Nothing here is signed or published."),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("counts", OrderedDict((
            ("pet_friendly_from_028", len(clean_028)),
            ("verified_no_pets_from_028", len(no_pets_028)),
            ("newly_resolved_in_029", len(new_rows)),
            ("pet_friendly_total", target["clean_pet_friendly_candidates_total"]),
        ))),
        ("pet_friendly_candidates_from_028", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("brand", r["brand"]), ("readiness", r["readiness"]),
            ("founder_decision", ""),
        )) for r in clean_028]),
        ("verified_no_pets_from_028", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("brand", r["brand"]), ("readiness", r["readiness"]),
            ("founder_decision", ""),
        )) for r in no_pets_028]),
        ("newly_resolved_in_029", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("classification", r["classification"]),
            ("identity_verdict", SAME_PROPERTY),
            ("policy_block", (r.get("reading") or {}).get("block", "")[:400]),
            ("evidence_quotes",
             (r.get("reading") or {}).get("evidence_quotes", [])),
            ("extraction", (r.get("reading") or {}).get("extraction", {})),
            ("needs", "a founder identity ruling AND a record approval: this "
                      "row was declined by the identity gate and is being "
                      "proposed on a reconciliation, not on a clean capture"),
            ("founder_decision", ""),
        )) for r in new_rows]),
        ("remaining_identity_holds",
         document["unresolved_remaining"]["identity_holds"]),
        ("still_open_but_settled_on_identity", OrderedDict((
            ("left_unread_by_the_stop_rule",
             document["unresolved_remaining"]["left_unread_by_the_stop_rule"]),
            ("withheld_brand_pages",
             document["unresolved_remaining"]["withheld_brand_pages"]),
        ))),
        ("target", OrderedDict((
            ("published_today", PUBLISHED_TODAY),
            ("if_every_row_here_is_approved",
             target["projected_final_published_pet_friendly"]),
            ("target", TARGET), ("target_reached", target["target_reached"]),
        ))),
        ("founder_decision", ""), ("founder_reviewer_id", ""),
        ("founder_reviewed_at", ""),
        ("review_status", "MACHINE_REVIEWED_PENDING_OPERATOR"),
        ("nothing_is_signed_here",
         "never sign an approval in the operator's name: the reviewer id and "
         "the decision are left empty for a human to fill"),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    document = run()
    Path(args.out).write_text(json.dumps(document, indent=2) + "\n",
                              encoding="utf-8")
    PACKET_PATH.write_text(json.dumps(founder_packet(document), indent=2) + "\n",
                           encoding="utf-8")

    review, reread = document["identity_review"], document["policy_reread"]
    target = document["target"]
    print("identity reviewed        %d" % review["reviewed"])
    print("  SAME_PROPERTY_CONFIRMED %d" % review["same_property_confirmed"])
    print("  DISTINCT_PROPERTY       %d" % review["distinct_property"])
    print("  HOLD_IDENTITY           %d" % review["hold_identity"])
    print("policy re-read           %s" % dict(reread["counts"]))
    print("stopped after            %r (rows left unread: %d)"
          % (document["stop_rule"]["stopped_after"],
             document["stop_rule"]["rows_left_unread"]))
    print("additional pet-friendly  %d" % target["additional_pet_friendly_recovered"])
    print("additional no-pets       %d" % target["additional_verified_no_pets_recovered"])
    print("clean candidates total   %d" % target["clean_pet_friendly_candidates_total"])
    print("projected published      %d   target %d   reached=%s"
          % (target["projected_final_published_pet_friendly"],
             target["target"], target["target_reached"]))
    print("provider calls           %d   spend $%.2f"
          % (document["provider_calls"], document["usd_spent"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
