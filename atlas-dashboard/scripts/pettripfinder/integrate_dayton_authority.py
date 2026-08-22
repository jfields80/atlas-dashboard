"""PTF-DAYTON-INTEGRATION-AND-CANDIDATE-BUILD-001 -- Dayton evidence into authority.

Turns the ``dayton-capture-run-001`` capture package into committed authority:
inventory rows, per-market policy facts, and verified-no-pets exclusions. The
captures are not re-run; the stored artifacts are the input, and every quote
below is asserted to be a literal substring of the capture that carries it.

WHY THIS MODULE EXISTS RATHER THAN A DIRECT MERGE OF THE WORKER BRANCH
---------------------------------------------------------------------
The worker emitted 44 records in a private dialect. None of them validated
against the frozen ``ptf-policy-observation/1.0`` contract:

  * 39 declared ``capture_method: "automated_browser"``, which is not in the
    contract's closed vocabulary (the value is ``browser_assisted``);
  * 26 carried no ``extraction`` at all -- their policy fields lived inside
    ``evidence[]`` entries alongside ``policy_verdict`` and ``text_excerpt``,
    keys the contract's ``additionalProperties: false`` rejects;
  * every flag used was outside the closed ``FLAG_CODES`` set, and several
    were dicts rather than strings.

So the worker's "38 proposed pet-friendly candidates" had never been seen by
the membrane. This module is the translation, and it is deliberately a
hand-reviewed table rather than a mechanical re-shaping, because three of the
worker's transcriptions were lossy in a way only a substring check catches:

  * Hampton Springfield's quote read "5.00 Non-refundable Fee" where the
    capture says "$75.00 Non-refundable Fee";
  * Courtyard Springfield Downtown's read "Per Stay: 5.00" and "(7.94)" where
    the capture says "$75.00" and "($87.94)";
  * Home2 Beavercreek's appended an editorial "[ly]" to a page that genuinely
    truncates at "dog/cat on".

The values were mostly right; the words backing them were not. Here the quote
is copied from the artifact, and ``build()`` refuses any fact whose quote is
not found in the capture -- so a lossy transcription fails loudly instead of
publishing a number nobody can point at.

WHAT IS DELIBERATELY WITHHELD, AND WHY
--------------------------------------
A withheld field is a decision that has to survive review, so each one is
recorded with its reason:

  * FEE SCOPE. Hilton and Marriott state an amount without saying whether it
    is charged per pet or per room. Hampton Troy is the one property whose page
    says "per pet" in as many words, and that scope stays on Hampton Troy --
    it is not generalized to the other Hamptons in this market.
  * CONTRADICTORY FEES. SpringHill Troy shows a $125.00 per-stay field beside
    a $75/$150/$250 stay-length ladder that no reading reconciles; TownePlace
    Beavercreek shows "$100.00 per stay" beside "$20.00 per night". Neither
    property publishes a fee at all. The conflicting text is preserved verbatim
    so a reviewer sees exactly what the page said.
  * ADDITIVE FEES. Hilton Garden Inn Beavercreek says "$75(1-5 nights)
    additional $75(5+ night)". "Additional" is not a replacement band, and this
    module does not compute the $150 total the worker inferred -- the sentence
    is published verbatim and the ladder is withheld.
  * SPECIES. "pets" alone is never read as dogs+cats. Xenia's page renders
    "dog/only" and Home2 Beavercreek's truncates at "dog/cat on"; both withhold
    species rather than complete the word.
  * FEE CAPS. La Quinta states a nightly rate AND a per-stay ceiling. Both are
    published, distinctly -- ``fee_cap`` is a ceiling, not a rate.

Run:  python -m scripts.pettripfinder.integrate_dayton_authority [--apply]
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                    # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD          # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MB              # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO           # noqa: E402
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name  # noqa: E402
from scripts.pettripfinder.contracts import enums          # noqa: E402

MARKET = "dayton-oh"
AS_OF = "2026-08-10"
REVIEWER = "jfields80"
CAPTURE_RUN = "dayton-capture-run-001"

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
               / "identity_census" / ("%s.json" % MARKET))
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / CAPTURE_RUN)
BATCH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "discovery"
         / "review_batches" / "dayton-market-factory-001")
OBSERVATIONS = BATCH / "observations" / "policy_observations.json"
FACTS_OUT = (_REPO_ROOT / "launch_packages" / "pettripfinder"
             / ("hotel_policy_facts_%s.json" % MARKET))

CATEGORY = "pet-friendly-hotels"


# --------------------------------------------------------------------------- #
# Stay-length ladders.
#
# The bands REPLACE one another -- a guest pays exactly one of them -- which is
# why ``additive`` is absent and why Hilton Garden Inn Beavercreek, whose page
# says "additional", gets no ladder at all.
#
# ``basis_stated`` is not cosmetic. Hilton's brands print only the bands and
# never say whether the amount is per stay or per night; Home2 Dayton South's
# page says "(Fee is per stay, not per night)" in as many words. Marking the
# silent ones as stating a basis would publish a claim the page does not make.
# --------------------------------------------------------------------------- #

def _ladder(bands, *, basis_stated: bool, scope: str = "unstated"):
    common = {"currency": "USD", "condition_type": "stay_length_range",
              "boundary_unit": "nights", "role": "ONE_TIME_CHARGE",
              "scope": scope, "source_type": "", "source_url": "",
              "basis_stated": basis_stated}
    stated = {"stated_basis": "per stay"} if basis_stated else {}
    return [dict(common, amount=amount, condition_min=lo, condition_max=hi,
                 **stated)
            for amount, lo, hi in bands]


TIERS = {
    # Hilton brands: bands only, no basis stated anywhere on the page.
    "STAY_75_125": _ladder([("75.00", 1, 4), ("125.00", 5, None)],
                           basis_stated=False),
    "STAY_50_75": _ladder([("50.00", 1, 4), ("75.00", 5, None)],
                          basis_stated=False),
    # Home2 Dayton South: same shape, but the page states the basis.
    "STAY_75_125_PER_STAY": _ladder([("75.00", 1, 4), ("125.00", 5, None)],
                                    basis_stated=True),
    # Hampton Troy: the one page in this market that says "per pet".
    "STAY_75_125_PER_PET": _ladder([("75.00", 1, 4), ("125.00", 5, None)],
                                   basis_stated=False, scope="per pet"),
}

#: Stated ceilings. A cap is a different promise from a rate, so it carries its
#: own amount and basis and is never folded into ``pet_fee``.
CAPS = {
    "CAP_75_PER_STAY": {"amount": "75.00", "currency": "USD",
                        "basis": "per stay"},
}

SCOPE_UNSTATED = ("the page states an amount without saying whether it is "
                  "charged per pet or per room")
SPECIES_UNSTATED = "the page names no species, and \"pets\" alone is not dogs+cats"
BASIS_UNSTATED = ("the page states an amount with no per-night or per-stay "
                  "qualifier")

#: hotel slug -> reviewed facts. Each fact is (published value, the exact quote
#: from that property's captured page that supports it).
FACTS: Dict[str, Dict] = {

    # ---- Drury: the fullest page in the market; nothing is withheld ------- #
    "drury-inn-suites-dayton-north": {
        "facts": {
            "pets_allowed": ("true", "Dogs and cats accepted."),
            "species_allowed": ("dogs, cats", "Dogs and cats accepted."),
            "cats_allowed": ("true", "Dogs and cats accepted."),
            "pet_fee": ("$50.00", "Rooms with pets will be charged a daily fee of $50 per room plus tax."),
            "fee_basis": ("per night", "Rooms with pets will be charged a daily fee of $50 per room plus tax."),
            "fee_scope": ("per room", "Rooms with pets will be charged a daily fee of $50 per room plus tax."),
            "pet_count_limit": ("2", "Limit of two pets per room with a combined weight of 80 pounds."),
            "pet_count_scope": ("room", "Limit of two pets per room with a combined weight of 80 pounds."),
            "weight_limit_combined": ("80 pounds", "Limit of two pets per room with a combined weight of 80 pounds."),
            "weight_limit_combined_operator": ("combined", "Limit of two pets per room with a combined weight of 80 pounds."),
            "service_animal_exception": ("true", "Service animals are free of charge."),
        },
        "withheld": {},
    },

    "ac-hotel-dayton": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$50.00", "Non-Refundable Pet Fee Per Night: $50.00"),
            "fee_basis": ("per night", "Non-Refundable Pet Fee Per Night: $50.00"),
            "fee_scope": ("per pet", "USD 50 nightly fee per pet- no aggressive breeds"),
            "weight_limit": ("25 pounds", "Maximum Pet Weight: 25.0lbs"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
            "breed_restrictions": ("no aggressive breeds", "USD 50 nightly fee per pet- no aggressive breeds"),
        },
        "withheld": {"species_allowed": SPECIES_UNSTATED},
    },

    "doubletree-by-hilton-dayton-fairborn": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED,
                     "pet_count_limit": "the page states no pet count"},
    },

    "holiday-inn-express-and-suites-dayton-centerville": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed: Only dogs allowed"),
            "species_allowed": ("dogs", "Pets allowed: Only dogs allowed"),
            "pet_fee": ("$100.00", "There is a 100 dollar DOG PET FEE, excluding an ADA compliant Service Dog."),
            "service_animal_exception": ("true", "There is a 100 dollar DOG PET FEE, excluding an ADA compliant Service Dog."),
        },
        "withheld": {"fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
                     "cats_allowed": "the page says dogs only, which is a "
                                     "species statement, not a cat refusal to publish"},
    },

    "hampton-inn-and-suites-dayton-vandalia": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "cats_allowed": ("true", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_fee": ("$50.00", "Deposit Yes. $50.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_50_75", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_count_limit": ("2", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED},
    },

    "courtyard-by-marriott-dayton-north": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED,
                     "pet_count_limit": "the page states no pet count"},
    },

    "hampton-inn-by-hilton-dayton-south": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            "cats_allowed": ("true", "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_75_125", "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            "pet_count_limit": ("2", "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED},
    },

    "days-inn-by-wyndham-sidney": {
        "facts": {
            "pets_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only."),
            "species_allowed": ("dogs, cats", "Pets Allowed - 2 pets max. Cats and dogs only."),
            "cats_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only."),
            "pet_count_limit": ("2", "Pets Allowed - 2 pets max. Cats and dogs only."),
            "pet_fee": ("$15.00", "Fees - Non-refundable 15 USD nightly per pet."),
            "fee_basis": ("per night", "Fees - Non-refundable 15 USD nightly per pet."),
            "fee_scope": ("per pet", "Fees - Non-refundable 15 USD nightly per pet."),
            "unattended_policy": ("not permitted", "Other Information - Pets cannot be left unattended in room."),
        },
        # The worker's extraction claimed a service-animal exception; the quote
        # it stored does not contain one, and neither does the captured block.
        "withheld": {"service_animal_exception":
                     "the captured policy block states no service-animal terms"},
    },

    "hampton-inn-dayton-huber-heights": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "$75.00(1-4n), $125.00(5+n) 2pets Max, dogs/cats only"),
            "cats_allowed": ("true", "$75.00(1-4n), $125.00(5+n) 2pets Max, dogs/cats only"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_75_125", "$75.00(1-4n), $125.00(5+n) 2pets Max, dogs/cats only"),
            "pet_count_limit": ("2", "$75.00(1-4n), $125.00(5+n) 2pets Max, dogs/cats only"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED},
    },

    # Quote re-derived from the capture: the worker stored "5.00" for "$75.00".
    "hampton-inn-springfield": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "1-4 night stay $75 5+ night stay $125 2 pets max dog/cat only"),
            "cats_allowed": ("true", "1-4 night stay $75 5+ night stay $125 2 pets max dog/cat only"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_75_125", "1-4 night stay $75 5+ night stay $125 2 pets max dog/cat only"),
            "pet_count_limit": ("2", "1-4 night stay $75 5+ night stay $125 2 pets max dog/cat only"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED},
    },

    # Quote re-derived: the worker stored "Per Stay: 5.00" and "(7.94)".
    "courtyard-by-marriott-springfield-downtown": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$75.00", "Non-Refundable Pet Fee Per Stay: $75.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $75.00"),
            "pet_count_limit": ("3", "Maximum Number of Pets in Room: 3"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 3"),
            "general_restrictions": (
                "Pets allowed with USD 75 + 17.25% tax, non-refundable fee per stay ($87.94)",
                "Pets allowed with USD 75 + 17.25% tax, non-refundable fee per stay ($87.94)"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED},
    },

    "hampton-inn-suites-sidney": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs", "$75(1-4n),$125(5+n) 2pets Max,dogs only"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_75_125", "$75(1-4n),$125(5+n) 2pets Max,dogs only"),
            "pet_count_limit": ("2", "$75(1-4n),$125(5+n) 2pets Max,dogs only"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED,
                     "weight_limit": "the page states no weight limit",
                     "cats_allowed": "the page says dogs only, which is a "
                                     "species statement, not a cat refusal to publish"},
    },

    "la-quinta-inn-suites-by-wyndham-fairborn-wright-patterson": {
        "facts": {
            "pets_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "species_allowed": ("dogs, cats", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "cats_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "pet_count_limit": ("2", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "weight_limit": ("75 pounds", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "pet_fee": ("$25.00", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            "fee_basis": ("per night", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            # A ceiling, not a rate. Kept distinct from pet_fee on purpose.
            "fee_cap": ("CAP_75_PER_STAY", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            "service_animal_exception": ("true", "Service Animals - ADA-defined service animals are welcome free of charge."),
        },
        "withheld": {"fee_scope": "the nightly rate covers \"up to 2 pets\", "
                                  "which is neither a per-pet nor a per-room "
                                  "statement in the vocabulary we publish",
                     "weight_limit_operator":
                         "the page scopes the weight \"per pet\", and the "
                         "published operator vocabulary is {lt, lte, combined}; "
                         "a non-member renders as nothing, so the plain limit "
                         "is published and the scoping is withheld"},
    },

    "hampton-inn-suites-xenia-dayton": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_75_125", "$75(1-4n),$125(5+n)2petsMax,dog/only"),
            "pet_count_limit": ("2", "$75(1-4n),$125(5+n)2petsMax,dog/only"),
            "weight_limit": ("35 pounds", "Max weight 35 lbs"),
        },
        # The page renders "dog/only". Its sibling Hamptons render "dog/cat
        # only" and "dogs only" -- two different meanings -- so the word is not
        # completed here.
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED,
                     "species_allowed": "the page renders \"dog/only\", which "
                                        "is neither \"dogs only\" nor \"dog/cat "
                                        "only\" and is not completed by us"},
    },

    "fairfield-inn-and-suites-dayton-north": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$50.00", "Pets Allowed $50 non-refundable fee per night"),
            "fee_basis": ("per night", "Pets Allowed $50 non-refundable fee per night"),
            "weight_limit": ("40 pounds", "Maximum Pet Weight: 40.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED},
    },

    "la-quinta-inn-suites-by-wyndham-miamisburg-dayton-south": {
        "facts": {
            "pets_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "species_allowed": ("dogs, cats", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "cats_allowed": ("true", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "pet_count_limit": ("2", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "weight_limit": ("75 pounds", "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per pet."),
            "pet_fee": ("$25.00", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            "fee_basis": ("per night", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            "fee_cap": ("CAP_75_PER_STAY", "Fees - Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay."),
            "service_animal_exception": ("true", "Service Animals - ADA-defined service animals are welcome free of charge."),
        },
        "withheld": {"fee_scope": "the nightly rate covers \"up to 2 pets\", "
                                  "which is neither a per-pet nor a per-room "
                                  "statement in the vocabulary we publish",
                     "weight_limit_operator":
                         "the page scopes the weight \"per pet\", and the "
                         "published operator vocabulary is {lt, lte, combined}; "
                         "a non-member renders as nothing, so the plain limit "
                         "is published and the scoping is withheld"},
    },

    # The ONE property in this market whose page states a per-pet scope. That
    # scope stays here and is not generalized to the other Hamptons.
    "hampton-inn-troy": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs", "$75 (1-4 nights) per pet, $125 (5+ nights) per pet, 2 pets Max, dogs only"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "fee_scope": ("per pet", "$75 (1-4 nights) per pet, $125 (5+ nights) per pet, 2 pets Max, dogs only"),
            "fee_tiers": ("STAY_75_125_PER_PET", "$75 (1-4 nights) per pet, $125 (5+ nights) per pet, 2 pets Max, dogs only"),
            "pet_count_limit": ("2", "$75 (1-4 nights) per pet, $125 (5+ nights) per pet, 2 pets Max, dogs only"),
        },
        "withheld": {"fee_basis": BASIS_UNSTATED,
                     "weight_limit": "the page states no weight limit",
                     "cats_allowed": "the page says dogs only, which is a "
                                     "species statement, not a cat refusal to publish"},
    },

    "fairfield-inn-and-suites-dayton-south": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "$100 USD Non-Refundable Pet Fee Per StayDogs only"),
            "pet_fee": ("$100.00", "$100 USD Non-Refundable Pet Fee Per StayDogs only"),
            "fee_basis": ("per stay", "$100 USD Non-Refundable Pet Fee Per StayDogs only"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "cats_allowed": "the page says dogs only, which is a "
                                     "species statement, not a cat refusal to publish"},
    },

    # ADDITIVE, not a replacement ladder. No total is computed here.
    "hilton-garden-inn-dayton-beavercreek": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room."),
            "cats_allowed": ("true", "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room."),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
            "pet_count_limit": ("2", "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room."),
            "pet_count_scope": ("room", "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room."),
            "general_restrictions": (
                "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room.",
                "$75(1-5 nights) additional $75(5+ night) dogs & cats only. Two pets max per room."),
        },
        "withheld": {
            "fee_tiers": "the page says \"additional\", which is an add-on and "
                         "not a replacement band; publishing a ladder here would "
                         "assert a $150 total the page never states",
            "fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
        },
    },

    # Quote re-derived: the worker appended an editorial "[ly]" to a page that
    # genuinely truncates at "dog/cat on".
    "home2-suites-by-hilton-dayton-beavercreek": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "pet_count_limit": ("2", "75.00(1-4n),$125(5+n) 2petsMax,dog/cat on"),
            "general_restrictions": ("75.00(1-4n),$125(5+n) 2petsMax,dog/cat on",
                                     "75.00(1-4n),$125(5+n) 2petsMax,dog/cat on"),
        },
        "withheld": {
            "species_allowed": "the page's own text truncates at \"dog/cat on\" "
                               "and the missing word is not supplied by us",
            "fee_tiers": "the first band renders without its currency marker "
                         "on a line the page itself truncates",
            "fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
        },
    },

    # The widget says $125.00; the prose says $75 for 1-4 nights AND states the
    # basis outright. The property's own sentence wins over the widget, exactly
    # as it did on the Cleveland IHG pages.
    "home2-suites-by-hilton-dayton-south": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "(Fee is per stay, not per night) $75(1-4 nights), $125(5+ nights)"),
            "fee_basis": ("per stay", "(Fee is per stay, not per night) $75(1-4 nights), $125(5+ nights)"),
            "fee_tiers": ("STAY_75_125_PER_STAY", "(Fee is per stay, not per night) $75(1-4 nights), $125(5+ nights)"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED,
                     "pet_count_limit": "the page states no pet count",
                     "pet_deposit": "the $125.00 \"Deposit\" field contradicts "
                                    "the property's own sentence and is not "
                                    "published as either a fee or a deposit"},
    },

    "staybridge-suites-miamisburg": {
        "facts": {
            "pets_allowed": ("true", "Guests will be charged 50 per pet for one to six night stays and 150 per pet for seven plus nights."),
            "pet_fee": ("$50.00", "Guests will be charged 50 per pet for one to six night stays and 150 per pet for seven plus nights."),
            "fee_scope": ("per pet", "Guests will be charged 50 per pet for one to six night stays and 150 per pet for seven plus nights."),
            "general_restrictions": (
                "Fee is nonrefundable. Guests will be charged 50 per pet for one to six night stays and 150 per pet for seven plus nights.",
                "Fee is nonrefundable. Guests will be charged 50 per pet for one to six night stays and 150 per pet for seven plus nights."),
        },
        "withheld": {
            # IHG's own words: a "deposit" it then calls nonrefundable.
            "pet_deposit": "the page labels the charge a deposit and then says "
                           "\"Fee is nonrefundable\"; it is published as a fee, "
                           "never as a refundable deposit",
            "fee_tiers": "the bands are 1-6 and 7+ nights, which is not the "
                         "1-4/5+ shape any published ladder in this repository "
                         "carries; the sentence is published verbatim instead",
            "fee_basis": BASIS_UNSTATED,
            "species_allowed": SPECIES_UNSTATED,
            "pet_count_limit": "the page states no pet count",
        },
    },

    "residence-inn-by-marriott-dayton-beavercreek": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs, cats", "Dogs & Cats allowed with USD $100 non-refundable fee per stay"),
            "cats_allowed": ("true", "Dogs & Cats allowed with USD $100 non-refundable fee per stay"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED},
    },

    "home2-suites-by-hilton-dayton-vandalia": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "cats_allowed": ("true", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_fee": ("$50.00", "Deposit Yes. $50.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_50_75", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_count_limit": ("2", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED,
                     "weight_limit": "the page states no weight limit"},
    },

    "residence-inn-by-marriott-dayton-miamisburg": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$75.00", "Non-Refundable Pet Fee Per Stay: $75.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $75.00"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED},
    },

    "residence-inn-by-marriott-dayton-troy": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED,
                     "weight_limit": "the page states no weight limit"},
    },

    "homewood-suites-by-hilton-south-dayton-miamisburg": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "75.00 non-refundable pet fee max 2 pets 19--4 night stay 125.00 non-refundable pet fee 5+ nights stay"),
            "pet_count_limit": ("2", "75.00 non-refundable pet fee max 2 pets 19--4 night stay 125.00 non-refundable pet fee 5+ nights stay"),
            "weight_limit": ("80 pounds", "Max weight 80 lbs"),
        },
        "withheld": {
            "fee_tiers": "the page renders the first band's boundary as "
                         "\"19--4 night stay\"; a ladder built on a garbled "
                         "boundary would publish a band nobody can read",
            "fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
            "species_allowed": SPECIES_UNSTATED,
            "pet_deposit": "the $125.00 \"Deposit\" field disagrees with the "
                           "property's own fee sentence and is not published",
        },
    },

    "residence-inn-by-marriott-dayton-vandalia": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$150.00", "Non-Refundable Pet Fee Per Stay: $150.00"),
            "fee_basis": ("per stay", "1 pet 50 pounds max per room with USD 150 non-refundable fee per room per stay"),
            "fee_scope": ("per room", "1 pet 50 pounds max per room with USD 150 non-refundable fee per room per stay"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
        },
        "withheld": {"species_allowed": SPECIES_UNSTATED},
    },

    "spark-by-hilton-dayton-fairborn": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "pet_fee": ("$75.00", "Deposit Yes. $75.00 Non-refundable Fee"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_basis": BASIS_UNSTATED, "fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED,
                     "pet_count_limit": "the page carries no \"Other pet "
                                        "information\" row at all"},
    },

    "tru-by-hilton-beavercreek-dayton": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed Yes"),
            "species_allowed": ("dogs, cats", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "cats_allowed": ("true", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_fee": ("$50.00", "Deposit Yes. $50.00 Non-refundable Fee"),
            "fee_tiers": ("STAY_50_75", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "pet_count_limit": ("2", "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            "weight_limit": ("75 pounds", "Max weight 75 lbs"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED, "fee_basis": BASIS_UNSTATED},
    },

    # CONTRADICTION PRESERVED: a $125.00 per-stay field beside a
    # $75/$150/$250 ladder that no reading reconciles. No fee publishes.
    "springhill-suites-troy-dayton": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "Dogs only, no cats. 1-7 Nights - $75, 8-14 Nights - $150, 15+ Nights - $250"),
            "cats_allowed": ("false", "Dogs only, no cats. 1-7 Nights - $75, 8-14 Nights - $150, 15+ Nights - $250"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
            "general_restrictions": (
                "Dogs only, no cats. 1-7 Nights - $75, 8-14 Nights - $150, 15+ Nights - $250",
                "Dogs only, no cats. 1-7 Nights - $75, 8-14 Nights - $150, 15+ Nights - $250"),
        },
        "withheld": {
            "pet_fee": "the page shows \"Non-Refundable Pet Fee Per Stay: "
                       "$125.00\" beside a $75/$150/$250 stay-length ladder "
                       "that contains no $125 band; the conflict is preserved "
                       "rather than resolved by us",
            "fee_basis": "withheld with the fee it would describe",
            "fee_scope": SCOPE_UNSTATED,
            "fee_tiers": "the ladder is published as the property's own "
                         "sentence, not as a priced ladder, while the $125 "
                         "field contradicts it",
        },
    },

    # DUAL REPRESENTATION: "$100.00 per stay" and "$20.00 per night" side by
    # side. Choosing either would be an inference, so neither publishes.
    "towneplace-suites-by-marriott-dayton-beavercreek": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "weight_limit": ("75 pounds", "Maximum Pet Weight: 75.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
            "general_restrictions": (
                "Non-Refundable Pet Fee Per Stay: $100.00 Non-Refundable Pet Fee Per Night: $20.00",
                "Non-Refundable Pet Fee Per Stay: $100.00 Non-Refundable Pet Fee Per Night: $20.00"),
        },
        "withheld": {
            "pet_fee": "the page lists a $100.00 per-stay fee and a $20.00 "
                       "per-night fee as separate rows; they are not two "
                       "spellings of one number unless the stay is exactly "
                       "five nights, and we do not pick one",
            "fee_basis": "the same two rows state both bases at once",
            "fee_scope": SCOPE_UNSTATED,
            "species_allowed": SPECIES_UNSTATED,
            "weight_limit_operator":
                "the page scopes the weight \"per pet per room\"; the published "
                "operator vocabulary is {lt, lte, combined} and a non-member "
                "renders as nothing, so the plain limit is published alone",
        },
    },

    "towneplace-suites-by-marriott-dayton-north": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$50.00", "Non-Refundable Pet Fee Per Stay: $50.00"),
            "fee_basis": ("per stay", "2 pets 60 pounds or less allowed with USD 50 per stay non-refundable fee"),
            "weight_limit": ("60 pounds", "Maximum Pet Weight: 60.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"fee_scope": SCOPE_UNSTATED,
                     "species_allowed": SPECIES_UNSTATED},
    },
}


#: Affirmative refusals. The quote is the property's own words, and each must
#: be found in that property's capture exactly like any published fact.
NO_PETS: Dict[str, str] = {
    "courtyard-by-marriott-dayton-beavercreek": "Pet Policy Pets Not Allowed",
    "courtyard-by-marriott-dayton-south": "Pet Policy Pets Not Allowed",
    "courtyard-by-marriott-dayton-university-of-dayton":
        "Pet Policy Pets Not Allowed No pets allowed-service animals only",
    "fairfield-inn-and-suites-dayton-downtown": "Pet Policy Pets Not Allowed",
    "marriott-at-the-university-of-dayton": "Pet Policy Pets Not Allowed",
    "springhill-suites-by-marriott-dayton-beavercreek": "Pet Policy Pets Not Allowed",
}

NO_PETS_NOTE = ("affirmative refusal on the property's own page; service-animal "
                "language is a legal access category and is never read as a pet "
                "permission or as a refusal on its own")

#: Hotels the worker proposed that this integration deliberately does NOT
#: publish, each with the exact next action that would unblock it.
HELD: Dict[str, Dict[str, str]] = {
    "americas-best-value-inn-suites-st-marys": {
        "reason": "PARAPHRASE_NO_CAPTURE",
        "detail": "the observation is a research-agent summary; no capture "
                  "artifact exists for this property in dayton-capture-run-001",
        "next_action": "attended capture of sonesta.com/americas-best-value-inn"
                       "/oh/st-marys/... -- no PTF adapter exists for Sonesta",
    },
    "americas-best-value-inn-celina": {
        "reason": "PARAPHRASE_NO_CAPTURE",
        "detail": "the observation is a research-agent summary; no capture "
                  "artifact exists for this property in dayton-capture-run-001",
        "next_action": "attended capture of sonesta.com/americas-best-value-inn"
                       "/oh/celina/... -- no PTF adapter exists for Sonesta",
    },
    "cobblestone-hotel-suites-bellefontaine": {
        "reason": "PARAPHRASE_NO_CAPTURE",
        "detail": "the observation is a research-agent summary at PT2 (brand "
                  "level), and no capture artifact exists for this property",
        "next_action": "attended capture of staycobblestone.com/oh/bellefontaine/"
                       " -- no PTF adapter exists for Cobblestone (Synxis 7721)",
    },
    "cobblestone-hotel-suites-indian-lake-russells-point": {
        "reason": "PARAPHRASE_NO_CAPTURE",
        "detail": "the observation is a research-agent summary at PT2 (brand "
                  "level), and no capture artifact exists for this property",
        "next_action": "attended capture of staycobblestone.com/oh/indian-lake/"
                       " -- no PTF adapter exists for Cobblestone (Synxis 7721)",
    },
    "springhill-suites-by-marriott-dayton-vandalia": {
        "reason": "IDENTITY_PROVISIONAL",
        "detail": "the census carries no phone for this property, leaving one "
                  "independent identity group; the capture additionally shows "
                  "\"$50.00 Per Stay Non-Refundable\" beside \"Non-Refundable "
                  "Pet Fee Per Stay: $75.00\"",
        "next_action": "confirm a second independent identity key (phone or "
                       "address on page), then re-adjudicate the fee conflict",
    },
    "holiday-inn-express-suites-troy": {
        "reason": "RETURNED_TO_UNRESOLVED",
        "detail": "the worker recorded VERIFIED_NO_PETS on a research-agent "
                  "assertion with no quote, no capture and no hash; a negative "
                  "fact needs an artifact exactly as a positive one does",
        "next_action": "capture the IHG property page and record the refusal, "
                       "or leave the property unresolved",
    },
}


# --------------------------------------------------------------------------- #
# Loading and quote verification.
# --------------------------------------------------------------------------- #

def _write_lf(path: Path, text: str) -> None:
    """Write with LF endings, explicitly.

    ``launch_packages/**/*.json`` and ``*.csv`` are pinned ``text eol=lf``
    in .gitattributes. ``Path.write_text`` on Windows translates every
    newline to CRLF, which rewrote all 654 lines of the shared exclusions
    file the first time this ran -- Columbus's and Cleveland's records
    included -- and tripped the seed's line-ending guard. Bytes, not text.
    """
    path.write_bytes(text.encode("utf-8"))


def _read_json(path: Path) -> Dict:
    """The worker wrote a handful of cp1252 em-dashes into otherwise-UTF-8
    files. Decoding leniently here (and normalizing on the way out) keeps a
    transport-layer defect from masquerading as missing evidence."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return json.loads(text)


def _norm(text: str) -> str:
    """Whitespace-collapsed. The captures keep the page's line breaks, so a
    naive substring test rejects true quotes."""
    return " ".join((text or "").split())


def load_census() -> Dict[str, Dict]:
    census = _read_json(CENSUS_PATH)
    return {h["slug"]: h for h in census["hotels"]}


def load_captures() -> Dict[str, Dict]:
    """Every capture in the run, indexed by the URL it finally resolved to and
    by its html hash."""
    index: Dict[str, Dict] = {}
    caps = RUN_DIR / "captures"
    if not caps.is_dir():
        return index
    for path in sorted(caps.glob("*.json")):
        try:
            doc = _read_json(path)
        except Exception:
            continue
        if "text" not in doc and "html" not in doc:
            continue
        body = _norm(doc.get("text", "")) + " " + _norm(doc.get("html", ""))
        rec = {"body": body, "html_sha256": doc.get("html_sha256", ""),
               "text_sha256": doc.get("text_sha256", ""),
               "final_url": doc.get("final_url", ""),
               "captured_at": doc.get("captured_at", "")}
        for key in (doc.get("final_url"), doc.get("requested_url"),
                    doc.get("canonical_url")):
            if key:
                index.setdefault(key.rstrip("/#"), rec)
        if doc.get("html_sha256"):
            index.setdefault(doc["html_sha256"], rec)
    return index


def _structured(field: str, value, quote: str):
    """Resolve the table-valued facts to their structures.

    ``fee_tiers`` and ``fee_cap`` are shapes the renderer reads, not display
    strings: a ceiling that arrived as "$75.00 per stay" would reach
    ``_verified_details`` as a str and be asked for ``.get("amount")``. The
    quote travels INTO the structure so the cap carries its own evidence, the
    way ``promote_attested_candidates._cap_fact`` builds one.
    """
    if field == "fee_tiers":
        return TIERS[value]
    if field == "fee_cap":
        return dict(CAPS[value], evidence_quote=quote)
    return value


def capture_for(hotel: Dict, captures: Dict[str, Dict]) -> Optional[Dict]:
    url = (hotel.get("_official_url") or "").rstrip("/#")
    if url in captures:
        return captures[url]
    # A brand may redirect; fall back to the longest indexed URL that shares
    # the property code, which is the brand's own identifier for the property.
    code = (hotel.get("_property_code") or "").lower()
    if code:
        hits = [rec for key, rec in captures.items()
                if code in key.lower() or code in (rec["final_url"] or "").lower()]
        if len(hits) == 1:
            return hits[0]
    return None


# --------------------------------------------------------------------------- #
# Build.
# --------------------------------------------------------------------------- #

def build(strict: bool = True):
    census = load_census()
    captures = load_captures()

    accepted: List[Dict] = []
    exclusions: List[Dict] = []
    quarantined: List[Dict] = []
    observations: List[Dict] = []

    for slug, spec in sorted(FACTS.items()):
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        if hotel["identity_state"] != "IDENTITY_CONFIRMED":
            quarantined.append({"slug": slug,
                                "reason": "identity_state is %s, not "
                                          "IDENTITY_CONFIRMED" % hotel["identity_state"]})
            continue
        cap = capture_for(hotel, captures)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no capture artifact in %s" % CAPTURE_RUN})
            continue

        facts: "OrderedDict[str, object]" = OrderedDict()
        evidence: List[Dict] = []
        bad: List[str] = []
        for field, (value, quote) in spec["facts"].items():
            if _norm(quote) not in cap["body"]:
                bad.append("%s: quote is not in the captured page -- %r"
                           % (field, quote))
                continue
            evidence.append(OrderedDict([
                ("field", field), ("quote", quote),
                ("source_url", hotel.get("_official_url", "")),
                ("value", value)]))
            facts[field] = _structured(field, value, quote)
        if bad:
            quarantined.append({"slug": slug, "reason": "; ".join(bad)})
            continue

        observations.append(build_observation(hotel, facts, evidence, cap))
        accepted.append(OrderedDict([
            ("key", normalize_name(hotel["canonical_name"])),
            ("name", hotel["canonical_name"]),
            ("facts", facts),
            ("evidence", evidence),
            ("evidence_count", len(evidence)),
            ("evidence_quote", _policy_block(cap, [e["quote"] for e in evidence])),
            ("source_url", hotel.get("_official_url", "")),
            ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", AS_OF), ("verified_at", AS_OF),
            ("approval", OrderedDict([("approval_date", AS_OF),
                                      ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
                                      ("operator", REVIEWER)])),
            ("withheld_fields", OrderedDict(sorted(spec.get("withheld", {}).items()))),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash", cap["html_sha256"]),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
        ]))

    for slug, quote in sorted(NO_PETS.items()):
        hotel = census.get(slug)
        if hotel is None:
            quarantined.append({"slug": slug, "reason": "not in the Dayton census"})
            continue
        cap = capture_for(hotel, captures)
        if cap is None:
            quarantined.append({"slug": slug,
                                "reason": "no capture artifact for a negative fact"})
            continue
        if _norm(quote) not in cap["body"]:
            quarantined.append({"slug": slug,
                                "reason": "refusal quote is not in the captured page"})
            continue
        rec = OrderedDict([
            ("exclusion_id", "day-%s" % slug),
            ("canonical_name", hotel["canonical_name"]),
            ("normalized_name", normalize_name(hotel["canonical_name"])),
            ("address", hotel.get("address", "")),
            ("city", hotel.get("city", "")), ("state", hotel.get("state", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("official_url", hotel.get("_official_url", "")),
            ("exclusion_state", EX.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", hotel.get("_official_url", "")),
            ("observed_at", AS_OF),
            ("source_hash", cap["html_sha256"]),
            ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
            ("notes", NO_PETS_NOTE), ("market_id", MARKET),
        ])
        rec["record_hash"] = EX.record_hash(rec)
        rec["approval_hash"] = EX.approval_hash(rec)
        exclusions.append(rec)

    if strict and quarantined:
        raise SystemExit("Dayton integration refused %d record(s):\n%s"
                         % (len(quarantined),
                            "\n".join("  %(slug)s: %(reason)s" % q
                                      for q in quarantined)))
    return accepted, exclusions, quarantined, observations, census


def _policy_block(cap: Dict, quotes: List[str]) -> str:
    """The property's own policy text, whitespace-collapsed.

    This is what the renderability boundary reads and what the seed row's
    ``pet_policy`` carries, so it has to satisfy one invariant: EVERY quote
    this integration publishes must be inside it. A fixed-width window from
    the first "Pet Policy" anchor does not -- IHG puts the fee sentence in an
    FAQ far below the amenities row, so Holiday Inn Express Centerville would
    have published a $100 fee above a policy block that never mentions it.

    So the block is the span of the capture that actually contains the quotes:
    tight when the page keeps them together, and the quotes themselves, in
    page order, when the page scatters them. Both are the page's own words.
    """
    body = cap["body"]
    spans = []
    for quote in quotes:
        needle = _norm(quote)
        i = body.find(needle)
        if i >= 0:
            spans.append((i, i + len(needle)))
    if not spans:
        return ""
    start, end = min(s for s, _ in spans), max(e for _, e in spans)
    if end - start <= 900:
        return body[start:end].strip()
    # Scattered across the page: publish the supporting sentences themselves,
    # in the order the page states them, rather than 4 KB of navigation.
    seen, ordered = set(), []
    for i, quote in sorted(zip([s for s, _ in spans], quotes)):
        text = _norm(quote)
        if text not in seen:
            seen.add(text)
            ordered.append(text)
    return " ".join(ordered)


def build_observation(hotel: Dict, facts: Dict, evidence: List[Dict],
                      cap: Dict) -> Dict:
    """A ptf-policy-observation/1.0 record for the membrane to judge.

    Money is integer MINOR UNITS here and a display string in the published
    facts record; the two shapes are converted rather than one being bent to
    fit the other.
    """
    extraction: "OrderedDict[str, object]" = OrderedDict()
    for key, value in facts.items():
        if key not in PO.EXTRACTION_FIELDS:
            continue
        if key == "fee_tiers":
            extraction[key] = [
                dict(tier, amount_minor=int(round(float(tier["amount"]) * 100)))
                for tier in value]
        elif key == "fee_cap":
            extraction[key] = dict(
                value, amount_minor=int(round(float(value["amount"]) * 100)))
        elif key in PO.MONEY_KEYS:
            extraction[key] = int(round(float(str(value).lstrip("$")) * 100))
        else:
            extraction[key] = value

    # The STREET only. The census stores "street|postal"; folding the postal
    # code into the token set stops the page's own spelling of the street from
    # matching, and M10's same-property override can then never fire.
    street = (hotel.get("street_identity") or "").split("|")[0].strip()

    check = [("name_on_page", hotel["canonical_name"]),
             ("address_on_page", hotel.get("address", ""))]
    if hotel.get("phone"):
        check.append(("phone_on_page", hotel["phone"]))
    if hotel.get("_property_code"):
        check.append(("property_code", hotel["_property_code"]))

    return OrderedDict([
        ("obs_id", "day-obs-%s" % hotel["slug"]),
        ("contract_version", PO.CONTRACT_VERSION),
        ("hotel_ref", OrderedDict([
            ("market_id", MARKET),
            ("canonical_name", hotel["canonical_name"]),
            ("normalized_name", normalize_name(hotel["canonical_name"])),
            ("street_identity", street or hotel.get("address", "")),
            ("official_url", hotel.get("_official_url", "")),
            ("property_code", hotel.get("_property_code") or ""),
        ])),
        ("identity_check", OrderedDict(check)),
        ("source_url", hotel.get("_official_url", "")),
        ("source_type", "official_property_page"),
        ("authority_tier", PO.PT1_OFFICIAL_PROPERTY),
        ("observed_at", AS_OF),
        ("retrieved_at", cap.get("captured_at") or AS_OF),
        # The contract's vocabulary. The worker wrote "automated_browser",
        # which is not a value this contract has ever had.
        ("capture_method", "browser_assisted"),
        ("evidence", [OrderedDict([("quote", e["quote"]),
                                   ("location", "policy_block"),
                                   ("field_refs", [e["field"]]),
                                   ("artifact_ref", cap["html_sha256"])])
                      for e in evidence]),
        ("extraction", extraction),
        ("extraction_confidence", "EXACT_QUOTE"),
        ("flags", []),
        ("capture_artifacts", [h for h in (cap["html_sha256"], cap["text_sha256"])
                               if h]),
    ])


def seed_rows(accepted: List[Dict], census: Dict[str, Dict]) -> List[Dict]:
    by_key = {normalize_name(h["canonical_name"]): h for h in census.values()}
    rows = []
    for rec in accepted:
        hotel = by_key[rec["key"]]
        rows.append({
            "name": hotel["canonical_name"], "category": CATEGORY,
            "address": hotel.get("address", ""), "city": hotel.get("city", ""),
            "state": hotel.get("state", ""),
            "postal_code": hotel.get("postal_code", ""),
            "phone": hotel.get("phone", ""),
            "website_url": hotel.get("_official_url", ""),
            "source_url": hotel.get("_official_url", ""),
            "source_type": "OFFICIAL_PROPERTY", "observed_at": AS_OF,
            "rating": "", "amenities": "",
            # PTF-INVENTORY-001's renderability boundary reads this field: an
            # empty value means "pending attestation" and the listing is
            # filtered out before the WGE. The value is the property's own
            # captured policy text, whitespace-collapsed and otherwise verbatim.
            "pet_policy": rec["evidence_quote"],
            "canonical": "", MARKET_ID_FIELD: MARKET,
        })
    return rows


def main() -> int:
    apply = "--apply" in sys.argv
    accepted, exclusions, quarantined, observations, census = build(strict=False)

    verdicts = MB.evaluate_batch(observations)
    rejected = [(o["obs_id"], v.verdict, v.reasons)
                for o, v in zip(observations, verdicts)
                if v.verdict in MB.REJECTING_VERDICTS]

    print("Dayton authority integration (%s)" % MARKET)
    print("  accepted pet-friendly : %d" % len(accepted))
    print("  verified no-pets      : %d" % len(exclusions))
    print("  held (not published)  : %d" % len(HELD))
    print("  quarantined           : %d" % len(quarantined))
    for q in quarantined:
        print("      %(slug)s: %(reason)s" % q)
    print("  membrane rejections   : %d" % len(rejected))
    for obs_id, verdict, why in rejected:
        print("      %s %s %s" % (obs_id, verdict, why))

    if rejected or quarantined:
        print("\nREFUSING to write: every observation must pass the membrane "
              "and every quote must be in its capture.")
        return 1

    if not apply:
        print("\nDry run. Pass --apply to write.")
        return 0

    _write_lf(FACTS_OUT, json.dumps(
        OrderedDict([("schema_version", "1.0"), ("market", MARKET),
                     ("hotels", accepted)]),
        indent=2, ensure_ascii=False) + "\n")
    print("\nwrote %s" % FACTS_OUT.relative_to(_REPO_ROOT))

    doc = _read_json(EX.EXCLUSIONS_PATH)
    existing = {r["exclusion_id"] for r in doc["exclusions"]}
    doc["exclusions"].extend(r for r in exclusions
                             if r["exclusion_id"] not in existing)
    _write_lf(EX.EXCLUSIONS_PATH,
              json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print("wrote %s" % EX.EXCLUSIONS_PATH.relative_to(_REPO_ROOT))

    rows = seed_rows(accepted, census)
    with PRODUCTION_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        current = list(reader)
    have = {(r["name"], r.get(MARKET_ID_FIELD, "")) for r in current}
    added = [r for r in rows if (r["name"], MARKET) not in have]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in current + added:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    _write_lf(PRODUCTION_CSV, buf.getvalue())
    print("wrote %s (+%d rows)" % (PRODUCTION_CSV.relative_to(_REPO_ROOT),
                                   len(added)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
