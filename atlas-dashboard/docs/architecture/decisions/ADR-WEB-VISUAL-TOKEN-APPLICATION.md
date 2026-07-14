# ADR-WEB-VISUAL-TOKEN-APPLICATION — Token-to-Property Commercial Visual System

| Field | Value |
|---|---|
| Status | Accepted |
| Scope | AES-WEB-001 §8.3 rendering — the applied CSS the Renderer emits (`engines/website_generation/rendering/`) |
| Decided in | AES-WEB-002J.15 (Commercial Visual System) |
| Supersedes | Nothing |
| Governs | How resolved `BrandPackage` design tokens become *applied* CSS declarations for the component catalog |

## Context

The AES-WEB-002J.14 visual diagnostic established that the Renderer's shared
CSS was, before this decision, a **token dump**: `css_emitter.py` compiled
every resolved `BrandPackage` token to a `:root` custom property and emitted,
per present component, a rule that only *self-aliased* those tokens
(`--x: var(--x)`) — with essentially no *applied* visual property. The
stylesheet loaded, its `.ac-*` selectors matched the emitted markup, and the
tokens compiled and resolved, but nothing consumed them, so browsers painted
near-native semantic HTML. The emitter's own docstring recorded this as a
deliberate AES-WEB-002J.8 foundation-scope deferral: "detailed
component-by-component visual design is out of scope … no authority document
specifies it." This ADR is that missing authority.

The design-token vocabulary the Brand Engine already produces is complete and
semantic (54 tokens): page/surface/text/action/border/focus colors,
`font`-shorthand typography, a spacing scale, grid columns + gap, radii,
shadows, a container width, and breakpoints. Every visual value this system
needs already exists as a semantic token — so the applied layer can be
authored **without inventing a single raw literal**.

## Decision

Introduce a reusable, deterministic **applied-visual layer** in the rendering
package (`rendering/visual_styles.py`), concatenated by
`css_emitter.compile_shared_css` after the `:root` token block. It is engine
behavior, not demo styling: any site rendered through the Renderer receives it.

### Normative rules

1. **Reusable, never demo-specific.** The visual layer lives in the Renderer
   and is keyed to catalog component classes / families, never to the J.13
   demo fixture. The demo harness gains no styling of its own.
2. **Token-derived values only.** Every applied color, spacing, radius,
   shadow, border, font, container width, and breakpoint references a CSS
   custom property that came from a `BrandPackage` token
   (`var(--…)` via `css_emitter.token_var`).
3. **No raw literals when a token exists.** No raw hex colors, pixel spacing,
   radii, shadows, or breakpoints are introduced. The only permitted bare
   literals are structural/standards-safe keywords and values with no token
   equivalent: `0`, `1`, `100%`, `auto`, `none`, `solid`, `inherit`,
   `currentColor`, `transparent`, `border-box`, `grid`, `flex`,
   `inline-flex`, `block`, `center`, `space-between`, `wrap`,
   `minmax(0, 1fr)`, `1px` for a hairline only where no border token applies,
   and the `-9999px`/clip offset of the visually-hidden skip-link idiom.
4. **`ac-*` class convention.** Component styling targets the existing
   `ac-<family>` / `ac-<family>--<component>` classes emitted by
   `html_emitter.class_names`. Element selectors (`html`, `body`, `a`, `img`,
   headings, `p`, lists, `table`, form controls, `main`, `header`, `footer`,
   `:focus-visible`) are used **only** in the global base layer (rule 5).
5. **Global base + family + variant.** Three ordered tiers: a small global
   element base; family-level shared treatment (`.ac-nav`, `.ac-hero`, …);
   and variant refinements (`.ac-hero--search-directory`). Child selectors are
   used only against **stable** emitted structure (e.g. `.ac-nav--header-standard ul`).
6. **Layout from layout tokens.** Container width (`container.width.default`),
   grid columns (`grid.columns.*`), and grid gap (`grid.gap.default`) drive the
   real `display:grid` / centered-container layout.
7. **Deterministic responsive behavior.** Responsive collapse uses the
   existing breakpoint token (`breakpoint.md`) via a single `@media
   (max-width: …)` mechanism; multi-column grids collapse to one column and
   the header nav stacks. No JavaScript.
8. **No external assets, fonts, CDNs, JavaScript, or runtime CSS.** No `url()`,
   no `@import`, no `@font-face`. Font families come only from the typography
   tokens' own font stacks.
9. **No inline styles.** All styling is in the shared stylesheet.
10. **Semantic HTML unchanged.** This sprint touches only emitted CSS; no
    `html_emitter` markup changes.
11. **Visible focus.** A `:focus-visible` outline uses `focus.ring.default` +
    `color.focus.ring`; the skip link is visually hidden until focused, then
    visible and usable.
12. **Native control usability preserved.** Form controls inherit font and
    receive token-driven borders/padding; no control is hidden or disabled.
13. **No motion this sprint** (so no reduced-motion handling is required).
14. **Deterministic, canonical order.** The applied layer emits global rules,
    then family/variant component rules, then responsive rules, each from a
    fixed authored order; output is independent of dict/set iteration order.
15. **Token gating.** A declaration is emitted only when **every** token it
    references is present in the build's token map (preserving the existing
    "no `var()` without a backing custom property" invariant). If a needed
    token is ever absent, the rule silently omits that declaration rather than
    emitting a dangling reference.
16. **Tested by applied-property assertions**, not only snapshots.

### Property families the tokens drive

page background (`color.surface.page`); text (`color.text.default`), muted
(`color.text.muted`), link (`color.text.link`), inverse
(`color.text.inverse`); focus outline (`focus.ring.default` +
`color.focus.ring`); fonts (`typography.body.default`,
`typography.heading.display|2|3`, `typography.label.default`); spacing
(`spacing.stack.default`, `spacing.inline.default`, `spacing.section.*`);
container width (`container.width.default`); grid columns/gap
(`grid.columns.*`, `grid.gap.default`); surfaces
(`color.surface.raised|elevated|featured|sponsored|inverse`); border
(`border.default` + `color.border.default`); radii (`radius.card`,
`radius.control`, `radius.badge`); shadow (`shadow.raised`); button
surface/text (`color.action.primary[-hover]` + `color.text.inverse`);
responsive stacking (`breakpoint.md`).

## Explicit non-goals (deferred, unchanged by this ADR)

Value-layer content/prop binding (the `Resolved …` placeholders, §5.5);
content composition / nested children (form fields, card internals); image
semantics (`alt=""`); the heading/`<h2>` and second-header-landmark gaps;
`ContentBlock.text` opacity. This ADR makes the site *look* like a commercial
directory; it does not make its *content* real.

## Consequences

The Renderer's emitted CSS and every downstream `styles.css` / `bundle_hash`
change. Per §11.4, the Renderer engine version bumps `1.0.0 → 1.1.0` in the
same delivery; component compatibility ranges (`renderer >=1.0.0,<2.0.0`)
already admit it. Contracts, schemas, other engines, the pipeline, and
component lifecycle are unchanged.
