"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' operative quotes.

Every row below is ONE operative first-party statement chosen by review from a
document the static / policy-page lanes persisted (or, for the one attended read,
hashed in the browser in the same call that read the quote). This builder PROVES
each choice before it commits it:

  * the quote occurs verbatim (whitespace-collapsed) in the persisted document;
  * the property's own house number and postal code occur in that same document,
    so the read binds to the building by the page's OWN street identity;
  * the sha256 and byte length come from the document on disk, never typed.

A row that fails either proof raises and nothing is written. The capture helper
reads the result (``raw_captures/brand_pages.json``); the shared first-party
binding gate still decides whether each quote is operative.

Output:
  launch_packages/pettripfinder/markets/staging/banner-elk-sugar-beech-nc/raw_captures/brand_pages.json
  (static rows from ROWS, attended rows from raw_captures/attended_pages_rows.json)
"""
from __future__ import annotations

import glob
import html as H
import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ACQ = os.path.join(_DASH, "data", "acquisition")
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "banner-elk-sugar-beech-nc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "banner_elk_sugar_beech_nc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("parkview-lodge-and-cabins", "Parkview Lodge & Cabins", "10345 Linville Falls Hwy", "Newland", "28657",
     "(828) 528-8999", "0a3cb4d9d373",
     "Pet-friendly (an extra pet fee applies)",
     {"pets_allowed": True}, None),
    # The lodge's own FAQ. "4 dog-friendly rooms" is an acceptance scoped to designated rooms; the $100 cleaning
    # charge beside it is a penalty for an unbooked dog, not a pet fee, and is not published.
    ("the-pineola", "The Pineola", "3085 Linville Falls Hwy", "Newland", "28657", "(828) 733-4979", "37d42a1fb5c6",
     "We do have 4 dog-friendly rooms (3 kings and 1 double queen), and you can choose them on our booking site.",
     {"pets_allowed": True}, None),
    # The inn's own policies page states 'Valle Crucis , NC 28604' -- a Watauga town beside the admitted ZIP. The
    # read is carried so the census holds it as a GEOGRAPHY_HOLD with its evidence; the fee is tiered by stay length
    # ("For stays of 4 nights or more ...") and is not published.
    ("the-mast-farm-inn", "The Mast Farm Inn", "2543 Broadstone Road", "Valle Crucis", "28604", "828-963-5857",
     "d6d9970b9b69",
     "Our entire property is pet friendly!",
     {"pets_allowed": True}, None),
    # verified no-pets
    ("smoketree-lodge", "Smoketree Lodge", "11914 Highway 105 South", "Banner Elk", "28604", "828-963-6505",
     "ac99116586f3",
     "No pets allowed",
     {"pets_allowed": False}, None),
    ("the-azalea-inn", "The Azalea Inn", "149 Azalea Circle", "Banner Elk", "28604", "828-260-9528", "a4725eb9e5c5",
     "Pets are not allowed.",
     {"pets_allowed": False}, None),
    # a refusal the shared reader does not read (QUOTE_NOT_OPERATIVE): carried verbatim, held by the clean set
    ("taylor-house-inn", "Taylor House Inn", "4584 Hwy 194 South", "Banner Elk", "28604", "(828) 963-5581",
     "ef0dd32357d1",
     "However, we cannot accommodate any pets at the present time.",
     {"pets_allowed": False}, None),
]

#: Attended independent reads: rows the browser built and digested in the SAME call that fetched the
#: document and verified the quote, house number and postal code in it. Committed verbatim in
#: raw_captures/attended_pages_rows.json; each row's canonical JSON sha256 is checked against the
#: digest the browser computed before the row is used.
ATTENDED_FILE = os.path.join(RAW, "attended_pages_rows.json")
ATTENDED_ROW_DIGESTS = OrderedDict([
    ("the-lodge-at-banner-elk", "19d78564a8d98b385721a023a32a34c4bcf4b26176369bc104f553f116c0f5c2"),
    ("4-seasons-at-beech-mountain", "ce3ccea914c748214320420040862636 3382db85405a8bdd378e23e4efe340ef".replace(" ", "")),
])


def attended_rows():
    import hashlib
    rows = json.load(open(ATTENDED_FILE, encoding="utf-8"))
    for r in rows:
        got = hashlib.sha256(json.dumps(r, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        if ATTENDED_ROW_DIGESTS.get(r["seed"]) != got:
            raise SystemExit("attended row %s digest %s != the browser's" % (r["seed"], got))
    if len(rows) != len(ATTENDED_ROW_DIGESTS):
        raise SystemExit("attended rows and browser digests disagree in count")
    return [OrderedDict(r) for r in rows]


def _plain(body):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return " ".join(t.split())


def _url_by_sha():
    doc = json.load(open(POLICY_LANE, encoding="utf-8"))
    out, by_sentence = {}, []
    for r in doc["rows"]:
        for p in r["pages"]:
            if p.get("sha256"):
                out.setdefault(p["sha256"], p["final_url"] or p["url"])
            by_sentence.append((p["final_url"] or p["url"], " ".join(" ".join(p["pet_sentences"]).split())))
    return out, by_sentence


#: The URL each reviewed document was read from, as the policy-page lane's FIRST run recorded it. The lane
#: was re-run once to follow sub-pages; a re-rendering server (Parkview, Taylor House) served new bytes and
#: The Pineola rate-limited (429) the second run, so those documents are no longer in the rewritten report.
#: The reviewed document on disk is still the one bound here.
FIRST_READ_URLS = {
    "0a3cb4d9d373": "https://www.parkviewlodge.com/",
    "37d42a1fb5c6": "https://www.thepineola.com/faqs",
    "ef0dd32357d1": "https://www.taylorhouseinn.com/our-property",
}


def _url_for(sha, quote, urls, by_sentence):
    """The document's URL. A page whose server re-renders on every request (a changing
    nonce) persists under a new sha256 each time it is read; the reviewed document is
    still the one on disk, and its URL is the lane page that serves the same pet sentence."""
    if sha in urls:
        return urls[sha]
    if sha[:12] in FIRST_READ_URLS:
        return FIRST_READ_URLS[sha[:12]]
    head = " ".join(quote.split())[:60]
    hits = sorted({u for u, s in by_sentence if head and head in s})
    return hits[0] if len(hits) == 1 else None


def build():
    urls, by_sentence = _url_by_sha()
    rows = []
    for seed, name, street, city, postal, phone, prefix, quote, ext, conflict in ROWS:
        # the same document may be persisted by more than one lane; one sha256 is one document
        files = sorted({os.path.basename(f): f for f in
                        glob.glob(os.path.join(ACQ, "banner_elk_sugar_beech_nc_*", prefix + "*.bin"))}.values())
        if len(files) != 1:
            raise SystemExit("%s: %d documents match %s" % (seed, len(files), prefix))
        raw = open(files[0], "rb").read()
        sha = os.path.basename(files[0])[:-4]
        text = _plain(raw.decode("utf-8", "replace"))
        if " ".join(quote.split()) not in text:
            raise SystemExit("%s: the quote is not verbatim in %s" % (seed, sha))
        num = street.split()[0]
        if not re.search(r"\b%s\b" % re.escape(num), text) or postal not in text:
            raise SystemExit("%s: the document does not state house number %s and postal code %s" % (seed, num, postal))
        rows.append(OrderedDict([
            ("seed", seed), ("brand", "INDEPENDENT"), ("lane", "DIRECT_STATIC_FETCH"),
            ("name", name), ("street", street), ("city", city), ("postal", postal), ("phone", phone),
            ("url", _url_for(sha, quote, urls, by_sentence)), ("sha256", sha), ("bytes", len(raw)), ("surface", SURFACE),
            ("quote", quote), ("extraction", OrderedDict(ext)), ("method", METHOD), ("conflict", conflict),
        ]))
        if not rows[-1]["url"]:
            raise SystemExit("%s: no lane row names the URL of %s" % (seed, sha))
    return rows + attended_rows()


def main():
    rows = build()
    os.makedirs(RAW, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("brand pages:", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
