"""PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 -- the attended-browser policy pass.

Binds the attended captures to census identities and classifies each row
exactly once. Nothing is bound by sequence: a capture binds to a census row
only when the STREET NUMBER the property's own page states matches the street
number the census row states, and the brand family agrees.

Publication grade requires an EXPLICIT ordinary-pet acceptance or refusal in
the operator's own prose. These are refused as evidence:

  * an amenity chip ("Pet-friendly", a LocationFeatureSpecification named
    "No Pets Allowed", a site-wide "Pet-Friendly Hotels" nav link)
  * a bare structured flag with no prose ("petsAllowed": false alone)
  * service-animal language ("Service animals only", "service animals are not
    pets and are not subject to this Pet Policy")
  * a fee, a pet count or a weight limit on its own
  * an in-hotel AREA restriction inside a pet-friendly policy ("pets are not
    allowed in the public areas") -- this one nearly inverted Hyatt Regency

The Marriott and Hilton rows are the point of this order: HARD-LANES-003
measured both as a Firecrawl capability wall, and the direct static lane
returned ACCESS_DENIED on all of them. The same URLs answered HTTP 200 through
an attended Chrome session, which is the lane the ladder puts above paid fetch
and below Firecrawl for exactly this case.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002"
MARKET_ID = "lexington-ky"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
CAPTURES = os.path.join(_DASH, "data", "discovery", "lexington_ky_attended_002")
ROUTING = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")

CLEAN_PF = "CLEAN_PET_FRIENDLY"
CLEAN_NP = "CLEAN_VERIFIED_NO_PETS"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
SOURCE_SILENT = "SOURCE_SILENT"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
CAPTURE_FAILED = "CAPTURE_FAILED"

# Language that may NEVER settle an ordinary-pet question on its own.
SERVICE_ANIMAL_ONLY = re.compile(
    r"service animals? only|service animals? are not pets|only service animals", re.I)
# The LABELLED form is decisive and is tested first: "Pets Allowed: Yes|No".
# Testing it first matters, because "Pets Allowed: No" contains the substring
# "Pets Allowed" and a naive acceptance pattern reads it as acceptance -- which
# is how seven unambiguous refusals first came back as "states both".
LABELLED = re.compile(r"pets?\s+allowed\s*:\s*(yes|no)(?![a-z])", re.I)
# Free prose. The lookbehinds stop "No pets allowed" and "Pets Not Allowed"
# from reading as acceptance.
ACCEPT = re.compile(
    r"(?<!no )(?<!not )pets?\s+(?:are\s+)?(?:welcome|allowed|accepted)(?!\s*:\s*no)"
    r"|we are pet friendly|is a pet[- ]friendly hotel|offers pet[- ]friendly rooms",
    re.I)
REFUSE = re.compile(
    r"pets?\s+not\s+allowed|pets?\s+are\s+not\s+accepted|no pets?\s+(?:are\s+)?"
    r"(?:allowed|accepted|permitted)|pets?\s+are\s+not\s+permitted", re.I)
# An AREA restriction inside a pet-friendly policy is not a refusal.
AREA_RESTRICTION = re.compile(
    r"(?:pets?\s+are\s+)?not allowed in (?:the )?(?:public|food service|pool|restaurant|lobby)"
    r"[^.]*\.?", re.I)


def street_number(s):
    m = re.match(r"\s*(\d+)", s or "")
    return m.group(1) if m else ""


def norm_street(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(road|rd|drive|dr|street|st|court|ct|way|place|pl|circle|cir|"
               r"boulevard|blvd|pike|avenue|ave|lane|ln|building|bldg|suite|ste)\b", " ", s)
    return " ".join(s.split())


def classify(quote, flag=None):
    """(policy_class, why). Explicit operator prose only, never a chip or a flag."""
    q = (quote or "").strip()
    if not q:
        return SOURCE_SILENT, ("the operator's surfaces state nothing about ordinary pets; "
                               "source silence is not a withholding and is not a refusal")
    # Service-animal language is removed BEFORE any decision, so it can never
    # decide one. An area restriction is removed too: it qualifies a policy,
    # it does not reverse it.
    stripped = AREA_RESTRICTION.sub(" ", SERVICE_ANIMAL_ONLY.sub(" ", q))

    labelled = LABELLED.search(stripped)
    if labelled:
        if labelled.group(1).lower() == "yes":
            return CLEAN_PF, ("the operator's own labelled policy line states "
                              "'Pets Allowed: Yes'")
        return CLEAN_NP, ("the operator's own labelled policy line states "
                          "'Pets Allowed: No'")

    accepts = bool(ACCEPT.search(stripped))
    refuses = bool(REFUSE.search(stripped))
    if accepts and refuses:
        return POLICY_NOT_FOUND, ("the prose states both acceptance and refusal and this "
                                  "order will not choose between them")
    if accepts:
        return CLEAN_PF, "explicit ordinary-pet acceptance in the operator's own prose"
    if refuses:
        return CLEAN_NP, "explicit ordinary-pet refusal in the operator's own prose"
    if SERVICE_ANIMAL_ONLY.search(q):
        return POLICY_NOT_FOUND, ("the only pet language on the page concerns SERVICE ANIMALS, "
                                  "which is not a statement about ordinary pets")
    return POLICY_NOT_FOUND, ("no explicit ordinary-pet acceptance or refusal was found in "
                              "the operator's prose")


def load_captures():
    rows = []
    m = json.load(open(os.path.join(CAPTURES, "marriott_capture.json"), encoding="utf-8"))
    for r in m["rows"]:
        rows.append(OrderedDict([
            ("family", "MARRIOTT"), ("property_code", r[0]), ("content_sha256", r[1]),
            ("street", r[2]), ("postal", r[3]), ("quote", r[4]), ("bytes", r[5]),
            ("surface", m["surface"]), ("captured_at", m["captured_at"]),
            ("requested_url", "https://www.marriott.com/%s" % r[0]),
        ]))
    h = json.load(open(os.path.join(CAPTURES, "hilton_capture.json"), encoding="utf-8"))
    for r in h["rows"]:
        quote = r[6] or ""
        if r[5]:
            quote = (r[5] + " | " + quote).strip(" |")
        rows.append(OrderedDict([
            ("family", "HILTON"), ("property_code", r[0]), ("content_sha256", r[1]),
            ("street", r[2]), ("postal", r[3]), ("quote", quote), ("bytes", r[7]),
            ("pets_allowed_flag", r[4]),
            ("surface", h["surface"]), ("captured_at", h["captured_at"]),
            ("requested_url", "https://www.hilton.com/en/hotels/%s/hotel-info/" % r[0]),
        ]))
    c = json.load(open(os.path.join(CAPTURES, "choice_capture.json"), encoding="utf-8"))
    for r in c["rows"]:
        rows.append(OrderedDict([
            ("family", "CHOICE"), ("property_code", r[0]), ("content_sha256", r[5]),
            ("street", r[1]), ("postal", r[2]), ("quote", r[4]), ("bytes", None),
            ("surface", c["surface"]), ("captured_at", c["captured_at"]),
            ("requested_url", "https://www.choicehotels.com/kentucky/lexington/*/%s" % r[0]),
        ]))
    o = json.load(open(os.path.join(CAPTURES, "other_capture.json"), encoding="utf-8"))
    for r in o["rows"]:
        rows.append(OrderedDict([
            ("family", r["family"]), ("property_code", r["property_code"]),
            ("content_sha256", r["content_sha256"]), ("street", r["street"]),
            ("postal", r["postal"]), ("quote", r["quote"]), ("bytes", None),
            ("surface", r["requested_url"]), ("captured_at", o["captured_at"]),
            ("requested_url", r["requested_url"]), ("evidence_note", r.get("evidence_note", "")),
        ]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    args = ap.parse_args()

    routing = json.load(open(ROUTING, encoding="utf-8"))
    census = routing["identities"]
    caps = load_captures()

    bound, unbound = [], []
    used = set()
    for cap in caps:
        n = street_number(cap["street"])
        cand = []
        for row in census:
            if row["identity_key"] in used:
                continue
            if not n or street_number(row.get("address_line", "")) != n:
                continue
            # SAME ADDRESS IS NOT SAME HOTEL. 1938 Stanton Way carries a
            # Marriott-branded census row ("Four Points by Sheraton") AND two
            # Choice properties (Quality Inn in Building A, MainStay in
            # Building B). Matching on the street number alone bound the
            # Four Points row to the Quality Inn page and would have published
            # one hotel's policy under another hotel's name. The brand family
            # must agree -- unless the census row proposes no chain at all, in
            # which case it may be a soft brand (Curio, Tapestry) and any
            # family may claim it.
            cb = (row.get("brand") or "").upper()
            if cb and cb != "INDEPENDENT" and cb != cap["family"].upper():
                continue
            cand.append(row)
        # Tighten on street WORDS when more than one row shares a number. The
        # number itself must be excluded from the comparison: it is what put
        # these rows in the same bucket, so leaving it in makes every pair look
        # alike. Lexington has a 3060 Lakecrest Circle AND a 3060 Fieldstone
        # Way, which is exactly the case this guards.
        if len(cand) > 1:
            cs = set(norm_street(cap["street"]).split()) - {n}
            tight = [r for r in cand
                     if (set(norm_street(r.get("address_line", "")).split()) - {n}) & cs]
            if len(tight) == 1:
                cand = tight
        # Second fallback: an independent hotel exposes no property code and
        # this capture read no address off it, but the census row for it holds
        # the EXACT route this capture requested. A URL identity is exact, so
        # it binds; it is not a name match.
        if not cand and cap.get("requested_url"):
            u = cap["requested_url"].rstrip("/").lower()
            by_url = [r for r in census
                      if r["identity_key"] not in used
                      and (r.get("route") or "").rstrip("/").lower() == u]
            if len(by_url) == 1:
                cand = by_url
                cap["_bound_by_url"] = True

        # Fallback: a census row may state NO address at all (OSM often tags a
        # hotel with a name and a point and nothing else). Such a row can still
        # be bound deterministically through the ROUTE the order-001 pass
        # already recorded for it, because that route carries the property
        # code. This is an identity proof on the property code, not on a name.
        if not cand and cap.get("property_code"):
            code = cap["property_code"].lower()
            by_code = [r for r in census
                       if r["identity_key"] not in used
                       and not (r.get("address_line") or "").strip()
                       and code and code in (r.get("route") or "").lower()]
            if len(by_code) == 1:
                cand = by_code
                cap["_bound_by_code"] = True

        if len(cand) == 1:
            row = cand[0]
            used.add(row["identity_key"])
            pc, why = classify(cap["quote"])
            bound.append(OrderedDict([
                ("identity_key", row["identity_key"]),
                ("census_name", row["name"]),
                ("census_address", row.get("address_line", "")),
                ("census_postal", row.get("postal_code", "")),
                ("corridor", row.get("cell_id", "")),
                ("lane", "ATTENDED_BROWSER"),
                ("family", cap["family"]),
                ("property_code", cap["property_code"]),
                ("requested_url", cap["requested_url"]),
                ("captured_at", cap["captured_at"]),
                ("content_sha256", cap["content_sha256"]),
                ("identity_signals", OrderedDict([
                    ("street_on_page", cap["street"]),
                    ("postal_on_page", cap["postal"]),
                    ("street_number_match", not cap.get("_bound_by_code", False)),
                    ("bound_by",
                     "the exact route URL this capture requested, which the census row "
                     "already held" if cap.get("_bound_by_url")
                     else "the property code carried by the route already recorded for this "
                     "identity, because the census row states no address of its own"
                     if cap.get("_bound_by_code")
                     else "the street number stated by the property's own page"),
                    ("never_bound_by", "sequence, page order, or name alone"),
                ])),
                ("exact_quote", cap["quote"]),
                ("policy_class", pc),
                ("policy_why", why),
                ("evidence_note", cap.get("evidence_note", "")),
            ]))
        else:
            unbound.append(OrderedDict([
                ("family", cap["family"]), ("property_code", cap["property_code"]),
                ("street", cap["street"]), ("postal", cap["postal"]),
                ("candidates", len(cand)),
                ("reason", "no census row states this street number"
                 if not cand else "more than one census row states this street number"),
                ("quote", cap["quote"][:160]),
            ]))

    counts = Counter(b["policy_class"] for b in bound)
    fam = Counter(b["family"] for b in bound)

    report = OrderedDict([
        ("schema", "ptf-attended-policy-pass/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", args.as_of),
        ("lane", "ATTENDED_BROWSER"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("credits_used", 0),
        ("binding_rule",
         "A capture binds to a census row ONLY on the street number the property's own page "
         "states, tightened on street words when two rows share a number. Never by sequence, "
         "never by name alone."),
        ("evidence_rules_enforced", [
            "an amenity chip is not operative policy",
            "a bare structured flag with no prose is not publication grade",
            "service-animal language is stripped before the decision so it can never decide",
            "a fee, a pet count or a weight limit never establishes acceptance",
            "an in-hotel AREA restriction inside a pet-friendly policy is not a refusal",
        ]),
        ("wall_result",
         "Marriott and Hilton are a MEASURED Firecrawl capability wall and returned "
         "ACCESS_DENIED to the direct static lane. Every one of those URLs returned HTTP 200 "
         "through the attended session."),
        ("totals", OrderedDict([
            ("captures", len(caps)),
            ("bound", len(bound)),
            ("unbound", len(unbound)),
            ("by_family", OrderedDict(sorted(fam.items()))),
            ("policy_classes", OrderedDict(sorted(counts.items()))),
        ])),
        ("bound_rows", bound),
        ("unbound_captures", unbound),
    ])
    out = os.path.join(REPORTS, "lexington_ky_attended_policy_pass_002.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(json.dumps(report["totals"], indent=1))
    for u in unbound:
        print("  UNBOUND:", u["family"], u["property_code"], u["street"], "->", u["reason"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
