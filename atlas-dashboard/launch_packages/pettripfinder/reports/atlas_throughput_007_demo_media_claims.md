# ATLAS-THROUGHPUT-007 — demo-media safety claims

Every claim the module made before 007, where it lives now, and what it would catch. Nothing was deleted: the
table is the contract that the split preserved the safety.

| claim | module after | cold builds | defect it catches |
|---|---|---|---|
| A manifest loads and validates | ….py | 0 | a manifest that escapes the package or omits a field |
| B ingestion puts HERO refs on configured listings only | ….py | 0 | media attached to the wrong listing, or a wrong byte |
| B2 no filesystem path leaks into the dataset | ….py | 0 | a generator embedding a local path in a published artifact |
| C generated HTML carries the images | ….py | 0 | an image rendered on the wrong page, or a missing one |
| D bundle is content addressed and materializes | ….py | 0 | a bundle that names bytes it cannot produce |
| E every img src is bundled and local | ….py | 0 | a published page fetching from a third party |
| F repeated real build is identical | …_determinism.py | 2 | a timestamp, path or iteration order in published bytes -- which would |
| F2 the two builds were genuinely independent | …_determinism.py | 0 | a memoised second build silently making determinism vacuous |
| G no media mapping yields zero img | …_fallback.py | 1 | a generator that assumes media exists |
| G2 the no-media site is still complete | …_fallback.py | 0 | zero images degrading into a truncated site |

Two claims were ADDED (F2, G2), both guarding the redesign itself: that the determinism pair really is two
independent executions, and that a zero-image site is complete rather than truncated.
