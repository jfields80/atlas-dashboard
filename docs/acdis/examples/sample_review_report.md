# Deterministic competitor comparison and wedge experiment review

## 1. Case identity

- Case ID: case-acdis-phase2-sample
- Case title: Synthetic competitor comparison and wedge review
- Operator notes: Fictional synthetic review case for deterministic Phase 2 behavior.

## 2. Operator recommendation

- Operator recommendation: HOLD
- Rationale: Continue manual evidence collection before deciding GO or REJECT.

## 3. Research-question status

- [rq-freshness] Do any competitors expose update freshness reliably?
  - Status: ANSWERED
  - Related evidence IDs: ev-fact-1
  - Related competitor IDs: comp-spruce
  - Notes: Answer is based on supplied synthetic artifacts only.
- [rq-monetization] How clearly do competitors expose monetization pathways?
  - Status: PARTIAL
  - Related evidence IDs: ev-fact-3
  - Related competitor IDs: comp-harbor
  - Notes: Not supplied
- [rq-workflow] Which workflow reduces urgent contact friction the most?
  - Status: OPEN
  - Related evidence IDs: Not supplied
  - Related competitor IDs: comp-spruce, comp-lantern, comp-harbor
  - Notes: Not supplied

## 4. Competitor comparison matrix

| Competitor | Freshness | Structured detail | Verification | User workflow |
| --- | --- | --- | --- | --- |
| comp-spruce (Spruce Local) | PRESENT; obs=obs-present; ev=ev-fact-1 | Not supplied | Not supplied | UNKNOWN; obs=obs-unknown; ev=Not supplied |
| comp-lantern (Lantern Listings) | Not supplied | Not supplied | ABSENT; obs=obs-absent; ev=ev-fact-2 | NOT_APPLICABLE; obs=obs-na; ev=Not supplied |
| comp-harbor (Harbor Directory) | Not supplied | PARTIAL; obs=obs-partial; ev=ev-fact-3 | Not supplied | Not supplied |

## 5. Comparison-observation details

- [obs-present] competitor=comp-spruce; dimension=dim-freshness; state=PRESENT
  - Statement: Spruce Local visibly presents update recency on most cards.
  - Supporting evidence IDs: ev-fact-1
  - Notes: Not supplied
- [obs-absent] competitor=comp-lantern; dimension=dim-verification; state=ABSENT
  - Statement: Lantern Listings shows no verification indicator in card UI.
  - Supporting evidence IDs: ev-fact-2
  - Notes: Not supplied
- [obs-partial] competitor=comp-harbor; dimension=dim-structured-detail; state=PARTIAL
  - Statement: Harbor Directory includes structured fields for only some categories.
  - Supporting evidence IDs: ev-fact-3
  - Notes: Not supplied
- [obs-unknown] competitor=comp-spruce; dimension=dim-user-workflow; state=UNKNOWN
  - Statement: The full contact workflow path was not captured in supplied artifacts.
  - Supporting evidence IDs: Not supplied
  - Notes: Not supplied
- [obs-na] competitor=comp-lantern; dimension=dim-user-workflow; state=NOT_APPLICABLE
  - Statement: No direct booking workflow is present in this competitor model.
  - Supporting evidence IDs: Not supplied
  - Notes: Not supplied

## 6. Evidence coverage audit

| Competitor ID | Dimension ID | Observation supplied | Observation state | FACT basis | Evidence IDs | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| comp-spruce | dim-freshness | yes | PRESENT | yes | ev-fact-1 | fact-supported |
| comp-spruce | dim-structured-detail | no | Not supplied | no | Not supplied | missing |
| comp-spruce | dim-verification | no | Not supplied | no | Not supplied | missing |
| comp-spruce | dim-user-workflow | yes | UNKNOWN | no | Not supplied | unknown |
| comp-lantern | dim-freshness | no | Not supplied | no | Not supplied | missing |
| comp-lantern | dim-structured-detail | no | Not supplied | no | Not supplied | missing |
| comp-lantern | dim-verification | yes | ABSENT | yes | ev-fact-2 | fact-supported |
| comp-lantern | dim-user-workflow | yes | NOT_APPLICABLE | no | Not supplied | not applicable |
| comp-harbor | dim-freshness | no | Not supplied | no | Not supplied | missing |
| comp-harbor | dim-structured-detail | yes | PARTIAL | yes | ev-fact-3 | fact-supported |
| comp-harbor | dim-verification | no | Not supplied | no | Not supplied | missing |
| comp-harbor | dim-user-workflow | no | Not supplied | no | Not supplied | missing |

- Evidence counts: FACT=3, INFERENCE=1, HYPOTHESIS=1, UNKNOWN=1

## 7. Verified facts

- [ev-fact-1] Spruce Local shows a visible last-updated timestamp on most operator cards.
  - Source references: Manual screenshot set A
  - Related competitors: comp-spruce
  - Supporting evidence: Not supplied
  - Notes: Observed directly in synthetic artifact set.
- [ev-fact-2] Lantern Listings does not display verification indicators on listing cards.
  - Source references: Manual screenshot set B
  - Related competitors: comp-lantern
  - Supporting evidence: Not supplied
  - Notes: Not supplied
- [ev-fact-3] Harbor Directory includes paid-featured rows on only selected categories.
  - Source references: Operator demo notes
  - Related competitors: comp-harbor
  - Supporting evidence: Not supplied
  - Notes: Not supplied

## 8. Supported inferences

- [ev-inf-1] Visible freshness cues may reduce operator-trust friction for first contact.
  - Source references: Not supplied
  - Related competitors: Not supplied
  - Supporting evidence: ev-fact-1
  - Notes: Not supplied

## 9. Hypotheses requiring validation

- [ev-hyp-1] Operators may pay for manual verification if lead quality appears higher.
  - Source references: Not supplied
  - Related competitors: Not supplied
  - Supporting evidence: Not supplied
  - Notes: Not supplied

## 10. Unknowns

- [ev-unk-1] The best initial neighborhood mix is not yet known.
  - Source references: Not supplied
  - Related competitors: Not supplied
  - Supporting evidence: Not supplied
  - Notes: Not supplied

## 11. Wedge candidates

- [wedge-ready] Manual verification timestamp overlay
  - Target user: Traveling pet owners
  - Payer: Local service operators
  - User pain: Hard to trust listing accuracy during urgent planning.
  - Proposed advantage: Verified timestamp and response-window annotation on each listing.
  - Competitor gap addressed: Existing competitors do not consistently expose verification freshness.
  - Supporting evidence IDs: ev-fact-1
  - Hypothesis evidence IDs: ev-hyp-1
  - Notes: Ready for a limited manual pilot only.
- [wedge-blocked] Urgent booking handoff board
  - Target user: Traveling pet owners
  - Payer: Not supplied
  - User pain: Not supplied
  - Proposed advantage: Not supplied
  - Competitor gap addressed: Not supplied
  - Supporting evidence IDs: Not supplied
  - Hypothesis evidence IDs: Not supplied
  - Notes: Intentionally incomplete for structural readiness demonstration.

## 12. Structural test-readiness results

Structural test readiness - not an ACDIS business recommendation.
- [wedge-ready] READY_FOR_MANUAL_TEST
  - Missing requirements: Not supplied
  - Invalid evidence basis: Not supplied
- [wedge-blocked] BLOCKED_INCOMPLETE
  - Missing requirements: payer, user_pain, proposed_advantage, competitor_gap, smallest_manual_test, test_timebox, success_signal, invalidating_signal, next_operator_action, supporting_evidence_ids
  - Invalid evidence basis: Not supplied

## 13. Manual experiment cards

### Wedge wedge-ready: Manual verification timestamp overlay
- Target user: Traveling pet owners
- Payer: Local service operators
- Pain: Hard to trust listing accuracy during urgent planning.
- Proposed advantage: Verified timestamp and response-window annotation on each listing.
- Evidence basis: ev-fact-1
- Hypothesis basis: ev-hyp-1
- Smallest manual test: Manually verify and annotate 12 listings across two neighborhoods.
- Timebox: 2 weeks
- Cost cap: $400
- Success signal: At least 4 operators request continuation after review.
- Invalidating signal: No operator asks for repeated inclusion after first pass.
- Target sample: 12 operators
- Dependencies: Verification checklist, Operator outreach script
- Risks and failure reasons: Verification workflow could be too labor-intensive, Operators may not value timestamp badges
- Next operator action: Build operator shortlist and run first verification cycle.
- Readiness status: READY_FOR_MANUAL_TEST
- Missing requirements: Not supplied

### Wedge wedge-blocked: Urgent booking handoff board
- Target user: Traveling pet owners
- Payer: Not supplied
- Pain: Not supplied
- Proposed advantage: Not supplied
- Evidence basis: Not supplied
- Hypothesis basis: Not supplied
- Smallest manual test: Not supplied
- Timebox: Not supplied
- Cost cap: Not supplied
- Success signal: Not supplied
- Invalidating signal: Not supplied
- Target sample: Not supplied
- Dependencies: Not supplied
- Risks and failure reasons: Not supplied
- Next operator action: Not supplied
- Readiness status: BLOCKED_INCOMPLETE
- Missing requirements: payer, user_pain, proposed_advantage, competitor_gap, smallest_manual_test, test_timebox, success_signal, invalidating_signal, next_operator_action, supporting_evidence_ids

## 14. Reasons not to pursue

- Operator participation might be too low initially
- Manual verification throughput could bottleneck

## 15. Outstanding research gaps

- Research question rq-monetization: PARTIAL
- Research question rq-workflow: OPEN
- Missing comparison observation for competitor=comp-spruce, dimension=dim-structured-detail
- Missing comparison observation for competitor=comp-spruce, dimension=dim-verification
- Missing comparison observation for competitor=comp-lantern, dimension=dim-freshness
- Missing comparison observation for competitor=comp-lantern, dimension=dim-structured-detail
- Missing comparison observation for competitor=comp-harbor, dimension=dim-freshness
- Missing comparison observation for competitor=comp-harbor, dimension=dim-verification
- Missing comparison observation for competitor=comp-harbor, dimension=dim-user-workflow

## 16. Next operator actions

- Interview additional operators
- Run one manual contact-flow rehearsal
- Build operator shortlist and run first verification cycle.

## 17. Evidence appendix

- [ev-fact-1] (FACT) Spruce Local shows a visible last-updated timestamp on most operator cards.
  - Source references: Manual screenshot set A
  - Supporting evidence: Not supplied
  - Related competitors: comp-spruce
- [ev-fact-2] (FACT) Lantern Listings does not display verification indicators on listing cards.
  - Source references: Manual screenshot set B
  - Supporting evidence: Not supplied
  - Related competitors: comp-lantern
- [ev-fact-3] (FACT) Harbor Directory includes paid-featured rows on only selected categories.
  - Source references: Operator demo notes
  - Supporting evidence: Not supplied
  - Related competitors: comp-harbor
- [ev-inf-1] (INFERENCE) Visible freshness cues may reduce operator-trust friction for first contact.
  - Source references: Not supplied
  - Supporting evidence: ev-fact-1
  - Related competitors: Not supplied
- [ev-hyp-1] (HYPOTHESIS) Operators may pay for manual verification if lead quality appears higher.
  - Source references: Not supplied
  - Supporting evidence: Not supplied
  - Related competitors: Not supplied
- [ev-unk-1] (UNKNOWN) The best initial neighborhood mix is not yet known.
  - Source references: Not supplied
  - Supporting evidence: Not supplied
  - Related competitors: Not supplied

## 18. Integrity statement

- All competitor states in this report were supplied by the operator.
- ACDIS performed validation and organization only.
- Missing research is not automatically a competitor weakness.
- Readiness is structural completeness, not a business recommendation.
- No score, ranking, market estimate, or autonomous recommendation was produced.
