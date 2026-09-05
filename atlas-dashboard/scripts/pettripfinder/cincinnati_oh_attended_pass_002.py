"""PTF-CINCINNATI-PARALLEL-REVALIDATION-002 -- Phase 13, the attended pass.

PTF-CINCINNATI-HARDENED-REVALIDATION-001 refused Marriott and Hilton as a
"measured capability wall". That reading was correct about the lanes it had
run -- a plain static client and Firecrawl are both refused by those origins --
and wrong as a statement about the properties. Inside the brand's own origin,
in an attended session, the same pages serve their pet policy in the markup.
This order walked that wall.

The technique is the Cleveland one: enter the origin once, then read a whole
brand cohort by same-origin fetch. Each row is one request. For every row the
sha256 of the exact response bytes is computed in the SAME call that reads the
quote, so the hash and the quote are provably about one document.

Identity is bound on the page's own declared fields -- the property's postal
code and street from its structured Hotel record -- never on the position of a
row in a list and never on the URL alone.

What is NOT accepted as evidence here:
    an amenity chip ("Pet-Friendly Accommodation", "Pet Friendly" on a search
      facet) is a category label, not a policy;
    a site-wide footer link ("Pets Stay Free Details") is not this property
      speaking about itself;
    a service-animal sentence alone is never pet acceptance;
    silence is never a refusal.

Nothing here writes authority. The output is one report.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CAPTURES = os.path.join(REPORTS, "cincinnati_oh_attended_captures_002.json")
OUT = os.path.join(REPORTS, "cincinnati_oh_attended_pass_002.json")

WORK_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-attended-pass/1.0"

REFUSAL = re.compile(r"pets\s+not\s+allowed|no\s+pets\s+allowed|service\s+animals?\s+only", re.I)
ACCEPT = re.compile(r"pets?\s+(are\s+)?(welcome|allowed)|dogs?\s+are\s+welcome", re.I)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def house_number(text):
    match = re.match(r"\s*(\d+)", text or "")
    return match.group(1) if match else None


def operative_quote(row):
    """The contiguous words the property used about its own pets.

    Marriott, Hyatt, Choice and IHG print a pet-policy section and the capture
    keeps it verbatim. Hilton prints a template label ("Pets allowed Yes
    Deposit") and carries the property-specific sentence in a structured
    description beside it. The description is the operative text; the label
    alone would publish a template.
    """
    if row.get("quote"):
        return row["quote"]
    if row.get("desc"):
        label = row.get("label")
        return "%s -- %s" % (label, row["desc"]) if label else row["desc"]
    return None


def classify(row):
    """One capture -> one Phase 13 verdict, on the page's own words."""
    if row.get("outcome") == "DEAD_ROUTE_DOMAIN_REPURPOSED":
        return "CAPTURE_FAILED", ("the committed route resolves, but to a site that is not this hotel's. "
                                 "A live 200 from a repurposed domain is a dead route, not an observation.")
    if row.get("outcome") == "UNEXPECTED_PAGE":
        return "CAPTURE_FAILED", ("the property URL redirects to a brand search page; nothing on it is this "
                                  "property speaking about itself")
    if row.get("evidence_grade") == "AMENITY_CHIP_ONLY":
        return "POLICY_NOT_FOUND", ("the only pet language on the page is an amenity card and a site-wide "
                                    "footer link; neither is this property's policy")
    quote = operative_quote(row)
    allowed = row.get("petsAllowed")
    if quote is None and allowed is None:
        return "SOURCE_SILENT", "the page served and bound to this identity, and says nothing about pets"
    if allowed is True:
        return "CLEAN_PET_FRIENDLY", "the brand's own structured policy field says pets are allowed"
    if allowed is False:
        return "CLEAN_VERIFIED_NO_PETS", "the brand's own structured policy field says pets are not allowed"
    if REFUSAL.search(quote or ""):
        return "CLEAN_VERIFIED_NO_PETS", "the property's own pet-policy section states a refusal"
    if ACCEPT.search(quote or ""):
        return "CLEAN_PET_FRIENDLY", "the property's own pet-policy section states acceptance"
    return "POLICY_NOT_FOUND", "a pet-policy section exists but states neither acceptance nor refusal"


def main():
    captures = load(CAPTURES)
    census = load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    partition = load(os.path.join(PKG, "cincinnati_final_partition_001.json"))
    shadow1 = load(os.path.join(REPORTS, "cincinnati_oh_shadow_reconciliation_001.json"))

    by_key = {h["identity_key"]: h for h in census["hotels"]}
    items = {i["identity_key"]: i for i in partition["items"]}
    # Route a capture back to the identity whose committed official_url it is.
    by_url = {}
    for item in partition["items"]:
        url = (item.get("official_url") or "").strip()
        if url:
            by_url.setdefault(url.rstrip("/"), item["identity_key"])

    already_clean = ({r["identity_key"] for r in shadow1["phase_14_clean_pending_inventory"]["rows_pet_friendly"]}
                     | {r["identity_key"] for r in shadow1["phase_14_clean_pending_inventory"]["rows_verified_no_pets"]})

    # How many census identities share a postal code with each other? A postal
    # code that two rows share cannot, on its own, tell them apart.
    postal_population = Counter((h.get("postal_code") or "").strip() for h in census["hotels"])

    rows = []
    for family in ("marriott", "hilton", "hyatt", "choice", "other"):
        for capture in captures.get(family, []):
            url = capture["url"].rstrip("/")
            key = by_url.get(url)
            verdict, why = classify(capture)

            identity = {"bound_on": [], "conflicts": []}
            hotel = by_key.get(key) if key else None
            if hotel:
                want_postal = (hotel.get("postal_code") or "").strip()
                got_postal = (capture.get("postal") or "").strip()[:5]
                if want_postal and got_postal:
                    if want_postal == got_postal:
                        identity["bound_on"].append("postal_code")
                    else:
                        identity["conflicts"].append("postal %s vs %s" % (want_postal, got_postal))
                want_street = house_number(hotel.get("address"))
                got_street = house_number(capture.get("street") or capture.get("street_header"))
                if want_street and got_street:
                    if want_street == got_street:
                        identity["bound_on"].append("street_number")
                    else:
                        identity["conflicts"].append("street number %s vs %s" % (want_street, got_street))
                identity["bound_on"].append("committed_official_url")

            if identity["conflicts"]:
                verdict, why = "IDENTITY_MISMATCH", ("the page's own declared address disagrees with the "
                                                     "census row this route belongs to")
            elif (verdict.startswith("CLEAN_")
                  and set(identity["bound_on"]) == {"committed_official_url", "postal_code"}
                  and postal_population.get((hotel or {}).get("postal_code", ""), 0) > 1):
                # A postal code shared with other census identities cannot tell
                # this row apart from its neighbours. Mason 45040 carries two
                # Choice properties; a ZIP match picks neither of them.
                verdict, why = "IDENTITY_REVIEW_REQUIRED", (
                    "the only thing the page declared that the census can check is a postal code, and %d "
                    "census identities share it. A ZIP shared with a sibling does not tell two hotels apart."
                    % postal_population[(hotel or {}).get("postal_code", "")])
            elif verdict.startswith("CLEAN_") and not (set(identity["bound_on"]) - {"committed_official_url"}):
                # A route is a claim about identity, not a proof of one. A clean
                # row has to be corroborated by something the PAGE declares about
                # itself; a slug that reads like the right hotel is not that.
                verdict, why = "IDENTITY_REVIEW_REQUIRED", (
                    "the page served a usable policy but declared no address of its own, so the only thing "
                    "tying it to this census row is the committed URL. A route is a claim about identity, "
                    "never a proof of one.")
            if capture.get("street_in_prose"):
                identity["conflicts"].append(
                    "the page names two different streets for itself: header %r, prose %r"
                    % (capture.get("street_header"), capture.get("street_in_prose")))

            rows.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", (hotel or {}).get("canonical_name")),
                ("brand_family", family.upper()),
                ("partition_state_now", (items.get(key) or {}).get("final_state")),
                ("already_in_001_clean_inventory", key in already_clean if key else None),
                ("canonical_url", capture["url"]),
                ("document_sha256", "sha256:" + capture["sha256"]),
                ("document_bytes", capture["bytes"]),
                ("identity_binding", identity),
                ("verdict", verdict),
                ("why", why),
                ("exact_quote", operative_quote(capture)),
                ("brand_structured_pets_allowed", capture.get("petsAllowed")),
                ("brand_structured_charge_refundable", capture.get("petChargeRefundable")),
                ("source_note", capture.get("note")),
                ("source_internal_conflict", capture.get("internal_conflict")),
            ]))

    unbound = [r for r in rows if not r["identity_key"]]
    report = OrderedDict()
    report["schema"] = SCHEMA
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET_ID
    report["phase"] = "13 -- attended browser, after the free static and Firecrawl rungs were exhausted by 001"
    report["run_id"] = "cincinnati_oh_attended_002"
    report["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["lane"] = "attended browser; same-origin fetch inside the brand's own origin"
    report["usd_spent"] = 0.0
    report["paid_provider_calls"] = 0
    report["plan_credits_spent"] = 0
    report["authority_mutation"] = "NONE"
    report["what_001_said"] = (
        "PTF-CINCINNATI-HARDENED-REVALIDATION-001 refused Marriott and Hilton as a measured capability wall "
        "and never became Firecrawl candidates. That was true of the static and Firecrawl lanes and is not "
        "true of the attended lane, which this order ran and which served every one of those rows.")
    report["attempted_rows"] = len(rows)
    report["rows_bound_to_an_identity"] = len(rows) - len(unbound)
    report["rows_unbound"] = len(unbound)
    report["distinct_document_hashes"] = len({r["document_sha256"] for r in rows})
    report["verdict_counts"] = OrderedDict(sorted(Counter(r["verdict"] for r in rows).items()))
    report["verdict_counts_by_family"] = {
        fam: OrderedDict(sorted(Counter(r["verdict"] for r in rows if r["brand_family"] == fam).items()))
        for fam in sorted({r["brand_family"] for r in rows})}
    report["evidence_refused"] = [
        "an amenity chip is a category label, never a pet policy",
        "a site-wide footer link is not this property speaking about itself",
        "a service-animal sentence alone is never pet acceptance",
        "silence is never a refusal",
    ]
    report["rows"] = rows

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("wrote", OUT)
    print(json.dumps(report["verdict_counts"], indent=2))
    print("bound", report["rows_bound_to_an_identity"], "of", report["attempted_rows"],
          "| distinct hashes", report["distinct_document_hashes"])
    for row in rows:
        if row["verdict"] in ("IDENTITY_MISMATCH", "CAPTURE_FAILED") or not row["identity_key"]:
            print("  !", row["verdict"], row["identity_key"], row["canonical_url"][:70])


if __name__ == "__main__":
    main()
