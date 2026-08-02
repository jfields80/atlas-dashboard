"""PTF-CAPTURE-003E -- the package must prove what the human is asked to sign.

Every test here writes a REAL PNG and lets the gate re-derive its digest and
dimensions from the bytes on disk, because the failure this gate exists to stop
is a sidecar that describes an image nobody checked.

The scenarios are the ones that actually happened or nearly did: a policy shot
with no address (Aloft), an address shot with only the brand reservations
number beside it, identity that lives in the DOM but paints nowhere, and two
views that disagree.
"""

from __future__ import annotations

import hashlib
import pathlib

import pytest

from services.research_workers.capture_automation.evidence_completeness import (
    FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POLICY_TEXT, FIELD_POSTAL_CODE,
    FIELD_PROPERTY_PHONE, FIELD_STATE, FIELD_STREET, PHONE_CENTRAL_RESERVATIONS,
    PHONE_PROPERTY, REQUIRED_FIELDS, EvidenceIncompleteError, EvidenceView,
    FieldObservation, assess_evidence, classify_phone, fields_to_recapture,
    require_complete_evidence, validate_view, view_from_sidecar,
)

from .conftest import make_png

OFFICIAL = ("https://www.marriott.com/en-us/hotels/"
            "cmhco-aloft-columbus-university-district/overview/")

NAME = "Aloft by Marriott Columbus University District"
STREET = "1295 Olentangy River Road"
CITY = "Columbus"
STATE = "Ohio"
ZIP_ = "43212"
PHONE = "+1 614-294-7500"
CENTRAL = "1-888-236-2427"
POLICY = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: $50.00 "
          "Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 2")

BOX = {"x": 120, "y": 380, "width": 460, "height": 48}


def _png(tmp_path, name, w=1408, h=1005):
    data = make_png(w, h)
    path = tmp_path / name
    path.write_bytes(data)
    return path, data


def _view(tmp_path, name, observations, *, url=OFFICIAL, w=1408, h=1005,
          sha=None, byte_len=None, dims=None):
    path, data = _png(tmp_path, name, w, h)
    dw, dh = dims if dims else (w, h)
    return EvidenceView(
        png_path=str(path),
        png_sha256=sha if sha is not None else hashlib.sha256(data).hexdigest(),
        png_bytes=byte_len if byte_len is not None else len(data),
        png_width=dw, png_height=dh,
        page_url=url, captured_at="2026-08-01T21:15:04.664Z",
        observations=tuple(observations))


def _obs(field, text, **kw):
    kw.setdefault("box", BOX)
    return FieldObservation(field=field, text=text, **kw)


def _identity_observations(phone=PHONE, phone_ctx="Tel:"):
    return [
        _obs(FIELD_HOTEL_NAME, NAME),
        _obs(FIELD_STREET, STREET),
        _obs(FIELD_CITY, CITY),
        _obs(FIELD_STATE, STATE),
        _obs(FIELD_POSTAL_CODE, ZIP_),
        _obs(FIELD_PROPERTY_PHONE, phone, context=phone_ctx),
    ]


# --------------------------------------------------------------------------- #
# 1. Policy visible, address missing -- the Aloft case exactly.
# --------------------------------------------------------------------------- #

def test_policy_visible_but_address_missing_fails_closed(tmp_path):
    views = [_view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert FIELD_POLICY_TEXT in report.proven
    for f in (FIELD_HOTEL_NAME, FIELD_STREET, FIELD_CITY, FIELD_STATE,
              FIELD_POSTAL_CODE, FIELD_PROPERTY_PHONE):
        assert f in report.missing
    # and it tells the capture layer exactly what to go and get
    assert FIELD_STREET in fields_to_recapture(report)


def test_the_prompt_is_withheld_not_merely_annotated(tmp_path):
    """An incomplete package must raise. A warning a human can click past is
    the same as no gate at all."""
    views = [_view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    with pytest.raises(EvidenceIncompleteError) as exc:
        require_complete_evidence(views, official_url=OFFICIAL)
    assert "INCOMPLETE" in str(exc.value)
    assert FIELD_STREET in exc.value.report.missing


# --------------------------------------------------------------------------- #
# 2. Address visible, property phone missing.
# --------------------------------------------------------------------------- #

def test_address_visible_but_property_phone_missing(tmp_path):
    obs = [o for o in _identity_observations() if o.field != FIELD_PROPERTY_PHONE]
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert report.missing == (FIELD_PROPERTY_PHONE,)
    assert FIELD_STREET in report.proven
    assert fields_to_recapture(report) == (FIELD_PROPERTY_PHONE,)


# --------------------------------------------------------------------------- #
# 3. A central-reservations number is not the property's phone.
# --------------------------------------------------------------------------- #

def test_central_reservation_number_is_never_the_property_phone(tmp_path):
    obs = _identity_observations(phone=CENTRAL, phone_ctx="For reservations call")
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert FIELD_PROPERTY_PHONE in report.missing
    assert any("central reservations" in r for r in report.rejected)
    assert (("identity.png", CENTRAL, PHONE_CENTRAL_RESERVATIONS)
            in [(v, t, k) for v, t, k in report.phones])


def test_central_number_present_but_property_phone_separately_visible(tmp_path):
    """Both numbers on the page is the normal case, not an error. The gate must
    classify them apart and accept the package on the strength of the local
    front-desk line."""
    obs = _identity_observations()
    obs.append(_obs(FIELD_PROPERTY_PHONE, CENTRAL, context="Reservations"))
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is True
    assert report.proven[FIELD_PROPERTY_PHONE][1] == PHONE
    kinds = {t: k for _, t, k in report.phones}
    assert kinds[PHONE] == PHONE_PROPERTY
    assert kinds[CENTRAL] == PHONE_CENTRAL_RESERVATIONS


@pytest.mark.parametrize("number,expected", [
    ("+1 614-294-7500", PHONE_PROPERTY),
    ("614-294-7500", PHONE_PROPERTY),
    ("1-888-236-2427", PHONE_CENTRAL_RESERVATIONS),
    ("1-800-445-8667", PHONE_CENTRAL_RESERVATIONS),
    ("1-877-834-3613", PHONE_CENTRAL_RESERVATIONS),
])
def test_toll_free_numbers_classify_as_central(number, expected):
    assert classify_phone(number) == expected


def test_a_local_number_labelled_reservations_is_still_not_the_front_desk():
    """Context beats area code: some brands publish a local-rate booking line,
    and a booking line is not the property."""
    assert classify_phone("614-555-0100", context="Central Reservations") == \
        PHONE_CENTRAL_RESERVATIONS


# --------------------------------------------------------------------------- #
# 4. Fields spread across several views is legitimate.
# --------------------------------------------------------------------------- #

def test_all_fields_spread_across_multiple_screenshots(tmp_path):
    """A 7,900px page cannot show its policy and its address in one 1005px
    frame. Requiring that would make every tall page unattestable."""
    views = [
        _view(tmp_path, "name.png", [_obs(FIELD_HOTEL_NAME, NAME)]),
        _view(tmp_path, "address.png", [_obs(FIELD_STREET, STREET),
                                        _obs(FIELD_CITY, CITY),
                                        _obs(FIELD_STATE, STATE),
                                        _obs(FIELD_POSTAL_CODE, ZIP_)]),
        _view(tmp_path, "phone.png", [_obs(FIELD_PROPERTY_PHONE, PHONE,
                                           context="Tel:")]),
        _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)]),
    ]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is True
    assert set(report.proven) == set(REQUIRED_FIELDS)
    # the package names the proving image per field, not just "somewhere"
    assert report.proven[FIELD_POLICY_TEXT][0] == "policy.png"
    assert report.proven[FIELD_STREET][0] == "address.png"
    assert report.proven[FIELD_PROPERTY_PHONE][0] == "phone.png"


# --------------------------------------------------------------------------- #
# 5. Hidden DOM text proves nothing.
# --------------------------------------------------------------------------- #

def test_hidden_dom_identity_is_not_visible_evidence(tmp_path):
    """The address existing in the markup is not the address being readable.
    A human affirming from this package would be affirming pixels that are not
    there."""
    obs = [_obs(FIELD_HOTEL_NAME, NAME),
           _obs(FIELD_STREET, STREET, visible=False),
           _obs(FIELD_CITY, CITY, visible=False),
           _obs(FIELD_STATE, STATE, visible=False),
           _obs(FIELD_POSTAL_CODE, ZIP_, visible=False),
           _obs(FIELD_PROPERTY_PHONE, PHONE, context="Tel:")]
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert set(report.missing) == {FIELD_STREET, FIELD_CITY, FIELD_STATE,
                                   FIELD_POSTAL_CODE}
    assert sum("hidden_in_dom" in r for r in report.rejected) == 4


def test_out_of_frame_text_is_not_visible_evidence(tmp_path):
    """Painted but scrolled past. Same outcome, different reason -- and the
    report says which, because the fix differs (re-frame vs the page lacks it)."""
    obs = _identity_observations()
    obs = [o if o.field != FIELD_STREET
           else _obs(FIELD_STREET, STREET, in_frame=False) for o in obs]
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert report.missing == (FIELD_STREET,)
    assert any("out_of_frame" in r for r in report.rejected)


def test_zero_area_box_is_not_visible_evidence(tmp_path):
    obs = [_obs(FIELD_POLICY_TEXT, POLICY,
                box={"x": 0, "y": 0, "width": 0, "height": 0})]
    report = assess_evidence([_view(tmp_path, "policy.png", obs)],
                             official_url=OFFICIAL)
    assert FIELD_POLICY_TEXT in report.missing
    assert any("empty_or_zero_area" in r for r in report.rejected)


# --------------------------------------------------------------------------- #
# 6. Ambiguity fails closed rather than choosing.
# --------------------------------------------------------------------------- #

def test_conflicting_identity_values_are_ambiguous_not_resolved(tmp_path):
    """Two views showing different street addresses is a question, not a vote.
    Picking one would publish an address no source agrees on."""
    a = _identity_observations()
    b = [_obs(FIELD_STREET, "1250 Olentangy River Road")]
    views = [_view(tmp_path, "identity-a.png", a),
             _view(tmp_path, "identity-b.png", b),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert FIELD_STREET in report.ambiguous
    assert FIELD_STREET not in report.proven
    assert FIELD_STREET in fields_to_recapture(report)


def test_two_different_property_phones_are_ambiguous(tmp_path):
    obs = _identity_observations()
    obs.append(_obs(FIELD_PROPERTY_PHONE, "614-294-7501", context="Tel:"))
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)

    assert report.complete is False
    assert FIELD_PROPERTY_PHONE in report.ambiguous


def test_the_same_value_seen_twice_is_corroboration_not_ambiguity(tmp_path):
    """Formatting differences must not read as disagreement."""
    views = [_view(tmp_path, "identity.png", _identity_observations()),
             _view(tmp_path, "header.png",
                   [_obs(FIELD_PROPERTY_PHONE, "1-614-294-7500", context="Tel:")]),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL)
    assert report.complete is True


def test_an_observation_contradicting_the_queue_is_rejected(tmp_path):
    """The seed expects cmhco's phone. A view showing a different number is not
    evidence for this hotel, however visible it is."""
    obs = _identity_observations(phone="614-555-0199")
    views = [_view(tmp_path, "identity.png", obs),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(views, official_url=OFFICIAL,
                             expected={FIELD_PROPERTY_PHONE: "614-294-7500"})
    assert report.complete is False
    assert FIELD_PROPERTY_PHONE in report.missing
    assert any("contradicts expected" in r for r in report.rejected)


# --------------------------------------------------------------------------- #
# 7. The complete package.
# --------------------------------------------------------------------------- #

def test_successful_complete_package(tmp_path):
    views = [_view(tmp_path, "identity.png", _identity_observations()),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = require_complete_evidence(views, official_url=OFFICIAL,
                                       expected={FIELD_PROPERTY_PHONE: "614-294-7500",
                                                 FIELD_STREET: STREET})
    assert report.complete is True
    assert fields_to_recapture(report) == ()
    rendered = report.render()
    for f in REQUIRED_FIELDS:
        assert ("%-15s PROVEN" % f) in rendered
    assert "identity.png" in rendered and "policy.png" in rendered


# --------------------------------------------------------------------------- #
# View validation: the image must be what the sidecar claims.
# --------------------------------------------------------------------------- #

def test_a_view_of_a_different_page_is_not_evidence(tmp_path):
    v = _view(tmp_path, "other.png", _identity_observations(),
              url="https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/")
    report = assess_evidence([v], official_url=OFFICIAL)
    assert report.complete is False
    assert any("view_url_is_not_the_official_page" in p for p in report.problems)
    # nothing from an untrusted view leaks into the proven set
    assert report.proven == {}


def test_sha256_mismatch_disqualifies_the_view(tmp_path):
    v = _view(tmp_path, "identity.png", _identity_observations(), sha="0" * 64)
    problems = validate_view(v, official_url=OFFICIAL)
    assert "view_sha256_mismatch" in problems


def test_truncated_png_is_caught(tmp_path):
    path, data = _png(tmp_path, "cut.png")
    path.write_bytes(data[:-12])                      # drop the IEND chunk
    v = EvidenceView(png_path=str(path),
                     png_sha256=hashlib.sha256(data[:-12]).hexdigest(),
                     png_bytes=len(data) - 12, png_width=0, png_height=0,
                     page_url=OFFICIAL, captured_at="2026-08-01T21:15:04Z",
                     observations=())
    assert "view_png_truncated_no_iend" in validate_view(v, official_url=OFFICIAL)


def test_dimension_mismatch_is_caught(tmp_path):
    v = _view(tmp_path, "identity.png", _identity_observations(), dims=(800, 600))
    problems = validate_view(v, official_url=OFFICIAL)
    assert any(p.startswith("view_dimensions_mismatch") for p in problems)


def test_missing_timestamp_is_caught(tmp_path):
    path, data = _png(tmp_path, "identity.png")
    v = EvidenceView(png_path=str(path), png_sha256=hashlib.sha256(data).hexdigest(),
                     png_bytes=len(data), png_width=1408, png_height=1005,
                     page_url=OFFICIAL, captured_at="", observations=())
    assert "view_missing_captured_at" in validate_view(v, official_url=OFFICIAL)


def test_unreadable_png_does_not_crash_the_gate(tmp_path):
    v = EvidenceView(png_path=str(tmp_path / "gone.png"), png_sha256="a" * 64,
                     png_bytes=10, png_width=1, png_height=1,
                     page_url=OFFICIAL, captured_at="2026-08-01T21:15:04Z",
                     observations=(_obs(FIELD_POLICY_TEXT, POLICY),))
    report = assess_evidence([v], official_url=OFFICIAL)
    assert report.complete is False
    assert any("view_png_unreadable" in p for p in report.problems)


def test_view_from_sidecar_round_trips(tmp_path):
    path, data = _png(tmp_path, "identity.png")
    sidecar = {"png_file": "identity.png",
               "png_sha256": hashlib.sha256(data).hexdigest(),
               "png_bytes": len(data), "png_width": 1408, "png_height": 1005,
               "final_url": OFFICIAL, "captured_at": "2026-08-01T21:15:04.664Z"}
    v = view_from_sidecar(sidecar, directory=tmp_path,
                          observations=_identity_observations())
    assert validate_view(v, official_url=OFFICIAL) == ()
    assert v.name == "identity.png"


def test_empty_package_is_incomplete_not_complete(tmp_path):
    """Vacuous truth is the classic way a completeness check passes everything."""
    report = assess_evidence([], official_url=OFFICIAL)
    assert report.complete is False
    assert set(report.missing) == set(REQUIRED_FIELDS)


# --------------------------------------------------------------------------- #
# The seed's address shape is not the page's address shape.
# --------------------------------------------------------------------------- #

def test_street_line_drops_a_flattened_city_state_zip():
    """The seed stores one flattened field; the page prints the street alone.
    Comparing the flattened form found nothing and called a plainly visible
    address missing -- caught by running the real CLI, not by a unit test."""
    from services.research_workers.capture_automation.evidence_completeness import (
        street_line, street_variants,
    )
    assert street_line("1295 Olentangy River Rd Columbus OH 43212") == \
        "1295 Olentangy River Rd"
    assert "1295 Olentangy River Road" in \
        street_variants("1295 Olentangy River Rd Columbus OH 43212")


def test_a_flattened_expected_address_still_matches_the_page(tmp_path):
    views = [_view(tmp_path, "identity.png", _identity_observations()),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(
        views, official_url=OFFICIAL,
        expected={FIELD_STREET: "1295 Olentangy River Rd Columbus OH 43212"})
    assert FIELD_STREET in report.proven
    assert report.complete is True


def test_a_genuinely_different_street_still_contradicts(tmp_path):
    """Loosening the comparison must not make it accept anything."""
    views = [_view(tmp_path, "identity.png", _identity_observations()),
             _view(tmp_path, "policy.png", [_obs(FIELD_POLICY_TEXT, POLICY)])]
    report = assess_evidence(
        views, official_url=OFFICIAL,
        expected={FIELD_STREET: "500 Metro Place North Dublin OH 43017"})
    assert FIELD_STREET in report.missing
    assert any("contradicts expected" in r for r in report.rejected)


# --------------------------------------------------------------------------- #
# PTF-CAPTURE-004C -- variants of one expected value are not two values.
# --------------------------------------------------------------------------- #

def test_several_renderings_of_the_expected_value_corroborate(tmp_path):
    """The planner hunts "Rd" and "Road", "OH" and "Ohio", the full name and
    its tail. The probe finds several, each recorded with the needle it
    matched. Comparing those to each other called a settled field AMBIGUOUS and
    sent the sweep back for another view that could only repeat the problem."""
    obs = [
        _obs(FIELD_STREET, "5510 Trabue Rd"),
        _obs(FIELD_STREET, "5510 TRABUE ROAD"),
        _obs(FIELD_STATE, "OH"),
        _obs(FIELD_STATE, "Ohio"),
    ]
    report = assess_evidence(
        [_view(tmp_path, "identity.png", obs)], official_url=OFFICIAL,
        expected={FIELD_STREET: "5510 Trabue Rd", FIELD_STATE: "OH"})
    assert FIELD_STREET not in report.ambiguous
    assert FIELD_STATE not in report.ambiguous
    assert FIELD_STREET in report.proven
    assert FIELD_STATE in report.proven


def test_two_genuinely_different_values_are_still_ambiguous_with_an_expectation(tmp_path):
    """The relaxation must not swallow a real conflict. An observation that
    contradicts the expected value is rejected outright, so a field backed by
    nothing survivable stays unproven rather than quietly passing."""
    obs = [_obs(FIELD_STREET, "5510 Trabue Rd"),
           _obs(FIELD_STREET, "9999 Nowhere Avenue")]
    report = assess_evidence(
        [_view(tmp_path, "identity.png", obs)], official_url=OFFICIAL,
        expected={FIELD_STREET: "5510 Trabue Rd"})
    assert any("contradicts expected" in r for r in report.rejected)
    assert report.proven[FIELD_STREET][1] == "5510 Trabue Rd"


def test_without_an_expectation_conflicting_text_is_still_ambiguous(tmp_path):
    """No expected value means nothing to agree with, so raw disagreement is
    the honest test and stays in force."""
    obs = [_obs(FIELD_STREET, "5510 Trabue Rd"),
           _obs(FIELD_STREET, "1250 Olentangy River Road")]
    report = assess_evidence([_view(tmp_path, "identity.png", obs)],
                             official_url=OFFICIAL)
    assert FIELD_STREET in report.ambiguous


# --------------------------------------------------------------------------- #
# Hotel names: a brand may add words; a different property drops them.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("seed,page", [
    # brand line inserted mid-name
    ("La Quinta Columbus West-Hilliard",
     "La Quinta Inn & Suites by Wyndham Columbus West - Hilliard"),
    ("Aloft Columbus University District",
     "Aloft by Marriott Columbus University District"),
    # punctuation only
    ("Staybridge Suites Columbus Dublin", "Staybridge Suites Columbus-Dublin"),
    # identical
    ("La Quinta Inn by Wyndham Columbus Dublin",
     "La Quinta Inn by Wyndham Columbus Dublin"),
])
def test_the_same_hotel_typeset_differently_still_matches(tmp_path, seed, page):
    report = assess_evidence(
        [_view(tmp_path, "identity.png", [_obs(FIELD_HOTEL_NAME, page)])],
        official_url=OFFICIAL, expected={FIELD_HOTEL_NAME: seed})
    assert FIELD_HOTEL_NAME in report.proven, report.rejected


@pytest.mark.parametrize("seed,page", [
    # a genuinely different property on the same brand
    ("La Quinta Columbus West-Hilliard",
     "La Quinta Inn by Wyndham Columbus Dublin"),
    ("Courtyard Columbus Easton", "Courtyard Columbus Worthington"),
    # the real Hilton case: a property page titled with another brand. A
    # two-word tail would have matched this on "Columbus Airport" alone.
    ("Hampton Inn Columbus Airport",
     "Embassy Suites by Hilton Columbus Airport"),
])
def test_a_different_property_is_still_refused(tmp_path, seed, page):
    report = assess_evidence(
        [_view(tmp_path, "identity.png", [_obs(FIELD_HOTEL_NAME, page)])],
        official_url=OFFICIAL, expected={FIELD_HOTEL_NAME: seed})
    assert FIELD_HOTEL_NAME in report.missing
    assert any("contradicts expected" in r for r in report.rejected)


def test_name_matching_is_not_applied_to_street_or_phone(tmp_path):
    """The allowance is for names only. An address that differs is a different
    fact, and must not inherit the name rule's tolerance."""
    obs = [_obs(FIELD_STREET, "9999 Somewhere Else Road"),
           _obs(FIELD_PROPERTY_PHONE, "614-555-0000", context="Tel:")]
    report = assess_evidence(
        [_view(tmp_path, "identity.png", obs)], official_url=OFFICIAL,
        expected={FIELD_STREET: "5510 Trabue Rd",
                  FIELD_PROPERTY_PHONE: "614-878-8844"})
    assert FIELD_STREET in report.missing
    assert FIELD_PROPERTY_PHONE in report.missing
