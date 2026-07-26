from __future__ import annotations


def make_phase1_case_data() -> dict:
    return {
        "case_id": "case-review-001",
        "case_title": "Synthetic Phase 2 review",
        "operator_notes": "Synthetic data for deterministic tests.",
        "opportunity_name": "Neighborhood helper directory",
        "target_market": "Urban pet owners",
        "proposed_directory_category": "Pet Services",
        "customer_type": "Pet owners",
        "user_problem": "Finding trustworthy local services quickly.",
        "proposed_minimum_useful_pilot": "Curated list for 3 neighborhoods.",
        "likely_monetization_paths": ["Sponsored listings"],
        "potential_data_moat_opportunities": ["Coverage density"],
        "reasons_not_to_pursue": ["Low operator supply"],
        "next_research_actions": ["Interview operators"],
        "competitors": [
            {
                "competitor_id": "comp-a",
                "name": "Alpha Local",
                "supplied_urls": ["https://alpha.example"],
            },
            {
                "competitor_id": "comp-b",
                "name": "Beta Board",
                "supplied_urls": ["https://beta.example"],
            },
            {
                "competitor_id": "comp-c",
                "name": "Gamma Guide",
                "supplied_urls": ["https://gamma.example"],
            },
        ],
        "evidence": [
            {
                "evidence_id": "ev-f1",
                "evidence_type": "FACT",
                "statement": "Alpha exposes local business details.",
                "source_references": ["Manual notes"],
                "related_competitor_ids": ["comp-a"],
            },
            {
                "evidence_id": "ev-f2",
                "evidence_type": "FACT",
                "statement": "Beta has sparse profile freshness.",
                "source_references": ["Operator screenshot"],
                "related_competitor_ids": ["comp-b"],
            },
            {
                "evidence_id": "ev-i1",
                "evidence_type": "INFERENCE",
                "statement": "Freshness likely matters for trust.",
                "supporting_evidence_ids": ["ev-f1"],
            },
            {
                "evidence_id": "ev-h1",
                "evidence_type": "HYPOTHESIS",
                "statement": "Operators may pay for verified placement.",
            },
            {
                "evidence_id": "ev-u1",
                "evidence_type": "UNKNOWN",
                "statement": "Exact adoption thresholds are unknown.",
            },
        ],
        "operator_recommendation": "HOLD",
        "operator_recommendation_rationale": "Need tighter comparison evidence.",
    }


def make_review_payload() -> dict:
    return {
        "research_questions": [
            {
                "question_id": "rq-1",
                "question_text": "Which competitor has freshest local records?",
                "status": "ANSWERED",
                "related_evidence_ids": ["ev-f1"],
                "related_competitor_ids": ["comp-a"],
                "operator_notes": "Answered from supplied artifact review.",
            },
            {
                "question_id": "rq-2",
                "question_text": "How visible is monetization to operators?",
                "status": "PARTIAL",
                "related_evidence_ids": ["ev-f2"],
                "related_competitor_ids": ["comp-b"],
            },
            {
                "question_id": "rq-3",
                "question_text": "Will operators accept concierge onboarding?",
                "status": "OPEN",
                "related_evidence_ids": [],
                "related_competitor_ids": ["comp-c"],
            },
        ],
        "comparison_dimensions": [
            {
                "dimension_id": "dim-freshness",
                "label": "Freshness",
                "description": "How recent profile updates appear.",
                "why_it_matters": "Stale records degrade trust.",
            },
            {
                "dimension_id": "dim-verification",
                "label": "Verification",
                "description": "Whether listings show verification markers.",
                "why_it_matters": "Verification lowers perceived risk.",
            },
            {
                "dimension_id": "dim-monetization",
                "label": "Monetization visibility",
                "description": "How pricing or paid placement is disclosed.",
                "why_it_matters": "Operator willingness depends on clarity.",
            },
            {
                "dimension_id": "dim-workflow",
                "label": "User workflow",
                "description": "How many steps user takes to reach contact.",
                "why_it_matters": "Friction impacts conversion.",
            },
        ],
        "comparison_observations": [
            {
                "observation_id": "obs-1",
                "competitor_id": "comp-a",
                "dimension_id": "dim-freshness",
                "state": "PRESENT",
                "statement": "Recent update dates are visible.",
                "supporting_evidence_ids": ["ev-f1"],
            },
            {
                "observation_id": "obs-2",
                "competitor_id": "comp-b",
                "dimension_id": "dim-verification",
                "state": "ABSENT",
                "statement": "No verification indicators on listing cards.",
                "supporting_evidence_ids": ["ev-f2"],
            },
            {
                "observation_id": "obs-3",
                "competitor_id": "comp-c",
                "dimension_id": "dim-monetization",
                "state": "PARTIAL",
                "statement": "Pricing appears on some but not all profile pages.",
                "supporting_evidence_ids": ["ev-f1"],
            },
            {
                "observation_id": "obs-4",
                "competitor_id": "comp-a",
                "dimension_id": "dim-workflow",
                "state": "UNKNOWN",
                "statement": "Workflow details were not captured.",
                "supporting_evidence_ids": [],
            },
            {
                "observation_id": "obs-5",
                "competitor_id": "comp-b",
                "dimension_id": "dim-workflow",
                "state": "NOT_APPLICABLE",
                "statement": "No direct booking flow exists in this interface.",
                "supporting_evidence_ids": [],
            },
        ],
        "wedge_candidates": [
            {
                "wedge_id": "wedge-ready",
                "title": "Verified local concierge intake",
                "target_user": "Traveling pet owner",
                "payer": "Local service operator",
                "user_pain": "Hard to confirm operator reliability quickly.",
                "proposed_advantage": "Manual verification badge with response-time note.",
                "competitor_gap": "Current options do not show recent verification timestamps.",
                "supporting_evidence_ids": ["ev-f1"],
                "hypothesis_evidence_ids": ["ev-h1"],
                "reasons_the_wedge_might_fail": ["Operators may ignore onboarding requests."],
                "smallest_manual_test": "Manually verify 10 operators and present badges on a static sheet.",
                "test_timebox": "10 business days",
                "cost_cap": "$300",
                "success_signal": "At least 3 operators request inclusion follow-up.",
                "invalidating_signal": "No operator response after two outreach attempts.",
                "test_participants": "10 operators across 2 neighborhoods",
                "dependencies": ["Operator interview script"],
                "next_operator_action": "Prepare outreach list and verification checklist.",
            },
            {
                "wedge_id": "wedge-blocked",
                "title": "Workflow shortcut for urgent bookings",
                "target_user": "Traveling pet owner",
            },
        ],
    }


def make_review_case_data() -> dict:
    data = make_phase1_case_data()
    data["review"] = make_review_payload()
    return data
