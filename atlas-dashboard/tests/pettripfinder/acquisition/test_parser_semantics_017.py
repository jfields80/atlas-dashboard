"""PTF-POLICY-PARSER-SEMANTIC-HARDENING-017 -- Phase 8.

Two semantics, hardened: what a positive species statement does NOT say, and
the fee constructions the reader could not read.

WHAT THE SPECIES TESTS ARE ACTUALLY GUARDING
--------------------------------------------
``species_allowed`` is a list of species the surface AFFIRMED. It is not an
exhaustive allow-list, and no consumer in this repository treats it as one:
``canonical_view.cats_state`` returns no state at all for a species missing
from it, the renderer prints "Not stated", and prohibition travels separately
in ``cats_allowed`` and in the 1.2 species map. So "All dogs are welcome"
already did not assert that cats are refused.

That is worth PINNING rather than assuming, because it is one careless consumer
away from being false, and the failure would be silent and guest-visible: a
hotel that takes cats, published as one that refuses them.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import canonical_view as CV                   # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY       # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.contracts import enums                        # noqa: E402
from . import authority_freeze as AUTHORITY_FREEZE

FIXTURE = (REPO / "tests" / "pettripfinder" / "fixtures"
           / "parser_semantics_017" / "differential.json")


def read(text):
    reading = PR.parse(text, strategy="test_017")
    result = PR.to_extraction(reading, location="")
    return (dict(result.extraction), dict(result.withheld or {}),
            [f.get("code") for f in (result.flags or [])], reading)


# --------------------------------------------------------------------------- #
# 1-4. species semantics
# --------------------------------------------------------------------------- #

def test_all_dogs_are_welcome_does_not_assert_that_cats_are_excluded():
    extraction, _withheld, _flags, reading = read(
        "All dogs are welcome at the lodge.")
    assert extraction["species_allowed"] == ["dog"]
    # the affirmation is recorded; the exclusion is not asserted anywhere
    assert "cats_allowed" not in extraction
    assert reading.species_exclusive is False


def test_a_bare_dog_affirmation_leaves_cats_with_no_state_downstream():
    """The claim that matters, checked where a guest would see it."""
    view = CV.build({"facts": {"species_allowed": "dog"}})
    assert view.cats_state == ""
    assert view.dogs_state == enums.SPECIES_ACCEPTED


def test_an_explicit_cat_prohibition_still_reaches_the_view():
    view = CV.build({"facts": {"species_allowed": "dog",
                               "cats_allowed": "false"}})
    assert view.cats_state == enums.SPECIES_PROHIBITED


def test_the_reader_says_out_loud_what_it_is_not_claiming():
    _extraction, _withheld, _flags, reading = read("Dogs are welcome.")
    notes = PR.to_extraction(reading, location="").non_inferences
    species = [n for n in notes if n.startswith("species")]
    assert species, "no species non-inference was recorded"
    assert "unknown rather than prohibited" in species[0]


def test_dogs_only_still_supports_explicit_restriction_semantics():
    """Decided semantics, unchanged: the exclusivity is recorded as such and
    the field it populates is the same one it always populated."""
    extraction, _withheld, _flags, reading = read(
        "Dogs only. Two pets max per room.")
    assert extraction["species_allowed"] == ["dog"]
    assert reading.species_exclusive is True
    assert extraction["pet_count_limit"] == 2


def test_dogs_and_cats_allowed_structures_both_species():
    """Previously recorded NO species at all: the pattern required the word
    "only", so the most explicit species statement a surface can make was
    dropped for want of one word."""
    extraction, _withheld, _flags, _reading = read(
        "Dogs and cats allowed. Pet fee 30 USD per night.")
    assert extraction["species_allowed"] == ["cat", "dog"]


def test_cats_and_dogs_only_is_still_exclusive():
    extraction, _withheld, _flags, reading = read(
        "Cats and dogs only. Maximum 2 pets per room.")
    assert extraction["species_allowed"] == ["cat", "dog"]
    assert reading.species_exclusive is True


def test_no_cats_remains_an_explicit_exclusion():
    extraction, _withheld, _flags, _reading = read(
        "Pets are welcome. No cats. $50 per stay.")
    assert extraction["cats_allowed"] is False


def test_dogs_allowed_cats_not_allowed_keeps_both_halves():
    extraction, _withheld, _flags, _reading = read(
        "Dogs allowed, cats not allowed. $40 per night.")
    assert extraction["species_allowed"] == ["dog"]
    assert extraction["cats_allowed"] is False


def test_a_two_species_refusal_never_reads_as_a_two_species_acceptance():
    """"Dogs and cats are not allowed" puts the negation where the verb has to
    be, so the acceptance pattern cannot match it."""
    extraction, _withheld, _flags, _reading = read("Dogs and cats are not allowed.")
    assert "species_allowed" not in extraction
    assert extraction.get("cats_allowed") is False


def test_a_generic_pets_welcome_still_names_no_species():
    extraction, _withheld, _flags, _reading = read("Pets are welcome. $50 per stay.")
    assert "species_allowed" not in extraction


# --------------------------------------------------------------------------- #
# 5-7. fee patterns
# --------------------------------------------------------------------------- #

def test_a_basis_first_label_with_the_amount_after_it_parses():
    """Pattern A. Every other charge pattern reads the amount first and looks
    rightwards, so this order read as no charge at all."""
    extraction, _withheld, _flags, _reading = read("Pet fee per night: 75 USD")
    assert extraction["pet_fee"] == 7500
    assert extraction["fee_currency"] == "USD"
    assert extraction["fee_basis"] == "per_night"


def test_a_basis_first_label_in_dollars_parses_too():
    extraction, _withheld, _flags, _reading = read("Pet charge per stay: $50")
    assert extraction["pet_fee"] == 5000
    assert extraction["fee_basis"] == "per_stay"


def test_a_basis_first_label_without_a_pet_word_is_a_room_rate():
    """"Rate per night: 189 USD" is the same shape. The pet word is required
    in the label, or this pattern reads a room rate as a pet fee."""
    extraction, _withheld, _flags, _reading = read(
        "Fitness centre and free parking. Rate per night: 189 USD")
    assert "pet_fee" not in extraction


def test_a_slash_species_fee_parses_with_a_per_pet_scope():
    """Pattern B."""
    extraction, _withheld, _flags, _reading = read("Pets welcome. $25/dog per night")
    assert extraction["pet_fee"] == 2500
    assert extraction["fee_basis"] == "per_night"
    assert extraction["fee_scope"] == "per_pet"


def test_a_per_species_per_night_fee_parses_with_a_per_pet_scope():
    """Pattern C. The amount and basis were already read; the SCOPE was lost,
    so a two-dog stay silently became a one-charge stay."""
    extraction, _withheld, _flags, _reading = read("Pets welcome. $25 per dog per night")
    assert extraction["pet_fee"] == 2500
    assert extraction["fee_basis"] == "per_night"
    assert extraction["fee_scope"] == "per_pet"


def test_a_named_species_is_a_scope_only_inside_a_charge():
    """"2 dogs per room" is a COUNT with a room scope. Adding dog to the charge
    scope vocabulary must not have reached the count vocabulary."""
    extraction, _withheld, _flags, _reading = read(
        "Pets welcome. A maximum of two (2) dogs per room.")
    assert extraction["pet_count_limit"] == 2
    assert extraction["pet_count_scope"] == "per_room"


def test_a_species_scope_without_a_basis_states_no_fee():
    """"$25 per dog" alone states no basis, and a basis is never guessed."""
    extraction, withheld, _flags, _reading = read("Pets welcome. $25 per dog.")
    assert extraction.get("fee_basis") is None
    assert "fee_basis" not in extraction or withheld


# --------------------------------------------------------------------------- #
# 8-11. safeguards preserved
# --------------------------------------------------------------------------- #

def test_a_room_rate_beside_pet_wording_is_still_not_a_pet_fee():
    extraction, _withheld, _flags, _reading = read(
        "This pet-friendly motel welcomes your furry friends. "
        "Best rate from $89 /night. Book now.")
    assert "pet_fee" not in extraction


def test_an_incidentals_deposit_is_still_not_a_pet_deposit():
    extraction, _withheld, _flags, _reading = read(
        "Read Full Pet Policy Deposit Policy: A $50 refundable deposit for "
        "incidentals is required at check-in for all guests.")
    assert "pet_deposit" not in extraction


def test_a_security_deposit_required_of_all_guests_is_not_a_pet_deposit():
    extraction, _withheld, _flags, _reading = read(
        "Pet Policy: pets welcome. A $200 security deposit is required of "
        "all guests at check-in.")
    assert "pet_deposit" not in extraction


def test_a_pet_security_deposit_is_still_a_pet_deposit():
    """Nearest wins: the pet word is adjacent to the amount and takes the tie,
    so the guard costs a genuine pet security deposit nothing."""
    extraction, _withheld, _flags, _reading = read(
        "Pet Policy: a refundable pet security deposit of 100 USD is required.")
    assert extraction["pet_deposit"] == 10000


def test_a_capped_fee_still_separates_the_ceiling_from_the_price():
    extraction, _withheld, _flags, _reading = read(
        "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay.")
    assert extraction["pet_fee"] == 2500
    assert extraction["fee_cap"]["amount_minor"] == 7500


def test_a_stay_length_tiered_fee_is_still_withheld():
    extraction, withheld, _flags, _reading = read(
        "Pet Charge 50.00 USD Per Stay for stays 1-6 nights. For stays of 7 "
        "or more nights the fee is 150.00 USD per stay.")
    assert "pet_fee" not in extraction
    # 034 carries this ladder in fee_tiers. What 017 pinned -- that no single
    # amount is published for a surface that prices by stay length -- is
    # asserted directly, and holds under either answer.
    assert (withheld.get("pet_fee") == enums.SCHEMA_CANNOT_REPRESENT
            or extraction.get("fee_tiers"))


def test_a_free_first_pet_makes_the_surface_tiered():
    """A stated FREE is a price. Counting only the numbers saw one price and
    published $15 as the fee for a pet this hotel takes for nothing."""
    extraction, withheld, flags, _reading = read(
        "One pet stays free. Second pet $15 per night.")
    assert "pet_fee" not in extraction
    assert withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "FLAG_TIERED_FEE" in flags


def test_a_single_priced_policy_is_not_made_tiered_by_the_word_free():
    """"free" with no second price and no tier qualifier is not a tier: the
    free-tier rule adds a price, it does not add a qualifier."""
    extraction, _withheld, _flags, _reading = read(
        "Pets welcome. Wi-Fi is free of charge. Pet fee $30 per night.")
    assert extraction["pet_fee"] == 3000


# --------------------------------------------------------------------------- #
# 12-15. nothing outside the parser moved
# --------------------------------------------------------------------------- #

BASELINE_COMMIT = "35dfac2"

FROZEN = (
    "scripts/pettripfinder/acquisition/routes.json",
    "scripts/pettripfinder/acquisition/providers.py",
    "scripts/pettripfinder/acquisition/registry.py",
    "scripts/pettripfinder/acquisition/router.py",
    "scripts/pettripfinder/acquisition/failures.py",
    "scripts/pettripfinder/acquisition/source_discovery.py",
    "scripts/pettripfinder/acquisition/source_selection.py",
    "launch_packages/pettripfinder/markets/discovered_policy_urls/milwaukee-wi.json",
)


def _git_prefix():
    out = subprocess.run(["git", "rev-parse", "--show-prefix"], cwd=REPO,
                         capture_output=True, check=True).stdout
    return out.decode("utf-8").strip()


def _oid_at(commit, path):
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--verify", "-q",
             "%s:%s%s" % (commit, _git_prefix(), path)],
            cwd=REPO, capture_output=True, check=True).stdout
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _oid_now(path):
    out = subprocess.run(["git", "hash-object", path], cwd=REPO,
                         capture_output=True, check=True).stdout
    return out.decode("utf-8").strip()


def test_routing_and_source_discovery_are_untouched():
    """Compared by git BLOB OID, not by a hash of the bytes on disk: this
    repository normalises line endings and a raw sha256 disagrees with the
    blob for files that never changed."""
    missing = []
    for path in FROZEN:
        before = _oid_at(BASELINE_COMMIT, path)
        if before is None:
            missing.append(path)
            continue
        assert before == _oid_now(path), path
    assert not missing, "could not read from git: %s" % missing


def test_the_registry_still_routes_every_brand_where_016_left_it():
    expected = {"CHOICE": "firecrawl", "WYNDHAM": "firecrawl",
                "IHG": "firecrawl", "MOTEL6": "brightdata_browser",
                "RED_ROOF": "brightdata_browser"}
    for brand, provider in expected.items():
        route = REGISTRY.resolve(brand=brand, url="https://example.test/")
        assert route.provider == provider, brand


def test_no_milwaukee_policy_authority_exists():
    # NARROWED. This claimed "parser semantics 017 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("1537625")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()


def test_the_committed_differential_records_no_publication():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert doc["authority_written"] is False
    assert doc["published"] is False


def test_the_committed_differential_still_matches_the_installed_reader():
    """A report is a claim about the code; a stale claim is worse than none."""
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for row in doc["cases"]:
        extraction, withheld, _flags, _reading = read(row["text"])
        if extraction.get("fee_tiers") or extraction.get("fee_pet_schedule"):
            # 034 added a structure this differential had no field for. Every
            # fact it DID record must still be present and identical, and the
            # fee must still not be a single amount.
            for key, value in row["new_extraction"].items():
                assert extraction.get(key) == value, (row["case_id"], key)
            assert "pet_fee" not in extraction, row["case_id"]
            continue
        assert extraction == row["new_extraction"], row["case_id"]
        assert withheld == row["new_withheld"], row["case_id"]


def test_no_property_name_appears_in_the_reader():
    source = Path(PR.__file__).read_text(encoding="utf-8")
    for name in ("Pfister", "Ingleside", "Wildwood", "Knickerbocker",
                 "Saint Kate", "Plaza Hotel", "Iron Horse"):
        assert name not in source, name
