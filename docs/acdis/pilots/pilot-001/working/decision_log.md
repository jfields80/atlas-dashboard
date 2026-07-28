# Pilot-001 Decision Log

Decision:
PROCEED TO VALIDATION

Confidence:
66/100

Decision meaning:
Authorize a constrained manual validation only.

Not authorized:
- estimator engine
- automated repair pricing
- full marketplace
- automatic lead routing
- shop dashboard
- appointment integration
- crawler
- ranking system
- broad Columbus directory build
- production deployment

Context note:
- During the synthesis pass, hypothesis_ledger.md and decision_log.md were identified as missing in working/. They are being created now to formalize the pilot decision artifacts.

Evidence supporting decision:
- FACT - official-site representation: Evidence captured across five representative models shows visible signals for repair-cost guidance, shop discovery, contact/booking entry points, and trust signals, but not a single fully observed end-to-end integrated flow.
- FACT - official-site representation: Columbus-specific content is visible in RepairPal Columbus page, Openbay Columbus page, AAA Columbus locator, and Oxford pages.
- FACT - official-site representation: Yelp page access remained verification-gated in this capture, preserving uncertainty in broad-discovery visibility.
- INFERENCE: Capabilities appear fragmented across models, supporting a low-cost validation of a narrower integrated promise before any build.

Strongest risks:
- insufficient estimate-data reliability for honest comparison outputs
- inability to obtain sufficiently comparable multi-shop responses
- low early demand and unclear monetization signal
- operational overhead of manual fulfillment
- legal/compliance exposure if estimate framing is interpreted as guaranteed pricing

Rejected alternatives:
- REQUIRE MORE RESEARCH as primary next step
  - Rejected because enough directional evidence exists to justify a constrained manual validation without product build.
- PIVOT immediately to non-comparison content-only model
  - Rejected because comparison-value hypotheses remain untested and can be validated cheaply.
- STOP
  - Rejected because evidence does not currently falsify the core validation hypotheses.

Evidence that would reverse decision:
- Gate 1 fails to recruit minimum participating shops within outreach and time caps.
- Gate 2 fails to produce minimum qualified consumer demand.
- Manual responses cannot be normalized into usable side-by-side comparisons.
- Legal review indicates unacceptable risk for proposed estimate-comparison language in pilot operations.

Reason implementation is premature:
- End-to-end workflows, demand strength, comparable quote quality, response-time viability, and monetization signals are not yet established by current evidence.
- The five-company set is a representative model sample, not a verified ranking of the market's largest competitors.

Competitor matrix language standard for downstream docs:
- Use YES only for directly observed presence.
- Use PARTIAL when some relevant evidence is visible.
- Use NO only when absence is directly observed on an accessible page.
- Use BLOCKED when access prevented observation.
- Use UNKNOWN when evidence is not established.
