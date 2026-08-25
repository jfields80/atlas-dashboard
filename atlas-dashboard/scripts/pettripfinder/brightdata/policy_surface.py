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
from scripts.pettripfinder.discovery.property_identity import (      # noqa: E402
    normalize_phone, street_identity,
)

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


# --------------------------------------------------------------------------- #
# Recovering a block that is poorer than its own document.
# --------------------------------------------------------------------------- #
#
# PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 found three Milwaukee properties whose
# COMPLETE policy sits in the document the capture persisted while the located
# block carries a fragment of it. Hyatt Regency's page says "Pet Fees Price :
# $40 / NIGHT ... Individual pet weight limit : 150 Pounds ... Maximum number
# of pets is 2" and the located block is twenty-two characters that stop
# mid-phrase before the word NIGHT. Hyatt Place Airport's block is the heading
# "Pets are Welcome". Wildwood Lodge's block is the list of collapsed FAQ
# QUESTIONS and the ANSWERS are in the same DOM.
#
# The container walk is not wrong about any of those: it picks the ancestor
# carrying the most policy FEATURES under a size cap, and on these surfaces the
# richest ancestor genuinely is small. What nothing checked is whether the
# document it came from says materially more.
#
# WHY THIS IS NOT "TAKE A BIGGER BLOCK"
# -------------------------------------
# Size is the thing that must not decide this. Wildwood's located block is a
# thousand characters of questions and the answers beside it are shorter; a
# length rule prefers the useless one. What is compared instead is ACTIONABLE
# POLICY TERMS -- a price, a weight, a count, a basis, a refusal -- each of
# which has to sit beside a pet word to count. A candidate is accepted only
# when it adds at least one term the current block does not have.
#
# That is what keeps the negative controls closed. "Pets allowed Yes" carries
# no actionable term, so a page of amenity chips has nothing to add and cannot
# trigger expansion. "Service Animals are Welcome" likewise. A room rate
# further down the page is not a pet term, because the amount has to be near a
# pet word AND survive the rate-marker test the reader uses for the same
# reason -- a discounted nightly rate beside "No Pets Allowed" is a room rate
# in both layers.

#: A term a guest could act on. The bare word "fee" is deliberately absent: a
#: page that says "a fee will be assessed for smoking" a few words from "Pets
#: allowed Yes" states no pet term, and admitting one there would expand a
#: block on the strength of a smoking charge.
ACTIONABLE_TERM_RE = re.compile(
    r"\$\s*\d[\d,]*(?:\.\d{2})?"
    r"|\b\d[\d,]*(?:\.\d{1,2})?\s*(?:USD|dollars)\b"
    r"|\b\d[\d,]*(?:\.\d+)?\s*(?:pounds?|lbs?|kgs?)\b"
    r"|\b(?:maximum|max)\s+(?:number\s+of\s+)?(?:pets?|dogs?|cats?)\b"
    r"|\b(?:one|two|three|four|five|\d+)\s*(?:\(\s*\d+\s*\)\s*)?"
    r"(?:pets?|dogs?|cats?)\s+(?:per|max|maximum|allowed)\b"
    r"|\bper\s+(?:night|stay|day|pet|dog)\b"
    r"|\bnot\s+(?:allowed|accepted|permitted)\b",
    re.IGNORECASE)

#: A pet word for the purpose of attributing a term. "service animal" is
#: excluded deliberately: a service animal is not a pet anywhere else in this
#: codebase, and admitting it here let Red Roof's "$50 refundable deposit for
#: incidentals ... required for all guests" read as a pet charge because the
#: words "Service Animals" sat forty characters away.
_TERM_PET_WORD_RE = re.compile(
    r"\bpets?\b|\bdogs?\b|\bcats?\b|(?<!service )\banimals?\b",
    re.IGNORECASE)

#: A purpose the surface names that is not a pet's. A term inside a statement
#: about parking, smoking, incidentals or a deposit every guest pays belongs to
#: THAT statement, however near a pet word it happens to sit. The reader
#: refuses the same amounts for the same reason, and both layers have to: a
#: locator that expands onto a parking charge hands the reader a block whose
#: guard then has to undo the expansion.
EXPANSION_NON_PET_PURPOSE_RE = re.compile(
    r"\bincidental(?:s)?\b|\bfor\s+all\s+guests\b|\ball\s+guests\b"
    r"|\bsecurity\s+deposit\b|\bdamage\s+deposit\b"
    r"|\bparking\b|\bsmoking\b|\bvalet\b|\bresort\s+fee\b",
    re.IGNORECASE)

#: How near a pet word an actionable term must sit to belong to it.
TERM_PET_WINDOW = 80


def actionable_pet_terms(text: str) -> frozenset:
    """Actionable policy terms that sit beside a pet word.

    Proximity is necessary and not sufficient: the term itself has to be a
    price, a weight, a count, a basis or a refusal, and a rate marker standing
    between it and the nearest pet word disqualifies it -- the same rule the
    reader applies, for the same reason.
    """
    text = text or ""
    found = set()
    for match in ACTIONABLE_TERM_RE.finditer(text):
        start = max(0, match.start() - TERM_PET_WINDOW)
        window = text[start:match.end() + TERM_PET_WINDOW]
        pet = None
        for candidate in _TERM_PET_WORD_RE.finditer(window):
            pet = candidate
            if candidate.end() + start > match.start():
                break
        if pet is None:
            continue
        # A rate marker between the pet word and the amount means the amount
        # was introduced by the rate, not by the pet policy.
        left = min(pet.end() + start, match.start())
        right = max(pet.start() + start, match.end())
        if EXPANSION_RATE_MARKER_RE.search(text[left:right]):
            continue
        # The term's own statement may name what it is FOR, and if that is not
        # a pet then it is not a pet term however close a pet word sits.
        sentence_start = max(0, text.rfind(".", 0, match.start()) + 1)
        sentence_end = text.find(".", match.end())
        sentence_end = len(text) if sentence_end < 0 else sentence_end
        if EXPANSION_NON_PET_PURPOSE_RE.search(
                text[sentence_start:sentence_end]):
            continue
        found.add(re.sub(r"\s+", " ", match.group(0)).strip().lower())
    return frozenset(found)


#: Words that introduce a price belonging to something other than a pet. Kept
#: beside the reader's own list on purpose: both layers must refuse the same
#: guest-room card, and a locator that expanded onto a room rate would hand the
#: reader a block its guard then has to undo.
EXPANSION_RATE_MARKER_RE = re.compile(
    r"\b(?:rate|rates|price|prices|total|subtotal|avg|average|starting|"
    r"from|nightly\s+rate|room\s+rate|member\s+rate|discounted)\b",
    re.IGNORECASE)

_SENTENCE_EDGE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class BlockRecovery:
    """Whether a richer bounded region exists in the same document."""

    recovered: bool = False
    text: str = ""
    reason: str = ""
    terms_before: Tuple[str, ...] = ()
    terms_after: Tuple[str, ...] = ()
    terms_added: Tuple[str, ...] = ()
    candidates_considered: int = 0

    def to_dict(self) -> Dict:
        return {
            "recovered": self.recovered,
            "reason": self.reason,
            "block_chars": len(self.text),
            "terms_before": list(self.terms_before),
            "terms_after": list(self.terms_after),
            "terms_added": list(self.terms_added),
            "candidates_considered": self.candidates_considered,
        }


def _snap_to_sentences(text: str, start: int, end: int) -> str:
    """A window widened to whole sentences, never past the size cap."""
    left = text.rfind(". ", max(0, start - 240), start)
    left = 0 if left < 0 else left + 2
    right = text.find(". ", end, min(len(text), end + 240))
    right = len(text) if right < 0 else right + 1
    return text[left:right].strip()


def _trim_to_pet_content(text: str) -> str:
    """Drop trailing sentences that are not about pets.

    The forward window overshoots on purpose -- a policy may run for several
    sentences and the reach cannot know where it ends -- so the tail is cut
    back to the last sentence carrying a pet word or an actionable term.
    Without it Hyatt's block ran on into "Accessibility at Our Hotel", which is
    page-wide content and not this property's pet policy.
    """
    sentences = [part for part in _SENTENCE_EDGE_RE.split(text) if part.strip()]
    if not sentences:
        return text
    keep = 0
    for index, sentence in enumerate(sentences):
        if _TERM_PET_WORD_RE.search(sentence) or                 ACTIONABLE_TERM_RE.search(sentence):
            keep = index + 1
    return " ".join(sentences[:keep]).strip() if keep else text


def _acceptable_candidate(text: str) -> bool:
    """The quality bar the locator already applies, unchanged."""
    if not (MIN_BLOCK_CHARS <= len(text) <= MAX_BLOCK_CHARS):
        return False
    if policy_features(text) < MIN_POLICY_FEATURES:
        return False
    mentions = len(_TERM_PET_WORD_RE.findall(text))
    needed = (MIN_PET_MENTIONS_LONG if len(text) >= LONG_BLOCK_CHARS
              else MIN_PET_MENTIONS_SHORT)
    return mentions >= needed


def recover_richer_block(block_text: str, document_text: str) -> BlockRecovery:
    """A bounded region of the SAME document that states more than the block.

    The document is the one this capture already bound to its identity, so
    recovery cannot move the record to another property: it re-reads a page
    that has already passed the identity gate and takes a different window of
    it. No page is fetched and no boundary is invented -- the candidate is a
    span of text the capture persisted.

    Returns a recovery only when a candidate adds an actionable term the
    current block lacks, clears the locator's existing size, feature and
    pet-mention bars, and is not merely longer.
    """
    block = MS.collapse(block_text or "")
    document = MS.collapse(document_text or "")
    have = actionable_pet_terms(block)
    if not document:
        return BlockRecovery(reason="no document to search",
                             terms_before=tuple(sorted(have)))
    whole = actionable_pet_terms(document)
    if not (whole - have):
        return BlockRecovery(
            reason="the document states no actionable pet term the block lacks",
            terms_before=tuple(sorted(have)),
            terms_after=tuple(sorted(have)))

    considered = 0
    best = None
    lowered = document.lower()
    anchors = []
    for phrase in SIGNAL_PHRASES:
        start = lowered.find(phrase)
        while start != -1:
            anchors.append(start)
            start = lowered.find(phrase, start + 1)
    for anchor in sorted(set(anchors)):
        for reach in (400, 800, MAX_BLOCK_CHARS):
            # The window opens AT the signal phrase and only ever grows
            # forwards. Reaching backwards pulled the amenity list that sits
            # above Hyatt's policy and the previous FAQ answer that sits above
            # Wildwood's, which is exactly the page-wide content a policy block
            # must not carry. ``_snap_to_sentences`` still widens left to the
            # start of the sentence the phrase is IN, so a heading is not cut
            # in half.
            candidate = _snap_to_sentences(
                document, anchor, min(len(document), anchor + reach))
            candidate = _trim_to_pet_content(candidate)
            if len(candidate) > MAX_BLOCK_CHARS:
                candidate = candidate[:MAX_BLOCK_CHARS]
            considered += 1
            if not _acceptable_candidate(candidate):
                continue
            terms = actionable_pet_terms(candidate)
            gained = terms - have
            if not gained:
                continue
            score = (len(gained), len(terms), -len(candidate))
            if best is None or score > best[0]:
                best = (score, candidate, terms, gained)

    if best is None:
        return BlockRecovery(
            reason=("the document states terms the block lacks, but no bounded "
                    "candidate carried them within the locator's own limits"),
            terms_before=tuple(sorted(have)),
            terms_after=tuple(sorted(have)),
            candidates_considered=considered)

    _score, candidate, terms, gained = best
    return BlockRecovery(
        recovered=True, text=candidate,
        reason=("the persisted document states %d actionable pet term(s) the "
                "located block does not carry" % len(gained)),
        terms_before=tuple(sorted(have)),
        terms_after=tuple(sorted(terms)),
        terms_added=tuple(sorted(gained)),
        candidates_considered=considered)


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
    # Added by PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028. Both brands put a
    # code in every property URL and the identity census already holds it, so
    # binding on the code is available and is strictly stronger than the
    # code-less route these two would otherwise take:
    #   /hyatt-place/en-US/mkeza-hyatt-place-milwaukee-airport
    #   /book/hotels-in-milwaukee/<slug>/propertyCode.50056.html
    "HYATT": r"/en-US/([a-z0-9]{5})-",
    "BEST_WESTERN": r"/propertyCode\.(\d{4,6})\.",
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


#: Words that appear in so many lodging names that sharing one proves nothing.
#: A code-less binding needs at least one token from OUTSIDE this vocabulary
#: and outside the property's own locality, or "The Plaza Hotel Milwaukee" and
#: "Milwaukee Hotel Amenities | Pet Friendly, Spa" agree on "hotel" and
#: "milwaukee" and bind two unrelated things together.
GENERIC_NAME_TOKENS: frozenset = frozenset({
    "hotel", "hotels", "motel", "motels", "inn", "inns", "suites", "suite",
    "lodge", "lodging", "resort", "resorts", "the", "a", "an", "and", "by",
    "at", "of", "on", "in", "house", "place", "plaza", "center", "centre",
    "downtown", "airport", "north", "south", "east", "west", "spa", "casino",
    "conference", "collection", "rooms", "stay", "bed", "breakfast",
})

#: Signals that name a PHYSICAL lodging -- a street or a telephone line. These
#: are the only ones that can carry a code-less binding, because everything
#: else on this list ("same domain", "the path looks right", "the name is
#: similar") answers whether the URL is related, not whether the page is about
#: this building.
PHYSICAL_SIGNALS: Tuple[str, ...] = ("street_identity", "phone")

#: Signals whose DISAGREEMENT vetoes a code-less binding. Everything the gate
#: already compared, plus the street: a page publishing a different street
#: address contradicts the census about which building it is, and that has to
#: fail closed even where the old path-and-name rule would have confirmed.
#: ``phone`` is deliberately absent -- see the telephone branch below.
VETOING_SIGNALS: Tuple[str, ...] = ("property_code", "name", "postal_code",
                                    "street_identity")


#: Compass words, folded the way ``street_identity`` already folds
#: "Street"/"St". Without this "1028 East Juneau Avenue" and "1028 E. Juneau
#: Avenue" are two buildings, and the gate refuses a hotel over a full stop.
#: Folded HERE rather than in ``street_identity`` itself, which the identity
#: census uses to decide whether two records are one property -- widening that
#: key is a separate question with its own blast radius.
_DIRECTIONALS: Dict[str, str] = {
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw",
    "southeast": "se", "southwest": "sw",
}


def _street_key(address: str) -> str:
    """A comparable street WITHOUT the ZIP, or empty when it names no building.

    An address with no leading house number -- "North Brookfield Road" -- is a
    road, and two properties sit on it. Returning nothing there is the
    difference between "no signal" and "a conflict".
    """
    key = street_identity(address or "", "").rstrip("|").strip()
    key = " ".join(_DIRECTIONALS.get(token, token) for token in key.split())
    return key if re.match(r"^\d", key) else ""

#: A telephone number as a human would see one written: separated, or behind a
#: ``tel:`` link. An unseparated run of ten digits is an id, a timestamp or a
#: tracking token far more often than it is a phone number, and admitting those
#: turned this signal into noise.
_PHONE_RE = re.compile(r"tel:\+?1?(\d{10})\b"
                       r"|\+?1?[\s\-.]?\(?(\d{3})\)?[\s\-.](\d{3})"
                       r"[\s\-.](\d{4})\b")


def phones_in(html: str) -> Tuple[str, ...]:
    """Every telephone number the page prints, normalised, in page order.

    Scanned from the raw markup so a ``tel:`` href counts. The separators the
    pattern accepts exclude ``<`` and ``>``, so a match cannot span two
    elements and pick up half of each.

    WHAT THIS IS NOT
    ----------------
    Not "the property's number", and not on its own an identity. A hotel group
    prints every location's number in one footer: the page for the Wildwood
    Lodge in Clive, Iowa prints the Pewaukee, Wisconsin number, and a rule that
    bound on "the census number appears somewhere" bound the wrong building.
    So this set is only ever read as CORROBORATION -- it can explain away an
    apparent conflict, and it can never confirm an identity.
    """
    seen: List[str] = []
    for groups in _PHONE_RE.findall(html or ""):
        key = normalize_phone("".join(groups))
        if key and key not in seen:
            seen.append(key)
    return tuple(seen)


def distinctive_overlap(page_name: str, expected_name: str, *,
                        locality: str = "") -> frozenset:
    """Name tokens the two share that could only belong to this property.

    Generic lodging vocabulary and the property's own city and state are
    removed first. What is left is the part of a name agreement that carries
    information; when it is empty, the names agree only on words half the
    market's hotels also use.
    """
    shared = MS.name_tokens(page_name) & MS.name_tokens(expected_name)
    geo = MS.name_tokens(locality)
    return frozenset(token for token in shared
                     if token not in GENERIC_NAME_TOKENS
                     and token not in geo
                     and not token.isdigit())


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
    printed = phones_in(html)
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
            jsonld_present=True, phones_on_page=printed)
    og = _OG_TITLE_RE.search(html or "")
    doc = _TITLE_RE.search(html or "")
    name = MS.collapse(og.group(1) if og else (doc.group(1) if doc else title))
    return MS.IdentitySignals(name_on_page=name, property_code_on_page=code,
                              canonical_url=canonical, jsonld_present=False,
                              phones_on_page=printed)


def assess_identity(signals: MS.IdentitySignals, *, expected_name: str,
                    expected_property_code: str, expected_url: str,
                    expected_postal_code: str = "",
                    expected_street: str = "", expected_phone: str = "",
                    expected_locality: str = "") -> MS.IdentityAssessment:
    """Is this page demonstrably about the same physical lodging as the census row?

    Where the brand puts a code in its URLs the code decides, exactly as in the
    Marriott pilot, and nothing below changes that path.

    WHERE THERE IS NO CODE
    ----------------------
    Most independents have none, and the original rule bound them through the
    page's own canonical PATH plus its name. That works for a chain whose
    property lives at ``/wi/waukesha/`` and fails for the ordinary case of a
    one-property site: ``path_identity`` deliberately ignores a one-segment
    path, so ``/faq`` yields no path signal at all and a hotel that answered
    correctly was refused. Ten Milwaukee properties failed exactly there.

    The repair does not relax that rule -- it stands, unchanged, and everything
    it used to confirm it still confirms. A second, independent route is added
    beside it: a page may bind when it agrees with the census on something
    PHYSICAL -- the street identity, or the telephone line -- and on a name
    whose agreement is more than the words every hotel shares.

    Both halves are required and neither is sufficient. A street with no name
    cannot separate two hotels at one address; a name with no street cannot
    separate two Wildwood Lodges in two states. Same-domain is not a signal
    here at all, and neither is a URL that merely looks related: what this
    function is asked is which BUILDING the page is about.

    Any conflicting signal fails the code-less binding closed. A page whose
    structured address is a different street is not this property however well
    its name reads.
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

    # The street the page publishes about itself, against the street the
    # identity census holds. ``street_identity`` normalises "Street"/"St" and
    # nothing else, so a different house number stays a different place.
    #
    # The ZIP is deliberately left OUT of both keys and compared on its own
    # above. It belongs in the key when two CENSUS rows are compared, because
    # both carry a plain five-digit code. A page carries "53221-2824", or
    # carries none at all, and folding that into the street key turned one
    # address into two and invented conflicts on properties that agreed.
    page_street = _street_key(signals.address_on_page)
    want_street = _street_key(expected_street)
    if page_street and want_street:
        if page_street == want_street:
            matched.append("street_identity")
        else:
            conflicting.append("street_identity")
            reasons.append("page street %r does not agree with expected %r"
                           % (signals.address_on_page, expected_street))
    elif want_street and signals.address_on_page:
        reasons.append("the page prints %r, which carries no house number and "
                       "so names a road rather than a building"
                       % signals.address_on_page)

    # Only the telephone number the page declares as ITS OWN can bind. A number
    # merely printed somewhere may belong to a sibling property on the same
    # operator's site, which is how a page about Clive, Iowa carried the
    # Pewaukee, Wisconsin line.
    want_phone = normalize_phone(expected_phone)
    structured_phone = normalize_phone(signals.phone_on_page)
    printed = {phone for phone in signals.phones_on_page if phone}
    if want_phone and structured_phone:
        if structured_phone == want_phone:
            matched.append("phone")
        elif want_phone in printed:
            # Both numbers are on the page. That is an operator site listing
            # more than one property, not a contradiction about this one.
            reasons.append("the page declares telephone %r and also prints "
                           "this property's %r -- one site, several properties"
                           % (signals.phone_on_page, expected_phone))
        else:
            # NOT a conflict. A hotel publishes a front desk line, a
            # reservations line and a toll-free line, and which one reaches the
            # structured data is an authoring choice, not a statement that this
            # is a different building. A telephone number may CONFIRM an
            # identity here; it is never allowed to deny one.
            reasons.append("page telephone %r is not the census number %r; "
                           "one property commonly publishes several"
                           % (signals.phone_on_page, expected_phone))
    elif want_phone:
        reasons.append("the page declares no telephone number of its own")

    if path_identity(expected_url) and \
            path_identity(signals.canonical_url or "") == path_identity(expected_url):
        matched.append("canonical_path")

    distinctive = distinctive_overlap(signals.name_on_page, expected_name,
                                      locality=expected_locality)
    name_agrees = ("name" in matched or "name_partial" in matched)
    physical = [signal for signal in PHYSICAL_SIGNALS if signal in matched]

    method = ""
    if want_code:
        confirmed = ("property_code" in matched
                     and "property_code" not in conflicting
                     and any(m != "property_code" for m in matched))
        method = "PROPERTY_CODE" if confirmed else ""
    else:
        # The original rule, with one deliberate change: a contradicted street
        # now vetoes it too. The old rule confirmed on the path and the name
        # because those were the only signals it had; a page that names a
        # different street is not this building, and the honest thing to do
        # with that information once we have it is fail closed. Every such
        # withdrawal is measured and enumerated rather than assumed harmless.
        vetoes = [signal for signal in conflicting
                  if signal in VETOING_SIGNALS]
        legacy = (("canonical_path" in matched or "postal_code" in matched)
                  and name_agrees and not vetoes)
        # The addition: something physical, and a name agreement that is not
        # only the words every hotel in the market shares.
        #
        # The name half is the STRICT one -- one name contains the other -- and
        # not the partial-overlap rule the legacy route accepts. A Studio 6 and
        # a Motel 6 share a building, a ZIP and four of six name tokens in
        # Brookfield; the partial rule calls that a name agreement and the
        # street agrees for the honest reason that it is the same street. Only
        # containment separates them.
        physical_bound = (bool(physical) and "name" in matched
                          and bool(distinctive) and not vetoes)
        confirmed = legacy or physical_bound
        if physical_bound and "street_identity" in physical:
            method = "EXACT_ADDRESS_AND_NAME"
        elif physical_bound:
            method = "PHONE_AND_NAME"
        elif confirmed:
            method = "CANONICAL_PATH_AND_NAME"
        if not confirmed and name_agrees and not distinctive:
            reasons.append("the names agree only on %s, which this market's "
                           "hotels share"
                           % (", ".join(sorted(page_tokens & want_tokens))
                              or "nothing"))
        if not confirmed and name_agrees and not physical:
            reasons.append("nothing physical agreed: no street identity and "
                           "no telephone match, and a related-looking URL on "
                           "the same domain is not an identity")
    if confirmed:
        reasons.append("confirmed on %s via %s" % (", ".join(matched), method))
    return MS.IdentityAssessment(confirmed=confirmed, reasons=tuple(reasons),
                                 signals_matched=tuple(matched),
                                 signals_conflicting=tuple(conflicting),
                                 binding_method=method)


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
    "GENERIC_NAME_TOKENS", "PHYSICAL_SIGNALS", "phones_in",
    "distinctive_overlap",
    "ACTIONABLE_TERM_RE", "actionable_pet_terms", "BlockRecovery",
    "recover_richer_block", "TERM_PET_WINDOW",
]
