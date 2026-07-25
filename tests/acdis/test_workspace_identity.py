from acdis.contracts.placeholders import CompetitorInput, EvidenceItem, EvidenceType, OpportunityInput


def test_evidence_categories_remain_distinct():
    assert EvidenceType.FACT != EvidenceType.INFERENCE
    assert EvidenceType.HYPOTHESIS != EvidenceType.UNKNOWN


def test_placeholder_contracts_can_be_constructed_without_external_behavior():
    evidence = EvidenceItem(evidence_type=EvidenceType.FACT, summary="Observed", source="manual")
    opportunity = OpportunityInput(name="Pet care", description="Need an evidence file")
    competitor = CompetitorInput(name="Example Co", notes="Manual review")

    assert evidence.evidence_type is EvidenceType.FACT
    assert opportunity.name == "Pet care"
    assert competitor.name == "Example Co"
