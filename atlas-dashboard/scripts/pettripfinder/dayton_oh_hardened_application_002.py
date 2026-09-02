"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phases 2 to 5.

Apply the 23-row clean inventory that PTF-DAYTON-OH-HARDENED-REVALIDATION-001
recovered: 7 CLEAN_PET_FRIENDLY into the policy package, 16
CLEAN_VERIFIED_NO_PETS into this market's exclusion shard.

The cohort is rebuilt MECHANICALLY from the committed shadow document and the
committed attended artifacts. Nothing is taken from a work-order prompt, and no
row is applied on the strength of the earlier run's classification alone: every
fact is re-read by the canonical reader from the artifact's own captured text at
application time, and every identity is re-bound against the pinned census.

Three binding guards, each for a defect order 001 actually hit:

  SPA_PREVIOUS_PROPERTY  A batched browser read can return the PREVIOUS
      property's DOM. Sequence position is not identity: the artifact's own
      captured address lines must agree with the census row, and no two rows in
      the cohort may bind on identical address lines.
  LETTER_SUFFIX_PREMISES  '6960 Miller Ln' must never match '6960B Miller Ln'.
      House numbers are compared as exact tokens, so a suffixed number binds
      only its own premises. Dayton carries two such hazards: 6960/6960B Miller
      Ln, and 1190/1195 Russ Road in Greenville.
  MARKUP_IS_NOT_PROSE  A brand markup record ('"petsAllowed" : "false"') is
      never reformatted into a sentence and handed to the reader -- rendered as
      prose it parses as True. Markup stays corroboration; a promoted fact comes
      only from the property's own prose.

Facts the current schema cannot represent safely are WITHHELD with the exact
source language and a reason. A value is never forced to preserve a parse.

Writes only this market's own authority: the policy package and the dayton-oh
exclusion shard. The pinned census is read and never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HX  # noqa: E402
from scripts.pettripfinder import policy_migration as PM  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA  # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC  # noqa: E402

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"
SOURCE_ORDER = "PTF-DAYTON-OH-HARDENED-REVALIDATION-001"
MARKET_ID = "dayton-oh"
RUN_ID = "dayton-hardened-attended-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", RUN_ID, "raw")
POLICY_PATH = os.path.join(PKG, "hotel_policy_facts_" + MARKET_ID + ".json")
EXCL_PATH = os.path.join(AUTH, "hotel_exclusions.json")
SHADOW = os.path.join(REPORTS, "dayton_oh_shadow_reconciliation_001.json")
CENSUS = os.path.join(PKG, "identity_census", MARKET_ID + ".json")

# The founder authorised this exact cohort in the work order that commissioned
# this run. The caveat on every applied record names that authorisation and
# states plainly which part was the agent's: the mechanical re-read, not the
# decision.
OPERATOR = "jfields80"
AUTHORIZATION_CAVEAT = (
    "FOUNDER AUTHORIZATION (%s): apply the 23-row clean inventory bound by %s -- "
    "7 CLEAN_PET_FRIENDLY and 16 CLEAN_VERIFIED_NO_PETS. The founder authorised "
    "this cohort by that work order; the re-read, re-binding and hashing below "
    "were performed mechanically by the agent." % (WORK_ORDER, SOURCE_ORDER))
READER_CAVEAT = (
    "Every fact was re-read at application time by the canonical reader "
    "(unlocker_capture.locate_policy_in_text -> policy_reading.parse / "
    "to_extraction) from the artifact's own captured first-party text. Fields "
    "the reader cannot represent safely are withheld with the exact source "
    "language and a reason, never inferred.")
LANE_CAVEAT = (
    "Attended Chrome, $0.00 and no provider: the artifact records the page's own "
    "address lines, its operative policy text and the document sha256 (%s). A "
    "brand markup record, where the page shipped one, is carried as "
    "corroboration only and is never the source of a published fact." % SOURCE_ORDER)

BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|moxy|element"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|ardent"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|studio 6"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|wingate"),
]


def brand_of(name):
    n = (name or "").lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def read_json(p, d=None):
    if not os.path.exists(p):
        return d
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, doc):
    with open(path, "wb") as fh:
        fh.write((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def digits(v):
    return re.sub(r"[^0-9]", "", v or "")[-10:]


def house_token(street):
    m = re.match(r"\s*(\d+[A-Za-z]?)", street or "")
    return m.group(1) if m else ""


def bind_identity(crow, address_lines, jsonld):
    """Exact-token premises binding. A suffixed house number binds only itself:
    '6960' must not match '6960B', and '1190 Russ' must not match '1195 Russ'."""
    hay = "\n".join(address_lines or []) + "\n" + json.dumps(jsonld or "")
    street = (crow or {}).get("address") or ""
    num = house_token(street)
    postal = ((crow or {}).get("postal_code") or "")[:5]
    phone = digits((crow or {}).get("phone") or "")
    parts = street.split()
    street_ok = bool(num) and len(parts) > 1 and bool(re.search(
        r"(?<![0-9A-Za-z])" + re.escape(num) + r"(?![0-9A-Za-z])[^\n]{0,40}" + re.escape(parts[1][:4]),
        hay, re.I))
    postal_ok = bool(postal) and bool(re.search(r"\b" + postal + r"\b", hay))
    phone_ok = bool(phone) and phone in re.sub(r"[^0-9]", "", hay)
    return OrderedDict([
        ("street_number_agrees", street_ok), ("postal_agrees", postal_ok),
        ("phone_agrees", phone_ok),
        ("bound", (street_ok and postal_ok) or (phone_ok and (postal_ok or street_ok))),
        ("census_house_token", num), ("census_postal", postal),
    ])


def reread(artifact, brand):
    """Re-run the canonical reader over the artifact's OWN captured windows.

    Visible policy text first, then the property-named FAQ. The brand markup
    record is deliberately not a source here: it is a key/value blob, and
    rendering it as prose makes the reader read '"petsAllowed" : "false"' as
    True.
    """
    for label in ("pet_windows", "pet_windows_faq"):
        windows = artifact.get(label) or []
        text = "\n\n".join(windows)
        if not text.strip():
            continue
        hit = UC.locate_policy_in_text(text)
        if not hit.found:
            continue
        if brand == "MARRIOTT":
            reading = MS.parse_policy_block(hit.text, locator_id=WORK_ORDER)
            result = MS.to_extraction(reading, location=MARKET_ID)
        else:
            reading = PR.parse(hit.text, strategy=hit.strategy or WORK_ORDER)
            result = PR.to_extraction(reading, location=MARKET_ID)
        return OrderedDict([
            ("source", "visible_text" if label == "pet_windows" else "property_named_faq"),
            ("block", hit.text),
            ("extraction", result.extraction),
            ("withheld", dict(result.withheld)),
            ("evidence", result.evidence),
            ("pets_allowed_quote", getattr(reading, "pets_allowed_quote", "") or ""),
            ("service_animal_quote", getattr(reading, "service_animal_quote", "") or ""),
            ("brand_generic", bool(getattr(reading, "brand_generic", False))),
            ("parser_warnings", list(result.parser_warnings)),
        ])
    return None


def facts_from_extraction(ext):
    """Project the reader's extraction onto the committed schema-1.2 fact shape.

    Anything the schema has no safe home for is NOT invented a home: it is
    returned as a withholding so the caller records it with its source language.
    """
    facts = OrderedDict()
    unmapped = OrderedDict()
    if ext.get("pets_allowed") is not None:
        facts["pets_allowed"] = bool(ext["pets_allowed"])
    fee = ext.get("pet_fee")
    if isinstance(fee, int):
        block = OrderedDict([("amount_cents", fee)])
        if ext.get("fee_currency"):
            block["currency"] = ext["fee_currency"]
        if ext.get("fee_basis"):
            block["basis"] = ext["fee_basis"]
        if ext.get("fee_scope"):
            block["scope"] = ext["fee_scope"]
        facts["pet_fee"] = block
    elif fee is not None:
        unmapped["pet_fee"] = repr(fee)
    # A deposit has NO top-level fact field. The schema's home for a named
    # charge is other_charges, whose kind comes from enums.OTHER_CHARGE_KINDS --
    # "pet_deposit" is the EVIDENCE spelling (FACT_EVIDENCE_ALIASES), not a kind.
    dep = ext.get("pet_deposit")
    if isinstance(dep, int):
        facts["other_charges"] = [OrderedDict([
            ("amount_cents", dep),
            ("currency", ext.get("fee_currency") or "USD"),
            ("kind", "refundable_deposit"),
            ("refundable_stated", True),
            ("refundable", True),
        ])]
    elif dep is not None:
        unmapped["pet_deposit"] = repr(dep)
    wl = ext.get("weight_limit")
    if isinstance(wl, dict) and wl.get("value") is not None:
        facts["weight_limit"] = OrderedDict([("value", float(wl["value"])),
                                             ("unit", wl.get("unit") or "lb"),
                                             ("operator", "lte"),
                                             ("scope", "per_pet")])
    elif wl is not None:
        unmapped["weight_limit"] = repr(wl)
    if isinstance(ext.get("pet_count_limit"), int):
        facts["pet_count_limit"] = ext["pet_count_limit"]
        # The SCOPE is published only where the source stated one. Defaulting an
        # unstated scope to "room" invents a fact and leaves it unevidenced --
        # "a maximum of 2 pets" says how many, not per what.
        scope = ext.get("pet_count_scope")
        if scope:
            facts["pet_count_scope"] = "room" if scope in ("per_room", "room") else str(scope)
    elif ext.get("pet_count_limit") is not None:
        unmapped["pet_count_limit"] = repr(ext["pet_count_limit"])
    if ext.get("species"):
        facts["species"] = ext["species"]
    if ext.get("breed_restrictions"):
        facts["breed_restrictions"] = ext["breed_restrictions"]
    # Everything the reader produced that this projection did not consume.
    consumed = {"pets_allowed", "pet_fee", "fee_currency", "fee_basis", "fee_scope",
                "pet_deposit", "weight_limit", "pet_count_limit", "pet_count_scope",
                "species", "breed_restrictions", "service_animal_exception"}
    for k, v in ext.items():
        if k not in consumed and v is not None:
            unmapped[k] = repr(v)
    return facts, unmapped


def evidence_entries(rd, source_url, doc_sha, captured_at):
    """One entry per FIELD the reader cited.

    The canonical reader emits ``field_refs`` -- a list, because one sentence can
    establish several fields ("25.00 USD per night" carries pet_fee, fee_currency
    and fee_basis). Reading a scalar ``field`` off it yields None on every entry,
    and the frozen schema rejects publication-grade evidence with no field. So
    each ref becomes its own entry, which is also the shape every committed
    market already uses.
    """
    out = []
    for e in rd.get("evidence") or []:
        refs = e.get("field_refs") or ([e["field"]] if e.get("field") else [])
        for ref in refs:
            entry = OrderedDict([
                ("field", ref),
                ("quote", e.get("quote")),
                ("source_url", source_url),
                ("value", str(e.get("value")) if e.get("value") is not None else ""),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", "sha256:" + doc_sha),
                ("artifact_kind", "rendered_html"),
                ("captured_at", captured_at),
                ("capture_method", "attended_browser"),
                ("source_grade", "PT1_FIRST_PARTY"),
            ])
            entry["evidence_ref"] = PM.evidence_ref_for(entry)
            out.append(entry)
    return out


def load_cohort():
    shadow = read_json(SHADOW)
    inv = shadow["pending_application_inventory"]
    return inv["pet_friendly_rows"], inv["verified_no_pets_rows"]


def load_artifact(row):
    path = os.path.join(RAW, row["artifact_file"])
    blob = open(path, "rb").read()
    got = hashlib.sha256(blob).hexdigest()
    want = (row.get("artifact_sha256") or "").replace("sha256:", "")
    if got != want:
        raise SystemExit("artifact sha mismatch for %s: %s != %s" % (row["identity_key"], got, want))
    return json.loads(blob.decode("utf-8")), got


def build(args):
    census = {h["identity_key"]: h for h in read_json(CENSUS)["hotels"]}
    pf_rows, np_rows = load_cohort()
    policy_doc = read_json(POLICY_PATH)
    excl_doc = read_json(EXCL_PATH)
    live_pf = {r["identity_key"] for r in policy_doc["hotels"]}
    live_np = {HX.normalize_name(e["canonical_name"]) for e in excl_doc["exclusions"]}

    audit = []
    new_policy, new_excl = [], []
    seen_address_fingerprints = {}

    for kind, rows in (("PET_FRIENDLY", pf_rows), ("VERIFIED_NO_PETS", np_rows)):
        for row in rows:
            key = row["identity_key"]
            crow = census.get(key)
            rec = OrderedDict([("identity_key", key), ("canonical_name", row["canonical_name"]),
                               ("kind", kind)])
            if crow is None:
                rec["verdict"] = "REJECTED_IDENTITY_NOT_IN_PINNED_CENSUS"
                audit.append(rec)
                continue
            artifact, doc_sha = load_artifact(row)
            brand = brand_of(crow["canonical_name"])

            # --- guard 1 + 2: exact-token premises binding, re-run now --------
            binding = bind_identity(crow, artifact.get("address_lines"), artifact.get("jsonld"))
            rec["identity_binding"] = binding
            fp = json.dumps(artifact.get("address_lines") or [], sort_keys=True)
            if fp in seen_address_fingerprints:
                rec["verdict"] = "REJECTED_SPA_PREVIOUS_PROPERTY_SUSPECTED"
                rec["collides_with"] = seen_address_fingerprints[fp]
                audit.append(rec)
                continue
            seen_address_fingerprints[fp] = key
            if not binding["bound"]:
                rec["verdict"] = "REJECTED_IDENTITY_NOT_BOUND"
                audit.append(rec)
                continue

            # --- guard 3: re-read the PROSE, never the markup -----------------
            rd = reread(artifact, brand)
            if rd is None:
                rec["verdict"] = "REJECTED_READER_FOUND_NO_POLICY_AT_APPLICATION_TIME"
                audit.append(rec)
                continue
            pa = rd["extraction"].get("pets_allowed")
            rec["reader_source"] = rd["source"]
            rec["pets_allowed"] = pa
            rec["brand_generic_wording"] = rd["brand_generic"]
            if kind == "PET_FRIENDLY" and pa is not True:
                rec["verdict"] = "REJECTED_REREAD_DOES_NOT_STATE_PET_FRIENDLY"
                audit.append(rec)
                continue
            if kind == "VERIFIED_NO_PETS" and pa is not False:
                rec["verdict"] = "REJECTED_REREAD_DOES_NOT_STATE_A_REFUSAL"
                audit.append(rec)
                continue
            mc = row.get("markup_corroboration") or {}
            if mc.get("agrees_with_prose_read") is False:
                rec["verdict"] = "REJECTED_MARKUP_CONTRADICTS_PROSE"
                audit.append(rec)
                continue
            rec["markup_corroboration"] = mc.get("agrees_with_prose_read")

            captured_at = row["captured_at"]
            src = row["canonical_url"]

            if kind == "PET_FRIENDLY":
                if key in live_pf:
                    rec["verdict"] = "REJECTED_ALREADY_PUBLISHED"
                    audit.append(rec)
                    continue
                facts, unmapped = facts_from_extraction(rd["extraction"])
                ev = evidence_entries(rd, src, doc_sha, captured_at)
                # A named charge is cited by the charge it names
                # (FACT_EVIDENCE_ALIASES: other_charges <- pet_deposit), but the
                # published fact key is other_charges, and the market's own
                # coverage guard looks the fact up by name. Sixteen committed
                # records already carry both spellings; this adds the second.
                if "other_charges" in facts and not any(e["field"] == "other_charges" for e in ev):
                    for e in list(ev):
                        if e["field"] == "pet_deposit":
                            alias = OrderedDict(e)
                            alias["field"] = "other_charges"
                            alias["evidence_ref"] = PM.evidence_ref_for(alias)
                            ev.append(alias)
                            break
                # The committed key is withheld_fields, shaped
                # {reason_code, reason, evidence_refs}. Two rules the schema
                # enforces and this pass must respect:
                #
                #   SILENCE IS NOT A WITHHOLDING. The reader reports
                #   pet_fee: SOURCE_SILENT for a page that says "Pets are
                #   welcome" and names no price. Recording that as a withholding
                #   would tell a reader the hotel withheld something it never
                #   had, so those entries are DROPPED, exactly as the schema
                #   migration dropped its 110.
                #
                #   A WITHHOLDING CITES EVIDENCE. Every entry names the evidence
                #   that shows the problem, so a reviewer can read the sentence
                #   the decision was made about.
                refs_for = {}
                for e in ev:
                    refs_for.setdefault(e["field"], []).append(e["evidence_ref"])
                section_refs = refs_for.get("pets_allowed") or [ev[0]["evidence_ref"]] if ev else []
                withheld = OrderedDict()
                for f, reason in (rd.get("withheld") or {}).items():
                    code = str(reason).upper()
                    if code == "SOURCE_SILENT":
                        continue
                    if code not in ("SOURCE_AMBIGUOUS", "SOURCE_CONTRADICTORY",
                                    "SCHEMA_CANNOT_REPRESENT", "ARTIFACT_INSUFFICIENT",
                                    "IDENTITY_NOT_CONFIRMED"):
                        code = "SOURCE_AMBIGUOUS"
                    withheld[f] = OrderedDict([
                        ("reason_code", code),
                        ("reason", str(reason)),
                        ("evidence_refs", refs_for.get(f) or section_refs),
                        ("source_language", rd["block"][:400])])
                for f, raw in unmapped.items():
                    withheld[f] = OrderedDict([
                        ("reason_code", "SCHEMA_CANNOT_REPRESENT"),
                        ("reason", "the reader produced a value the committed schema has no "
                                   "safe representation for; it is recorded rather than forced"),
                        ("evidence_refs", refs_for.get(f) or section_refs),
                        ("reader_value", raw),
                        ("source_language", rd["block"][:400])])
                record = OrderedDict([
                    ("key", key), ("name", crow["canonical_name"]), ("facts", facts),
                    ("evidence", ev), ("evidence_count", len(ev)),
                    ("evidence_quote", " ".join(e["quote"] for e in ev)[:600]),
                    ("source_url", src), ("source_type", "EXACT_ENTITY_DOMAIN"),
                    ("verification_state", "VERIFIED_PET_FRIENDLY"),
                    ("verification_date", captured_at[:10]), ("verified_at", captured_at[:10]),
                ])
                if withheld:
                    record["withheld_fields"] = withheld
                # The committed shape is STRUCTURED ({stated, charges_stated,
                # quote}), not a bare quote: canonical_view reads
                # service_animal.get("stated"), so a string here crashes the
                # renderer. charges_stated is decided by the canonical contract
                # helper rather than by a regex written here.
                sa_quote = rd.get("service_animal_quote")
                if sa_quote:
                    record["service_animal_statement"] = OrderedDict([
                        ("stated", True),
                        ("charges_stated", SA.charges_stated(sa_quote)),
                        ("quote", sa_quote),
                    ])
                record["worker_model_id"] = ""
                record["worker_prompt_version"] = ""
                record["worker_result_hash"] = doc_sha
                record["worker_routing_version"] = ""
                record["worker_validator_version"] = ""
                record["schema_version"] = "1.2"
                record["identity_key"] = key
                record["market_id"] = MARKET_ID
                # Derived by the canonical classifier. Asserting a class the facts
                # do not support is exactly what test_stored_computation_class_
                # equals_recomputation exists to catch.
                record["computation_class"] = FC.classify(facts).computation_class
                approval = OrderedDict([
                    ("decision", "APPROVED_AFTER_CURRENT_REVIEW"), ("operator", OPERATOR),
                    ("approval_date", time.strftime("%Y-%m-%d", time.gmtime())),
                    ("caveats", [AUTHORIZATION_CAVEAT, READER_CAVEAT, LANE_CAVEAT]),
                ])
                record["approval"] = approval
                approval["record_hash"] = PM.record_hash(record)
                approval["evidence_hash"] = PM.evidence_hash(ev)
                new_policy.append(record)
                rec["verdict"] = "APPLIED_PET_FRIENDLY"
                rec["facts"] = facts
                rec["withheld_fields"] = sorted(withheld)
            else:
                nn = HX.normalize_name(crow["canonical_name"])
                if nn in live_np:
                    rec["verdict"] = "REJECTED_ALREADY_EXCLUDED"
                    audit.append(rec)
                    continue
                if key in live_pf:
                    rec["verdict"] = "REJECTED_WOULD_CONTRADICT_A_PUBLISHED_PET_FRIENDLY_RECORD"
                    audit.append(rec)
                    continue
                quote = rd.get("pets_allowed_quote") or ""
                block = rd["block"]
                excl = OrderedDict([
                    ("exclusion_id", "day-" + re.sub(r"[^a-z0-9]+", "-", key).strip("-")),
                    ("canonical_name", crow["canonical_name"]),
                    ("normalized_name", nn),
                    ("address", crow["address"]), ("city", crow["city"]),
                    ("state", crow["state"]), ("postal_code", crow["postal_code"]),
                    ("official_url", src),
                    ("exclusion_state", "VERIFIED_NO_PETS"),
                    ("evidence_quote", block[:400]),
                    ("source_url", src),
                    ("observed_at", captured_at[:10]),
                    ("source_hash", doc_sha),
                    ("reviewer_id", OPERATOR),
                    ("reviewed_at", time.strftime("%Y-%m-%d", time.gmtime())),
                    ("notes", "%s. Refusal read from the property's own page by the canonical "
                              "reader at application time (matched phrase: %r). Service-animal "
                              "language is a legal access category and is never read as pet "
                              "acceptance or as a refusal on its own." % (AUTHORIZATION_CAVEAT, quote)),
                    ("market_id", MARKET_ID),
                ])
                excl["record_hash"] = "sha256:" + HX.record_hash(excl).replace("sha256:", "")
                excl["approval_hash"] = "sha256:" + HX.approval_hash(excl).replace("sha256:", "")
                new_excl.append(excl)
                rec["verdict"] = "APPLIED_VERIFIED_NO_PETS"
                rec["quote"] = quote
            audit.append(rec)

    return audit, new_policy, new_excl, policy_doc, excl_doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply to authority (default: dry run)")
    ap.add_argument("--out", default=os.path.join(REPORTS, "dayton_oh_application_002.json"))
    args = ap.parse_args(argv)
    audit, new_policy, new_excl, policy_doc, excl_doc = build(args)
    counts = Counter(r["verdict"] for r in audit)
    print("verdicts:", json.dumps(dict(sorted(counts.items())), indent=1))
    print("policy rows to add:", len(new_policy), " exclusions to add:", len(new_excl))
    print("policy %d -> %d   exclusions %d -> %d"
          % (len(policy_doc["hotels"]), len(policy_doc["hotels"]) + len(new_policy),
             len(excl_doc["exclusions"]), len(excl_doc["exclusions"]) + len(new_excl)))

    if args.write:
        policy_doc["hotels"] = policy_doc["hotels"] + new_policy
        write_json(POLICY_PATH, policy_doc)
        excl_doc["exclusions"] = excl_doc["exclusions"] + new_excl
        excl_doc["count"] = len(excl_doc["exclusions"])
        write_json(EXCL_PATH, excl_doc)
        HX.validate(read_json(EXCL_PATH))
        print("WRITTEN. exclusion shard revalidated by the canonical contract.")

    report = OrderedDict([
        ("schema", "ptf-market-application/1.0"), ("work_order", WORK_ORDER),
        ("source_order", SOURCE_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("mode", "APPLIED" if args.write else "DRY_RUN"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("cohort_size", len(audit)),
        ("verdict_counts", OrderedDict(sorted(counts.items()))),
        ("policy_rows_added", len(new_policy)), ("exclusions_added", len(new_excl)),
        ("guards", OrderedDict([
            ("SPA_PREVIOUS_PROPERTY", "no two applied rows share an address fingerprint"),
            ("LETTER_SUFFIX_PREMISES", "house numbers compared as exact tokens (6960 != 6960B, 1190 != 1195)"),
            ("MARKUP_IS_NOT_PROSE", "markup never reformatted into prose; corroboration only"),
        ])),
        ("rows", audit),
    ])
    write_json(args.out, report)
    print("written", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
