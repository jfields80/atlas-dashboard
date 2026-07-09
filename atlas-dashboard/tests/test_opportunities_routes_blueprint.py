"""
atlas/tests/test_opportunities_routes_blueprint.py

Regression guard for the AES-008C fix: routes/opportunities.py
referenced `opportunities_bp` in a route decorator without ever
defining it anywhere in the codebase (confirmed via repo-wide grep
before the fix — the name existed only at its two use sites in
app.py, never at a definition site).

Scope: only guards that the Blueprint now exists and is wired up
correctly. Does not exercise run_autonomous_opportunity_scan()'s
actual body (NicheGenerator/BatchOpportunityGenerator/etc.) — that
logic is unrelated to the initialization-order defect this fix
addresses.
"""

from __future__ import annotations

from flask import Blueprint, Flask

from routes.opportunities import opportunities_bp


def test_opportunities_bp_is_defined_as_a_blueprint():
    assert isinstance(opportunities_bp, Blueprint)
    assert opportunities_bp.name == "opportunities"


def test_opportunities_bp_registers_the_auto_scan_route():
    test_app = Flask(__name__)
    test_app.register_blueprint(opportunities_bp)

    rules = {rule.rule: rule.endpoint for rule in test_app.url_map.iter_rules()}
    assert "/opportunities/auto" in rules
    assert rules["/opportunities/auto"] == "opportunities.run_autonomous_opportunity_scan"
