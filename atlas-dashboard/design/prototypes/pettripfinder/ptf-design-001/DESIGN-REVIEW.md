# PTF-DESIGN-001 — Adversarial design review & recommendation

Design review only. No production code changed. Screenshots referenced below
live in `screenshots/`.

---

## 1. Concept summaries

### Concept A — Premium Travel Editorial
- **Layout:** asymmetric wide hero (serif identity left, branded monogram
  right); two-column body with a sticky booking/trust sidebar.
- **Type/color:** serif display (Iowan/Palatino/Georgia) + humanist sans;
  warm off-white `#f6f1e7`, evergreen, muted terracotta accent.
- **Action hierarchy:** calm primary "Check booking options" in the sidebar
  card; secondary official-site/call beneath; disclosure attached.
- **Trust:** elegant framed provenance card with an expandable exact quote.
- **Strengths:** by far the most *premium, custom, credible-travel-brand*
  feel; excellent emotional appeal; monogram placeholder looks intentional.
- **Weaknesses:** softer commercial prominence; serif-heavy reading; a very
  sparse property risks feeling airy/empty in the editorial voice.

### Concept B — Modern Marketplace
- **Layout:** compact hero (monogram thumbnail + identity + fact chips);
  main column of bordered panels; **sticky right booking rail**; **sticky
  bottom action bar on mobile**.
- **Type/color:** system humanist sans; light-gray/navy with a confident
  teal-green action color.
- **Action hierarchy:** the strongest — a large primary button always in
  view (rail on desktop, bottom bar on mobile), official-site/directions/call
  secondary.
- **Trust:** compact verified module in the rail with expandable quote.
- **Strengths:** best scannability and **conversion**; best mobile action
  pattern; snapshot reads like a comparison grid.
- **Weaknesses:** closest to a generic product/component-library look; trust
  evidence risks being demoted to a small sidebar; least warmth.

### Concept C — Trusted Local Guide
- **Layout:** corridor chip + serif title; a prominent **"Why you can trust
  this pet policy"** strip high on the page; body + rail carrying booking, a
  **local trip-planning module**, and provenance.
- **Type/color:** restrained serif headings + warm humanist sans; warm
  neutrals, evergreen, muted local blue.
- **Action hierarchy:** clear primary "Check booking options"; official/call
  secondary; framed inside a trusted-guide context.
- **Trust:** strongest — verification is presented as the product's headline
  advantage, not fine print.
- **Strengths:** best **trust clarity**; handles sparse/no-pets/unverified
  most naturally; strongest SEO/AI-citation posture (provenance + dates +
  local context as real text); best fit for PetTripFinder's actual moat.
- **Weaknesses:** booking slightly less punchy than B; more modules to
  maintain; must guard against drifting text-heavy.

---

## 2. Adversarial review (all concepts)

**Visual quality** — All three read as credible travel products, not debug
output; whitespace is intentional; cards compose rather than float; the
no-photo monogram looks professional in every concept. A is the most custom;
B is the most conventional.

**Information hierarchy (10-second test)** — Dogs / cats / fee / max pets /
weight / verified date / where-to-book are all answerable within ~10s in B
and C (snapshot + chips). A takes marginally longer because the snapshot sits
below the editorial lede.

**Trust** — One dominant verification state in every concept; source is named;
unknowns are honest ("Not stated by the reviewed source"); commercial links
are visually and textually separated from policy evidence; no contradictory
"verified/partial/unknown" stacking. C makes trust a headline; B risks
under-weighting it.

**Conversion** — Primary action is unambiguous and distinct from the official
site in all three; the affiliate disclosure is visible next to it; no
"best price / rooms available now / guaranteed" claims anywhere. B is
strongest, C close, A softest.

**Mobile** — Reading order is correct (identity → verification → policy →
actions → details → location → trust); the hero stacks; nav collapses; B adds
a sticky bottom action bar that does **not** cover content. Verified with a
viewport ruler: `document.scrollWidth == innerWidth` (no horizontal overflow).

**SEO / AI retrieval** — Specific H1s; all policy facts are real server-side
text (not images or JS-gated); verification date and source sit adjacent to
the facts; "nearby" language is accurate (honest fallback, never fabricated
distance). C is strongest for retrieval because provenance, dates, and local
context are prominent, citable text.

**Implementation reality** — Every concept renders from the exact fields the
current backend already produces; each survives missing photos (proven — it's
the default) and missing fee/weight data (sparse state proven); none requires
a rating, review, price, coordinate, or licensed image the backend cannot
supply. All three can become a single reusable template driven by the same
data object.

---

## 3. Scorecard (1–10, higher is better)

| Dimension | A · Editorial | B · Marketplace | C · Local Guide |
|---|:--:|:--:|:--:|
| Visual credibility | 9 | 7 | 8 |
| Mobile usability | 7 | 9 | 8 |
| Trust clarity | 7 | 6 | **10** |
| Sparse-data resilience | 6 | 7 | **9** |
| No-photo resilience | 8 | 7 | 8 |
| Conversion potential | 6 | **9** | 7 |
| Implementation simplicity | 7 | 7 | 6 |
| Compatibility with current data | 8 | 8 | **9** |
| SEO usefulness | 8 | 8 | **9** |
| AI-retrieval usefulness | 8 | 7 | **9** |
| Scalability across Atlas directories | 7 | 8 | 8 |
| **Average** | **7.4** | **7.5** | **8.3** |

---

## 4. Recommendation — Hybrid, Concept C as the backbone

**Adopt Concept C (Trusted Local Guide) as the structural authority, and fold
in Concept B's action system and Concept A's typographic polish.**

Rationale: PetTripFinder's only durable advantage is **verified pet-policy
trust with honest unknowns** — exactly what C foregrounds, and what scores
highest on trust, sparse resilience, data compatibility, and AI-retrieval.
But two targeted borrowings remove C's only weaknesses:

- **From B:** the scannable snapshot/fact-chips, the prominent always-visible
  primary action, and the sticky mobile action bar (lifts conversion + the
  10-second test without diluting trust).
- **From A:** the serif display headings, the generous spacing scale, and the
  branded monogram treatment (lifts it from "competent" to "premium," which
  is the whole point of this rescue).

This hybrid is already reflected in the `states/` prototypes, which are built
on the Concept-C base and demonstrate that the trust-first skeleton absorbs
the sparse, no-photo, no-pets, and unverified states cleanly.

**Do not** default to this because it was hinted — it is the honest result of
the scorecard and the screenshots: C wins outright on the dimensions that
matter most to this product, and A/B contribute precisely where C is weakest.

---

## 5. Deviations, limits, and honest notes

- **Mobile screenshots were captured at 500 px**, not 390 px: headless Chrome
  enforces a 500 px minimum window width (verified — `innerWidth` clamped to
  500). 500 px still triggers every `≤640 px` mobile rule, so the captures are
  a faithful mobile-breakpoint representation; they are simply wider than a
  phone. True-390 device-emulation capture would require driving the DevTools
  Protocol, which was out of scope for a no-install sprint.
- The **no-pets** and **unverified** fixtures use real, repository-authorized
  evidence from operational candidates (Columbus Hilliard Hotel; Hampton Inn
  Columbus-Airport). They are intentionally **not** in the verified
  pet-friendly production set and are shown here only to design their states.
- Accessibility was **checked, not certified**: see the final report.
