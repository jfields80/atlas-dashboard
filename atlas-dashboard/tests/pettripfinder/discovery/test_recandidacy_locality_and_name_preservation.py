"""PTF-DETROIT-ANN-ARBOR-RECANDIDACY-REPAIR-003 -- a silence is not a correction.

What went wrong
---------------
``absorb_prior_by_street`` reconciles a committed census row with a fresh
discovery sighting of the same building, keeps the fresh row, and used to
discard everything the committed row knew except its identity key. That is the
right call for a CONTRADICTION and the wrong one for a SILENCE, and an
OpenStreetMap node is silent about nearly everything a census row states.

Two defects came out of the Detroit shadow recensus, and both are pinned here:

* **D-002-A** -- Crowne Plaza Auburn Hills is committed with a city, a state and
  a ZIP. It was absorbed into an OSM sighting carrying none of them; the merged
  row kept the sighting's blanks; projection then held it with "the candidate
  states no city", about a property whose committed row names its city plainly.
  TEN Detroit identities were stranded exactly this way.
* **D-002-B** -- the same discard renamed SEVENTY committed identities to
  whatever OSM happened to call the building: "Daxton Hotel" became "Daxon
  Hotel" (an OSM misspelling) and "Best Western Greenfield Inn" became plain
  "Best Western".

Neither is a Detroit fact. Both are properties of the generic recandidacy
module and would apply to any market rebuilt against a free provider.

The rules
---------
1. A committed value fills a BLANK on the survivor, never overwrites a stated
   one.
2. Where both records state a value and they disagree, nothing is rewritten and
   the disagreement is surfaced.
3. A committed canonical name outranks a discovery label, always. Renaming a
   reviewed hotel is a founder ruling about a rebrand, and no string comparison
   produces one.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.pettripfinder.discovery import census_recandidacy as CR

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CENSUS = (REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
          / "detroit-ann-arbor-mi.json")


def osm(name, **kw):
    """An OpenStreetMap-shaped sighting: a name, a coordinate, little else."""
    row = {"candidate_id": "dc_osm", "name": name, "normalized_name": name.lower(),
           "address_line": "", "city": "", "state": "", "postal_code": "",
           "phone": "", "latitude": 42.5, "longitude": -83.2}
    row.update(kw)
    return row


def committed(name, **kw):
    row = {"candidate_id": CR.candidate_id_for(name.lower()), "name": name,
           "normalized_name": name.lower()}
    row.update(kw)
    return row


# --------------------------------------------------------------------------- #
# D-002-A -- locality
# --------------------------------------------------------------------------- #

class TestASilenceNeverErasesAStatedFact:

    def test_a_blank_discovery_locality_is_filled_from_the_committed_row(self):
        """The Crowne Plaza Auburn Hills shape, reduced to its essentials."""
        host = osm("Crowne Plaza Auburn Hills",
                   address_line="1500 Opdyke", postal_code="48326")
        prior = committed("Crowne Plaza Auburn Hills", address_line="1500 Opdyke Rd",
                          city="Auburn Hills", state="MI", postal_code="48326",
                          phone="248-373-4550")
        survivors, absorptions = CR.absorb_prior_by_street([host], [prior])

        assert survivors == []
        assert host["city"] == "Auburn Hills"
        assert host["state"] == "MI"
        assert host["phone"] == "248-373-4550"
        assert set(absorptions[0]["locality_backfilled_from_prior_census"]) == {
            "city", "state", "phone"}

    def test_the_backfilled_row_can_now_state_where_it_is(self):
        """The whole point: projection admits on a ZIP, or on city AND state."""
        host = osm("Some Hotel", address_line="1 Main St", postal_code="48000")
        prior = committed("Some Hotel", address_line="1 Main St",
                          postal_code="48000", city="Novi", state="MI")
        CR.absorb_prior_by_street([host], [prior])
        assert (host["city"].strip() and host["state"].strip())

    def test_a_stated_discovery_value_is_never_overwritten(self):
        host = osm("Some Hotel", address_line="1 Main St", postal_code="48000",
                   city="Novi", state="MI", phone="248-111-2222")
        prior = committed("Some Hotel", address_line="1 Main St",
                          postal_code="48000", city="Northville", state="MI",
                          phone="248-999-8888")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert host["city"] == "Novi"
        assert host["phone"] == "248-111-2222"
        assert absorptions[0]["locality_backfilled_from_prior_census"] == []

    def test_a_disagreement_is_surfaced_rather_than_resolved(self):
        host = osm("Some Hotel", address_line="1 Main St", postal_code="48000",
                   city="Novi", state="MI")
        prior = committed("Some Hotel", address_line="1 Main St",
                          postal_code="48000", city="Northville", state="MI")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        conflicts = absorptions[0]["locality_conflicts"]
        assert [c["field"] for c in conflicts] == ["city"]
        assert conflicts[0] == {"field": "city", "discovery_states": "Novi",
                                "prior_census_states": "Northville"}
        assert host["recandidacy_conflicts"] == conflicts

    def test_spelling_is_not_disagreement(self):
        """'1500 Opdyke Rd' vs '1500 opdyke rd' is one fact, not two."""
        host = osm("H", address_line="1500 Opdyke Rd", postal_code="48326",
                   city="Auburn Hills", state="mi")
        prior = committed("H", address_line="1500 opdyke rd  ", postal_code="48326",
                          city="auburn hills", state="MI")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert absorptions[0]["locality_conflicts"] == []

    def test_a_phone_is_compared_on_its_digits(self):
        host = osm("H", address_line="1 A St", postal_code="48000",
                   phone="+1 (248) 111-2222")
        prior = committed("H", address_line="1 A St", postal_code="48000",
                          phone="248-111-2222")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert absorptions[0]["locality_conflicts"] == []

    def test_to_candidate_carries_the_state(self):
        """It carried city and ZIP but not state, so a committed row with a city
        and no ZIP arrived missing half of the only pair it could be admitted
        on."""
        c = CR.to_candidate({"identity_key": "the bell tower hotel",
                             "canonical_name": "The Bell Tower Hotel",
                             "city": "Ann Arbor", "state": "MI",
                             "postal_code": ""},
                            market_id="detroit-ann-arbor-mi",
                            observed_at="2026-08-28")
        assert c["city"] == "Ann Arbor"
        assert c["state"] == "MI"


# --------------------------------------------------------------------------- #
# D-002-B -- names
# --------------------------------------------------------------------------- #

class TestACommittedNameOutranksASighting:

    @pytest.mark.parametrize("sighting,committed_name", [
        ("Daxon Hotel", "Daxton Hotel"),                       # an OSM typo
        ("Best Western", "Best Western Greenfield Inn"),        # brand-only label
        ("Comfort Inn Hotel", "Comfort Inn Metro Airport"),     # generic label
        ("Embassy Suites", "Embassy Suites by Hilton Detroit Livonia Novi"),
    ])
    def test_the_sighting_never_renames_the_committed_hotel(self, sighting,
                                                            committed_name):
        host = osm(sighting, address_line="1 Main St", postal_code="48000")
        prior = committed(committed_name, address_line="1 Main St",
                          postal_code="48000", city="Detroit", state="MI")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert host["name"] == committed_name
        assert host["discovery_observed_name"] == sighting
        assert absorptions[0]["into_name"] == committed_name

    def test_the_sighting_label_is_kept_as_observation_not_discarded(self):
        host = osm("Daxon Hotel", address_line="1 Main St", postal_code="48000")
        prior = committed("Daxton Hotel", address_line="1 Main St",
                          postal_code="48000")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert absorptions[0]["discovery_observed_name"] == "Daxon Hotel"

    def test_a_longer_sighting_name_still_does_not_win(self):
        """Longer is not stronger. Only a founder rebrand ruling renames."""
        host = osm("Some Hotel Downtown Riverfront Tower",
                   address_line="1 Main St", postal_code="48000")
        prior = committed("Some Hotel", address_line="1 Main St",
                          postal_code="48000")
        CR.absorb_prior_by_street([host], [prior])
        assert host["name"] == "Some Hotel"

    def test_two_committed_identities_at_one_address_pick_the_one_the_sighting_names(self):
        """The Detroit Novi case. A Courtyard became a Sonesta Select; both
        identities are committed and both absorb into the one OSM sighting. The
        sighting's label is too thin to BE the name, but it is real evidence of
        which identity is at that address today."""
        host = osm("Sonesta Select", address_line="42700 W 11 Mile Rd",
                   postal_code="48375")
        old = committed("Courtyard by Marriott Detroit Novi",
                        address_line="42700 W 11 Mile Rd", postal_code="48375")
        new = committed("Sonesta Select Detroit Novi",
                        address_line="42700 West 11 Mile Rd", postal_code="48375")
        CR.absorb_prior_by_street([host], [old, new])
        assert host["name"] == "Sonesta Select Detroit Novi"
        assert set(host["absorbed_committed_names"]) == {
            "Courtyard by Marriott Detroit Novi", "Sonesta Select Detroit Novi"}

    def test_the_choice_does_not_depend_on_absorption_order(self):
        host_a = osm("Sonesta Select", address_line="42700 W 11 Mile Rd",
                     postal_code="48375")
        host_b = osm("Sonesta Select", address_line="42700 W 11 Mile Rd",
                     postal_code="48375")
        old = committed("Courtyard by Marriott Detroit Novi",
                        address_line="42700 W 11 Mile Rd", postal_code="48375")
        new = committed("Sonesta Select Detroit Novi",
                        address_line="42700 West 11 Mile Rd", postal_code="48375")
        CR.absorb_prior_by_street([host_a], [old, new])
        CR.absorb_prior_by_street([host_b], [new, old])
        assert host_a["name"] == host_b["name"] == "Sonesta Select Detroit Novi"

    def test_every_prior_identity_key_is_still_traceable(self):
        host = osm("Sonesta Select", address_line="42700 W 11 Mile Rd",
                   postal_code="48375")
        old = committed("Courtyard by Marriott Detroit Novi",
                        address_line="42700 W 11 Mile Rd", postal_code="48375")
        new = committed("Sonesta Select Detroit Novi",
                        address_line="42700 West 11 Mile Rd", postal_code="48375")
        CR.absorb_prior_by_street([host], [old, new])
        assert host["prior_census_identity_keys"] == [
            "courtyard by marriott detroit novi", "sonesta select detroit novi"]


# --------------------------------------------------------------------------- #
# the committed Detroit census, end to end
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not CENSUS.exists(), reason="Detroit census not on this branch")
class TestTheCommittedDetroitCensus:

    @staticmethod
    def _rows():
        return json.loads(CENSUS.read_text(encoding="utf-8"))["hotels"]

    def test_every_committed_row_recandidates_with_its_locality_intact(self):
        """Nothing a committed row states about where it is may be lost on the
        way into a rebuild."""
        for row in self._rows():
            c = CR.to_candidate(row, market_id="detroit-ann-arbor-mi",
                                observed_at="2026-08-28")
            assert c["city"] == (row.get("city") or "")
            assert c["state"] == (row.get("state") or "")
            assert c["postal_code"] == (row.get("postal_code") or "")
            assert c["address_line"] == (row.get("address") or "")

    def test_every_committed_row_can_still_say_where_it_is(self):
        """Projection admits on a ZIP, or on city AND state. Every Detroit row
        satisfies one of those, so none may be held IDENTITY_NO_LOCALITY for
        want of a field the census actually states."""
        for row in self._rows():
            c = CR.to_candidate(row, market_id="detroit-ann-arbor-mi",
                                observed_at="2026-08-28")
            assert c["postal_code"].strip() or (c["city"].strip() and c["state"].strip()), \
                row["canonical_name"]


class TestAnAbsorptionRecordSaysWhereTheRowLanded:
    """``into_name`` is written mid-pass, so a second absorption that renames
    the host must not leave the first record naming a host that no longer
    exists under that name -- a reconciliation following it would walk to a
    dead end and report a live identity as an unexplained loss."""

    def test_every_record_names_the_hosts_final_name(self):
        host = osm("Sonesta Select", address_line="42700 W 11 Mile Rd",
                   postal_code="48375")
        old = committed("Courtyard by Marriott Detroit Novi",
                        address_line="42700 W 11 Mile Rd", postal_code="48375")
        new = committed("Sonesta Select Detroit Novi",
                        address_line="42700 West 11 Mile Rd", postal_code="48375")
        _, absorptions = CR.absorb_prior_by_street([host], [old, new])
        assert {a["into_name"] for a in absorptions} == {"Sonesta Select Detroit Novi"}
        assert host["name"] == "Sonesta Select Detroit Novi"

    def test_a_single_absorption_still_names_its_host(self):
        host = osm("Daxon Hotel", address_line="1 Main St", postal_code="48000")
        prior = committed("Daxton Hotel", address_line="1 Main St",
                          postal_code="48000")
        _, absorptions = CR.absorb_prior_by_street([host], [prior])
        assert absorptions[0]["into_name"] == "Daxton Hotel"
