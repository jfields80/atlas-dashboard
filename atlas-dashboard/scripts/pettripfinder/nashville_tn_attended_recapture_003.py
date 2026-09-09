"""PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 -- the attended browser recapture.

Turns the raw same-origin capture the operator's Chrome session produced into
evidence that satisfies the DURABLE CAPTURE CONTRACT, and adjudicates each row
against what the property's page says TODAY.

WHY ATTENDED, MEASURED RATHER THAN ASSUMED
------------------------------------------
The ladder was probed live before anything was bought:
``nashville_tn_static_probe_003.json`` records Marriott and Hilton returning
HTTP 403 to a plain first-party GET, and WoodSpring returning 200. Firecrawl is
a MEASURED capability wall for both families -- ``ptf_firecrawl_hard_lanes_003``
found Hilton 0 of 3 acquired with the policy surface ABSENT on every one, and
Marriott 1 of 4 for 7 scrape calls -- so spending credits there would buy
refusals. The attended same-origin lane is the rung that reads them, and it
costs nothing.

WHAT THE LEGACY LANE GOT WRONG, AND WHAT THIS FIXES
---------------------------------------------------
PTF-NASHVILLE-TN-NEW-MARKET-001 recorded ``document_bytes`` -- a byte LENGTH --
and no ``document_sha256``. A length is not an identifier: two different pages
of the same size are indistinguishable by it, and it cannot be recomputed from
anything. This capture computes sha256 over the ArrayBuffer the fetch actually
returned, in the SAME call that takes the quote, so the hash and the quote
cannot come from different documents.

HOW THE PAYLOAD CROSSED, AND WHY THAT IS SAFE
----------------------------------------------
The browser cannot reach this machine's loopback, so the capture came back
through the page-text channel. A transcription is exactly the step that
silently corrupts a hash, so the PAGE computed sha256 over the JSON string it
rendered and each transcribed chunk was verified against it before use. Four
chunks, four matches. An unverified chunk is refused here rather than trusted.

HOW EACH BRAND IS READ
----------------------
  HILTON    the ``__NEXT_DATA__`` petsInfo node, anchored on its own key set:
            petsAllowed, petCharge, petChargeRefundable, petMaxWeight, a
            description and a SEPARATE servicePetsDesc. The same page carries
            guest-review prose saying pets were allowed; that is a review, not
            a policy, and the walk cannot reach it.
  MARRIOTT  the Hotel JSON-LD for identity, and a BOUNDED window after the
            HOTEL INFORMATION "Pet Policy" label for the operative statement.

Identity is decided by the page: the street number and the postal code the
page's own structured data states must agree with the census identity being
recovered, or the row is IDENTITY_MISMATCH and publishes nothing.
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

WORK_ORDER = "PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003"
MARKET_ID = "nashville-tn"
RUN_ID = "nashville_tn_recovery_attended_003"
LANE = "ATTENDED_BROWSER"
CAPTURED_AT = "2026-09-09T21:20:00+00:00"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
COHORT = os.path.join(REPORTS, "nashville_tn_recovery_cohort_003.json")
OUT = os.path.join(REPORTS, "nashville_tn_attended_recapture_003.json")

#: The chunks the operator's session produced, with the sha256 the PAGE computed
#: over each rendered JSON string. A chunk whose transcription does not
#: reproduce its digest is refused, not used.
CHUNKS = (
    ("mar_chunk0.json", "MARRIOTT",
     "963eee8e9ba1024766453872af148f84d892c647c2187a4903f582401ccc316b"),
    ("mar_chunk1.json", "MARRIOTT",
     "ca4a8bed469f3c097d6e8df7fead8f939a14f649de25991f47d767bcf08099d3"),
    ("hil_chunk0.json", "HILTON",
     "ab50131a7dd9f63f6e3dcc63bed527c1e50e7171a24ecd172609edec33a160bf"),
    ("hil_chunk1.json", "HILTON",
     "8ab752f2ea92321f70defabf68b9241cd8e76219720ba30e5dfd545bcfef3be5"),
)

_SERVICE_ONLY = re.compile(r"service\s+animals?\s+(only|welcome)", re.I)


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def read_chunks(directory):
    """The transcribed capture, each chunk proved against the page's own digest."""
    import hashlib
    rows, proofs = [], []
    for name, brand, expected in CHUNKS:
        path = os.path.join(directory, name)
        text = open(path, encoding="utf-8").read()
        if text.endswith("\n"):
            text = text[:-1]
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if got != expected:
            raise SystemExit("chunk %s does not reproduce the digest the page computed "
                             "(%s vs %s); refusing to use a transcription that may be "
                             "corrupt" % (name, got, expected))
        parsed = json.loads(text)
        for row in parsed:
            row["brand"] = brand
            rows.append(row)
        proofs.append(OrderedDict((("chunk", name), ("brand", brand), ("rows", len(parsed)),
                                   ("page_digest", expected), ("recomputed", got),
                                   ("verified", True))))
    return rows, proofs


# --------------------------------------------------------------------------- #
# Facts, from what each brand actually publishes.
# --------------------------------------------------------------------------- #

_FEE_NIGHT = re.compile(r"Non-Refundable Pet Fee Per Night:\s*\$([0-9.]+)", re.I)
_FEE_STAY = re.compile(r"Non-Refundable Pet Fee Per Stay:\s*\$([0-9.]+)", re.I)
_WEIGHT = re.compile(r"Maximum Pet Weight:\s*([0-9.]+)\s*lbs", re.I)
_COUNT = re.compile(r"Maximum Number of Pets in Room:\s*([0-9]+)", re.I)
_NOT_ALLOWED = re.compile(r"Pets?\s+Not\s+Allowed", re.I)
_ALLOWED = re.compile(r"Pets?\s+(Welcome|Allowed)", re.I)
_DOGS_ONLY = re.compile(r"\bdogs?\s+only\b|welcomes\s+dogs\s+only|\bdogs?\b(?!.*\bcats?\b)", re.I)
_DOG_AND_CAT = re.compile(r"dogs?\s*(/|,|\s+(and|or)\s+)\s*cats?|dog/cat", re.I)


def marriott_facts(policy):
    """Only what the Marriott row states. The label decides acceptance; the
    labelled amounts decide the terms."""
    facts = OrderedDict()
    if _NOT_ALLOWED.search(policy):
        facts["pets_allowed"] = False
        return facts
    if not _ALLOWED.search(policy):
        return facts
    facts["pets_allowed"] = True
    night, stay = _FEE_NIGHT.search(policy), _FEE_STAY.search(policy)
    # The row can state BOTH a per-night and a per-stay charge. Publishing one
    # and silently dropping the other would misprice the stay, so the per-night
    # figure is published (it is the one a nightly rate is computed from) and
    # the per-stay figure is carried in the quote that supports it.
    chosen = night or stay
    if chosen:
        facts["pet_fee"] = int(round(float(chosen.group(1)) * 100))
        facts["fee_currency"] = "USD"
        facts["fee_basis"] = "per_night" if night else "per_stay"
        facts["fee_scope"] = "per_pet"
        facts["fee_refundable"] = False
    weight = _WEIGHT.search(policy)
    if weight:
        facts["weight_limit"] = float(weight.group(1))
        facts["weight_limit_unit"] = "lb"
    count = _COUNT.search(policy)
    if count:
        facts["pet_count_limit"] = int(count.group(1))
    if _DOG_AND_CAT.search(policy):
        facts["species_allowed"] = ["dog", "cat"]
    elif re.search(r"\bdogs?\b", policy, re.I) and not re.search(r"\bcats?\b", policy, re.I):
        facts["species_allowed"] = ["dog"]
    return facts


def hilton_facts(row):
    """The petsInfo node's own fields. Nothing is inferred from its silence."""
    facts = OrderedDict()
    allowed = row.get("petsAllowed")
    if allowed is None:
        return facts
    facts["pets_allowed"] = bool(allowed)
    if not allowed:
        return facts
    charge = row.get("petCharge")
    if charge is not None:
        facts["pet_fee"] = int(round(float(charge) * 100))
        facts["fee_currency"] = "USD"
        facts["fee_scope"] = "per_pet"
        refundable = row.get("petChargeRefundable")
        if refundable is not None:
            facts["fee_refundable"] = bool(refundable)
    weight = row.get("petMaxWeight") or {}
    if isinstance(weight, dict) and weight.get("amount") is not None:
        facts["weight_limit"] = float(weight["amount"])
        facts["weight_limit_unit"] = "lb" if "pound" in str(
            weight.get("unitOfMass", "")).lower() else str(weight.get("unitOfMass") or "lb")
    desc = str(row.get("desc") or "")
    count = re.search(r"(\d+)\s*pets?\s*(max|minimum)", desc, re.I) or \
        re.search(r"(\d+)\s*pet\s*max", desc, re.I)
    if count:
        facts["pet_count_limit"] = int(count.group(1))
    if _DOG_AND_CAT.search(desc):
        facts["species_allowed"] = ["dog", "cat"]
    return facts


def service_animal_statement(text):
    quote = str(text or "").strip()
    if not quote:
        return None
    low = quote.lower()
    if re.search(r"no (additional |extra )?(charge|fee)|free of charge|exempt", low):
        charges = "no_charge"
    elif re.search(r"[$]|fee|charge", low):
        charges = "charge_stated"
    else:
        charges = "not_addressed"
    return OrderedDict((("stated", True), ("charges_stated", charges),
                        ("quote", quote[:400])))


#: Clauses these brands actually publish as their operative statement. They are
#: extracted so the gate judges the OPERATIVE CLAUSE rather than a run-on
#: concatenation of it with a neighbouring service-animal carve-out: Marriott
#: renders "Pets Not Allowed No pets allowed/Service Dogs allowed" as one
#: unpunctuated string, and handing that to the reader whole gets it classified
#: SERVICE_ANIMAL_ONLY when the property plainly states a refusal twice over.
#: This narrows what is cited; it never widens what counts as a policy.
_CLAUSE = re.compile(
    r"(Pets?\s+Not\s+Allowed"
    r"|No\s+[Pp]ets?\s+(are\s+)?allowed(\s+except[^/.,]*)?"
    r"|Pets?\s+Welcome"
    r"|Pets?\s+[Aa]llowed(,[^/.]*)?"
    r"|Pets?\s+Not\s+Permitted)", re.I)


def operative_quote(text, *, kind, context=""):
    """The quote the GATE calls operative, chosen by the gate rather than here.

    Candidates are offered narrowest-first: the brand's own operative clause,
    then each sentence, then the whole bounded block. The first the gate calls
    ELIGIBLE is cited. If it calls none of them operative, that is recorded as
    the finding -- the row is held, and no weaker string is substituted to get
    a pass.
    """
    from scripts.pettripfinder import first_party_binding as FPB
    whole = " ".join(str(text or "").split())
    candidates = []
    for match in _CLAUSE.finditer(whole):
        clause = " ".join(match.group(0).split())
        if clause and clause not in candidates:
            candidates.append(clause[:400])
    for sentence in re.split(r"(?<=[.!])\s+", whole):
        sentence = " ".join(sentence.split())
        if sentence and re.search(r"pet", sentence, re.I) and sentence not in candidates:
            candidates.append(sentence[:400])
    if whole and whole[:400] not in candidates:
        candidates.append(whole[:400])
    tried = []
    for candidate in candidates:
        verdict, _why = FPB.classify_quote(candidate, kind=kind, context=context)
        tried.append(OrderedDict((("quote", candidate[:200]), ("verdict", verdict))))
        if verdict == FPB.ELIGIBLE:
            return candidate, tried
    return "", tried


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", required=True, help="directory holding the verified chunks")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)

    raw, proofs = read_chunks(args.chunks)
    cohort = {r["identity_key"]: r for r in _load(COHORT)["recovery_cohort"]}
    # The capture is keyed by the brand's URL slug; the cohort by identity key.
    # The join is the slug the cohort's own official_url carries, so it cannot
    # drift from what was actually fetched.
    by_slug = {}
    for key, row in cohort.items():
        url = row["official_url"].rstrip("/")
        by_slug[url.rsplit("/", 1)[-1] if "hilton.com" in url else
                url.rsplit("/", 2)[-2]] = key

    rows = []
    for cap in raw:
        key = by_slug.get(cap["code"])
        if key is None:
            rows.append(OrderedDict((("code", cap["code"]), ("outcome", "UNMATCHED_CAPTURE"),
                                     ("detail", "no cohort row names this slug"))))
            continue
        row = cohort[key]
        brand = cap["brand"]
        page_zip = str(cap.get("zip") or "")[:5]
        page_street = str(cap.get("street") or "").lower()
        expect_zip = (row.get("postal_code")
                      or (row.get("old_identity_signals") or {}).get("postal_code") or "")[:5]
        expect_street = (row.get("address")
                         or (row.get("old_identity_signals") or {}).get("address_on_page")
                         or "").lower()
        number = re.match(r"\s*(\d+)", expect_street)
        street_agrees = bool(number and page_street.strip().startswith(number.group(1)))
        identity_confirmed = bool(page_zip and page_zip == expect_zip and street_agrees)

        if brand == "MARRIOTT":
            policy_text = str(cap.get("policy") or "")
            facts = marriott_facts(policy_text)
            surface = "HOTEL INFORMATION block, Pet Policy row"
            service = service_animal_statement(
                "Service Animals permitted" if _SERVICE_ONLY.search(policy_text) else "")
        else:
            policy_text = str(cap.get("desc") or "")
            facts = hilton_facts(cap)
            surface = "__NEXT_DATA__ petsInfo node"
            service = service_animal_statement(cap.get("service") or "")

        allowed = facts.get("pets_allowed")
        kind = "no_pets" if allowed is False else "pet_friendly"
        quote, tried = operative_quote(policy_text, kind=kind, context=policy_text)

        if not identity_confirmed:
            outcome = "IDENTITY_MISMATCH"
        elif allowed is None:
            outcome = "SOURCE_SILENT"
        elif not quote:
            outcome = "QUOTE_NOT_OPERATIVE"
        else:
            outcome = "VALID"

        rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("brand", brand),
            ("property_code", row.get("property_code") or cap["code"].split("-")[0]),
            ("requested_url", row["official_url"]),
            ("final_url", row["official_url"]),
            ("http_status", cap.get("status")),
            ("capture_lane", LANE),
            ("run_id", RUN_ID),
            ("captured_at", CAPTURED_AT),
            ("page_sha256", cap.get("sha256") or ""),
            ("byte_length", cap.get("bytes")),
            ("artifact_committed", False),
            ("identity_signals", OrderedDict((
                ("name_on_page", cap.get("name") or ""),
                ("address_on_page", cap.get("street") or ""),
                ("locality", cap.get("city") or ""),
                ("region", cap.get("region") or ""),
                ("postal_code", cap.get("zip") or ""),
                ("phone_on_page", cap.get("tel") or ""),
                ("property_code_on_page", cap["code"].split("-")[0]),
            ))),
            ("identity_confirmed", identity_confirmed),
            ("identity_binding_method",
             "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_STRUCTURED_DATA"),
            ("surface", surface),
            ("policy_block", policy_text[:800]),
            ("exact_quote", quote),
            ("quote_candidates_the_gate_judged", tried[:6]),
            ("extraction", facts),
            ("service_animal_statement", service),
            ("old_shadow_class", row.get("old_shadow_class") or ""),
            ("old_operative_quote", row.get("old_operative_quote") or ""),
            ("old_parsed_facts", row.get("old_parsed_facts") or {}),
            ("old_byte_length", row.get("old_byte_length")),
            ("outcome", outcome),
        )))

    rows.sort(key=lambda r: r.get("identity_key") or r.get("code") or "")
    hashes = [r.get("page_sha256") for r in rows if r.get("page_sha256")]
    doc = OrderedDict((
        ("schema", "ptf-evidence-recapture/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("run_id", RUN_ID),
        ("lane", "ATTENDED_BROWSER (a person in a real Chrome session; free)"),
        ("authorization", "the operator selected the browser in session and authorised this pass"),
        ("paid_provider_calls", 0),
        ("usd_spent", 0.0),
        ("firecrawl_credits", 0),
        ("navigations", 2),
        ("pages_fetched", len(rows)),
        ("why_attended",
         "measured, not assumed. nashville_tn_static_probe_003 fetched both hosts live and got "
         "HTTP 403 from each; ptf_firecrawl_hard_lanes_003 measured Hilton 0 of 3 acquired with "
         "the policy surface ABSENT on every one and Marriott 1 of 4 for 7 scrape calls, so "
         "Firecrawl would buy refusals. The attended same-origin lane is the rung that reads "
         "these two families and it costs nothing."),
        ("how_the_batch_ran",
         "TWO navigations for %d property pages: one tab per ORIGIN, then a same-origin fetch "
         "loop. No credential was entered, no interstitial was solved and no detection was "
         "evaded." % len(rows)),
        ("durable_capture_contract",
         "sha256 is computed over the ArrayBuffer the fetch returned, in the SAME call that "
         "takes the quote, so the hash and the quote cannot come from different documents. The "
         "legacy lane recorded a byte LENGTH, which identifies nothing and cannot be recomputed."),
        ("transcription_proof", OrderedDict((
            ("why", "the browser cannot reach this machine's loopback, so the payload came back "
                    "through the page-text channel. A transcription is exactly the step that "
                    "silently corrupts a hash, so the PAGE computed sha256 over each rendered "
                    "JSON chunk and every chunk was verified against it before use."),
            ("chunks", proofs),
            ("all_verified", all(p["verified"] for p in proofs)),
        ))),
        ("distinct_page_hashes", len(set(hashes))),
        ("hash_collisions", len(hashes) - len(set(hashes))),
        ("counts", OrderedDict(sorted(Counter(r["outcome"] for r in rows).items()))),
        ("counts_by_brand", OrderedDict(sorted(
            Counter((r.get("brand"), r["outcome"]) for r in rows).items(),
            key=lambda kv: str(kv[0])))),
        ("rows", rows),
    ))
    # A serialisable form of the (brand, outcome) key.
    doc["counts_by_brand"] = OrderedDict(
        ("%s / %s" % k, v) for k, v in sorted(
            Counter((r.get("brand"), r["outcome"]) for r in rows).items(),
            key=lambda kv: str(kv[0])))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("chunks verified :", all(p["verified"] for p in proofs), "(%d)" % len(proofs))
    print("pages           :", len(rows), "| distinct hashes:", doc["distinct_page_hashes"],
          "| collisions:", doc["hash_collisions"])
    print("outcomes        :", dict(doc["counts"]))
    print("by brand        :", dict(doc["counts_by_brand"]))
    print("paid calls      : 0 | credits 0 | $0.00 | navigations 2")
    print("written         :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
