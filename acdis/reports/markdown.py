from __future__ import annotations

from acdis.casefiles.models import EvidenceItem, ResearchCaseFile
from acdis.contracts.placeholders import EvidenceType


def _render_list(items: tuple[str, ...]) -> str:
    if not items:
        return "Not supplied"
    return "\n".join(f"- {item}" for item in items)


def _render_evidence_section(evidence: tuple[EvidenceItem, ...], evidence_type: EvidenceType) -> str:
    matching = [item for item in evidence if item.evidence_type is evidence_type]
    if not matching:
        return "Not supplied"
    lines = []
    for item in matching:
        lines.append(f"- [{item.evidence_id}] {item.statement}")
        if item.source_references:
            lines.append(f"  - Source references: {', '.join(item.source_references)}")
        if item.excerpt:
            lines.append(f"  - Excerpt: {item.excerpt}")
        if item.related_competitor_ids:
            lines.append(f"  - Related competitors: {', '.join(item.related_competitor_ids)}")
        if item.supporting_evidence_ids:
            lines.append(f"  - Supporting evidence: {', '.join(item.supporting_evidence_ids)}")
        if item.operator_notes:
            lines.append(f"  - Notes: {item.operator_notes}")
    return "\n".join(lines)


def render_markdown(case: ResearchCaseFile) -> str:
    sections = [
        "# Manual research opportunity report",
        "",
        "## 1. Case identity",
        "",
        f"- Case ID: {case.case_id}",
        f"- Case title: {case.case_title}",
        f"- Operator notes: {case.operator_notes or 'Not supplied'}",
        "",
        "## 2. Concept summary",
        "",
        f"- Opportunity name: {case.opportunity_name}",
        f"- Proposed directory category: {case.proposed_directory_category}",
        f"- Customer type: {case.customer_type}",
        "",
        "## 3. Problem definition",
        "",
        f"- User problem: {case.user_problem}",
        "",
        "## 4. Target users and market",
        "",
        f"- Target market: {case.target_market}",
        f"- Proposed minimum useful pilot: {case.proposed_minimum_useful_pilot}",
        "",
        "## 5. Competitor table",
        "",
        "| Competitor ID | Name | Supplied URLs | Artifact refs | Observed monetization | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    if case.competitors:
        for competitor in case.competitors:
            sections.append(
                f"| {competitor.competitor_id} | {competitor.name} | {', '.join(competitor.supplied_urls) if competitor.supplied_urls else 'Not supplied'} | {', '.join(competitor.artifact_references) if competitor.artifact_references else 'Not supplied'} | {', '.join(competitor.observed_monetization_methods) if competitor.observed_monetization_methods else 'Not supplied'} | {competitor.operator_notes or 'Not supplied'} |"
            )
    else:
        sections.append("| Not supplied | Not supplied | Not supplied | Not supplied | Not supplied | Not supplied |")

    sections.extend([
        "",
        "## 6. Verified observations",
        "",
        _render_evidence_section(case.evidence, EvidenceType.FACT),
        "",
        "## 7. Supported inferences",
        "",
        _render_evidence_section(case.evidence, EvidenceType.INFERENCE),
        "",
        "## 8. Hypotheses requiring validation",
        "",
        _render_evidence_section(case.evidence, EvidenceType.HYPOTHESIS),
        "",
        "## 9. Unknowns",
        "",
        _render_evidence_section(case.evidence, EvidenceType.UNKNOWN),
        "",
        "## 10. Proposed market wedge",
        "",
        _render_list(case.proposed_wedge_ideas),
        "",
        "## 11. Minimum useful pilot",
        "",
        f"- {case.proposed_minimum_useful_pilot}",
        "",
        "## 12. Likely monetization paths",
        "",
        _render_list(case.likely_monetization_paths),
        "",
        "## 13. Data-moat potential",
        "",
        _render_list(case.potential_data_moat_opportunities),
        "",
        "## 14. Reasons not to pursue",
        "",
        _render_list(case.reasons_not_to_pursue),
        "",
        "## 15. Unresolved questions",
        "",
        _render_list(case.unresolved_questions),
        "",
        "## 16. Next research actions",
        "",
        _render_list(case.next_research_actions),
        "",
        "## 17. Operator recommendation",
        "",
        f"- Recommendation: {case.operator_recommendation or 'Not supplied'}",
        f"- Rationale: {case.operator_recommendation_rationale or 'Not supplied'}",
        "",
        "## 18. Evidence appendix",
        "",
    ])

    if case.evidence:
        for item in case.evidence:
            sections.append(f"- [{item.evidence_id}] {item.statement}")
            if item.source_references:
                sections.append(f"  - Source references: {', '.join(item.source_references)}")
            if item.excerpt:
                sections.append(f"  - Excerpt: {item.excerpt}")
            if item.related_competitor_ids:
                sections.append(f"  - Related competitors: {', '.join(item.related_competitor_ids)}")
            if item.supporting_evidence_ids:
                sections.append(f"  - Supporting evidence: {', '.join(item.supporting_evidence_ids)}")
            if item.operator_notes:
                sections.append(f"  - Notes: {item.operator_notes}")
    else:
        sections.append("Not supplied")

    return "\n".join(sections) + "\n"
