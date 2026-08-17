"""PTF-CONTRACT-FOUNDATION-001 -- the one identity normaliser.

The golden set below is not a style preference. Each case is a divergence that
was actually observed between the five ``normalize_name`` implementations and
the committed authority documents, and each one broke a real join.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts.identity_key import (
    IDENTITY_KEY_CONTRACT, IdentityKeyError, divergences, is_canonical_key,
    key_collisions, ptf_identity_key, rekey,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"


class TestGoldenSet:
    """The four divergences that motivated the contract."""

    @pytest.mark.parametrize("name,expected", [
        # "&" becomes a word rather than vanishing. discovery.duplicates drops
        # it entirely, which is right for fuzzy dedupe and wrong for identity;
        # the committed routing authority already spells it "and".
        ("Holiday Inn Express & Suites Greenville",
         "holiday inn express and suites greenville"),
        ("Drury Inn & Suites Beachwood", "drury inn and suites beachwood"),
        # A hyphen is a separator, not a character to keep. The Dayton census
        # stores "i-70" while its routing record stores "i 70", which is why
        # the routing subset check reported two orphans that do not exist.
        ("Comfort Suites Springfield I-70", "comfort suites springfield i 70"),
        # Combining marks are FOLDED, never treated as separators. Unfolded,
        # "méridien" tokenises to "m" + "ridien", and a bare one-character
        # token is free to match inside unrelated hotels' names.
        ("Le Méridien Columbus, The Joseph", "le meridien columbus the joseph"),
    ])
    def test_divergence_cases(self, name, expected):
        assert ptf_identity_key(name) == expected

    def test_accented_and_unaccented_agree(self):
        """The Marriott page and our record name the same hotel."""
        assert (ptf_identity_key("Le Méridien Columbus, The Joseph")
                == ptf_identity_key("Le Meridien Columbus, The Joseph"))

    @pytest.mark.parametrize("name,expected", [
        ("  Red Roof PLUS+ Columbus - Dublin ", "red roof plus columbus dublin"),
        ("Hotel   With    Runs", "hotel with runs"),
        ("UPPER CASE INN", "upper case inn"),
        ("Hampton Inn & Suites (Downtown)", "hampton inn and suites downtown"),
    ])
    def test_normalisation(self, name, expected):
        assert ptf_identity_key(name) == expected

    def test_idempotent(self):
        """A key run through the contract again is unchanged.

        Non-idempotence would mean a record rekeyed twice lands somewhere new,
        so a migration could not safely be re-run.
        """
        for name in ("Drury Inn & Suites Beachwood", "Le Méridien Columbus",
                     "Comfort Suites Springfield I-70"):
            once = ptf_identity_key(name)
            assert ptf_identity_key(once) == once


class TestFailClosed:
    """An empty key would match every other empty key."""

    @pytest.mark.parametrize("name", ["", "   ", "---", "!!!", "...", "()"])
    def test_empty_result_raises(self, name):
        with pytest.raises(IdentityKeyError):
            ptf_identity_key(name)

    def test_non_string_raises(self):
        with pytest.raises(IdentityKeyError):
            ptf_identity_key(None)

    def test_ampersand_alone_is_not_a_key(self):
        """"&" alone folds to "and", which is a word but not an identity."""
        assert ptf_identity_key("& Hotel") == "and hotel"


class TestIsCanonical:

    def test_accepts_own_output(self):
        assert is_canonical_key("drury inn and suites beachwood")

    @pytest.mark.parametrize("value", [
        "Drury Inn & Suites Beachwood",          # unnormalised
        "drury inn & suites beachwood",          # legacy census spelling
        "comfort suites springfield i-70",       # legacy hyphen
        "",
    ])
    def test_rejects_legacy_spellings(self, value):
        assert not is_canonical_key(value)

    def test_is_a_form_check_not_a_provenance_check(self):
        """A mangled key can still be well FORMED, and this cannot see that.

        "le m ridien columbus the joseph" -- the diacritic split that made M10
        reject a confirmed capture -- contains only lowercase letters and
        spaces, so it is a fixed point of the contract and passes here.

        That is a real limit, not an oversight. Catching it needs the name it
        should have derived FROM, which is why the census validator compares
        identity_key against ptf_identity_key(canonical_name) rather than
        merely asking whether the stored key looks canonical.
        """
        mangled = "le m ridien columbus the joseph"
        assert is_canonical_key(mangled)
        assert ptf_identity_key("Le Méridien Columbus, The Joseph") != mangled


class TestCollisions:

    def test_reports_only_genuine_collisions(self):
        collisions = key_collisions([
            "Drury Inn & Suites Beachwood",
            "Drury Inn and Suites Beachwood",
            "Hampton Inn Dayton",
        ])
        assert list(collisions) == ["drury inn and suites beachwood"]

    def test_identical_names_are_not_a_collision(self):
        """One property listed twice is a duplicate row, not two identities."""
        assert key_collisions(["Hampton Inn Dayton", "Hampton Inn Dayton"]) == {}


class TestRekey:

    def test_returns_copies_and_leaves_input_alone(self):
        rows = [{"canonical_name": "Drury Inn & Suites Beachwood"}]
        out = rekey(rows)
        assert out[0]["identity_key"] == "drury inn and suites beachwood"
        assert "identity_key" not in rows[0]

    def test_divergences_names_rows_needing_migration(self):
        found = divergences([
            {"canonical_name": "Comfort Suites Springfield I-70",
             "normalized_name": "comfort suites springfield i-70"},
            {"canonical_name": "Hampton Inn Dayton",
             "normalized_name": "hampton inn dayton"},
        ])
        assert len(found) == 1
        assert found[0]["stored"] == "comfort suites springfield i-70"
        assert found[0]["canonical"] == "comfort suites springfield i 70"


class TestAgainstCommittedAuthority:
    """The contract's real job, proven on the committed documents."""

    def _routes(self):
        path = PACKAGE_DIR / "identity_routing.json"
        if not path.is_file():
            pytest.skip("identity_routing.json is not present")
        return json.loads(path.read_text(encoding="utf-8-sig"))["routes"]

    def _census_keys(self, market_id):
        path = PACKAGE_DIR / "identity_census" / ("%s.json" % market_id)
        if not path.is_file():
            pytest.skip("%s census is not committed" % market_id)
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        return {ptf_identity_key(h["canonical_name"]) for h in doc["hotels"]}

    def test_dayton_phantom_orphans_disappear(self):
        """Dayton's two "orphans" were one normaliser disagreeing with another.

        Comfort Suites Springfield I-70 and Holiday Inn Express & Suites
        Greenville are in the census AND hold routing records. Under the
        canonical key the market is clean, which is what the audit concluded by
        eye and could not demonstrate mechanically.
        """
        census = self._census_keys("dayton-oh")
        orphans = [r for r in self._routes()
                   if r["market_id"] == "dayton-oh"
                   and ptf_identity_key(r["hotel_ref"]["canonical_name"]) not in census]
        assert orphans == []

    def test_cleveland_real_orphans_survive(self):
        """Cleveland's two are genuinely absent, and must stay visible.

        A normalisation that "fixed" these would be hiding two non-lodging
        identities holding accommodation routes.
        """
        census = self._census_keys("cleveland-akron-canton-oh")
        orphans = sorted(
            r["hotel_ref"]["canonical_name"] for r in self._routes()
            if r["market_id"] == "cleveland-akron-canton-oh"
            and ptf_identity_key(r["hotel_ref"]["canonical_name"]) not in census)
        assert orphans == ["Eastland Inn Restaurant", "The Welshfield Inn"]

    def test_no_census_collisions(self):
        """Two distinct identities sharing a key would be unjoinable."""
        for market_id in ("dayton-oh", "cleveland-akron-canton-oh",
                          "indianapolis-in"):
            path = PACKAGE_DIR / "identity_census" / ("%s.json" % market_id)
            if not path.is_file():
                continue
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            collisions = key_collisions(h["canonical_name"] for h in doc["hotels"])
            assert collisions == {}, "%s: %s" % (market_id, collisions)


def test_contract_version_is_pinned():
    """A change to the algorithm must be a visible contract bump.

    Silently altering normalisation would rekey every join in the system.
    """
    assert IDENTITY_KEY_CONTRACT == "ptf_identity_key/1.0"
