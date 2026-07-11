# ADR-WEB-COMPONENT-FAMILY-TAXONOMY — ComponentFamily exact member set

| Field | Value |
|---|---|
| Status | Accepted |
| Scope | AES-WEB-002 component system — `ComponentFamily` enum (`engines/website_generation/contracts/enums.py`) |
| Decided in | AES-WEB-002A (Contracts and Registry Foundation) |
| Supersedes | Nothing |
| Governs | The normative set of component families for the catalog, registry, and all compatibility work |

## Context

`ComponentFamily` is a closed enum whose values are the `component_id`
family segment (AES-WEB-002 §4.1). While implementing AES-WEB-002A we found
the authority's *advertised family totals* to be internally inconsistent, so
the exact enum cardinality could not be read off a single sentence.

### Authority sections reviewed

- **§5** (opening sentence): "**Fourteen** top-level families. Family
  membership is permanent per component."
- **§5.1–§5.15**: fifteen distinct commercial family segments are defined,
  one per subsection — `nav` (§5.1), `hero` (§5.2), `directory` (§5.3,
  titled `directory.discovery`), `listing` (§5.4), `profile` (§5.5),
  `trust` (§5.6), `cta` (§5.7), `content` (§5.8), `seo` (§5.9),
  `monetization` (§5.10), `social` (§5.11), `commerce` (§5.12), `form`
  (§5.13), `status` (§5.14), `legal` (§5.15).
- **§5.16**: two foundation/structural families, `layout` and `atom`,
  explicitly described as "**Not in the original brief's family list** but
  required as the composition substrate."
- **§34.1** (binding decisions): "**Sixteen**-family taxonomy (§5)."

### Origin of the 14, 16, and 17 counts

- **14** — the §5 opening sentence ("Fourteen top-level families").
- **16** — the §34.1 binding-decision summary ("Sixteen-family taxonomy").
- **17** — the literal enumeration of §5.1–§5.16: fifteen commercial family
  segments (§5.1–§5.15) plus the two foundation families (§5.16).

No arithmetic reconciles 14, 16, and 17. The 14 and 16 are prose summaries;
the 17 is the explicit, itemized definition.

## Decision

**Adopt the exact 17-member enumeration explicitly listed in §5.1–§5.16.**
The textual totals of 14 (§5 intro) and 16 (§34.1) are treated as editorial
inconsistencies superseded by the explicit enumeration.

Adopted set (enum value = `component_id` family segment):

**15 commercial families** — `nav`, `hero`, `directory`, `listing`,
`profile`, `trust`, `cta`, `content`, `seo`, `monetization`, `social`,
`commerce`, `form`, `status`, `legal`.

**2 foundation / structural families** — `layout`, `atom` (§5.16), classified
as the composition substrate, not commercial primitives.

## Consequences

- **No runtime behavior changes** beyond removing ambiguity: AES-WEB-002A
  registers zero components, so enum cardinality affects nothing observable
  yet. The change is purely which `component_family` values are legal.
- **All future catalog and compatibility work MUST use this enum as
  normative.** A component authored in AES-WEB-002B+ selects its family from
  exactly these 17 members; the registry rejects any other value.
- The enum is the **complete, non-lossy superset** of every family segment
  the authority names, so no authored component can lack a valid family.
- The external architecture documents are **not** rewritten here (out of
  scope). If the authority is later corrected, this ADR is superseded by a
  new ADR or a minor amendment, and the enum follows by version bump.

## Notes

The `ComponentFamily` docstring in `contracts/enums.py` references this
decision. This ADR records repository-side intent only and has no authority
over AES-WEB-002 itself.
