"""The fixed identity corpus for PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027.

A gate that decides which building a page is about cannot be evaluated on the
properties it was written for. This is the corpus it is evaluated on: the
code-less property that already bound, the ten that did not, and a set of pages
that MUST NOT bind however related they look.

REAL PAGES WHEREVER THE CORPUS HAS THEM
----------------------------------------
Most adversarial cases here are retained captures, not invented markup, and
they are adversarial because of what those sites actually do:

* thewildwoodlodge.com serves Pewaukee, Wisconsin and Clive, Iowa under one
  name, and prints both telephone numbers in one footer.
* 325 North Brookfield Road holds a Motel 6 and a Studio 6 -- one street
  identity, two properties, two census rows.
* woodspring.com is a chain site whose pet-policy page belongs to no property.

Only where the corpus holds no example -- a redirect to an unrelated hotel, a
fabricated property path, a page whose address contradicts the census -- is the
markup written here, and then it is written as the smallest page that poses the
question.

HOW A CASE IS EVALUATED
-----------------------
Exactly as production would: the expected identity comes from the census row,
and ``requested_url`` is the URL the pipeline would have asked for -- the census
URL, or the validated discovered policy URL. Feeding the gate the adversarial
page's OWN url as the expected url would make the canonical-path check agree
with itself and prove nothing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

POSITIVE = "POSITIVE"
ADVERSARIAL = "ADVERSARIAL"

DISCOVERY = ("data/acquisition/independent-url-discovery-014/url-discovery-014")
FINAL_026 = "data/acquisition/milwaukee-final-026/milwaukee-final-026"
PROOF_019A = ("data/acquisition/locator-fresh-proof-019a/"
              "locator-fresh-proof-019a")
ROUTER_001 = "data/acquisition/milwaukee-router-001/milwaukee-router-001"


@dataclass(frozen=True)
class Case:
    """One identity question, and the answer the contract must give."""

    case_id: str
    kind: str
    scenario: str
    #: The census row the page is tested against.
    identity_key: str
    #: The URL production would have requested for that row.
    requested_url: str
    #: The page under test: a retained capture, or inline markup.
    artifact: str = ""
    html: str = ""
    #: The URL the page under test was actually served from.
    fetched_url: str = ""
    expect: str = "PASS"
    why: str = ""

    def load(self) -> str:
        if self.html:
            return self.html
        return (REPO / self.artifact).read_text(encoding="utf-8",
                                                errors="replace")

    def exists(self) -> bool:
        return bool(self.html) or (REPO / self.artifact).is_file()


def _page(name: str, *, street: str = "", postal: str = "", phone: str = "",
          canonical: str = "", body: str = "") -> str:
    """The smallest page that answers an identity question.

    Structured data when the case is about structured data, and a title when it
    is about a title -- a synthetic fixture that carries more than the case is
    about would pass or fail for the wrong reason.
    """
    parts: List[str] = ['<!doctype html><html><head>',
                        '<title>%s</title>' % name]
    if canonical:
        parts.append('<link rel="canonical" href="%s">' % canonical)
    if street or phone:
        address = ('"address":{"@type":"PostalAddress",'
                   '"streetAddress":"%s","postalCode":"%s"},'
                   % (street, postal)) if street else ""
        telephone = '"telephone":"%s",' % phone if phone else ""
        parts.append(
            '<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Hotel",'
            '"name":"%s",%s%s"url":"%s"}</script>'
            % (name, address, telephone, canonical or ""))
    parts.append('</head><body><h1>%s</h1><p>%s</p></body></html>'
                 % (name, body or "Welcome."))
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Positive controls.
# --------------------------------------------------------------------------- #

POSITIVE_CASES: Tuple[Case, ...] = (
    Case(case_id="P1-cobblestone-canonical-path",
         kind=POSITIVE,
         scenario="code-less property that already bound, on its own path",
         identity_key="cobblestone hotel and suites waukesha west milwaukee",
         requested_url="https://staycobblestone.com/wi/waukesha/",
         artifact=("%s/cobblestone-hotel-suites-waukesha-west-milwaukee/"
                   "attempt-01/rendered.html" % PROOF_019A),
         fetched_url="https://staycobblestone.com/wi/waukesha/",
         expect="PASS",
         why="the path-and-name rule must keep confirming what it confirmed"),
    Case(case_id="P2-pfister-full-structured-identity",
         kind=POSITIVE,
         scenario="independent publishing name, street, ZIP and telephone",
         identity_key="the pfister hotel",
         requested_url="https://www.thepfisterhotel.com/accommodations/pets/",
         artifact="%s/the-pfister-hotel/attempt-01/rendered.html" % FINAL_026,
         fetched_url="https://www.thepfisterhotel.com/accommodations/pets/",
         expect="PASS",
         why="already acquired in 026; must not regress"),
    Case(case_id="P3-saint-kate-street-and-name",
         kind=POSITIVE,
         scenario="one-segment policy path, structured street and name agree",
         identity_key="saint kate the arts hotel",
         requested_url="https://www.saintkatearts.com/faq",
         artifact="%s/saint-kate-the-arts-hotel--faq/rendered.html" % DISCOVERY,
         fetched_url="https://www.saintkatearts.com/faq",
         expect="PASS",
         why="refused by the old gate purely for having a one-segment path"),
    Case(case_id="P4-ingleside-street-and-name",
         kind=POSITIVE,
         scenario="canonical points at the site root, street and name agree",
         identity_key="the ingleside hotel",
         requested_url=("https://www.theinglesidehotel.com/accommodations/"
                        "dog-friendly"),
         artifact=("%s/the-ingleside-hotel--accommodations-dog-friendly/"
                   "rendered.html" % DISCOVERY),
         fetched_url=("https://www.theinglesidehotel.com/accommodations/"
                      "dog-friendly"),
         expect="PASS",
         why="a site-root canonical is not a different property"),
    Case(case_id="P5-marc-street-and-name",
         kind=POSITIVE,
         scenario="one-segment amenities path, street and name agree",
         identity_key="the marc hotel",
         requested_url="https://www.marchotelmilwaukee.com/amenities/",
         artifact="%s/the-marc-hotel--amenities/rendered.html" % DISCOVERY,
         fetched_url="https://www.marchotelmilwaukee.com/amenities/",
         expect="PASS",
         why="refused by the old gate purely for having a one-segment path"),
    Case(case_id="P6-branded-property-code",
         kind=POSITIVE,
         scenario="branded property bound by its code, unchanged",
         identity_key="homewood suites by hilton milwaukee downtown",
         requested_url="",
         artifact=("data/acquisition/hilton-milwaukee-023/"
                   "hilton-milwaukee-023/homewood-suites-by-hilton-milwaukee-downtown/"
                   "attempt-01/rendered.html"),
         expect="PASS",
         why="the property-code path must be untouched by this repair"),
    Case(case_id="P7-structured-phone-no-street",
         kind=POSITIVE,
         scenario="lodging data with a telephone and no street address",
         identity_key="the marc hotel",
         requested_url="https://www.marchotelmilwaukee.com/amenities/",
         html=_page("The Marc Hotel", phone="+1-414-390-1800",
                    canonical="https://www.marchotelmilwaukee.com/amenities/"),
         fetched_url="https://www.marchotelmilwaukee.com/amenities/",
         expect="PASS",
         why="a self-declared telephone line plus a contained name binds"),
)


# --------------------------------------------------------------------------- #
# Adversarial controls.
# --------------------------------------------------------------------------- #

ADVERSARIAL_CASES: Tuple[Case, ...] = (
    Case(case_id="A1-same-name-wrong-city",
         kind=ADVERSARIAL,
         scenario="same hotel name, wrong city -- Clive, Iowa, not Pewaukee",
         identity_key="wildwood lodge",
         requested_url="https://thewildwoodlodge.com/pewaukee/",
         artifact="%s/wildwood-lodge--clive/rendered.html" % DISCOVERY,
         fetched_url="https://thewildwoodlodge.com/clive",
         expect="FAIL",
         why="one operator, one name, two states -- and one shared footer"),
    Case(case_id="A2-same-name-wrong-city-faqs",
         kind=ADVERSARIAL,
         scenario="the wrong city's FAQ page, printing the census telephone",
         identity_key="wildwood lodge",
         requested_url="https://thewildwoodlodge.com/pewaukee/",
         artifact="%s/wildwood-lodge--clive-faqs/rendered.html" % DISCOVERY,
         fetched_url="https://thewildwoodlodge.com/clive/faqs/",
         expect="FAIL",
         why="the Pewaukee number is printed on the Clive page; a number "
             "merely present may not bind"),
    Case(case_id="A3-same-operator-wrong-property-one-street",
         kind=ADVERSARIAL,
         scenario="same brand family at the SAME street -- Studio 6 for Motel 6",
         identity_key="motel 6 suites milwaukee brookfield wi",
         requested_url=("https://www.motel6.com/property/"
                        "motel-brookfield-wisconsin-us-368045/"),
         artifact=("%s/studio-6-extended-stay-milwaukee-brookfield-wi/"
                   "attempt-01/rendered.html" % FINAL_026),
         fetched_url=("https://www.motel6.com/property/"
                      "motel-milwaukee-wi-wisconsin-us-357314/"),
         expect="FAIL",
         why="two census rows share 325 North Brookfield Road; the street "
             "cannot separate them and the name must"),
    Case(case_id="A4-chain-page-no-property",
         kind=ADVERSARIAL,
         scenario="a chain's pet-policy page, belonging to no property",
         identity_key="woodspring suites milwaukee menomonee falls",
         requested_url=("https://www.woodspring.com/extended-stay-hotels/"
                        "locations/wisconsin/Menomonee-Falls/"
                        "woodspring-suites-Milwuakee-Menomonee-Falls"),
         artifact=("%s/woodspring-suites-milwaukee-menomonee-falls--"
                   "offers-pet-friendly-hotel/rendered.html" % DISCOVERY),
         fetched_url="https://www.woodspring.com/offers/pet-friendly-hotel",
         expect="FAIL",
         why="a group page is about a brand, not a building"),
    Case(case_id="A5-same-domain-generic-faq",
         kind=ADVERSARIAL,
         scenario="same domain, a brand-wide FAQ with no property binding",
         identity_key="woodspring suites milwaukee menomonee falls",
         requested_url=("https://www.woodspring.com/extended-stay-hotels/"
                        "locations/wisconsin/Menomonee-Falls/"
                        "woodspring-suites-Milwuakee-Menomonee-Falls"),
         artifact=("%s/woodspring-suites-milwaukee-menomonee-falls--faqs/"
                   "rendered.html" % DISCOVERY),
         fetched_url="https://www.woodspring.com/faqs",
         expect="FAIL",
         why="same domain is not a signal in this contract"),
    Case(case_id="A6-common-name-tokens-only",
         kind=ADVERSARIAL,
         scenario="agreement only on words half the market's hotels use",
         identity_key="the plaza hotel milwaukee",
         requested_url="https://plazahotelmilwaukee.com/amenities/",
         artifact=("%s/the-plaza-hotel-milwaukee--amenities/rendered.html"
                   % DISCOVERY),
         fetched_url="https://plazahotelmilwaukee.com/amenities/",
         expect="FAIL",
         why='"hotel" and "milwaukee" are not an identity'),
    Case(case_id="A7-contact-page-no-binding",
         kind=ADVERSARIAL,
         scenario="a contact page that names no property",
         identity_key="the iron horse hotel",
         requested_url="https://www.theironhorsehotel.com/dogs/",
         html=_page("Contact Us",
                    canonical="https://www.theironhorsehotel.com/contact/",
                    body="Send us a message and we will be in touch."),
         fetched_url="https://www.theironhorsehotel.com/contact/",
         expect="FAIL",
         why="a page with no property name binds to no property"),
    Case(case_id="A8-redirected-to-unrelated-property",
         kind=ADVERSARIAL,
         scenario="the request redirected to a different hotel entirely",
         identity_key="the marc hotel",
         requested_url="https://www.marchotelmilwaukee.com/amenities/",
         html=_page("Hotel Metro Milwaukee", street="411 E Mason St",
                    postal="53202", phone="+1-414-272-1937",
                    canonical="https://www.hotelmetro.com/"),
         fetched_url="https://www.hotelmetro.com/",
         expect="FAIL",
         why="a different name at a different street is a different hotel"),
    Case(case_id="A9-fabricated-property-path",
         kind=ADVERSARIAL,
         scenario="a made-up property path that the site answered anyway",
         identity_key="the clarke hotel",
         requested_url="https://www.theclarkehotel.com/",
         html=_page("Page not found",
                    canonical="https://www.theclarkehotel.com/pets/",
                    body="The page you were looking for does not exist."),
         fetched_url="https://www.theclarkehotel.com/pets/",
         expect="FAIL",
         why="a 200 response is not an identity"),
    Case(case_id="A10-address-contradicts-census",
         kind=ADVERSARIAL,
         scenario="right name, structured address on a different street",
         identity_key="the ingleside hotel",
         requested_url=("https://www.theinglesidehotel.com/accommodations/"
                        "dog-friendly"),
         html=_page("The Ingleside Hotel", street="1 Different Way",
                    postal="53072",
                    canonical=("https://www.theinglesidehotel.com/"
                               "accommodations/dog-friendly")),
         fetched_url=("https://www.theinglesidehotel.com/accommodations/"
                      "dog-friendly"),
         expect="FAIL",
         why="a conflicting street fails the code-less binding closed"),
    Case(case_id="A11-discovered-url-does-not-bypass",
         kind=ADVERSARIAL,
         scenario="a validated discovered policy URL on an unbindable page",
         identity_key="potawatomi casino hotel",
         requested_url="https://www.potawatomi.com/hotel",
         artifact=("%s/potawatomi-casino-hotel--casino-house-rules/"
                   "rendered.html" % DISCOVERY),
         fetched_url="https://www.potawatomi.com/casino/house-rules",
         expect="FAIL",
         why="source discovery chooses a PAGE; it never confirms an identity"),
)


CASES: Tuple[Case, ...] = POSITIVE_CASES + ADVERSARIAL_CASES


def available() -> List[Case]:
    """The cases whose page is actually on disk.

    A case whose artifact is missing is reported as missing rather than
    silently skipped: a corpus that quietly shrinks stops being a control.
    """
    return [case for case in CASES if case.exists()]


def missing() -> List[str]:
    return [case.case_id for case in CASES if not case.exists()]
