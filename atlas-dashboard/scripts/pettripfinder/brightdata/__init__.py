"""Bright Data Browser API acquisition for PetTripFinder.

Bright Data is ACQUISITION INFRASTRUCTURE and nothing else. Nothing in this
package writes to a market authority, a partition, an exclusion registry, a
routing record or an approval ledger, and nothing here promotes a capture to a
published fact. The governance chain is unchanged and unshortened:

    ACQUISITION -> EVIDENCE -> STRUCTURED PROPOSAL -> FOUNDER REVIEW
                -> AUTHORITY APPLICATION

This package owns the first arrow and stops at the second. A capture becomes a
proposal only by passing the EXISTING contracts -- ``policy_observation``,
``policy_membrane``, ``readiness`` and ``contracts.evidence`` -- which this
package calls and never modifies. Where one of those contracts cannot express
what a managed-browser capture is, the correct output is a reported GAP, not a
widened vocabulary.

Module map
----------
``client``            credential handling, the wss endpoint, redaction, and the
                      Bright Data usage meter. The only module that knows the
                      secret exists.
``marriott_surface``  pure Marriott-template knowledge: identity signals, page
                      health predicates, the bounded pet-policy locator, and a
                      deterministic reading of the policy block. No network.
``browser_capture``   one attempt = one fresh Bright Data session. Owns the
                      closed outcome vocabulary and artifact persistence.
``publication_grade`` runs a finished capture through the CURRENT evidence
                      contract, unmodified, and reports confirmation or the
                      exact reasons for rejection.
``marriott_pilot_001`` the bounded five-property benchmark: fixed targets,
                      batch runner, benchmark comparison, reports.
"""
