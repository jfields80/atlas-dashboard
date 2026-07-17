"""AES-DATA-001 -- evidence-span validation, normalization, category
whitelist, and policy composition (mission sections 10/11/12/13/28)."""

from __future__ import annotations

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.category_templates import allowed_fields
from scripts.pettripfinder.importer.evidence import build_llm_evidence, locate_quote
from scripts.pettripfinder.importer.extraction import parse_extraction_payload
from scripts.pettripfinder.importer.models import ProposedFact
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy

_TEXT = "Dogs and cats are welcome. A $50 per night fee applies. Limit two pets."


def _fact(field, value, quote, ambiguous=False, cs=-1, ce=-1):
    return ProposedFact(field, value, quote, cs, ce, ambiguous, "")


class TestEvidence:
    def test_verbatim_quote_supported(self):
        ev = build_llm_evidence(_fact("pets_allowed", "true", "Dogs and cats are welcome"),
                                _TEXT, "https://s.test/")
        assert ev.support_state == C.SUPPORT_SUPPORTED
        assert ev.char_start >= 0 and _TEXT[ev.char_start:ev.char_end] == "Dogs and cats are welcome"

    def test_offsets_relocated_when_wrong(self):
        ev = build_llm_evidence(_fact("pet_fee", "$50", "A $50 per night fee applies",
                                      cs=999, ce=1050), _TEXT, "https://s.test/")
        assert ev.support_state == C.SUPPORT_SUPPORTED and ev.char_start >= 0

    def test_absent_quote_rejected(self):
        ev = build_llm_evidence(_fact("pet_fee", "$0", "the fee is zero dollars"),
                                _TEXT, "https://s.test/")
        assert ev.support_state == C.SUPPORT_UNSUPPORTED
        assert C.REASON_EVIDENCE_MISMATCH in ev.warnings

    def test_ambiguous_marked(self):
        ev = build_llm_evidence(_fact("pets_allowed", "true", "Dogs and cats are welcome",
                                      ambiguous=True), _TEXT, "https://s.test/")
        assert ev.support_state == C.SUPPORT_AMBIGUOUS

    def test_quote_capped_300(self):
        long_quote = "Dogs and cats are welcome. " + ("x" * 400)
        ev = build_llm_evidence(_fact("pets_allowed", "true", long_quote),
                                _TEXT, "https://s.test/")
        assert "quote_truncated_to_300" in ev.warnings

    def test_unicode_and_whitespace_tolerant(self):
        text = N.normalize_whitespace("Dogs   and cats are “welcome”")
        ev = build_llm_evidence(_fact("pets_allowed", "true", "Dogs and cats are \"welcome\""),
                                text, "https://s.test/")
        assert ev.support_state == C.SUPPORT_SUPPORTED

    def test_locate_missing_returns_negative(self):
        assert locate_quote(_TEXT, "not present here") == (-1, -1)


class TestWhitelist:
    def test_unknown_field_dropped(self):
        payload = {"facts": [
            {"field": "pets_allowed", "value": "true", "quote": "q"},
            {"field": "approve", "value": "true", "quote": "q"},
            {"field": "recommendation", "value": "READY", "quote": "q"},
        ]}
        res = parse_extraction_payload(payload, allowed_fields("hotels"), "static", "m")
        names = {f.field_name for f in res.facts}
        assert names == {"pets_allowed"}

    def test_wrong_category_field_dropped(self):
        # off_leash is a park field, not a hotel field.
        payload = {"facts": [{"field": "off_leash", "value": "true", "quote": "q"}]}
        res = parse_extraction_payload(payload, allowed_fields("hotels"), "static", "m")
        assert res.facts == ()

    def test_malformed_json_unparseable(self):
        res = parse_extraction_payload("{not json", allowed_fields("hotels"), "static", "m")
        assert res.ok is False and res.error == C.REASON_EXTRACTION_UNPARSEABLE


class TestNormalize:
    def test_phone(self):
        assert N.normalize_phone("(614) 854-0216") == "614-854-0216"
        assert N.normalize_phone("+1 614 854 0216") == "614-854-0216"
        assert N.normalize_phone("nope") == ""

    def test_state(self):
        assert N.normalize_state("Ohio") == "OH"
        assert N.normalize_state("oh") == "OH"
        assert N.normalize_state("Nowhere") == ""

    def test_postal(self):
        assert N.normalize_postal("43215-1234") == "43215"
        assert N.normalize_postal("abc") == ""

    def test_fee_weight_count(self):
        assert N.normalize_fee("$50 per night") == "$50"
        assert N.normalize_weight("80 pounds combined") == "80 lb"
        assert N.normalize_count("two") == "2"

    def test_url_and_date(self):
        assert N.normalize_url("HTTPS://Ex.Test:443/A#f") == "https://ex.test/A"
        assert N.normalize_date("2026-07-16T10:00") == "2026-07-16"
        assert N.normalize_date("July 16") == ""

    def test_address_strips_trailing_locality(self):
        assert N.normalize_address("8805 Orion Place, Columbus, OH", "Columbus", "OH") \
            == "8805 Orion Place"


class TestPolicyCompose:
    def test_supported_clauses_only(self):
        pol = compose_pet_policy({
            "pets_allowed": "true", "species_allowed": "dogs and cats",
            "pet_fee": "$50", "fee_basis": "per night",
            "pet_count_limit": "2", "weight_limit": "80 lb",
        }, "hotels")
        assert "Dogs and cats are accepted." in pol
        assert "$50" in pol and "per night" in pol
        assert "two pets" not in pol and "maximum of 2 pets" in pol

    def test_conservative_fallback_only_with_pet_evidence(self):
        assert compose_pet_policy({"pets_allowed": "true"}, "hotels").startswith(
            "The property identifies itself as pet-friendly")
        assert compose_pet_policy({}, "hotels") == ""
        assert compose_pet_policy({"pets_allowed": "false"}, "hotels") == ""

    def test_park_fallback_wording(self):
        pol = compose_pet_policy({"pets_allowed": "true"}, "parks")
        assert "park authority" in pol
