"""Commercial strategy identity, classification keywords, and per-
(strategy, page-role) commercial defaults (AES-WEB-002L.1).

Constants only -- no computation, no imports beyond the standard library
(§3.2 constants-are-stdlib-only doctrine): this module may not import
``contracts/`` (``BusinessSpec``) or ``constants/components.py`` (the recipe
tables). The classifier function that consumes ``BusinessSpec`` and the
recipe-table lookup function that consumes ``constants/components.py``'s
tables both live in ``components/commercial_strategy.py`` -- the same
constants-hold-data / components-hold-logic split ``composition_rules.py``
(J.20) and ``brand/token_resolver.py`` (J.2) already established.

Extends the existing recipe/composition system with a second key
(``CommercialStrategy``) rather than replacing it (AES-WEB-002L.1 approved
verdict: EXTEND_EXISTING_RECIPE_SYSTEM, not a standalone Commercial
Presentation Engine). ``constants/components.py`` remains the single owner
of recipe *content*; this module only adds the strategy dimension and the
previously-homeless commercial facts (primary CTA, required trust surfaces)
that AES-WEB-002K.2 had to hardcode into emitter constants for lack of a
better home (see ``PAGE_COMMERCIAL_DEFAULTS`` below).

Two V1 strategies only, mirroring ``constants/brand.py``'s
family-classification shape exactly:

* ``STRATEGY_DIRECTORY`` -- the live PetTripFinder archetype, and the
  designated fallback (this architecture already assumes directory as the
  dominant archetype throughout -- ``BusinessSpec.directory_taxonomy`` is a
  core field IA composes every category/profile route from; there is no
  scenario where "no strategy signal" should mean anything other than
  "directory"). Unlike ``constants/brand.py``'s ``FAMILY_FALLBACK`` (one of
  four *actively keyword-matched* families that also happens to be the
  fallback), DIRECTORY carries no keywords of its own and is *never*
  positively matched -- it is pure fallback. This means classification
  between the two V1 strategies can never actually tie (only
  LEAD_GENERATION is ever positively matched), so no SHA-256 tie-break
  mechanism is needed here the way brand's four-way classification needs
  one.
* ``STRATEGY_LEAD_GENERATION`` -- an architectural proof archetype only
  (AES-WEB-002L.1 mission: "structural proof, not a commercially validated
  business"), reusing the pre-existing, already-registered
  ``lead-gen-landing`` PageRole recipe (``LEAD_GEN_LANDING_RECIPE_SLOTS``,
  AES-WEB-002J.1) and its two real catalog candidates
  (``trust.statistics.strip``, ``form.lead.quote``) -- no new component, no
  new recipe content authored by this delivery.

Classification keywords deliberately name multi-word direct-response
phrases ("quote request", "free estimate"), never bare single words like
"lead" or "quote" -- a single word matched via substring (this module's
matching convention, mirroring ``constants/brand.py``'s ``FAMILY_KEYWORDS``)
would false-positive on ordinary prose ("a **lead**ing provider", "our
price **quote**book"). Generic monetization language (e.g. PetTripFinder's
real ``monetization_model="affiliate_booking_links"``) never contains one of
these phrases and must never classify as LEAD_GENERATION merely because
money is involved (AES-WEB-002L.1 explicit requirement).
"""

from typing import Dict, Tuple

STRATEGY_DIRECTORY = "directory"
STRATEGY_LEAD_GENERATION = "lead_generation"

STRATEGY_ORDER: Tuple[str, ...] = (STRATEGY_DIRECTORY, STRATEGY_LEAD_GENERATION)

# DIRECTORY is pure fallback -- never keyword-matched (see module docstring).
STRATEGY_FALLBACK = STRATEGY_DIRECTORY

COMMERCIAL_STRATEGY_VERSION = "1.0.0"

# Lower-case multi-word phrases only (see module docstring's false-positive
# rationale). Checked against the same kind of lower-cased, space-joined
# classification text ``brand/token_resolver.build_keyword_bag`` builds
# (niche/audience/value_proposition/monetization_model/directory_taxonomy) --
# never against ``business_name`` (same exclusion brand classification uses).
STRATEGY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    STRATEGY_LEAD_GENERATION: (
        "lead generation",
        "quote request",
        "request a quote",
        "get a quote",
        "request an estimate",
        "free estimate",
        "service inquiry",
        "schedule a consultation",
        "request a consultation",
        "book a consultation",
    ),
}

# ---------------------------------------------------------------------------
# Page commercial defaults (AES-WEB-002L.1) -- the previously-homeless facts
# AES-WEB-002K.2 had to hardcode directly into emitters_discovery.py's
# module-level constants for lack of a declarative owner. Keyed by
# (commercial_strategy, page_role) using the *bare* PageRole string values
# (independently declared here, never imported from contracts/enums --
# constants/ may not import contracts/; must stay byte-identical to
# PageRole's values, the same "documented duplication" precedent
# ``ia/information_architecture_engine.py``'s local PAGE_ROLE_BUSINESS_PROFILE
# already established).
#
# Deliberately small: only fields with an actual consumer this delivery
# (primary CTA; required trust surfaces, recorded for the record but not yet
# gate-enforced -- CG-COM-* gates are explicitly deferred, AES-WEB-002L.1
# operator decision 21). No density score, no conversion score, no
# optimization weight, no subjective page-quality metric -- none of those
# have a consumer, so none are added (operator decision 6's own rule).
# ---------------------------------------------------------------------------

PAGE_COMMERCIAL_DEFAULTS: Dict[Tuple[str, str], Dict[str, object]] = {
    (STRATEGY_DIRECTORY, "home"): {
        "primary_cta_label": "Browse the directory",
        "primary_cta_href": "#main",
        "primary_cta_external": False,
        "required_trust_surfaces": ("disclosure",),
    },
    (STRATEGY_LEAD_GENERATION, "home"): {
        # AES-WEB-002L.1 structural proof only. Unlike DIRECTORY, no render-
        # data-backed anchor is produced for this fact: hero.search.
        # directory (the only component K.2 wired a CTA producer for) is
        # not part of the lead-gen-landing recipe, and lead-gen-landing's
        # own hero slot (hero.leadgen.offer) is a documented, pre-existing
        # catalog gap -- §6.1 names it but no wave ever registered it, so
        # the slot always resolves to the empty layout.section.container
        # fallback (unchanged by this delivery; registering a new component
        # is out of scope and would break the "72 components" invariant).
        # The real, honest primary action on this page is form.lead.quote's
        # own rendered submit button (§27.6, already real, already tested)
        # -- this fact exists so the *data* proves strategy-differentiated
        # CTA intent even though rendering it as a second, redundant anchor
        # would have no safe, honest target to point at.
        "primary_cta_label": "Start your estimate",
        "required_trust_surfaces": ("trust_adjacent_to_form",),
    },
}
