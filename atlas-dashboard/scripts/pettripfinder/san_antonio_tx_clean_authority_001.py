"""PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 -- Phases 15-19: policy adjudication over one identity per row.

Identity (census_reconciliation) and routing are already settled. This pass attaches a POLICY FACT to each
admitted TRUE_HOTEL_IDENTITY row from the evidence this order actually captured, and gives every row exactly
one disposition (Phase 19). It never re-decides identity or membership.

EVIDENCE SOURCES, EACH KEYED BACK TO A CENSUS ROW
--------------------------------------------------
  BRAND_CODE match   (brand, property_code) -- Marriott, Hilton, Hyatt, Best Western supported-browser reads
                      (marriott_browser_rows.jsonl, hilton_browser_rows.jsonl, resort_browser_rows.jsonl) and the
                      Wyndham property-service lane (wyndham_rows.json, matched on brand=WYNDHAM + house number +
                      postal code, since Wyndham's own service carries no property_code the census stores).
  IDENTITY_KEY match  the free static capture (VALID rows) and the Firecrawl pass (publication-grade rows), both
                      already keyed to the census identity_key.
  ADDRESS match       the independents' own policy/FAQ pages lane (policy_pages_rows.json), keyed to identity_key
                      directly (it was built from routing, which carries identity_key).

NEGATION SAFETY (Phase 17)
---------------------------
Every quote is scanned for an explicit refusal ("not allowed", "not accepted", "no pets", "not permitted",
"prohibited") independently of the pets_allowed flag this order read from the page. A row where the flag says
True but the quote itself contains a refusal phrase is a NEGATION_HOLD, never published. A generic amenity
badge ("pet-friendly") beside an explicit refusal is not a conflict; the explicit Pet Policy / FAQ text governs
and is what this order's pets_allowed flag was set from in the first place (see Best Western Wesley Chapel,
resort_browser_rows.jsonl).

Every row not matched to captured evidence keeps its exact router state as its hold reason: no route
(ROUTING_HOLD), a browser wall reached before this order's turn came (BROWSER_CAPTURE_NEEDED), every free/paid
lane exhausted (ACCESS_BLOCKED), or a page that served and said nothing (SOURCE_SILENT).

Output:
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_clean_authority_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH_EARLY = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH_EARLY not in sys.path:
    sys.path.insert(0, _DASH_EARLY)
from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402
from scripts.pettripfinder.san_antonio_tx_census_reconciliation_001 import canonical_street  # noqa: E402

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-antonio-tx"
SCHEMA = "ptf-clean-authority/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "san-antonio-tx", "raw_captures")
CENSUS = os.path.join(PKG, "identity_census_proposed", "san-antonio-tx.json")
ROUTING = os.path.join(REPORTS, "san_antonio_tx_routing_001.json")
STATIC = os.path.join(REPORTS, "san_antonio_tx_free_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "san_antonio_tx_firecrawl_pass_001.json")
#: The retry pass (after the census street restatement); a retry row supersedes the first pass's row for its key.
FIRECRAWL_RETRY = os.path.join(REPORTS, "san_antonio_tx_firecrawl_pass_002.json")
#: The second probe pass: rows whose route reached the router's Firecrawl rung only after the Places lane found
#: the property's own site (they were not in the static report the first cohort was planned from).
FIRECRAWL_PROBE2 = os.path.join(REPORTS, "san_antonio_tx_firecrawl_pass_003.json")


def firecrawl_rows():
    by_key = OrderedDict()
    for path in (FIRECRAWL, FIRECRAWL_RETRY, FIRECRAWL_PROBE2):
        for r in (_load(path, {}) or {}).get("rows", []):
            by_key[r["identity_key"]] = r
    return list(by_key.values())


OUT = os.path.join(REPORTS, "san_antonio_tx_clean_authority_001.json")

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"
NEGATION_HOLD = "NEGATION_HOLD"
ROUTING_HOLD = "ROUTING_HOLD"
BROWSER_CAPTURE_NEEDED = "BROWSER_CAPTURE_NEEDED"
ACCESS_BLOCKED = "ACCESS_BLOCKED"
SOURCE_SILENT = "SOURCE_SILENT"
EVIDENCE_HOLD = "EVIDENCE_HOLD"
IDENTITY_MISMATCH_HOLD = "IDENTITY_MISMATCH_HOLD"

#: "No pet fee" is an ACCEPTANCE term, not a refusal: the lookahead keeps a charge line from reading as "no pets"
#: (caught on Aloft Miami Brickell, whose page says "Pets Welcome" and "No pet fee").
_REFUSAL = re.compile(
    r"\bpets?\s+(?:are\s+)?not\s+(?:allowed|accepted|permitted)\b"
    # SAN ANTONIO: "a cleaning fee ... applies to ensure that no pet allergens are left in the guestroom" (Hotel
    # Emma, which takes dogs) read as "no pets"; a pet's hair, dander or odor is not a pet.
    r"|\bno\s+pets?\b(?!\s+(?:fee|fees|charge|charges|deposit|policy|policies|allergens?|hair|dander|odou?rs?))"
    r"|\bpets?\s+prohibited\b"
    # SAN ANTONIO: "Service dogs are welcome at the Crockett Hotel, even if not pet friendly" is a CONDITIONAL on
    # an accessibility page the Crockett (which takes pets for a fee) shares with the Menger; it refuses nothing.
    r"|(?<!\bif\s)\bnot\s+pet[- ]friendly\b|\bpets?\s+not\s+welcome\b"
    # SAN ANTONIO: Wyndham's own refusal after its service-animal sentence, "Sorry no other pets are allowed."
    r"|\bno\s+other\s+pets?\s+(?:are\s+|is\s+)?(?:allowed|accepted|permitted)\b"
    # SAN ANTONIO: the Menger's own policy page, "The hotel does not allow pets."
    r"|\b(?:does|do)\s+not\s+allow\s+(?:any\s+)?pets?\b|\bdoesn['’]?t\s+allow\s+(?:any\s+)?pets?\b"
    # SAN DIEGO: Choice's (and Hilton's) LABEL-VALUE form. Without it, "Pets Allowed: No" matched only the
    # acceptance pattern's bare "pets allowed" and 17 Choice refusals were claimed pet-friendly -- the shared
    # reader (FAST rule C) caught every one as QUOTE_CONTRADICTS_CLAIM, so none published, but none resolved.
    r"|\bpets?\s+allowed\s*:\s*no\b"
    # AUSTIN: three refusal shapes this market's own pages use, each measured on a read that the narrower
    # pattern missed. (1) A parenthetical between the noun and the verb: Kalahari Round Rock's own FAQ, "pets
    # (including ESAs) are not permitted" -- missed, and with the FAQ question "Are pets allowed?" read as
    # acceptance the refusal PUBLISHED AS PET-FRIENDLY. (2) "Sorry, pets cannot be accommodated" (Sage Hill Inn).
    # (3) "we can NOT accommodate children under 12 or pets of any kind" (Strickland Arms).
    r"|\bpets?\s+\([^)]{0,60}\)\s*(?:are\s+|is\s+)?not\s+(?:allowed|accepted|permitted)\b"
    # SAN ANTONIO: the same refusal without the parentheses, "Pets including ESAs are not permitted."
    r"|\bpets?\s+including\s+[^.|()]{0,60}?\b(?:are|is)\s+not\s+(?:allowed|accepted|permitted)\b"
    r"|\bpets?\s+(?:cannot|can\s*not|can['’]t)\s+be\s+accommodated\b"
    # SAN ANTONIO: Noble Inns writes the typographic apostrophe, "we can’t accommodate any pets".
    r"|\b(?:cannot|can\s*not|can['’]t|unable\s+to)\s+accommodate\b[^.|]{0,60}\bpets?\b", re.I)
#: DENVER: the site's title limit -- a profile page's title is its H1 cut at this many characters by the shared SEO
#: engine (engines/website_generation/constants/seo.py TITLE_MAX_LENGTH). Stated here, not imported: a market-local
#: module may not import the website engine (the registration classifier refuses it), and FAST rule J builds the
#: real site, so a drift between the two fails the seal rather than passing silently.
TITLE_MAX_LENGTH = 60
#: DENVER: a property's own name stating that it has not opened ("Opening Early 2027", "Coming Soon").
_PREOPENING = re.compile(r"\b(?:opening|opens)\s+(?:(?:early|late|mid|spring|summer|fall|autumn|winter|in|q[1-4])\s+)?(?:20\d\d)\b"
                         r"|\bcoming\s+soon\b|\bopening\s+soon\b", re.I)
#: A brand states acceptance in several shapes: "Pets Welcome", "Your pet is welcome, too", "dog-friendly stays".
_ACCEPT = re.compile(r"\b(?:pets?|dogs?|cats?)\s+(?:is\s+|are\s+)?(?:welcome|accepted|permitted|allowed)\b"
                     # AUSTIN: two statements of acceptance Commodore Perry Estate's own FAQ makes -- "Two pets
                     # maximum are allowed." and "Pets under 60 pounds are permitted." Before the question rule,
                     # this row read as accepted only through its QUESTION "How many pets are allowed?".
                     r"|\b(?:pets?|dogs?|cats?)\s+(?:maximum\s+|under\s+\d+\s*(?:pounds|lbs?)\s+)(?:are|is)\s+"
                     r"(?:welcome|accepted|permitted|allowed)\b"
                     r"|\bpets?\s+allowed\b"
                     # SAN ANTONIO: "... even if not pet friendly" is never acceptance.
                     r"|(?<!\bnot\s)\b(?:pet|dog)[- ]friendly\b|\bwe\s+welcome\b.{0,20}\b(?:pets?|dogs?)\b"
                     r"|\bwelcomes?\b.{0,30}\b(?:pets?|dogs?)\b"
                     r"|\ballow(?:s|ed)?\s+(?:up\s+to\s+\w+\s+)?dogs?\b"
                     # SAN ANTONIO: Hotel Gibbs' own page, "Furry Friends Are Welcome".
                     r"|\bfurry\s+(?:friends?|companions?|family\s+members?)\s+(?:are\s+|is\s+)?welcome\b", re.I)
#: SAN DIEGO: two acceptance shapes this market's own pages use were added -- "two pets ARE ALLOWED in each
#: suite" (Extended Stay America) and "welcomes well-mannered pets" (Sonesta) -- and "allow up to two dogs"
#: (Best Western). The refusal pattern is still checked FIRST, so "pets are not allowed" can never read as this.
#: Weight-only, fee-only or count-only text is never read as acceptance on its own (Phase 16).
#: AUSTIN: A QUESTION IS NEVER AN ACCEPTANCE. A property's FAQ asks "Are pets allowed?" and then answers it; the
#: acceptance pattern's bare "pets allowed" matched the QUESTION, so Kalahari Round Rock's refusal (its answer)
#: was claimed pet-friendly. Acceptance is read only from the quote's statements: every part that ends in a
#: question CLAUSE is removed first -- a capitalised interrogative through its own question mark ("Are pets
#: allowed?", "How many pets are allowed?", "Is Hotel ZaZa Austin pet-friendly?"). Only the clause goes: a
#: static capture that runs a whole amenity list into one closing question ("... Pet-Friendly hotel ... What are
#: you waiting for?") keeps the list. The refusal pattern still reads the whole quote.
_QUESTION_CLAUSE = re.compile(r"\b(?:Are|Is|Can|Could|Do|Does|May|Will|What|How|Which|Where|When|Why|Who)\b"
                              r"[^.?!|]{0,160}\?")


#: SAN ANTONIO: A SERVICE-ANIMAL ALLOWANCE IS NEVER ORDINARY-PET ACCEPTANCE. "Service dogs are welcome at the Crockett
#: Hotel, even if not pet friendly" matched "dogs are welcome" (and "pet friendly"), so a page whose only other pet
#: text was a fee was claimed pet-friendly. Every service, assistance or emotional-support ANIMAL PHRASE is replaced
#: by a neutral token before acceptance is read, so "Service dogs are welcome" states nothing about pets while
#: "Both small pets and service animals are always welcome" still states it about pets (the refusal pattern still
#: reads the whole quote).
_SERVICE_ANIMAL_PHRASE = re.compile(r"\b(?:service|assistance|emotional[- ]support|support|guide|therapy)"
                                    r"\s+(?:animals?|dogs?)\b", re.I)


def _statements(text):
    """The quote with every question clause removed and every service-animal phrase neutralised."""
    return _SERVICE_ANIMAL_PHRASE.sub(" SERVICE_ANIMAL ", _QUESTION_CLAUSE.sub(" ", text or ""))


def _accepts(text):
    """True when a STATEMENT in the quote (never a question) states acceptance."""
    return bool(_ACCEPT.search(_statements(text)))


_WEIGHT_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)
_FEE_RX = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", re.I)
#: A pet COUNT is only a count when a pet noun follows it: "up to 25 lbs" is a weight, and reading its leading
#: digit as "2 pets" published a count the quote contradicts (FAST rule C caught it on Avalon Hotel).
_COUNT_RX = re.compile(r"(?:max(?:imum)?(?: of| number of pets(?: in room)?:?)?|up to|only|limit(?:ed)? to)\s*"
                       r"\(?(\d(?!\d)|one|two|three)\)?\s*(?:additional\s+|small\s+|well[- ]behaved\s+)?"
                       r"(?:pets?|dogs?|cats?|animals?)\b", re.I)
_WORDS = {"one": 1, "two": 2, "three": 3}


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip().lstrip("﻿")
            if line:
                out.append(json.loads(line))
    return out


#: Two different pages stating one address: the evidence is ambiguous and neither page may publish that row.
_AMBIGUOUS = object()


def _esa_name(name):
    """An Extended Stay America property name reduced to its location words (brand words and punctuation dropped)."""
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    n = re.sub(r"\b(extended stay america|premier|suites|select|stes|the)\b", " ", n)
    return " ".join(n.split())


def _house_number(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def negation_check(quote, claimed_pets_allowed):
    """(final_pets_allowed, conflict_note_or_None). The explicit refusal always wins."""
    refused = bool(_REFUSAL.search(quote or ""))
    accepted = _accepts(quote or "")
    if refused and claimed_pets_allowed is True:
        return False, ("QUOTE_CONTRADICTS_CLAIM -- the captured quote contains an explicit refusal phrase "
                       "while this order's own read claimed acceptance; the refusal governs")
    if refused:
        return False, None
    if claimed_pets_allowed is True and not accepted:
        # A fee/weight/count sentence alone, with no explicit welcome wording, never establishes acceptance
        # on its own (Phase 16) -- but every row in this order's own captures was read directly from a
        # "Pets allowed: Yes" / "Pets Welcome" field or FAQ sentence, so this branch is a safety net, not the
        # normal path.
        return None, "EXPLICIT_ACCEPTANCE_WORDING_NOT_FOUND_IN_QUOTE -- held rather than published on a fee/weight/count sentence alone"
    return claimed_pets_allowed, None


#: A fact is read only from the part of the quote that NAMES pets. A page's own amenity or resort fee sits in the
#: same captured text ("a $35 nightly amenity fee ... We welcome up to 2 dogs"), and taking the first dollar
#: amount in the quote published a pet fee the quote contradicts (FAST rule C caught it on Cardozo South Beach).
_PET_WORD = re.compile(r"\b(pets?|dogs?|cats?|canine|animals?)\b", re.I)


def pet_text(quote):
    """The parts of the quote that state the pet policy: every part naming a pet, plus a part that directly
    continues one ("Pets allowed: Yes." / "$125 non-refundable fee, max weight 30 lbs")."""
    kept, prev_kept = [], False
    for part in re.split(r"(?<=[.!?])\s+|\s*\|\s*|\s{2,}", quote or ""):
        if _PET_WORD.search(part):
            kept.append(part)
            prev_kept = True
        elif prev_kept and not _OTHER_FEE.search(part) and re.search(r"\$|\blbs?\b|\bpounds\b|\bmax", part, re.I):
            kept.append(part)
        else:
            prev_kept = False
    return " ".join(kept)


#: A dollar amount this market's pages carry that is NOT a pet fee.
_OTHER_FEE = re.compile(r"\b(amenity|resort|facility|destination|parking|valet|service|urban|tax|deposit for "
                        r"incidental|room rate|per night from|starting at)\b", re.I)


def pet_fee_cents(quote):
    """The dollar amount the quote states as the PET charge: an amount with pet wording near it and no
    amenity/resort/parking/valet wording in its own neighbourhood. None when the quote names no such amount."""
    best = None
    for m in _FEE_RX.finditer(quote or ""):
        before = quote[max(0, m.start() - 40):m.start()]
        after = quote[m.end():m.end() + 45]
        if _OTHER_FEE.search(before) or _OTHER_FEE.search(after):
            continue
        cents = int(round(float(m.group(1)) * 100))
        if best is None:
            best = cents
    return best


def extract_facts(quote):
    quote = pet_text(quote)
    fee = pet_fee_cents(quote)
    weight = None
    # "Maximum Pet Weight: 0.0lbs" on a Marriott page means NO stated limit, never a zero-pound pet.
    # SAN DIEGO: A CONDITIONAL WEIGHT IS NOT ONE NUMBER. San Diego Marriott La Jolla states "1 dog 50lbs 2 dogs
    # combined weight of 75lbs" and a 75.0lbs field; the first match (50) was published and FAST rule C refused
    # it as contradicted. When the quote states more than one distinct weight, the weight is withheld -- the same
    # rule as a tiered fee -- and acceptance still publishes.
    _weights = {float(w) for w in _WEIGHT_RX.findall(quote or "") if float(w) > 0}
    # SAN ANTONIO: A COMBINED WEIGHT IS NOT A PER-PET LIMIT. Hilton's Homewood Suites Airport states "Max weight:
    # 75 lbs" and "75lbs max total weight allowed between the 2 pets" -- one distinct number, but a total for two
    # pets; the package publishes weights per pet, so a weight the quote calls combined or total is withheld.
    _combined = re.search(r"\bcombined\b|\btotal\s+weight\b|\bweight\s+total\b|\bbetween\s+(?:the\s+)?(?:2|two)\s+pets\b"
                          r"|\bfor\s+all\s+pets\b|\baggregate\b", quote or "", re.I)
    if len(_weights) == 1 and not _combined:
        weight = _weights.pop()
    count = None
    m = _COUNT_RX.search(quote or "")
    if m:
        v = m.group(1).lower()
        count = _WORDS.get(v, None) or (int(v) if v.isdigit() else None)
    refundable = None
    if re.search(r"non-?refundable", quote or "", re.I):
        refundable = False
    elif re.search(r"\brefundable\b", quote or "", re.I):
        refundable = True
    return OrderedDict([("pet_fee_cents", fee), ("fee_currency", "USD" if fee is not None else None),
                        ("fee_refundable", refundable), ("max_pet_weight_lbs", weight),
                        ("max_pet_count", count)])


def _transcription_sha(line_obj):
    """The sha256 of the canonical JSON transcription line itself -- declared as a TRANSCRIPTION_SHA256, never
    passed off as a page hash (Phase 15's durability rule for an accessibility-tree read)."""
    import hashlib
    return hashlib.sha256(json.dumps(line_obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


#: STREET-TYPE WORDS ONE SOURCE WRITES AND ANOTHER OMITS. Measured on this market's own rows: the census
#: states "8277 Western Way" for a Comfort Suites whose OWN brand page states "8277 Western Way Circle", and the
#: shared address_key keeps the word "circle", so one premises produced two keys and a page that plainly states
#: "Pets Allowed: No" bound to nothing. The row was then reported as awaiting an attended browser it never
#: needed -- a MISLABEL, not a missing read.
_STREET_TYPE_WORDS = frozenset("""
street st avenue ave boulevard blvd road rd drive dr lane ln court ct circle cir place pl terrace ter
parkway pkwy pky highway hwy way trail trl square sq expressway expy loop run crossing crossings
plaza commons center centre point pointe ridge park north south east west n s e w ne nw se sw
""".split())


def _street_word_set(street):
    """The distinctive words of a street: no house number, no street type, no directional."""
    import re as _re
    toks = _re.sub(r"[^a-z0-9 ]", " ", (street or "").lower()).split()
    toks = toks[1:] if toks and toks[0].isdigit() else toks
    return {t for t in toks if t not in _STREET_TYPE_WORDS and not t.isdigit()}


def _house_no(v):
    import re as _re
    m = _re.match(r"\s*(\d+)", v or "")
    return m.group(1) if m else ""


#: identity_key -> every evidence row added for it, in the order added (see ``add_key``).
BY_KEY_ALL = {}

#: SAN ANTONIO: A CRAWLED SITE SPEAKS FOR A PROPERTY ONLY IF IT IS THE PROPERTY'S OWN. Places named, as the website
#: of several motels, a business-directory page ('capital-motel-san-antonio.poi.place', 'mayfield-motel.jany.io'),
#: a third-party travel blog (sahotelvisit.com) and OYO's booking pages, whose text interleaves GUEST REVIEWS ("It
#: was also pet-friendly ... since we brought our dog along") with the listing. A review is never a policy. The
#: binding rule (house number + ZIP on the page) cannot tell such a page from the hotel's own, so the host must:
#: its registrable domain has to carry a distinctive word of the property's own name ('thehotelemma.com',
#: 'crocketthotel.com', 'lavillitainn.com'). Site-builder hosts are judged on the property's own subdomain.
_NAME_STOP = {"hotel", "hotels", "motel", "motels", "inn", "inns", "suites", "suite", "lodge", "lodging", "the", "and",
              "san", "antonio", "texas", "studio", "studios", "extended", "stay", "express", "resort", "resorts",
              "spa", "house", "bed", "breakfast", "downtown", "riverwalk", "river", "walk", "north", "south", "east",
              "west", "airport", "plaza", "center", "centre", "motor", "court", "courts", "place", "boutique",
              "historic", "luxury", "near", "area", "llc", "inc", "company", "on"}
_SITE_BUILDERS = ("square.site", "wixsite.com", "godaddysites.com", "weebly.com", "business.site", "squarespace.com",
                  "webflow.io", "wordpress.com")


def first_party_site(url, name):
    """True when the site's own registrable domain carries a distinctive word of the property's own name."""
    from urllib.parse import urlparse
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) < 2:
        return False
    if ".".join(parts[-2:]) in _SITE_BUILDERS and len(parts) >= 3:
        label = parts[-3]
    else:
        label = parts[-2]
    label = re.sub(r"[^a-z0-9]", "", label)
    all_words = re.findall(r"[a-z0-9]+", (name or "").lower())
    words = [w for w in all_words if len(w) >= 4 and w not in _NAME_STOP]
    # A name built only from generic words ("Riverwalk Plaza Hotel") is matched on two adjacent words together.
    pairs = [a + b for a, b in zip(all_words, all_words[1:]) if len(a + b) >= 8 and {a, b} - {"the", "and", "at"}]
    return any(w in label for w in words) or any(p in label for p in pairs)


#: SAN ANTONIO: A FORMER KEY STILL NAMES ITS IDENTITY. Every lane keys its rows by the census identity key current
#: when it ran; a later census pass that learns a longer trade name from the brand's own page renames the identity
#: ("stayapt" became "stayapt suites san antonio lackland afb hotel"), and the census keeps the former key in
#: ``identity_key_aliases``. Evidence keyed by a former key is translated through that list -- only when exactly ONE
#: census row carries the alias -- so a read is never orphaned by a rename and never attached to a second row.
ALIAS_TO_KEY = {}


def current_key(key):
    """The census identity key an evidence row's (possibly former) key names today."""
    return ALIAS_TO_KEY.get(key, key)


def build_alias_map(census_hotels):
    ALIAS_TO_KEY.clear()
    owners = {}
    for h in census_hotels:
        for a in set(h.get("identity_key_aliases") or []) | {h["identity_key"]}:
            owners.setdefault(a, set()).add(h["identity_key"])
    live = {h["identity_key"] for h in census_hotels}
    for a, keys in owners.items():
        if len(keys) == 1 and a not in live:
            ALIAS_TO_KEY[a] = next(iter(keys))


#: identity_key -> the crawled site refused as not the property's own (see ``first_party_site``).
NOT_FIRST_PARTY_SITES = {}
#: the crawled page URL -> the census identity it was re-keyed to by its own address.
REKEYED_CRAWLED_ROWS = {}

#: SAN ANTONIO: a crawled site's pet text is read only from sentences that NAME a pet, dog or cat (a home page's
#: "visit this 56-acre animal zoo" is not policy text), and an acceptance stated only by a bare amenity LABEL
#: ("Pet friendly." closing The Inn at Market Square's amenity paragraph) states no policy: a label is never
#: acceptance, exactly as a brand's amenity chip is not.
_PET_NOUN = re.compile(r"\b(?:pets?|dogs?|cats?)\b", re.I)
AMENITY_LABEL_ONLY = {}


def crawled_pet_text(identity_key, sentences):
    """The quote a crawled site supports: its pet-naming sentences, or "" when its only acceptance is a bare label."""
    kept = [s for s in sentences if _PET_NOUN.search(s)]
    text = " ".join(kept)
    if not kept or _REFUSAL.search(text):
        return text
    statements = [s for s in kept if len(re.findall(r"[A-Za-z]+", s)) > 3 and _accepts(s)]
    if _accepts(text) and not statements:
        AMENITY_LABEL_ONLY[identity_key] = text
        return ""
    return text


def build_evidence_index(census_hotels):
    _names = {h["identity_key"]: h.get("canonical_name") or "" for h in census_hotels}
    _keys_at = {}
    for h in census_hotels:
        _keys_at.setdefault(address_key(canonical_street(h.get("street") or ""), (h.get("postal_code") or "")[:5]),
                            []).append(h["identity_key"])

    def _own_site(r):
        # SAN ANTONIO: a crawled row keeps the identity key the census had when the site was read. When a later
        # census pass renamed that identity (a merge chose a longer trade name), the row is re-keyed to the ONE
        # census row at the same address -- never by name, and never when two rows share the address.
        if current_key(r["identity_key"]) != r["identity_key"]:
            r = dict(r)
            r["identity_key"] = current_key(r["identity_key"])
        if r["identity_key"] not in _names:
            _at = _keys_at.get(address_key(canonical_street(r.get("street") or ""), (r.get("postal") or "")[:5]), [])
            if len(_at) == 1:
                r = dict(r)
                r["identity_key"] = _at[0]
                REKEYED_CRAWLED_ROWS[r["u"]] = _at[0]
        url = r.get("final_url") or r.get("u") or ""
        if first_party_site(url, _names.get(r["identity_key"], "")) or first_party_site(r.get("u") or "",
                                                                                       _names.get(r["identity_key"], "")):
            return r
        NOT_FIRST_PARTY_SITES[r["identity_key"]] = url
        return None

    by_code = {}   # (brand, property_code_lower) -> evidence
    by_key = {}    # identity_key -> evidence
    by_house = {}  # (house_number, postal5) -> [(street, evidence), ...]  -- the bounded fallback below
    by_addr = {}   # address_key(street, postal5) -> evidence  (house number AND street words; a house number
    #                alone collides: 4681 Salisbury Rd and 4681 Lenoir Ave are both 4681 in 32256)

    def add_code(brand, code, ev):
        if brand and code:
            by_code[(brand.upper(), code.lower())] = ev

    def add_key(key, ev):
        key = current_key(key)
        if key:
            by_key[key] = ev
            # DENVER: every read of an identity is KEPT, not only the last one written. A static read of a vanity
            # domain or a bare amenity label arriving after the attended-browser read of the brand's own page
            # overwrote it here (Cambria RiNo, Sonesta Denver Downtown), so the fallback below could never find
            # the read that cites the bound route or that the shared reader accepts.
            BY_KEY_ALL.setdefault(key, []).append(ev)

    def add_addr(street, postal, ev):
        key = address_key(canonical_street(street or ""), (postal or "")[:5])
        if street and postal and key.split("|")[0]:
            if key in by_addr and by_addr[key].get("source_url") != ev.get("source_url"):
                by_addr[key] = _AMBIGUOUS       # two different pages claim one address: neither may publish
            else:
                by_addr.setdefault(key, ev)
            by_house.setdefault((_house_no(street), (postal or "")[:5]), []).append((street, ev))

    for path, brand in (
        (os.path.join(STAGING, "marriott_browser_rows.jsonl"), "MARRIOTT"),
        (os.path.join(STAGING, "hilton_browser_rows.jsonl"), "HILTON"),
    ):
        for r in _jsonl(path):
            if "pets_allowed" not in r:
                continue
            ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["url"]),
                              ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                              ("document_sha256", _transcription_sha(r)),
                              ("captured_via", "supported browser, accessibility tree (navigate + find only)")])
            add_code(brand, r["code"], ev)

    for r in _jsonl(os.path.join(STAGING, "resort_browser_rows.jsonl")):
        if "pets_allowed" not in r:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["url"]),
                          ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                          ("document_sha256", _transcription_sha(r)),
                          ("captured_via", "supported browser, accessibility tree (navigate + find only)")])
        if r.get("code"):
            add_code(r["family"], r["code"], ev)

    wyndham_doc = _load(os.path.join(STAGING, "wyndham_rows.json"), {}) or {}
    for r in wyndham_doc.get("rows", []):
        if not r.get("p") or r.get("pet_indicator") not in ("Y", "N"):
            continue
        pets = r["pet_indicator"] == "Y"
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r["u"]),
                          ("pets_allowed_claim", pets), ("quote", r["p"]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property-service API (same JSON the overview page renders)")])
        add_addr(r.get("st") or "", r.get("z") or "", ev)
        add_code("WYNDHAM", r.get("id") or "", ev)

    # PTF-MIAMI-FL-BROWSER-CLOSURE-002: the supported-browser reads of the 114-row browser queue, each already
    # bound to its own premises by san_antonio_tx_browser_closure_002 (property code, or the brand page's own name with
    # its own postal code / full street). The quote is the page's own policy text nodes, joined in page order.
    for r in (_load(os.path.join(STAGING, "browser_closure_rows.json"), {}) or {}).get("rows", []):
        if r.get("outcome") != "READ" or not r.get("operative_quote"):
            continue
        quote = r["operative_quote"]
        if _REFUSAL.search(quote):
            pets = False
        elif _accepts(quote):
            pets = True
        else:
            # The page's own policy block served and was bound to these premises, but it states only a fee, a
            # weight or a count -- never the acceptance wording the publication rule requires. That is an
            # EVIDENCE hold, not a capture that still has to be made: claiming NOTHING here (rather than
            # skipping the row) keeps the fee/weight/count rule intact AND stops a row whose page this order
            # did read from being reported as still awaiting the browser.
            pets = None
        ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r.get("final_url") or r["requested_url"]),
                          ("pets_allowed_claim", pets), ("quote", quote[:500]),
                          ("document_sha256", r["transcription_sha256"]),
                          ("captured_via", "supported attended browser (claude-in-chrome), accessibility tree "
                                           "(navigate + find only), PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"),
                          ("binding", r.get("binding"))])
        if pets is None:
            # never displaces a lane that DID state a policy for these premises
            by_key.setdefault(r["identity_key"], ev)
        else:
            add_key(r["identity_key"], ev)

    # MIAMI: the Choice / IHG property pages the Firecrawl route-discovery lane found (their own sitemaps refused
    # this client, so these routes never reached the census by name). Bound ONLY on the house number + postal code
    # the page itself states.
    for r in (_load(os.path.join(STAGING, "brand_page_rows.json"), {}) or {}).get("rows", []):
        if r.get("status") != 200 or not r.get("st") or not r.get("z"):
            continue
        sentences = [s for s in (r.get("pet_sentences") or [])
                     if not (re.search(r"service animals?", s, re.I) and not re.search(r"\bpets?\b|\bdogs?\b", s, re.I))]
        if not sentences:
            # PHOENIX: THE BRAND'S OWN PAGE WAS READ AND STATES NO POLICY. A Firecrawl read of the brand's own
            # property page that bound its own premises but carries no pet statement is a SOURCE_SILENT read -- it
            # never leaves the row labelled as still awaiting a browser (measured: IHG Holiday Inn & Suites Phoenix
            # Airport, whose rendered page, re-opened in the attended browser, states nothing about pets either).
            SILENT_BRAND_PAGES[address_key(canonical_street(r["st"]), (r["z"] or "")[:5])] = (
                r.get("final_url") or r["u"])
            continue
        text = " ".join(sentences)
        if _REFUSAL.search(text):
            pets = False
        elif _accepts(text):
            pets = True
        else:
            continue
        ev = OrderedDict([("lane", "FIRECRAWL"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", text[:500]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property page (route discovered on the brand's own city "
                                           "page), Firecrawl rendered scrape, existing plan credits")])
        add_addr(r["st"], r["z"], ev)

    # MIAMI: Extended Stay America's own property pages answered this client (Tampa's did not). The operative
    # statement is the property's own FAQ answer ("Is <property> pet friendly?"); the count sentence on the same
    # page is context. Bound by the page's own JSON-LD street + ZIP, or -- where the page omits its address card --
    # by the page's own property name (from its FAQ question) matching exactly ONE ESA census row.
    esa_doc = _load(os.path.join(STAGING, "esa_rows.json"), {}) or {}
    esa_census = {}
    for h in census_hotels:
        if re.search(r"extended stay america", h.get("canonical_name") or "", re.I):
            esa_census.setdefault(_esa_name(h["canonical_name"]), []).append(h["identity_key"])
    for r in esa_doc.get("rows", []):
        if r.get("s") != 200 or not r.get("p"):
            continue
        ans = r["p"]
        if re.match(r"\s*yes\b", ans, re.I):
            pets = True
        elif re.match(r"\s*no\b", ans, re.I):
            pets = False
        else:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", ans[:500]),
                          ("context", r.get("count_sentence") or ""),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property page FAQ JSON-LD, plain client")])
        if r.get("st") and r.get("z"):
            add_addr(r["st"], r["z"], ev)
            continue
        qname = re.sub(r"^\s*is\s+|\s+pet friendly\?\s*$", "", r.get("q") or "", flags=re.I)
        keys = esa_census.get(_esa_name(qname), [])
        if len(keys) == 1:
            ev["binding"] = "BRAND_PAGE_OWN_PROPERTY_NAME_UNIQUE_IN_FAMILY"
            add_key(keys[0], ev)

    for r in _jsonl(os.path.join(STAGING, "policy_pages_rows.json")) if False else \
            (_load(os.path.join(STAGING, "policy_pages_rows.json"), {}) or {}).get("rows", []):
        r = _own_site(r) if r.get("bound") else None
        if r is None:
            continue
        sentences = [s for p in r.get("pages", []) for s in p.get("pet_sentences", [])]
        if not sentences:
            continue
        text = crawled_pet_text(r["identity_key"], sentences)
        if not text:
            continue
        if _REFUSAL.search(text):
            pets = False
        elif _accepts(text) or _FEE_RX.search(text) or _WEIGHT_RX.search(text):
            pets = True
        else:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", text[:500]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the independent property's own policy/FAQ page, plain client")])
        add_key(r["identity_key"], ev)

    static_doc = _load(STATIC, {}) or {}
    for r in static_doc.get("rows", []):
        if r.get("outcome") != "VALID":
            continue
        ext = ((r.get("observation") or {}).get("extraction") or {})
        pa = ext.get("pets_allowed")
        if pa is None:
            continue
        evs = (r.get("observation") or {}).get("evidence") or []
        # The record's OWN pets_allowed quote is the operative statement, but the shared reader's amenity-chip
        # rule needs the OTHER field quotes on the same page (fee, count, weight) as context to tell a policy
        # BLOCK ("Pets Welcome" beside "$50 fee") from a bare amenity chip -- deduplicated so a fact quoted for
        # two fields is not repeated into what looks like a duplicated, garbled sentence.
        pa_quotes = [e.get("quote", "") for e in evs if "pets_allowed" in (e.get("field_refs") or [])]
        other_quotes = list(dict.fromkeys(e.get("quote", "") for e in evs
                                          if e.get("quote") and "pets_allowed" not in (e.get("field_refs") or [])))
        quotes = pa_quotes or [e.get("quote", "") for e in evs if e.get("quote")]
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (shared reader)" % pa)),
                          ("context", " ".join(other_quotes)[:500]),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "shared direct_http_capture pipeline, plain client")])
        add_key(r["identity_key"], ev)

    # CLOSURE (PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002): 12 supported-browser
    # reads over rows the source-ready build routed to BROWSER_CAPTURE_NEEDED
    # but never reached (Best Western, additional Hyatt/Hilton/IHG rows).
    for r in _jsonl(os.path.join(STAGING, "closure_browser_rows.jsonl")):
        if r.get("outcome") != "READ" or "pets_allowed" not in r:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_ATTENDED"), ("source_url", r["final_url"]),
                          ("pets_allowed_claim", r["pets_allowed"]), ("quote", r["quote"]),
                          ("document_sha256", r["transcription_sha256"]),
                          ("captured_via", "supported browser, accessibility tree (navigate + find only), closure pass")])
        add_key(r["identity_key"], ev)

    # CLOSURE (PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002): the 4 newly-admitted
    # Wyndham sub-brand (La Quinta / Days Inn) reads, keyed straight to the
    # identity_key the closure census-additions pass minted for them.
    for r in _load(os.path.join(STAGING, "closure_wyndham_rows.json"), {}).get("rows", []):
        if not r.get("id") or r.get("pet_indicator") not in ("Y", "N"):
            continue
        pets = r["pet_indicator"] == "Y"
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r["u"]),
                          ("pets_allowed_claim", pets), ("quote", r["p"]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the brand's own property-service API, closure pass")])
        add_key(r["identity_key"], ev)

    # CLOSURE: the routing-hold independents' own websites the Places
    # route-discovery lane found and this pass fetched (same binding
    # discipline as policy_pages_rows.json: house number + postal code,
    # phone digits, or JSON-LD street/postal -- never name alone).
    for r in (_load(os.path.join(STAGING, "closure_static_rows.json"), {}) or {}).get("rows", []):
        r = _own_site(r) if r.get("bound") else None
        if r is None:
            continue
        sentences = [s for p in r.get("pages", []) for s in p.get("pet_sentences", [])]
        if not sentences:
            continue
        text = crawled_pet_text(r["identity_key"], sentences)
        if not text:
            continue
        if _REFUSAL.search(text):
            pets = False
        elif _accepts(text) or _FEE_RX.search(text) or _WEIGHT_RX.search(text):
            pets = True
        else:
            continue
        ev = OrderedDict([("lane", "PROPERTY_PAGE_STATIC"), ("source_url", r.get("final_url") or r["u"]),
                          ("pets_allowed_claim", pets), ("quote", text[:500]),
                          ("document_sha256", r.get("h") or _transcription_sha(r)),
                          ("captured_via", "the independent property's own site (route discovered via Google "
                                          "Places, closure pass), plain client")])
        add_key(r["identity_key"], ev)

    for r in firecrawl_rows():
        if r.get("firecrawl_class") != "FIRECRAWL_PUBLICATION_GRADE":
            continue
        pa = r.get("pets_allowed")
        if pa is None:
            continue
        evs = (r.get("observation") or {}).get("evidence") or []
        pa_quotes = [e.get("quote", "") for e in evs if "pets_allowed" in (e.get("field_refs") or [])]
        other_quotes = list(dict.fromkeys(e.get("quote", "") for e in evs
                                          if e.get("quote") and "pets_allowed" not in (e.get("field_refs") or [])))
        quotes = pa_quotes or [e.get("quote", "") for e in evs if e.get("quote")]
        # SAN ANTONIO: the shared extractor can cite a bare amenity LABEL as its pets_allowed quote ("pet-friendly",
        # stayAPT) while the page's own acceptance SENTENCE sits under another field ("Both small pets and service
        # animals are always welcome in our pet-friendly rooms."). A label never publishes on its own: the sentence
        # becomes the quote, and with no sentence the row is held.
        if pa is True and not any(len(re.findall(r"[A-Za-z]+", q)) > 3 and _accepts(q) for q in quotes):
            sentences = [q for q in other_quotes if len(re.findall(r"[A-Za-z]+", q)) > 3 and _accepts(q)]
            if not sentences:
                AMENITY_LABEL_ONLY[r["identity_key"]] = " ".join(quotes)
                continue
            quotes = sentences
        ev = OrderedDict([("lane", "FIRECRAWL"), ("source_url", r.get("final_url") or r.get("requested_url")),
                          ("pets_allowed_claim", pa), ("quote", " ".join(quotes)[:500] or ("pets_allowed=%s (Firecrawl reader)" % pa)),
                          ("context", " ".join(other_quotes)[:500]),
                          ("document_sha256", r.get("page_sha256") or _transcription_sha({"k": r["identity_key"], "u": r.get("requested_url")})),
                          ("captured_via", "Firecrawl rendered scrape, existing plan credits")])
        add_key(r["identity_key"], ev)

    return by_code, by_key, by_addr, by_house


#: THE MEASURED supported-browser outcome of THIS order, per family. Nothing here is inherited: every line
#: states what this session's attended browser actually did on that brand's own host.
#:
#: Fort Lauderdale's build recorded extension read-permission refusals on hilton.com, hyatt.com and
#: bestwestern.com. THIS session had no such refusal on any of them -- it read 28 Hilton properties, 3 Hyatt
#: properties and 2 Best Western properties first-party. Carrying that market's blocker text forward would
#: have labelled a row as awaiting a browser that had already answered, which is exactly the mislabel
#: Phase 11 rule 7 forbids, so the text is restated from this run's own measurements.
BROWSER_BLOCKERS = {
    "MARRIOTT": "the router sends Marriott to the attended browser. This session read every in-market Marriott "
                "route the owned harvest and the brand's own Arizona sitemap list (106 attended reads, 0 Akamai "
                "denials, measured pacing of ~30 s per property); a Marriott row not matched to one of those reads "
                "had no Marriott route in either inventory",
}

#: Families whose own host this session's attended browser DID reach, measured this run.
BROWSER_REACHED = {
    "MARRIOTT": "every in-market Marriott route was read first-party on marriott.com (0 Akamai denials)",
    "HILTON": "every in-market Hilton property the brand's own Arizona city pages list was opened first-party on "
              "hilton.com (the three Hilton Vacation Club resorts excepted: TIMESHARE on the brand's own card)",
}

#: FAMILY WALLS THIS ORDER MAY NOT CROSS, measured this run. Empty until a wall is MEASURED here: nothing is
#: inherited from Miami's or Denver's family walls.
FAMILY_TERMINAL_WALLS = {
}


def _domain(url):
    host = re.sub(r"^https?://", "", (url or "").strip().lower()).split("/")[0].split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def route_domain_conflict(census_row, ev):
    """The reason a read may not be published against this identity's bound route, or None.

    The sealed-package contract requires a record to cite the endpoint the census routes the identity to (or the
    same brand family). A brand-routed identity read on its own separate domain is a real, first-party read and a
    real conflict at once: both pages are the property's, and this pass is not allowed to repoint a census route.
    """
    official = str(census_row.get("official_url") or "")
    if not official:
        return None
    src, dst = _domain(ev.get("source_url")), _domain(official)
    if not src or not dst or src == dst:
        return None
    brand = (census_row.get("brand") or "").lower()
    if brand and (brand.split()[0][:6] in src or brand.split()[0][:6] in dst) and src.split(".")[0] in dst:
        return None
    return ("ROUTE_DOMAIN_CONFLICT -- this order read the property's own page at %r while the census binds the "
            "identity to %r; the package contract requires the cited page and the bound route to agree, so the "
            "row is held for a routing decision rather than published against a route it does not cite" % (src, dst))


def router_hold_reason(identity_key, routing_by_key, static_by_key, fc_by_key, census_row=None):
    if identity_key in BROWSER_CLOSURE_STATE:
        return BROWSER_CLOSURE_STATE[identity_key]
    if census_row is not None:
        _silent = SILENT_BRAND_PAGES.get(address_key(canonical_street(census_row.get("street") or ""),
                                                     (census_row.get("postal_code") or "")[:5]))
        if _silent:
            return SOURCE_SILENT, ("the brand's own property page (read through Firecrawl, existing plan credits) "
                                   "bound these premises and states no pet policy; silence is never a refusal "
                                   "(%s)" % _silent)
    r = routing_by_key.get(identity_key)
    if r is None:
        return ROUTING_HOLD, "no route was assembled for this identity in the routing pass"
    state = r.get("routing_state")
    if not r.get("url"):
        pl = PLACES_BY_KEY.get(identity_key)
        site = SITES_BY_KEY.get(identity_key)
        if pl is None:
            return ROUTING_HOLD, ("routing state %s: %s" % (state, r.get("why_no_route", "no first-party route stated")))
        if not pl.get("bound"):
            return ROUTING_HOLD, ("NO_OFFICIAL_WEB_PRESENCE_FOUND -- no first-party route, and Places route discovery "
                                  "returned no place with this row's own street number and ZIP")
        if not (pl.get("place") or {}).get("website_uri"):
            return ROUTING_HOLD, ("NO_OFFICIAL_WEB_PRESENCE_FOUND -- Places bound this building (street number + ZIP) "
                                  "but its card names no website")
        if site is None:
            return ROUTING_HOLD, ("OTHER_EXPLICIT_REASON -- the website Places names is a brand / OTA / social host "
                                  "that the independents' lane does not read (%s)" % pl["place"]["website_uri"])
        if site.get("s") != 200:
            return ACCESS_BLOCKED, ("the property's own site (found via Places) did not serve to the plain client "
                                    "(status %s)" % site.get("s"))
        if not site.get("bound"):
            return IDENTITY_MISMATCH_HOLD, ("the site Places names never stated this row's house number + ZIP, phone "
                                            "or JSON-LD address; it is not bound to this identity")
        return SOURCE_SILENT, ("the property's own site (found via Places, bound on its own address/phone) states no "
                               "operative pet policy on its home or policy/FAQ pages")
    s = static_by_key.get(identity_key)
    fc = fc_by_key.get(identity_key)
    if (r.get("brand_family") or "") in FAMILY_TERMINAL_WALLS:
        return ACCESS_BLOCKED, FAMILY_TERMINAL_WALLS[r["brand_family"]]
    if s is None and fc is None and (r.get("url") or "").rstrip("/").lower() in WYNDHAM_RETIRED:
        return ROUTING_HOLD, ("RETIRED_BRAND_ROUTE -- the Wyndham lane read this route and the brand redirects it to "
                              "its own city search: the brand no longer publishes a property page for these "
                              "premises (%s)" % r["url"])
    if s is None and fc is None:
        if (r.get("brand_family") or "") in BROWSER_BLOCKERS:
            return BROWSER_CAPTURE_NEEDED, ("routed to a %s page (%s) that no static, Firecrawl or browser pass in "
                                           "this order reached yet" % (r.get("brand_family"), r["url"]))
        return ROUTING_HOLD, "routed but no acquisition lane in this order attempted the page yet"
    outcome = (s or {}).get("outcome")
    cls = (s or {}).get("classification")
    if cls in ("SOURCE_SILENT_STATIC", "IDENTITY_TEXT_BOUND_POLICY_SILENT", "BLOCK_FOUND_BUT_SILENT"):
        return SOURCE_SILENT, "the page served and stated no operative pet policy (%s)" % cls
    if cls == "IDENTITY_MISMATCH" or cls == "IDENTITY_NOT_CONFIRMED_STATIC":
        return IDENTITY_MISMATCH_HOLD, "the fetched page's own identity did not confirm this census row"
    fam = r.get("brand_family") or ""
    if outcome == "ACCESS_DENIED" and fam in BROWSER_BLOCKERS and (fc is None or fam == "MARRIOTT"):
        return BROWSER_CAPTURE_NEEDED, ("static fetch was ACCESS_DENIED; %s" % BROWSER_BLOCKERS[fam])
    if outcome == "ACCESS_DENIED" and fam in ("IHG", "CHOICE") and fc is None:
        return BROWSER_CAPTURE_NEEDED, "static fetch was ACCESS_DENIED; the router's Firecrawl rung did not reach this row"
    if fc is not None and fc.get("firecrawl_class") in ("FIRECRAWL_FAILED", "FIRECRAWL_MISMATCH"):
        return ACCESS_BLOCKED, "router exhausted: static %s, Firecrawl %s" % (outcome, fc.get("firecrawl_class"))
    return ACCESS_BLOCKED, "router exhausted on every free/authorized lane attempted this order (static %s)" % outcome


PLACES_BY_KEY = {}
#: address_key -> the brand's own page (read through Firecrawl) that bound these premises and states no pet policy.
SILENT_BRAND_PAGES = {}
#: Wyndham routes the Wyndham lane READ and found redirected to the brand's own city search (retired).
WYNDHAM_RETIRED = {u.rstrip("/").lower() for u in (_load(os.path.join(STAGING, "wyndham_rows.json"), {}) or {})
                   .get("retired_routes_redirected_to_brand_search", [])}
SITES_BY_KEY = {}
#: PTF-MIAMI-FL-BROWSER-CLOSURE-002: what a browser attempt that produced no publishable quote means for the row.
BROWSER_OUTCOME_STATE = {
    "AMENITY_CHIP_ONLY": (SOURCE_SILENT, "the brand's own page served and states no pet policy -- only an amenity "
                                         "chip, which is never a policy (Phase 16)"),
    "NO_POLICY_ON_PAGE": (SOURCE_SILENT, "the property's own page served and carries no pet policy section at all"),
    "IDENTITY_NOT_BOUND": (IDENTITY_MISMATCH_HOLD, "the page read did not bind to this row's exact premises "
                                                   "(property code, name + postal code, or full street)"),
    "ACCESS_DENIED": (ACCESS_BLOCKED, "the brand answered the authorized browser with an Access Denied / anti-bot "
                                      "challenge page, which this order does not bypass"),
    "SHARED_PAGE_CENSUS_DUPLICATE": (IDENTITY_MISMATCH_HOLD, "one brand page bound more than one census row; the "
                                                             "duplicate identity is resolved before either publishes"),
    "NO_BRAND_PROPERTY_PAGE": (ROUTING_HOLD, "the census routes this identity to a brand HOME page, and the brand "
                                             "publishes no property page for these premises -- there is nothing "
                                             "first-party to read, so no browser capture can resolve it"),
    # SAN DIEGO -- the outcomes this market's own attended-browser lane records. Phase 11 rule 7: a page this
    # order DID read never stays labelled as still awaiting the browser.
    "IDENTITY_BOUND_POLICY_SOURCE_SILENT": (
        SOURCE_SILENT, "the property's own pages served, bound these exact premises, and state no operative pet "
                       "policy anywhere the reader reached; silence is never a refusal (Phase 17)"),
    "AMENITY_CHIP_ONLY_NOT_OPERATIVE": (
        SOURCE_SILENT, "the brand's own page served and bound these premises, and the only pet wording on it is "
                       "an amenity chip, which is never acceptance (Phase 17)"),
    "CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED": (
        ACCESS_BLOCKED, "the brand answered the authorized attended browser with an Akamai Access Denied page "
                        "across paced windows; the challenge was never bypassed"),
    "REJECTED_STALE_DOM_ADDRESS_MISMATCH": (
        IDENTITY_MISMATCH_HOLD, "the browser read returned the PREVIOUS property's address, so the page never "
                                "bound these premises; a route/premises mismatch is never valid evidence"),
    "NAVIGATION_FAILED_ERROR_PAGE": (
        ROUTING_HOLD, "the route the census carries served an error page (expired domain, site error or browser "
                      "error page) and no other first-party route was proved for these premises"),
    "RENDER_FAILED_POLICY_PANEL_NOT_EXPOSED": (
        ACCESS_BLOCKED, "the brand's own page served, but its pet-policy accordion never exposed its text to the "
                        "attended browser on two bounded attempts (the panel did not open or the renderer froze); "
                        "nothing was read and nothing is inferred"),
    "NO_OPERATIVE_STATEMENT": (
        EVIDENCE_HOLD, "the property's own page served and bound these premises, but its only pet statement is "
                       "conditional ('may be accepted, please contact the hotel') or was not exposed -- neither an "
                       "acceptance nor a refusal"),
    "NO_PROPERTY_PAGE_ROUTE_LANDS_ON_BRAND_SEARCH": (
        ROUTING_HOLD, "the brand's own property-code route lands on a hotel-search page: the brand publishes no "
                      "property page for these premises"),
    "CHALLENGE_DENIED_DATADOME_CAPTCHA": (
        ACCESS_BLOCKED, "the brand served a DataDome CAPTCHA to the attended browser; never solved or bypassed"),
    "IDENTITY_READ_ROW_EXCLUDED_AS_TIMESHARE": (
        SOURCE_SILENT, "the brand's own page named these premises a vacation-ownership resort; the row is "
                       "excluded before any policy applies and publishes nothing"),
}
BROWSER_CLOSURE_STATE = {}


def build():
    PLACES_BY_KEY.clear()
    SITES_BY_KEY.clear()
    NOT_FIRST_PARTY_SITES.clear()
    AMENITY_LABEL_ONLY.clear()
    REKEYED_CRAWLED_ROWS.clear()
    SILENT_BRAND_PAGES.clear()
    for r in (_load(os.path.join(REPORTS, "san_antonio_tx_places_route_discovery_001.json"), {}) or {}).get("rows", []):
        if r.get("cohort") == "ROUTE_DISCOVERY":
            PLACES_BY_KEY[r["identity_key"]] = r
    for r in (_load(os.path.join(STAGING, "closure_static_rows.json"), {}) or {}).get("rows", []):
        SITES_BY_KEY[r["identity_key"]] = r
    BROWSER_CLOSURE_STATE.clear()
    for r in (_load(os.path.join(STAGING, "browser_closure_rows.json"), {}) or {}).get("rows", []):
        state = BROWSER_OUTCOME_STATE.get(r.get("outcome"))
        if state:
            # SAN DIEGO: the read's own note (what the page actually showed) is carried with the generic reason.
            BROWSER_CLOSURE_STATE[r["identity_key"]] = (
                state[0], state[1] + " (%s)" % (r.get("final_url") or r.get("requested_url"))
                + ((" -- " + r["note"]) if r.get("note") else ""))
    census = _load(CENSUS, {}) or {}
    hotels = census.get("hotels", [])
    routing_doc = _load(ROUTING, {}) or {}
    routing_by_key = {r["identity_key"]: r for r in routing_doc.get("routes", [])}
    build_alias_map(hotels)
    for _d in (PLACES_BY_KEY, SITES_BY_KEY, BROWSER_CLOSURE_STATE):
        _moved = {k: v for k, v in _d.items() if current_key(k) != k}
        for k, v in _moved.items():
            del _d[k]
            _d.setdefault(current_key(k), v)
    static_by_key ={current_key(r["identity_key"]): r for r in (_load(STATIC, {}) or {}).get("rows", [])}
    fc_by_key = {current_key(r["identity_key"]): r for r in firecrawl_rows()}
    by_code, by_key, by_addr, by_house = build_evidence_index(hotels)

    rows = []
    negation_conflicts = []
    for h in hotels:
        key = h["identity_key"]
        brand = (h.get("brand") or "").upper()
        code = (h.get("property_code") or "").lower()
        ev = None
        if brand and code:
            ev = by_code.get((brand, code))
        if ev is None:
            ev = by_key.get(key)
        if ev is None:
            # the census row's street is canonicalised on the SAME path the evidence index used
            # (line ~251), or "1120 W SR 84" and "1120 W. State Road 84" build two keys for one building.
            ev = by_addr.get(address_key(canonical_street(h.get("street") or ""),
                                         (h.get("postal_code") or "")[:5]))
            if ev is _AMBIGUOUS:
                ev = None
            if ev is None:
                # THE BOUNDED HOUSE-NUMBER FALLBACK. Same house number, same postal code, and the census row's
                # distinctive street words are a SUBSET of the page's own (or the page's of the census row's),
                # with EXACTLY ONE candidate. It is stricter than a house-number match -- the words still have
                # to agree -- and it exists because a street TYPE word that one source writes and another omits
                # ("Western Way" / "Western Way Circle") is not a different street. A tie refuses, as always.
                cw = _street_word_set(h.get("street"))
                cands = []
                for st, cand in by_house.get((_house_no(h.get("street")),
                                              (h.get("postal_code") or "")[:5]), []):
                    if cand is _AMBIGUOUS or not cw:
                        continue
                    pw = _street_word_set(st)
                    if pw and (cw <= pw or pw <= cw):
                        if all(c is not cand for _s, c in cands):
                            cands.append((st, cand))
                if len(cands) == 1:
                    ev = cands[0][1]
                    ev = dict(ev)
                    ev["binding_note"] = (
                        "bound on house number + postal code with the street's distinctive words agreeing "
                        "(%r vs %r); exactly one candidate" % (h.get("street"), cands[0][0]))

        row = OrderedDict([
            ("identity_key", key), ("canonical_name", h["canonical_name"]), ("brand", h.get("brand") or ""),
            ("corridor", h.get("corridor", "")), ("street", h.get("street", "")), ("postal_code", h.get("postal_code", "")),
        ])
        # SAN DIEGO: TWO FIRST-PARTY READS OF ONE PREMISES, ONE OF THEM ON THE BOUND ROUTE. Days Inn Oceanside was
        # read on its own site AND through the brand's own property service; the lookup order above picked the
        # own-site read, which conflicts with the census's brand route, while the brand read agrees with it. When
        # the first candidate conflicts, the other candidates for the SAME identity (by code, by key, by exact
        # address -- never the ambiguous or the house-number fallback) are tried in the same order, and the first
        # that cites the bound route is used. If none does, the row is held exactly as before.
        if ev is not None and route_domain_conflict(h, ev):
            for alt in [by_code.get((brand, code)) if (brand and code) else None, by_key.get(key),
                        by_addr.get(address_key(canonical_street(h.get("street") or ""),
                                                (h.get("postal_code") or "")[:5]))] + list(BY_KEY_ALL.get(key, [])):
                if alt is not None and alt is not _AMBIGUOUS and not route_domain_conflict(h, alt):
                    ev = alt
                    break
        if ev is not None and route_domain_conflict(h, ev):
            # The read is first-party for the building, but the census binds this identity to another host (a
            # brand route). The package contract requires the cited page and the bound route to agree, and this
            # order does not get to repoint a census route from the adjudication pass, so the row is HELD.
            row["disposition"] = EVIDENCE_HOLD
            row["hold_reason"] = route_domain_conflict(h, ev)
            row["evidence"] = ev
            negation_conflicts.append(OrderedDict([("identity_key", key), ("name", h["canonical_name"]),
                                                   ("why", "ROUTE_DOMAIN_CONFLICT -- " + row["hold_reason"])]))
            rows.append(row)
            continue
        if ev is not None:
            final_pa, conflict = negation_check(ev["quote"], ev["pets_allowed_claim"])
            row["evidence"] = ev
            if conflict:
                negation_conflicts.append(OrderedDict([("identity_key", key), ("name", h["canonical_name"]), ("why", conflict)]))
            if final_pa is True:
                row["disposition"] = CLEAN_PET_FRIENDLY
                row["policy_facts"] = extract_facts((ev["quote"] + " " + ev.get("context", "")).strip())
            elif final_pa is False:
                row["disposition"] = CLEAN_VERIFIED_NO_PETS
            else:
                row["disposition"] = NEGATION_HOLD if conflict and "QUOTE_CONTRADICTS_CLAIM" in conflict else EVIDENCE_HOLD
                # every hold carries its reason (the Lafayette FAQ answer was held with none)
                row["hold_reason"] = conflict or (
                    "the first-party quote states neither an acceptance nor a refusal sentence -- a fee, a weight "
                    "or a count alone is never read as acceptance (Phase 16) -- so it is held, not published")
            if conflict:
                row["negation_conflict"] = conflict
            # A SECOND, INDEPENDENT gate: the shared first_party_binding reader that the sealed package's own
            # FAST rule C will run at seal time. Publishing only what this order's own read agrees with is not
            # enough (Phase 17): if the shared reader reads the same quote differently -- most often because it
            # finds service-animal wording alongside the acceptance/refusal statement and will not treat that
            # combination as operative -- this order must hold the row here rather than have the seal reject it
            # later. Never modifies the shared reader; only decides whether THIS row may be published.
            # A THIRD gate, for the same reason: the registration layer refuses to turn an identity with no
            # address into inventory, and it is right to. Two Miami identities reached the census from a brand
            # roster that named the property and its code but no street; their own brand page states one, but
            # writing it into the census is a census edit this order does not make. Held, not published.
            if row["disposition"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS) and not (h.get("street") or "").strip():
                row["disposition"] = EVIDENCE_HOLD
                row.pop("policy_facts", None)
                row["hold_reason"] = ("the census states no street for this identity, so it cannot become "
                                      "inventory; the policy read is sound but a profile without an address is "
                                      "not publishable, and this order does not write census addresses")
            if row["disposition"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
                kind = FPB.KIND_PET_FRIENDLY if row["disposition"] == CLEAN_PET_FRIENDLY else FPB.KIND_NO_PETS
                cls, why = FPB.classify_quote(ev["quote"], kind=kind, context=ev.get("context", ""))
                # DENVER: ANOTHER READ OF THE SAME IDENTITY MAY BE OPERATIVE WHERE THIS ONE IS A LABEL. When the
                # chosen read's quote is not eligible, every other read of the SAME identity that states the same
                # claim, does not conflict with the bound route and that the shared reader accepts is tried, in
                # the order added. The shared reader stays the only gate.
                if cls != FPB.ELIGIBLE:
                    for alt in BY_KEY_ALL.get(key, []):
                        if alt is ev or alt.get("pets_allowed_claim") != ev.get("pets_allowed_claim"):
                            continue
                        if route_domain_conflict(h, alt):
                            continue
                        alt_pa, alt_conflict = negation_check(alt["quote"], alt["pets_allowed_claim"])
                        if alt_conflict or alt_pa is not (row["disposition"] == CLEAN_PET_FRIENDLY):
                            continue
                        acls, awhy = FPB.classify_quote(alt["quote"], kind=kind, context=alt.get("context", ""))
                        if acls == FPB.ELIGIBLE:
                            ev, cls, why = alt, acls, awhy
                            row["evidence"] = ev
                            if row["disposition"] == CLEAN_PET_FRIENDLY:
                                row["policy_facts"] = extract_facts((ev["quote"] + " " + ev.get("context", "")).strip())
                            break
                if cls != FPB.ELIGIBLE:
                    negation_conflicts.append(OrderedDict([
                        ("identity_key", key), ("name", h["canonical_name"]),
                        ("why", "SHARED_READER_DISAGREES -- this order read %s; the shared first_party_binding "
                                "reader classifies the same quote %s: %s" % (row["disposition"], cls, why))]))
                    row["disposition"] = EVIDENCE_HOLD
                    row.pop("policy_facts", None)
                    row["hold_reason"] = ("the shared reader that FAST rule C re-runs at seal time classifies "
                                          "this quote %s (%s), not an operative %s statement; held rather than "
                                          "published on a disagreement this order does not get to override"
                                          % (cls, why[:200], kind))
        else:
            reason, why = router_hold_reason(key, routing_by_key, static_by_key, fc_by_key, census_row=h)
            row["disposition"] = reason
            row["hold_reason"] = why
        rows.append(row)

    # ONE ARTIFACT, MANY PREMISES (the rule Fort Lauderdale's build proved and this one inherits). A
    # multi-property operator can serve one landing page for every building it runs -- Hollywood's Richard's
    # Motel family ran six licensed premises behind one site there, and the Philips Highway and
    # multi-building motor-court operators are the same shape here. A document bound to more than one census identity cannot say which building it is about, so it
    # establishes a policy for NONE of them -- the inverse of the rule that two pages claiming one address
    # publish neither. Held on the document, never resolved by preferring one row.
    shared_documents = []
    by_document = {}
    for row in rows:
        ev = row.get("evidence") or {}
        doc = (ev.get("document_sha256") or "").strip()
        if doc and row["disposition"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
            by_document.setdefault(doc, []).append(row)
    for doc, sharing in sorted(by_document.items()):
        if len(sharing) < 2:
            continue
        keys = sorted(r["identity_key"] for r in sharing)
        for row in sharing:
            row["disposition"] = EVIDENCE_HOLD
            row["hold_reason"] = (
                "one artifact (sha256:%s) is the ONLY policy evidence for %d different premises (%s); a "
                "document bound to more than one building cannot say which building it is about, so it "
                "establishes a policy for none of them" % (doc[:16], len(sharing), ", ".join(keys)))
        shared_documents.append(OrderedDict([
            ("document_sha256", doc), ("identity_keys", keys),
            ("source_url", (sharing[0].get("evidence") or {}).get("source_url", "")),
            ("held", len(sharing)),
        ]))

    # TWO ROWS, ONE PREMISES. A dual-brand building is TWO hotels (standing rule) and publishes only
    # once a committed same-campus resolution in the SHARED identity_resolutions.json says the two identities
    # at that address are distinct. This order writes no shared document, so both halves are HELD and the
    # resolution a registration order should add is named in the reason. Left unheld, the site generator folds
    # the pair into one profile and the release gates refuse the build.
    same_premises = []
    preopening_held = []
    _census_by_key = {h["identity_key"]: h for h in hotels}
    resolved_keys = set()
    try:
        _res = _load(os.path.join(PKG, "identity_resolutions.json"), {}) or {}
        for _r in _res.get("resolutions") or []:
            if _r.get("market_id") == MARKET_ID and _r.get("address_key"):
                resolved_keys.add(_r["address_key"])
    except Exception:                                            # noqa: BLE001 - absence is not a resolution
        resolved_keys = set()
    by_premises = {}
    for row in rows:
        if row["disposition"] not in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
            continue
        h = _census_by_key.get(row["identity_key"]) or {}
        street, postal = (h.get("street") or ""), (h.get("postal_code") or "")[:5]
        m = re.match(r"\s*(\d+)", street)
        if not (m and postal):
            continue
        token = ""
        for word in street.split()[1:]:
            w = re.sub(r"[^a-z0-9]", "", word.lower())
            if w and w not in ("n", "s", "e", "w", "ne", "nw", "se", "sw", "north", "south", "east", "west"):
                token = w
                break
        by_premises.setdefault("%s|%s|%s" % (m.group(1), token, postal), []).append(row)
    for _akey, sharing in sorted(by_premises.items()):
        if len(sharing) < 2 or _akey in resolved_keys:
            continue
        codes = sorted({(_census_by_key.get(r["identity_key"]) or {}).get("property_code") or "" for r in sharing})
        names = sorted((_census_by_key.get(r["identity_key"]) or {}).get("canonical_name") or r["identity_key"]
                       for r in sharing)
        for row in sharing:
            row["disposition"] = IDENTITY_MISMATCH_HOLD
            row["hold_reason"] = (
                "SAME PREMISES, TWO IDENTITIES (address_key %s): %s. A dual-brand building is TWO hotels and "
                "publishes only once a committed same_campus_distinct_entity resolution for this address_key "
                "names both identities; this order writes no shared document, so both halves are held. The "
                "split IS proved -- brand property codes %s, each read on its own first-party page."
                % (_akey, " / ".join(names), " + ".join(c for c in codes if c)))
        same_premises.append(OrderedDict([
            ("address_key", _akey), ("identities", names),
            ("brand_property_codes", [c for c in codes if c]), ("held", len(sharing)),
            ("resolution_a_registration_order_should_add", "same_campus_distinct_entity"),
        ]))

    # DENVER: A HOTEL THAT IS NOT YET OPEN DOES NOT PUBLISH (PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003).
    # Wyndham's own property service names 13560 Grant St "ECHO Suites Denver North - Thornton - Opening Early
    # 2027": the pet policy it states is first-party and genuine, but a traveller cannot stay at a hotel that does
    # not operate yet. The founder ruled it nonpublishing until it is open and revalidated. It is HELD -- never
    # VERIFIED_NO_PETS, never deleted -- and its first-party evidence and the facts it would publish are kept on
    # the row for that revalidation.
    # PHOENIX: THE PAGE'S OWN WORDS COUNT, NOT ONLY ITS NAME. Home2 Suites Peoria North's own Hilton page states
    # "We're accepting reservations for September 30, 2026 and beyond" (read 2026-09-29) under a name with no
    # opening wording at all, so a name-only test would have published a hotel that is not open. Every attended
    # read that recorded such a statement holds its bound identity, whatever the row's disposition.
    page_stated = {}
    for _br in (_load(os.path.join(STAGING, "browser_closure_rows.json"), {}) or {}).get("rows", []):
        if _br.get("identity_key") and _br.get("preopening_statement"):
            page_stated[_br["identity_key"]] = _br["preopening_statement"]
    # SAN ANTONIO: THE BRAND'S OWN INVENTORY CARD COUNTS TOO. Hilton's own San Antonio city page lists "Homewood
    # Suites by Hilton San Antonio at the Rim, TX" (ausbohw) with open = false and an opening date of 2027-02-05;
    # the attended browser could not open its page (Akamai), so without the card the row would read as merely
    # unattempted. A brand card that states the hotel is not open holds the row exactly like the page's own words.
    card_stated = {}
    for _lead in (_load(os.path.join(REPORTS, "san_antonio_tx_brand_inventory_001.json"), {}) or {}).get("leads", []):
        _card = _lead.get("brand_card") or {}
        if _card.get("open") is False and _lead.get("property_code"):
            card_stated[((_lead.get("family") or "").upper(), _lead["property_code"].lower())] = (
                "open = false; opening %s (the brand's own city-page card)" % (_card.get("open_date") or "undated"))
    for row in rows:
        h = _census_by_key.get(row["identity_key"]) or {}
        _name_hit = _PREOPENING.search(h.get("canonical_name") or "")
        _card_hit = card_stated.get(((h.get("brand") or "").upper(), (h.get("property_code") or "").lower()), "")
        stated_text = (_name_hit.group(0) if _name_hit else page_stated.get(row["identity_key"], "")) or _card_hit
        if not stated_text:
            continue
        stated_where = "name" if _name_hit else ("page" if not _card_hit or page_stated.get(row["identity_key"])
                                                 else "inventory card")
        row["disposition_before_preopening_hold"] = row["disposition"]
        if "policy_facts" in row:
            row["policy_facts_for_revalidation"] = row.pop("policy_facts")
        row["disposition"] = EVIDENCE_HOLD
        row["hold_reason"] = (
            "PREOPENING_NOT_YET_OPEN -- the property's own first-party %s states %r: the hotel is not open, so "
            "no profile publishes until it opens and its policy is revalidated. The first-party evidence is kept "
            "on this row; this is not a refusal and never a verified no-pets." % (stated_where, stated_text))
        preopening_held.append(OrderedDict([
            ("identity_key", row["identity_key"]), ("canonical_name", h.get("canonical_name")),
            ("street", h.get("street")), ("postal_code", h.get("postal_code")),
            ("official_url", h.get("official_url")), ("stated_opening", stated_text),
            ("stated_on", stated_where),
            ("disposition_before_hold", row["disposition_before_preopening_hold"])]))

    # DENVER: TWO NAMES THE SITE CANNOT TELL APART. A profile page's title is its H1 cut at the shared SEO
    # engine's TITLE_MAX_LENGTH, and the engine refuses to compile two pages with one title (FAST rule J measured
    # it: "Extended Stay America Select Suites Denver - Tech Center South" and "... - Tech Center South -
    # Greenwood Village" are both the brand's own names and share their first 60 characters). Shortening either
    # name would invent a name no source states, so BOTH are held; the display name each should carry is a
    # founder naming decision.
    by_title = {}
    for row in rows:
        if row["disposition"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
            by_title.setdefault(row["canonical_name"][:TITLE_MAX_LENGTH], []).append(row)
    for title, sharing in sorted(by_title.items()):
        if len(sharing) < 2:
            continue
        names = sorted(r["canonical_name"] for r in sharing)
        for row in sharing:
            row["disposition"] = IDENTITY_MISMATCH_HOLD
            row.pop("policy_facts", None)
            row["hold_reason"] = (
                "SITE TITLE COLLISION: %s share their first %d characters (%r), the site's title limit, and the "
                "shared SEO engine refuses two pages with one title. Both names are first-party; shortening either "
                "would invent a name, so both are held for a founder naming decision."
                % (" / ".join(names), TITLE_MAX_LENGTH, title))

    counts = Counter(r["disposition"] for r in rows)
    pf = [r for r in rows if r["disposition"] == CLEAN_PET_FRIENDLY]
    np_ = [r for r in rows if r["disposition"] == CLEAN_VERIFIED_NO_PETS]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "15-19 -- policy adjudication, negation safety, one disposition per row"),
        ("no_inference_from_silence",
         "A page that states no pet policy is SOURCE_SILENT; it is never read as acceptance or refusal."),
        ("no_inference_from_amenity_alone",
         "A fee, weight or count sentence alone, with no explicit acceptance wording in the same quote, is held "
         "as EVIDENCE_HOLD rather than published; every genuine CLEAN_PET_FRIENDLY row in this market was read "
         "directly from a 'Pets allowed: Yes' / 'Pets Welcome' field or FAQ sentence, so this rule is a safety "
         "net that this run's own captures did not need to exercise except as a guard."),
        ("negation_conflicts_caught", negation_conflicts),
        ("one_artifact_many_premises_held", shared_documents),
        ("same_premises_two_identities_held", same_premises),
        ("preopening_held", preopening_held),
        ("preopening_rule",
         "A property whose own first-party name states it has not opened yet ('Opening Early 2027', 'Coming "
         "Soon') is HELD (EVIDENCE_HOLD, hold reason PREOPENING_NOT_YET_OPEN) until it opens and its policy is "
         "revalidated; its evidence is kept, and it is never a verified no-pets."),
        ("same_premises_rule",
         "Two rows that share one premises publish only when a committed same_campus_distinct_entity "
         "resolution for that address_key names both. This order writes no shared document, so both "
         "halves of each dual-brand building are HELD and the resolution a registration order should "
         "add is named in the hold reason."),
        ("not_first_party_sites_refused", OrderedDict(sorted(NOT_FIRST_PARTY_SITES.items()))),
        ("amenity_label_only_not_acceptance", OrderedDict(sorted(AMENITY_LABEL_ONLY.items()))),
        ("crawled_rows_rekeyed_by_own_address", OrderedDict(sorted(REKEYED_CRAWLED_ROWS.items()))),
        ("not_first_party_site_rule",
         "A crawled site (the independents' policy-pages lane and the Places closure lane) speaks for a property "
         "only when its registrable domain carries a distinctive word of the property's own name; a directory, "
         "travel-blog or booking page that interleaves guest reviews never binds a policy."),
        ("one_artifact_many_premises_rule",
         "A document that is the only policy evidence for more than one census premises establishes a "
         "policy for NONE of them. A multi-property operator's shared landing page is the common case "
         "in Fort Lauderdale (Hollywood's Richard's Motel family of lodgings), and re-armed here. The inverse of the rule that two "
         "pages claiming one address publish neither."),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("valid_pet_friendly", len(pf)), ("valid_verified_no_pets", len(np_)),
        ("resolved", len(pf) + len(np_)), ("unresolved", len(hotels) - len(pf) - len(np_)),
        ("rows", rows),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("counts:", dict(rep["counts"]))
    print("PF %d / NP %d / resolved %d / unresolved %d" % (
        rep["valid_pet_friendly"], rep["valid_verified_no_pets"], rep["resolved"], rep["unresolved"]))
    print("negation conflicts:", len(rep["negation_conflicts_caught"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
