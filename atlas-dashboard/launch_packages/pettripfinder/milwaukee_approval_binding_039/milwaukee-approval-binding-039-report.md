# Approval binding, corrected -- PTF-MILWAUKEE-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039

A founder approval is a statement about a claim: this property, these facts, this evidence, this source, this schema. 036 bound each decision to a hash of the whole store row, which also carries how the reading was produced -- including `rederivation.reader_commit`, a field the projection re-derives every run.

## What that cost, reproduced from committed state

| | |
| --- | ---: |
| founder decisions | 98 |
| withdrawn by a re-projection under the 036 binding | 16 |
| of those, approved meaning byte-identical | 15 |
| of those, approved meaning genuinely changed | 1 |

Every one of the byte-identical rows is an **approval**. The single row whose meaning moved is a **hold**, so not one founder approval in this market has a substantive change.

## Classification

| class | rows |
| --- | ---: |
| A_FACTS_AND_EVIDENCE_IDENTICAL | 82 |
| B_FACTS_IDENTICAL_EVIDENCE_PROVENANCE_CHANGED | 15 |
| C_SUBSTANTIVE_FACT_CHANGE | 1 |

## What is semantic and what is not

Semantic -- change it and the approval must be earned again: the property identity, the proposed facts, the withheld fields (a withholding is a claim that nothing is being asserted), the service animal statement, the refusal flag, the cited evidence, the publication grade, the identity check, the review status, the frozen semantics violations, the schema version, the source URL and its snapshot hash, the authority tier and source type, and the canonical evidence block's own sha256.

Provenance -- recorded, never deleted, never on its own a reason to withdraw an approval: `reader_commit`, the derivation note, the superseding work order, the block's filesystem PATH (the block's HASH is semantic), the previous reader's facts, the retrieval timestamp, capture method, provider, reader name, raw pointer and observation id, the source run, and the mutable `published`/`founder_approved` flags an approval itself sets.

Neither list is open-ended. A field in a store row that appears on neither fails `unclassified_fields`, and hashing refuses rather than guessing -- an unclassified field is either a tamper hole or a spurious invalidation, and which one it is is not for code to decide.

## Rows still needing the founder

* **Saint Kate - The Arts Hotel** (HOLD) -- evidence, proposed_facts, withheld_fields

Nothing here was approved, published or deployed.

