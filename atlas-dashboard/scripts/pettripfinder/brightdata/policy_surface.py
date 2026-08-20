"""Finding a pet policy on a page nobody wrote a scraper for.

WHY THIS IS NOT SIX BRAND SCRAPERS
----------------------------------
The work order is explicit: do not prematurely write permanent brand scrapers;
record the successful pattern and then decide whether an adapter is justified.
So this module locates a policy the same way for every brand, and REPORTS
which strategy worked. Six scrapers would answer the question by assuming it.

A generic locator is also the only honest instrument for the question being
asked. If a per-brand selector finds Hilton's panel, that tells us a human read
Hilton's DOM; it says nothing about whether the seventh brand will work. What
the pilot needs to know is how far one bounded, structural strategy carries.

STILL BOUNDED, STILL NOT A KEYWORD SWEEP
----------------------------------------
The previous pilot's failure mode was collecting every line containing "pet" or
"weight" and returning, among the policy::

    Fitness center with cardiovascular and weight equipment

Generalising the locator must not reintroduce that. Two rules keep it out:

1. A match requires a POLICY SIGNAL PHRASE -- "pet policy", "pets welcome",
   "pets not allowed", "pet fee", "maximum pet weight" -- never a bare topic
   word. "weight equipment" contains "weight" and matches nothing here.
2. The result is a CONTAINER under a length cap, chosen by walking up from the
   signal and keeping whichever ancestor carries the MOST distinct policy
   features. Minimising size instead was tried and was wrong in a way that
   looked right: the smallest element containing "Pet Policy" is the heading
   "Pet Policy", so five brands returned a ten-character block and an
   extraction of nothing while every gate still said VALID. A container that
   grows past the cap is dropped rather than trimmed, because "the whole page"
   is not a policy block and a trimmed one is a stitched quote.

INTERACTION BEFORE LOCATION
---------------------------
Several brands render the policy behind an accordion or a tab. The page is
therefore prodded first -- ``<details>`` opened, and elements whose own label
mentions pets or policies clicked -- and every action is recorded in the
manifest. Clicks are restricted to in-page disclosure controls and never to
anything that navigates, because a click that leaves the page loses the
capture and a click that opens a dialog freezes the session.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402

#: The smallest container that may count as a policy block, and the largest.
#: Below the floor there is not enough text to carry a policy; above the
#: ceiling the "container" is a page section and the quote stops being a quote.
MIN_BLOCK_CHARS = 16
MAX_BLOCK_CHARS = 1500

#: How many distinct policy FEATURES a container must carry to count. One
#: is enough -- a property whose entire statement is "Pets allowed" has
#: said something -- but the winner is whichever qualifying container
#: carries the most, so a bare heading loses to the block holding it and
#: the fee.
MIN_POLICY_FEATURES = 1

#: How many distinct pet mentions a container needs, and the length past which
#: one is no longer enough.
#:
#: A hotel's amenity list carries the chip "Pet Friendly" among a thousand
#: characters of parking and wifi: a page section that MENTIONS pets rather
#: than one about them. A ratio was tried first and failed in the other
#: direction -- it rewarded a twenty-three-character fragment over the real
#: policy -- so the rule is a scaled count instead. Short statements qualify on
#: one mention; anything long enough to be a page section must say it twice.
MIN_PET_MENTIONS_SHORT = 1
MIN_PET_MENTIONS_LONG = 2
LONG_BLOCK_CHARS = 300

#: Phrases that mean a page is TALKING ABOUT ITS PET POLICY. Every one names
#: pets and a policy act -- welcoming, refusing, charging, limiting. None is a
#: bare topic word, which is what keeps a gym's weight equipment out.
SIGNAL_PHRASES: Tuple[str, ...] = (
    "pet policy", "pet policies", "pets welcome", "pets are welcome",
    "pets not allowed", "pets are not allowed", "no pets allowed",
    "pets not permitted", "pets are not permitted", "pets allowed",
    "pets permitted", "pet fee", "pet fees", "pet friendly",
    "maximum pet weight", "maximum number of pets", "service animals",
    "we welcome pets", "pet charge", "pet deposit", "dogs only",
    "pets stay free",
    # A property that names the SPECIES has still named a pet policy. The
    # parser already accepts "Dogs Allowed" as an acceptance; the locator did
    # not, so a page whose only wording was species-named was never reached at
    # all -- Wildwood Lodge published a fee, a count and a species under the
    # heading "dog friendly hotel" and this walk considered zero candidates on
    # it. These are the species-named mirrors of the phrases already above,
    # added by PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016.
    # Only the DOG forms, and deliberately. The cat forms were symmetry rather
    # than measurement -- no surface in the corpus needed them -- and admitting
    # them would have meant loosening the invariant that every signal phrase
    # names an animal, because "cat" is a substring of ordinary hotel words
    # like "vacation" and "location". A speculative phrase is not worth a
    # weaker guard.
    "dog friendly", "dog-friendly", "dogs welcome", "dogs are welcome",
    "dogs allowed", "dogs are allowed", "dog policy", "dog fee", "dog charge",
)

#: Selectors that name a brand's own pet-policy container, tried BEFORE the
#: generic walk and permitted to read text the page has not rendered.
#:
#: Deliberately short and deliberately not a scraper: each entry is one
#: container selector, discovered by reading a persisted artifact rather than
#: by guessing, and the generic walk still runs when it misses.
BRAND_LOCATORS = {
    "WYNDHAM": (
        # <span class="policy-desc pet-policy-desc">Service Animals - ... /
        # Dogs Allowed - 2 dogs max. ... / Fees - 25 USD per pet per night.</span>
        ("wyndham_pet_policy_desc", ".pet-policy-desc"),
        ("wyndham_pet_policy_items", ".policy-items.pet-policy"),
    ),
    "CHOICE": (
        ("choice_pet_section", "[class*='pet'],[data-testid*='pet']"),
    ),
    "HILTON": (
        ("hilton_pet_panel", "[data-testid*='pet'],[id*='pet'],[class*='pet']"),
    ),
}

#: Labels whose disclosure control is worth opening before looking. Kept narrow
#: on purpose: a click is a page mutation and the wrong one navigates away.
EXPAND_LABEL_RE = (r"pet|policy|policies|amenit|hotel information|"
                   r"property information|good to know|house rules|faq")

#: Elements that may be clicked to disclose. Anchors with an href that leaves
#: the page are excluded inside the script itself.
EXPAND_SELECTORS = ("details > summary", "button", "[role='button']",
                    "[aria-expanded='false']", ".accordion-button",
                    "[data-toggle='collapse']", "[class*='accordion'] button")


#: The distinct things a pet policy can SAY. Counting them measures how much of
#: a policy a block actually holds, and is the one yardstick every locator in
#: this package is judged by -- the in-page walk, the brand selectors and the
#: static-HTML reader alike.
POLICY_FEATURE_RES: Tuple[re.Pattern, ...] = (
    re.compile(r"pets?\s*:?\s*(?:are\s+)?(?:welcome|allowed|permitted|"
               r"not\s+allowed|not\s+permitted)", re.IGNORECASE),
    re.compile(r"no\s+pets?\b", re.IGNORECASE),
    re.compile(r"\$\s*\d|\d+(?:\.\d{2})?\s*USD\b"),
    re.compile(r"\d+\s*(?:lbs?|pounds?|kgs?)\b", re.IGNORECASE),
    re.compile(r"\d+\s*pets?\b", re.IGNORECASE),
    re.compile(r"\bpets?\s+(?:fee|deposit|charge)\b", re.IGNORECASE),
    re.compile(r"\b(?:non-?refundable|deposit)\b", re.IGNORECASE),
    re.compile(r"\bservice\s+animals?\b", re.IGNORECASE),
    re.compile(r"\b(?:dogs?|cats?)\b", re.IGNORECASE),
    re.compile(r"\bbreed\b", re.IGNORECASE),
)


def policy_features(text: str) -> int:
    """How many distinct policy features a block carries."""
    return sum(1 for pattern in POLICY_FEATURE_RES if pattern.search(text or ""))


@dataclass(frozen=True)
class SurfaceHit:
    """One located policy container."""

    found: bool
    text: str = ""
    strategy: str = ""
    selector: str = ""
    matched_phrase: str = ""
    container_chars: int = 0
    candidates_considered: int = 0
    policy_features: int = 0
    brand_generic: bool = False
    rendered: bool = True

    def to_dict(self) -> Dict:
        return {"found": self.found, "strategy": self.strategy,
                "selector": self.selector,
                "matched_phrase": self.matched_phrase,
                "container_chars": self.container_chars,
                "policy_features": self.policy_features,
                "brand_generic": self.brand_generic,
                "rendered": self.rendered,
                "candidates_considered": self.candidates_considered}


# --------------------------------------------------------------------------- #
# In-page scripts.
# --------------------------------------------------------------------------- #

#: Open disclosure controls whose label suggests they hide a policy.
#:
#: Returns what it opened so the manifest can record the interaction. Anchors
#: that would navigate are skipped, and so is anything already expanded --
#: clicking an open accordion closes it.
_EXPAND_SCRIPT = """
(args) => {
    const labelRe = new RegExp(args.labelRe, 'i');
    const opened = [];
    for (const el of document.querySelectorAll('details')) {
        const label = (el.textContent || '').slice(0, 120);
        if (!el.open && labelRe.test(label)) { el.open = true;
            opened.push('details: ' + label.trim().slice(0, 60)); }
    }
    for (const selector of args.selectors) {
        for (const el of document.querySelectorAll(selector)) {
            if (opened.length >= args.limit) return opened;
            const tag = (el.tagName || '').toLowerCase();
            if (tag === 'a') {
                const href = el.getAttribute('href') || '';
                if (href && !href.startsWith('#')) continue;
            }
            if (el.getAttribute('aria-expanded') === 'true') continue;
            const label = (el.getAttribute('aria-label') || el.textContent || '')
                          .trim().slice(0, 120);
            if (!label || !labelRe.test(label)) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) continue;
            try { el.click();
                  opened.push(selector + ': ' + label.slice(0, 60)); }
            catch (e) { /* a control that refuses to be clicked is not fatal */ }
        }
    }
    return opened;
}
"""

#: Locate the RICHEST bounded container holding a policy signal phrase.
#:
#: The first version of this minimised container size and was wrong in a way
#: that looked right: the smallest element containing "Pet Policy" is the
#: HEADING "Pet Policy", so five brands returned a ten-character block, an
#: extraction of nothing, and a perfectly valid-looking capture. A bounded
#: locator has to be bounded on BOTH sides.
#:
#: So each signal is walked upward and every ancestor under the ceiling is
#: scored by how many distinct policy FEATURES it carries -- an acceptance or
#: refusal, a price, a weight, a count, a deposit, service-animal wording. The
#: winner is the ancestor carrying the most, and only among equals is the
#: smaller preferred. A heading alone scores one and loses to the block that
#: contains it and the fee.
_LOCATE_SCRIPT = r"""
(args) => {
    const phrases = args.phrases;
    const isVisible = (el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return false;
        const s = window.getComputedStyle(el);
        return s.visibility !== 'hidden' && s.display !== 'none';
    };
    const cssPath = (el) => {
        const parts = [];
        let node = el;
        while (node && node.nodeType === 1 && parts.length < 5) {
            let part = node.tagName.toLowerCase();
            if (node.id) { parts.unshift(part + '#' + node.id); break; }
            const cls = (node.getAttribute('class') || '').trim()
                        .split(/\s+/).filter(Boolean).slice(0, 2);
            if (cls.length) part += '.' + cls.join('.');
            parts.unshift(part);
            node = node.parentElement;
        }
        return parts.join(' > ');
    };
    const norm = (t) => (t || '').replace(/\s+/g, ' ').trim();
    // What the page DISPLAYS. textContent joins adjacent elements with no
    // separator ("Pets allowedYes"), which breaks every word boundary the
    // reader depends on; innerText inserts the breaks the layout implies.
    const shown = (el) => norm(el.innerText !== undefined && el.innerText !== null
                               ? el.innerText : el.textContent);
    // Chain-wide phrasing. A sentence about every hotel in the brand is not
    // this property's policy, so it is outranked by anything property-specific.
    const GENERIC = /\ball (?:of )?our (?:hotels|properties|locations)\b|\ball locations\b|\bmost of our\b|\bvaries by (?:hotel|location|property)\b|\bat all .{0,20}hotels\b/i;

    // Distinct policy FEATURES. Each is a different thing a policy can say, so
    // counting them measures how much of the policy a container actually holds.
    const FEATURES = [
        /pets?\s*:?\s*(?:are\s+)?(?:welcome|allowed|permitted|not\s+allowed|not\s+permitted)/i,
        /no\s+pets?\b/i,
        /\$\s*\d/,
        /\d+\s*(?:lbs?|pounds?|kgs?)\b/i,
        /\d+\s*pets?\b/i,
        /\bpets?\s+(?:fee|deposit|charge)\b/i,
        /\b(?:non-?refundable|deposit)\b/i,
        /\bservice\s+animals?\b/i,
        /\b(?:dogs?|cats?)\b/i,
        /\bbreed\b/i,
    ];
    const petMentions = (text) => {
        const hits = text.match(/pets?|animals?|dogs?|cats?/gi);
        return hits ? hits.length : 0;
    };
    const aboutPets = (text) => petMentions(text) >= (
        text.length > args.longBlock ? args.minMentionsLong
                                     : args.minMentionsShort);
    const score = (text) => {
        const features = FEATURES.reduce((n, re) => n + (re.test(text) ? 1 : 0), 0);
        return GENERIC.test(text) ? features - 1 : features;
    };

    const candidates = [];
    for (const el of document.querySelectorAll(
            'h1,h2,h3,h4,h5,h6,p,span,div,li,dt,dd,strong,b,td,th,summary')) {
        const text = norm(el.textContent).toLowerCase();
        if (!text || text.length > args.maxBlock * 3) continue;
        const phrase = phrases.find((p) => text.includes(p));
        if (!phrase) continue;
        if (!isVisible(el)) continue;
        candidates.push({el: el, phrase: phrase});
    }

    let best = null;
    for (const candidate of candidates) {
        let node = candidate.el;
        let hops = 0;
        while (node && hops < 8) {
            const text = shown(node);
            if (text.length > args.maxBlock) break;
            if (text.length >= args.minBlock && aboutPets(text)) {
                const features = score(text);
                if (features >= args.minFeatures || (best === null && features > 0)) {
                    if (!best || features > best.features
                        || (features === best.features && text.length < best.chars)) {
                        best = {chars: text.length, text: text,
                                features: features, selector: cssPath(node),
                                phrase: candidate.phrase, hops: hops,
                                generic: GENERIC.test(text)};
                    }
                }
            }
            node = node.parentElement;
            hops += 1;
        }
    }
    if (!best) return {found: false, considered: candidates.length};
    return {found: true, text: best.text, selector: best.selector,
            phrase: best.phrase, chars: best.chars, hops: best.hops,
            features: best.features, generic: best.generic,
            considered: candidates.length};
}
"""


async def expand_disclosures(page, *, limit: int = 12) -> Tuple[str, ...]:
    """Open accordions and tabs that plausibly hide a policy. Never fatal."""
    try:
        opened = await page.evaluate(
            _EXPAND_SCRIPT,
            {"labelRe": EXPAND_LABEL_RE, "selectors": list(EXPAND_SELECTORS),
             "limit": limit})
        return tuple(str(x) for x in (opened or ()))
    except Exception:                                            # noqa: BLE001
        return ()


_BRAND_READ_SCRIPT = r"""
(selector) => {
    for (const el of document.querySelectorAll(selector)) {
        const shown = (el.innerText || '').replace(/\s+/g, ' ').trim();
        const present = (el.textContent || '').replace(/\s+/g, ' ').trim();
        const text = shown || present;
        if (!text) continue;
        return {text: text, rendered: shown.length > 0, chars: text.length};
    }
    return null;
}
"""


async def locate_brand_policy(page, brand: str) -> Optional[SurfaceHit]:
    """A brand's own policy container, including text the page has not painted.

    Returns ``None`` when the brand has no entry or none of its selectors
    resolve, so the caller falls through to the generic walk unchanged.
    """
    for locator_id, selector in BRAND_LOCATORS.get(brand or "", ()):
        try:
            result = await page.evaluate(_BRAND_READ_SCRIPT, selector)
        except Exception:                                        # noqa: BLE001
            continue
        if not result:
            continue
        text = MS.collapse(str(result.get("text") or ""))
        if not (MIN_BLOCK_CHARS <= len(text) <= MAX_BLOCK_CHARS):
            continue
        return SurfaceHit(found=True, text=text, strategy=locator_id,
                          selector=selector, matched_phrase="brand container",
                          container_chars=len(text),
                          policy_features=policy_features(text),
                          rendered=bool(result.get("rendered")))
    return None


async def locate_policy(page, brand: str = "") -> SurfaceHit:
    """Find the bounded policy container, generically.

    Tried in order: the Marriott-shaped structural locators first (they are
    exact where they apply and cost one selector each), then the generic
    signal-phrase walk. Whichever succeeds is NAMED in the result, which is the
    observation the adapter decision rests on.
    """
    # The brand selector is a CANDIDATE, not an answer. It competes with the
    # structural and generic strategies below on policy features, because a
    # brand selector that matches a two-word label is worse than the walk it
    # would otherwise have pre-empted.
    brand_hit = await locate_brand_policy(page, brand)

    for locator_id, selector in MS.POLICY_LOCATORS:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            text = MS.collapse(await locator.inner_text(timeout=8_000))
        except Exception:                                        # noqa: BLE001
            continue
        if MIN_BLOCK_CHARS <= len(text) <= MAX_BLOCK_CHARS:
            structural = SurfaceHit(found=True, text=text, strategy=locator_id,
                                    selector=selector,
                                    matched_phrase=MS.POLICY_HEADING.lower(),
                                    container_chars=len(text),
                                    policy_features=policy_features(text))
            return _best(brand_hit, structural)

    try:
        result = await page.evaluate(
            _LOCATE_SCRIPT,
            {"phrases": list(SIGNAL_PHRASES), "minBlock": MIN_BLOCK_CHARS,
             "maxBlock": MAX_BLOCK_CHARS,
             "minFeatures": MIN_POLICY_FEATURES,
             "minMentionsShort": MIN_PET_MENTIONS_SHORT,
             "minMentionsLong": MIN_PET_MENTIONS_LONG,
             "longBlock": LONG_BLOCK_CHARS})
    except Exception:                                            # noqa: BLE001
        return SurfaceHit(found=False, strategy="generic_signal_walk")

    if not result or not result.get("found"):
        return brand_hit or SurfaceHit(
            found=False, strategy="generic_signal_walk",
            candidates_considered=int((result or {}).get("considered") or 0))
    return _best(brand_hit, SurfaceHit(
        found=True, text=MS.collapse(str(result.get("text") or "")),
        strategy="generic_signal_walk",
        selector=str(result.get("selector") or ""),
        matched_phrase=str(result.get("phrase") or ""),
        container_chars=int(result.get("chars") or 0),
        policy_features=int(result.get("features") or 0),
        brand_generic=bool(result.get("generic")),
        candidates_considered=int(result.get("considered") or 0)))


def _best(*hits) -> SurfaceHit:
    """The candidate carrying the most policy features; smaller breaks a tie."""
    found = [h for h in hits if h is not None and h.found]
    if not found:
        return SurfaceHit(found=False, strategy="no_candidate")
    return max(found, key=lambda h: (h.policy_features, -h.container_chars))


async def locate_element(page, hit: SurfaceHit):
    """A Playwright locator for the container ``hit`` describes, for the
    element screenshot. Falls back to a text-anchored locator when the CSS
    path does not resolve -- a path built from two class names is a
    convenience, not an identity."""
    if hit.selector and hit.strategy != "generic_signal_walk":
        return page.locator(hit.selector).first
    if hit.selector:
        try:
            locator = page.locator("css=" + hit.selector).first
            if await locator.count() > 0:
                return locator
        except Exception:                                        # noqa: BLE001
            pass
    snippet = hit.text[:60]
    if snippet:
        try:
            locator = page.get_by_text(snippet, exact=False).first
            if await locator.count() > 0:
                return locator
        except Exception:                                        # noqa: BLE001
            pass
    return None


# --------------------------------------------------------------------------- #
# Identity, generically.
# --------------------------------------------------------------------------- #

_OG_TITLE_RE = re.compile(
    r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"']([^\"']+)[\"']",
    re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

#: Brands whose property URLs carry a code we can bind identity to. Absent from
#: this map means the URL PATH is the binding instead -- which is weaker, and
#: the assessment says so rather than pretending otherwise.
PROPERTY_CODE_PATTERNS: Dict[str, str] = {
    "MARRIOTT": r"/hotels/([a-z0-9]{4,7})-",
    "HILTON": r"/en/hotels/([a-z0-9]{6,12})-",
    "IHG": r"/hotels/[a-z]{2}/[a-z]+/([a-z0-9]{5})/",
    "CHOICE": r"/[a-z]{2}/[a-z-]+/[a-z-]+-hotel/([a-z0-9]{4,8})",
}


def property_code(url: str, brand: str) -> str:
    pattern = PROPERTY_CODE_PATTERNS.get(brand)
    if not pattern:
        return ""
    match = re.search(pattern, url or "", re.IGNORECASE)
    return match.group(1).lower() if match else ""


def any_hotel_jsonld(html: str) -> Optional[Dict]:
    """The page's lodging JSON-LD, whatever ``@type`` it chose.

    ``Hotel`` is the common one; ``LodgingBusiness``, ``Motel``, ``Resort`` and
    ``BedAndBreakfast`` all appear across this corpus's independents, and a
    reader that only knows ``Hotel`` would call an inn's identity absent.
    """
    lodging_types = {"hotel", "lodgingbusiness", "motel", "resort",
                     "bedandbreakfast", "inn", "hostel", "apartment"}
    for match in MS._LD_JSON_RE.finditer(html or ""):
        try:
            parsed = json.loads(match.group(1).strip())
        except (ValueError, TypeError):
            continue
        stack = parsed if isinstance(parsed, list) else [parsed]
        for node in stack:
            if not isinstance(node, Mapping):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(x for x in graph if isinstance(x, Mapping))
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if any(str(t or "").lower() in lodging_types for t in types):
                return dict(node)
    return None


def read_identity(html: str, *, final_url: str, title: str,
                  brand: str) -> MS.IdentitySignals:
    """Identity signals for any brand.

    Prefers structured data, falls back to ``og:title`` and then the document
    title. The fallbacks are recorded by ``jsonld_present`` being False, which
    the assessment treats as a weaker binding rather than an equal one.
    """
    node = any_hotel_jsonld(html)
    canonical = MS.canonical_url(html)
    code = (property_code(canonical, brand) or property_code(final_url, brand))
    if node:
        address = node.get("address") or {}
        if not isinstance(address, Mapping):
            address = {}
        pets = node.get("petsAllowed")
        return MS.IdentitySignals(
            name_on_page=str(node.get("name") or "").strip(),
            address_on_page=str(address.get("streetAddress") or "").strip(),
            postal_code=str(address.get("postalCode") or "").strip(),
            phone_on_page=str(node.get("telephone") or "").strip(),
            property_code_on_page=code,
            canonical_url=canonical or str(node.get("url") or ""),
            pets_allowed_structured=("" if pets is None else str(pets).strip()),
            jsonld_present=True)
    og = _OG_TITLE_RE.search(html or "")
    doc = _TITLE_RE.search(html or "")
    name = MS.collapse(og.group(1) if og else (doc.group(1) if doc else title))
    return MS.IdentitySignals(name_on_page=name, property_code_on_page=code,
                              canonical_url=canonical, jsonld_present=False)


def assess_identity(signals: MS.IdentitySignals, *, expected_name: str,
                    expected_property_code: str, expected_url: str,
                    expected_postal_code: str = "") -> MS.IdentityAssessment:
    """Is this the property we asked for, when there may be no property code?

    Where a code exists it decides, exactly as in the Marriott pilot. Where the
    brand has no code in its URLs -- most independents, and several chains --
    the binding falls back to the URL PATH plus the name, and the assessment
    records which of the two it used. A generic brand page never passes either
    way: its path is not the property's path and its name is the brand's.
    """
    matched: List[str] = []
    conflicting: List[str] = []
    reasons: List[str] = []

    page_code = (signals.property_code_on_page or "").lower()
    want_code = (expected_property_code or "").lower()
    if want_code:
        if page_code == want_code:
            matched.append("property_code")
        elif page_code:
            conflicting.append("property_code")
            reasons.append("page property code %r != expected %r"
                           % (page_code, want_code))
        else:
            reasons.append("no property code found on the page")

    page_tokens = MS.name_tokens(signals.name_on_page)
    want_tokens = MS.name_tokens(expected_name)
    if page_tokens and want_tokens:
        overlap = page_tokens & want_tokens
        if page_tokens <= want_tokens or want_tokens <= page_tokens:
            matched.append("name")
        elif len(overlap) >= 2 and len(overlap) >= len(want_tokens) - 2:
            # A brand page's name shares at most the brand word. Two or more
            # distinctive tokens in common, with at most two missing, is the
            # same property described differently -- "Hampton Inn Dayton South"
            # against "Hampton Inn by Hilton Dayton South".
            matched.append("name_partial")
        else:
            conflicting.append("name")
            reasons.append("page names %r, which does not agree with %r"
                           % (signals.name_on_page, expected_name))
    else:
        reasons.append("no comparable name on the page")

    if expected_postal_code and signals.postal_code:
        if signals.postal_code.strip()[:5] == expected_postal_code.strip()[:5]:
            matched.append("postal_code")
        else:
            conflicting.append("postal_code")
            reasons.append("page ZIP %r != expected %r"
                           % (signals.postal_code, expected_postal_code))

    if path_identity(expected_url) and \
            path_identity(signals.canonical_url or "") == path_identity(expected_url):
        matched.append("canonical_path")

    if want_code:
        confirmed = ("property_code" in matched
                     and "property_code" not in conflicting
                     and any(m != "property_code" for m in matched))
    else:
        # No code to lean on: require the page's own path AND its own name.
        confirmed = (("canonical_path" in matched or "postal_code" in matched)
                     and ("name" in matched or "name_partial" in matched)
                     and not conflicting)
    if confirmed:
        reasons.append("confirmed on %s" % ", ".join(matched))
    return MS.IdentityAssessment(confirmed=confirmed, reasons=tuple(reasons),
                                 signals_matched=tuple(matched),
                                 signals_conflicting=tuple(conflicting))


def path_identity(url: str) -> str:
    """The URL's path, lowercased and stripped of trailing slash and query.

    Used as an identity signal where no property code exists. A brand homepage
    has an empty or one-segment path and therefore cannot match a property's.
    """
    without_scheme = re.sub(r"^https?://", "", url or "")
    path = "/" + "/".join(without_scheme.split("/")[1:])
    path = path.split("?")[0].split("#")[0].rstrip("/").lower()
    return path if path.count("/") >= 2 else ""


def page_health(*, title: str, body_text: str, final_url: str,
                expected_url: str, expected_property_code: str,
                brand: str) -> Optional[str]:
    """The outcome this page forces, or ``None`` when it is worth reading.

    The generic form of the Marriott gate. The property-identity check becomes
    "the final URL is this property's path, or carries its code" -- which is
    what catches a locale redirect to a brand homepage on any domain, the
    failure that cost the previous pilot a property.
    """
    from scripts.pettripfinder.brightdata import outcomes as O

    haystack = (MS.collapse(title) + " \n " + MS.collapse(body_text)).lower()
    for marker in MS.DENIAL_MARKERS:
        if marker in haystack:
            return O.ACCESS_DENIED
    if not MS.collapse(title) and len(MS.collapse(body_text)) < MS.MIN_ANY_BODY_CHARS:
        return O.BLANK_PAGE
    if len(MS.collapse(body_text)) < MS.MIN_HYDRATED_BODY_CHARS:
        return O.UNHYDRATED

    expected_host = MS.host_of(expected_url)
    final_host = MS.host_of(final_url)
    if expected_host and final_host and final_host != expected_host:
        # A brand may legitimately move between www and a regional host; a
        # different registrable domain is a different party.
        if _registrable(final_host) != _registrable(expected_host):
            return O.UNEXPECTED_PAGE

    if expected_property_code:
        if property_code(final_url, brand).lower() != expected_property_code.lower():
            return O.UNEXPECTED_PAGE
    else:
        wanted = path_identity(expected_url)
        if wanted and path_identity(final_url) != wanted:
            return O.UNEXPECTED_PAGE
    return None


def _registrable(host: str) -> str:
    labels = [label for label in (host or "").split(".") if label]
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


__all__ = [
    "MIN_BLOCK_CHARS", "MAX_BLOCK_CHARS", "MIN_POLICY_FEATURES",
    "POLICY_FEATURE_RES", "policy_features",
    "MIN_PET_MENTIONS_SHORT", "MIN_PET_MENTIONS_LONG", "LONG_BLOCK_CHARS",
    "SIGNAL_PHRASES",
    "EXPAND_LABEL_RE", "EXPAND_SELECTORS", "PROPERTY_CODE_PATTERNS",
    "BRAND_LOCATORS", "SurfaceHit", "expand_disclosures", "locate_policy",
    "locate_brand_policy", "locate_element",
    "property_code", "any_hotel_jsonld", "read_identity", "assess_identity",
    "path_identity", "page_health",
]
