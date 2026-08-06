"""PETTRIPFINDER-DESIGN-005 -- founder-approved FINAL homepage renderer.

Visual authority: ``pettripfinder-final-approved-homepage.png`` (binding).

The approved final design repositions PetTripFinder as a broader Columbus
*pet-travel* guide rather than a hotel directory. Its mandated headline is:

    "Find a Columbus trip that actually works for your pet."

Structure (per the mockup): slim wordmark header with trip-shaped navigation
(Places to Stay / Things to Do / Eat & Drink / Emergency Pet Care / How we
verify) -> hero whose photograph bleeds off the right edge and fades into the
page, carrying the headline, the inline search row, five filter chips and a
"Columbus, Ohio" overlay badge -> then a two-column body:

  left column   qualitative trust strip -> "Start with what matters to your
                trip" (4 quick-starts) -> "Recently verified pet-friendly
                places" (6 compact cards) -> "Plan the rest of your
                pet-friendly trip in Columbus" (3 cards) -> "Travel better
                together" band
  right column  "Compare pet policies at a glance" (5-row table) -> "Why
                PetTripFinder exists" -> decorative skyline

Deliberate, disclosed departures from the mockup image -- each one protects a
data-honesty invariant the image (an unpopulated design comp) does not:

  * The mockup's card/table values are comp placeholders and several of its
    place names are not in the verified package at all. Every fact rendered
    here is copied from the committed package instead, and "Not stated" is
    printed wherever the source was silent -- never back-filled.
  * The mockup prints a decorative "$$" price tier on every card. A static
    tier glyph would assert a price band we never verified (and would sit
    beside "Fee not stated" on records with no fee), so a neutral fee icon
    is used and the exact fee text carries the meaning.
  * The glance table's first species column is labelled "Dogs", not the
    mockup's "Pets" -- a check under "Pets" beside a separate "Cats" column
    states nothing, and the underlying field is species-specific.

Honesty rules carried through unchanged: search and filter controls are
browse/navigation controls (no live search, booking, rates or availability is
implied); the emergency-care card links to a plain Google Maps query
deep-link (the same no-API doctrine the /go/ directions pages use) because
production carries no vet inventory, so no business is ever fabricated. The
imagery is approved TEMPORARY review imagery -- compliant Google Places media
is a separate later phase, and the footer says so.
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.hotel_profile import _friendly_date

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Stylesheet (single source: the approved FINAL homepage mockup).
# --------------------------------------------------------------------------- #

HOME_CSS = r""":root{
  --ever:#12402c;--deep:#0b3122;--warm:#c2500f;--fact:#9a3b2b;
  --bg:#fefcf8;--paper:#fff;--panel:#f7f6f0;--soft:#f9f6f0;
  --ink:#1b2a24;--muted:#5f6d67;--line:#eae4d8;--ok:#1e6a4b;--max:1280px;
}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-size:14px;line-height:1.5;
  -webkit-font-smoothing:antialiased;
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
h1,h2,h3,.serif{font-family:Georgia,'Times New Roman',serif;font-weight:700}
.wrap{width:min(var(--max),calc(100% - 48px));margin:auto}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:12px;z-index:100;background:#fff;padding:10px 14px;border-radius:8px}
img{max-width:100%;display:block}
a{color:inherit}
:focus-visible{outline:2px solid var(--ever);outline-offset:2px}

/* header */
.ph-top{background:var(--paper);border-bottom:1px solid #f1ece1;position:sticky;top:0;z-index:30}
.ph-top .wrap{display:flex;align-items:center;justify-content:space-between;gap:20px;height:46px}
.brand{display:inline-flex;align-items:baseline;text-decoration:none;white-space:nowrap;
  font-family:Georgia,'Times New Roman',serif;font-size:19.5px;font-weight:700;
  color:var(--ever);letter-spacing:-.2px}
.brand .dot{margin:0 8px;color:var(--warm);font-weight:700}
.brand em{font-style:normal;color:var(--warm)}
.links{display:flex;gap:21px;align-items:center}
.links a{display:inline-flex;align-items:center;gap:5px;color:#28382f;text-decoration:none;
  font-size:12.5px;font-weight:600;white-space:nowrap}
.links a:hover{color:var(--warm)}
.links .caret{width:11px;height:11px;flex:0 0 auto;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round}
.nav-actions{display:flex;align-items:center;gap:16px}
.saved{display:inline-flex;align-items:center;gap:7px;color:#28382f;text-decoration:none;
  font-size:12.5px;font-weight:600;white-space:nowrap}
.saved svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:8px;
  padding:8px 15px;border:1px solid transparent;text-decoration:none;font-weight:700;
  font-size:12.5px;cursor:pointer;white-space:nowrap}
.btn-primary{background:var(--ever);color:#fff}
.btn-primary:hover{background:var(--deep)}
.btn-outline{background:var(--paper);color:var(--ever);border-color:#e2d8c4}
.btn-outline:hover{border-color:#c3b79c}
/* 44x44 is the minimum comfortable touch target; the glyph keeps its 25px
   size and is centred inside that box rather than the box being shrunk to
   the glyph. Fixed width/height (not padding) so the target cannot vary with
   the font. The button is the flex-end child of .nav-actions, so the extra
   width grows leftward into empty header space -- the brand does not move,
   and the header height is unchanged (46px desktop / 54px mobile both clear
   44px). */
.menu{display:none;background:none;border:0;font-size:25px;line-height:1;color:var(--ever);
  cursor:pointer;padding:0;width:44px;height:44px;flex:0 0 auto;
  align-items:center;justify-content:center}

/* hero -- photo bleeds off the right edge and fades into the page */
.ph-hero{position:relative;overflow:hidden}
/* max-width keeps the frame near the photograph's own 2.52 aspect. Without it
   the panel widens with the viewport (3.46 at 1920) and object-fit:cover pays
   for that by cropping ~27% off the height -- which is exactly the skyline and
   river the approved composition is built around. */
.hero-media{position:absolute;top:0;right:0;bottom:0;width:55%;max-width:820px;
  pointer-events:none}
.hero-media img{width:100%;height:100%;object-fit:cover;object-position:50% 45%;
  -webkit-mask-image:linear-gradient(to right,rgba(0,0,0,0) 0,#000 14%);
          mask-image:linear-gradient(to right,rgba(0,0,0,0) 0,#000 14%)}
.hero-inner{position:relative;z-index:2;padding:20px 0 17px}
.ph-hero h1{margin:0 0 10px;font-size:37px;line-height:1.12;letter-spacing:-.8px;
  color:var(--ever);max-width:500px}
.ph-hero h1 em{font-style:italic;color:var(--warm)}
.ph-hero .sub{margin:0 0 15px;font-size:13px;line-height:1.5;max-width:385px;color:#3f4f47}
/* The badge is a child of the centred wrap, so `right:0` pins it to the wrap
   edge -- at wide viewports that lands mid-photo, on top of the walker. The
   calc re-anchors it to the photo's own right edge (= viewport edge) with a
   fixed 24px clearance, dropping it into the open path/grass corner. Any
   sub-pixel drift from the scrollbar in 100vw is clipped by .ph-hero's
   overflow:hidden, so it can never widen the page. */
.hero-badge{position:absolute;right:calc((100% - 100vw)/2 + 24px);bottom:22px;
  z-index:3;max-width:225px;
  background:rgba(18,64,44,.94);color:#fff;border-radius:13px;padding:12px 15px}
.hero-badge b{display:flex;align-items:center;gap:8px;font-size:13.5px;font-weight:700;
  margin-bottom:6px}
.hero-badge svg{width:16px;height:16px;flex:0 0 auto;fill:none;stroke:currentColor;
  stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
.hero-badge p{margin:0;font-size:12px;line-height:1.42;color:#e4ede8}

/* search row (inline on the page -- no floating panel) */
.ph-search{display:grid;grid-template-columns:minmax(0,1fr) 162px 96px;gap:10px;max-width:615px}
.ph-field{display:flex;align-items:center;gap:9px;border:1px solid #e6dfd0;border-radius:10px;
  background:var(--paper);padding:0 12px;min-height:40px;font-size:12.5px;
  box-shadow:0 1px 2px rgba(30,45,38,.04)}
.ph-field svg{width:15px;height:15px;flex:0 0 auto;fill:none;stroke:#5c6a63;stroke-width:1.8;
  stroke-linecap:round;stroke-linejoin:round}
.ph-field input{border:0;outline:0;flex:1;min-width:0;background:transparent;font:inherit;color:var(--ink)}
.ph-field input::placeholder{color:#96a09a}
.ph-field.loc b{font-weight:650}
.ph-field.loc .caret{margin-left:auto;stroke:#8b968f}
.ph-go{border:0;border-radius:10px;background:var(--ever);color:#fff;font-weight:700;font-size:12.5px;
  min-height:40px;display:flex;align-items:center;justify-content:center;text-decoration:none;cursor:pointer}
.ph-go:hover{background:var(--deep)}
.ph-chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
.ph-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid #e9e2d4;border-radius:9px;
  background:var(--paper);padding:6px 11px;font-size:10.5px;font-weight:600;color:#2c3d35;
  text-decoration:none;white-space:nowrap}
.ph-chip:hover{border-color:#a6b8ac}
.ph-chip svg{width:14px;height:14px;flex:0 0 auto;fill:none;stroke:#3d4f46;stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round}

/* two-column body. The secondary column is PROPORTIONAL, not a fixed width:
   a fixed sidebar keeps its pixels as the viewport narrows and progressively
   crushes the six place cards. 31.5% holds the approved 66/31 balance at
   every width, with a floor so the glance table never collapses. */
.ph-body{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,31.5%);gap:26px;
  align-items:start;padding-top:2px}
.col-main{min-width:0}
.col-side{min-width:0;display:flex;flex-direction:column;gap:12px}

/* qualitative trust strip (no counts -- the approved design states the
   promise, the pages carry the evidence) */
.ph-trust{display:flex;flex-wrap:wrap;gap:8px 38px;align-items:center;background:var(--panel);
  border:1px solid #efe9dc;border-radius:11px;padding:8px 18px}
.ph-trust span{display:inline-flex;align-items:center;gap:8px;font-size:11.5px;font-weight:650;color:#24352d}
.ph-trust svg{width:15px;height:15px;flex:0 0 auto;fill:none;stroke:var(--ever);stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}

/* sections */
.section{padding:17px 0 0}
.sechead{display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:9px}
.sechead h2{margin:0;font-size:19px;letter-spacing:-.3px;color:var(--ever)}
.sechead a{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;
  color:var(--ever);text-decoration:none;white-space:nowrap}
.sechead a:hover{text-decoration:underline}
.sechead a svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round}

/* quick-start cards */
.start-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px}
.start-card{display:flex;align-items:center;gap:10px;background:var(--paper);border:1px solid var(--line);
  border-radius:11px;padding:11px 12px;text-decoration:none;color:var(--ink);font-weight:700;
  font-size:11px;line-height:1.25;transition:.15s border-color}
.start-card:hover{border-color:#a6b8ac}
.start-card .ico{width:22px;height:22px;flex:0 0 auto}
.start-card .ico svg{width:100%;height:100%;display:block;fill:currentColor}
.start-card .ico.g{color:var(--ever)}
.start-card .ico.o{color:var(--warm)}
.start-card .chev{margin-left:auto;width:14px;height:14px;flex:0 0 auto;fill:none;stroke:#4c5c54;
  stroke-width:2;stroke-linecap:round;stroke-linejoin:round}

/* recently verified place cards */
.places{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
.place{display:flex;flex-direction:column;background:var(--paper);border:1px solid var(--line);
  border-radius:11px;overflow:hidden;text-decoration:none;color:inherit;
  box-shadow:0 1px 3px rgba(35,52,45,.04);transition:.2s transform,.2s box-shadow}
.place:hover{transform:translateY(-2px);box-shadow:0 9px 20px rgba(31,58,48,.11)}
.place .photo{display:block;height:64px;flex:0 0 auto;background-size:cover;
  background-position:center;background-color:#e7e0d2}
.place .body{display:flex;flex-direction:column;flex:1;padding:7px 8px 8px}
/* min-height reserves the two lines the approved comp shows on every card, so
   a short name never leaves its card visually lighter than its neighbours. */
.place h3{margin:0 0 5px;font-family:inherit;font-size:10px;font-weight:700;line-height:1.22;
  min-height:24px;color:var(--ink)}
.place .fact{display:flex;align-items:center;gap:6px;font-size:9.5px;color:#33443c;margin-top:2px}
.place .fact svg{width:12px;height:12px;flex:0 0 auto;fill:none;stroke:var(--fact);stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round}
.place .vline{display:flex;align-items:center;gap:5px;margin-top:auto;padding-top:5px;
  border-top:1px solid #f1ebde;font-size:9px;white-space:nowrap;color:var(--ok);font-weight:650}
.place .vline svg{width:11px;height:11px;flex:0 0 auto;fill:none;stroke:currentColor;stroke-width:2.4;
  stroke-linecap:round;stroke-linejoin:round}

/* trip-planning cards */
.trip-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.trip-card{display:grid;grid-template-columns:minmax(0,38%) minmax(0,1fr);min-height:86px;
  background:var(--paper);border:1px solid var(--line);border-radius:11px;overflow:hidden;
  text-decoration:none;color:inherit}
.trip-card:hover{box-shadow:0 8px 18px rgba(31,58,48,.09)}
.trip-card img{width:100%;height:100%;object-fit:cover}
.trip-copy{padding:9px 11px 10px;display:flex;flex-direction:column;gap:3px}
.trip-copy .ico{width:26px;height:26px;flex:0 0 auto;border-radius:50%;display:grid;place-items:center;color:#fff}
.trip-copy .ico.g{background:var(--ever)}
.trip-copy .ico.o{background:var(--warm)}
.trip-copy .ico svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.8;
  stroke-linecap:round;stroke-linejoin:round}
.trip-copy h3{margin:1px 0 0;font-family:inherit;font-size:12px;font-weight:700}
.trip-copy p{margin:0;font-size:10px;line-height:1.38;color:var(--muted)}
.trip-copy .go{margin-top:auto;font-size:10px;font-weight:700;color:var(--ever);text-decoration:underline}

/* travel-better band */
.ph-band{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--panel);
  border:1px solid #efe9dc;border-radius:12px;padding:12px 18px;margin-top:16px;
  position:relative;overflow:hidden}
.ph-band .pawcircle{width:36px;height:36px;flex:0 0 auto;border-radius:50%;background:var(--ever);
  color:#fff;display:grid;place-items:center}
.ph-band .pawcircle svg{width:19px;height:17px;fill:currentColor}
.ph-band h3{margin:0 0 1px;font-size:16.5px;color:var(--ever)}
.ph-band p{margin:0;font-size:11px;color:var(--muted)}
.ph-band .actions{display:flex;gap:10px;margin-left:auto;position:relative;z-index:1}
.ph-band .skyline{flex:0 0 150px;align-self:flex-end;margin:0 0 -12px 14px;color:var(--ever);
  opacity:.2;pointer-events:none}
.ph-band .skyline svg{width:100%;height:auto;fill:none;stroke:currentColor;stroke-width:1.3;
  stroke-linecap:round;stroke-linejoin:round}

/* sidebar */
.side-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:12px}
.side-card h3{margin:0 0 8px;font-size:16px;letter-spacing:-.2px;color:var(--ever)}
.glance{width:100%;border-collapse:collapse;font-size:10.5px;table-layout:fixed}
.glance th{font-size:9.5px;color:#4d5c55;font-weight:700;text-align:left;padding:0 3px 5px;
  border-bottom:1px solid #ece5d6}
.glance td{padding:4px 3px;border-bottom:1px solid #f3eee2;vertical-align:middle;white-space:nowrap}
.glance tr:last-child td{border-bottom:0}
.glance td.name{font-weight:700;color:var(--ever);font-size:10px;line-height:1.25;white-space:normal}
.glance td.name a{text-decoration:none;color:inherit}
.glance td.name a:hover{text-decoration:underline}
.glance .ok svg{width:12px;height:12px;fill:none;stroke:var(--ok);stroke-width:2.6;
  stroke-linecap:round;stroke-linejoin:round}
/* NB: never give .ns a `display` other than table-cell -- it sits on the <td>
   itself, and taking it out of table layout shifts every following column. */
.glance .ns{color:#9aa39c;font-size:8.5px;line-height:1.2;white-space:normal}
.glance-more{display:inline-flex;align-items:center;gap:6px;margin-top:8px;font-size:11px;
  font-weight:700;color:var(--ever);text-decoration:underline}
.glance-more svg{width:12px;height:12px;fill:none;stroke:currentColor;stroke-width:2;
  stroke-linecap:round;stroke-linejoin:round}
.why-card{background:var(--soft);border:1px solid #efe9dc;border-radius:12px;padding:12px}
.why-card h3{margin:0 0 5px;font-size:16px;letter-spacing:-.2px;color:var(--ever)}
.why-card>p{margin:0 0 11px;font-size:11.5px;color:#41504a}
.why-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.why-grid div{display:flex;align-items:flex-start;gap:7px;font-size:10px;font-weight:650;
  line-height:1.28;color:#25352e}
.why-grid svg{width:19px;height:19px;flex:0 0 auto;fill:none;stroke:var(--ever);stroke-width:1.6;
  stroke-linecap:round;stroke-linejoin:round}
.side-skyline{color:var(--ever);opacity:.11;padding:6px 2px 0;pointer-events:none}
.side-skyline svg{width:100%;height:auto;fill:none;stroke:currentColor;stroke-width:1.2;
  stroke-linecap:round;stroke-linejoin:round}

/* footer */
.footer{padding:30px 0 46px;margin-top:28px;border-top:1px solid var(--line);background:var(--paper)}
.footer-grid{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:28px}
.footer h4{margin:0 0 10px;font-family:inherit;font-size:14px;color:var(--ever)}
.footer a{display:block;color:#53615c;text-decoration:none;font-size:13px;margin:7px 0}
.footer a:hover{color:var(--ever)}
.footer .brand{font-size:19px}
.note{margin-top:12px;font-size:12px;line-height:1.5;color:#74817b;max-width:420px}

/* responsive */
@media(max-width:1180px){
  .ph-body{grid-template-columns:minmax(0,1fr)}
  .col-side{max-width:none}
  .why-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:1080px){
  .links{display:none}.menu{display:flex}.saved{display:none}
  .links.pt-open{display:flex;position:absolute;top:46px;left:0;right:0;flex-direction:column;
    align-items:flex-start;gap:0;background:#fffdf9;border-bottom:1px solid #ece6da;
    padding:6px 24px 14px;box-shadow:0 18px 40px rgba(26,50,41,.12);z-index:29}
  .links.pt-open a{padding:13px 0;width:100%;font-size:15px}
  .places{grid-template-columns:repeat(3,minmax(0,1fr))}
  .place .photo{height:104px}
  .place h3{font-size:12.5px;min-height:0}
}
@media(max-width:920px){
  .ph-hero{overflow:visible}
  .hero-media{position:static;width:auto;height:210px;margin:0 auto 18px;border-radius:14px;
    overflow:hidden;max-width:calc(100% - 48px)}
  .hero-media img{height:210px;-webkit-mask-image:none;mask-image:none}
  .hero-inner{padding-top:0}
  .hero-badge{position:static;max-width:none;margin-top:16px;display:block}
  .ph-hero h1{font-size:36px}
  .start-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .trip-grid{grid-template-columns:minmax(0,1fr)}
  .trip-card{min-height:0}
}
@media(max-width:720px){
  .wrap{width:min(100% - 28px,var(--max))}
  .hero-media{max-width:calc(100% - 28px)}
  .ph-top .wrap{height:54px;gap:10px}
  .brand{font-size:17px}
  .nav-actions .btn{display:none}
  .ph-hero h1{font-size:30px;letter-spacing:-.6px}
  .ph-search{grid-template-columns:minmax(0,1fr);max-width:none}
  .places{grid-template-columns:repeat(2,minmax(0,1fr))}
  .start-grid{grid-template-columns:minmax(0,1fr);gap:10px}
  .sechead h2{font-size:19px}
  .why-grid{grid-template-columns:minmax(0,1fr)}
  .ph-trust{gap:9px 24px}
  .ph-band .actions{margin-left:0;width:100%;flex-direction:column}
  .ph-band .actions .btn{width:100%}
  .ph-band .skyline{display:none}
  .footer-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .footer-grid>div:first-child{grid-column:1/-1}
}
@media(max-width:430px){
  .places{grid-template-columns:minmax(0,1fr)}
  .place .photo{height:130px}
  .trip-card{grid-template-columns:minmax(0,40%) minmax(0,1fr)}
}

/* ---- wide desktop (>=1600px) ---------------------------------------------
   The compact 1280 shell is calibrated for 1440. On a 1920 display it strands
   ~320px of dead margin per side and the page reads as a shrunken screenshot.
   This block widens the shell to 1680 (120px margins at 1920) and pins the
   secondary column to a fixed 360px, so every pixel gained goes to the main
   column and the six place cards -- the sidebar must not grow with the page.
   Type and controls lift ~10%; vertical density is unchanged, and the hero
   block (crop, mask, max-width, badge anchor) is deliberately absent here so
   the approved hero framing carries over untouched. */
@media(min-width:1600px){
  :root{--max:1680px}
  .wrap{width:min(var(--max),calc(100% - 120px))}

  .ph-top .wrap{height:52px}
  .brand{font-size:21px}
  .links{gap:24px}
  .links a{font-size:13.5px}
  .saved{font-size:13.5px}
  .saved svg{width:16px;height:16px}
  .btn{font-size:13.5px;padding:9px 17px}

  .ph-hero h1{font-size:41px;max-width:560px}
  .ph-hero .sub{font-size:14.5px;max-width:430px;margin-bottom:17px}
  .ph-search{grid-template-columns:minmax(0,1fr) 178px 108px;gap:11px;max-width:690px}
  .ph-field{min-height:44px;font-size:13.5px}
  .ph-field svg{width:16px;height:16px}
  .ph-go{min-height:44px;font-size:13.5px}
  .ph-chip{font-size:11.5px;padding:7px 13px}
  .ph-chip svg{width:15px;height:15px}

  .ph-body{grid-template-columns:minmax(0,1fr) 360px;gap:30px}
  .ph-trust{padding:10px 22px;gap:9px 46px}
  .ph-trust span{font-size:12.5px}
  .ph-trust svg{width:16px;height:16px}

  .section{padding:20px 0 0}
  .sechead{margin-bottom:11px}
  .sechead h2{font-size:21px}
  .sechead a{font-size:12.5px}

  .start-grid{gap:14px}
  .start-card{font-size:12px;padding:13px 15px;gap:11px}
  .start-card .ico{width:25px;height:25px}

  .places{gap:14px}
  .place .photo{height:96px}
  .place .body{padding:9px 11px 10px}
  .place h3{font-size:11.5px;line-height:1.24;min-height:29px;margin-bottom:6px}
  .place .fact{font-size:10.5px;gap:7px;margin-top:3px}
  .place .fact svg{width:13px;height:13px}
  .place .vline{font-size:10px;padding-top:6px}
  .place .vline svg{width:12px;height:12px}

  .trip-grid{gap:16px}
  .trip-card{min-height:104px}
  .trip-copy{padding:11px 14px 12px}
  .trip-copy .ico{width:29px;height:29px}
  .trip-copy .ico svg{width:16px;height:16px}
  .trip-copy h3{font-size:13.5px}
  .trip-copy p{font-size:11px}
  .trip-copy .go{font-size:11px}

  .ph-band{padding:15px 22px;margin-top:20px;gap:16px}
  .ph-band .pawcircle{width:40px;height:40px}
  .ph-band .pawcircle svg{width:21px;height:19px}
  .ph-band h3{font-size:18px}
  .ph-band p{font-size:12px}
  .ph-band .skyline{flex:0 0 175px}

  .side-card,.why-card{padding:15px}
  .side-card h3,.why-card h3{font-size:17.5px}
  .glance{font-size:11.5px}
  .glance th{font-size:10.5px;padding:0 4px 6px}
  .glance td{padding:5px 4px}
  .glance td.name{font-size:11px}
  .glance .ns{font-size:9.5px}
  .glance .ok svg{width:13px;height:13px}
  .glance-more{font-size:12px;margin-top:10px}
  .why-card>p{font-size:12.5px;margin-bottom:13px}
  .why-grid{gap:12px}
  .why-grid div{font-size:11px}
  .why-grid svg{width:21px;height:21px}

  .footer{padding:34px 0 50px}
  .footer h4{font-size:15px}
  .footer a{font-size:14px}
  .note{font-size:12.5px;max-width:470px}
}"""

_JS = ("<script>(function(){var b=document.querySelector('.menu'),"
       "l=document.querySelector('.links');if(b&&l){b.addEventListener('click',function(){"
       "var o=l.classList.toggle('pt-open');b.setAttribute('aria-expanded',String(o));});}"
       "})();</script>")


# --------------------------------------------------------------------------- #
# Inline SVGs. Thin-stroke line icons for controls/trust marks; solid glyphs
# for the quick-start cards and the paw mark, exactly as the mockup shows.
# --------------------------------------------------------------------------- #

_PAW_SOLID = ('<svg viewBox="0 0 48 42" aria-hidden="true">'
              '<ellipse cx="24" cy="29" rx="12.5" ry="10.5"/>'
              '<ellipse cx="8.5" cy="18" rx="5" ry="7" transform="rotate(-18 8.5 18)"/>'
              '<ellipse cx="18" cy="8.5" rx="5" ry="7" transform="rotate(-7 18 8.5)"/>'
              '<ellipse cx="30" cy="8.5" rx="5" ry="7" transform="rotate(7 30 8.5)"/>'
              '<ellipse cx="39.5" cy="18" rx="5" ry="7" transform="rotate(18 39.5 18)"/></svg>')

_SVG_CARET = '<svg class="caret" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
_SVG_HEART = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0'
              'L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.9-8.6a5.5 5.5 0 0 0-.1-7.8Z"/></svg>')
_SVG_SEARCH = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/>'
               '<path d="m20 20-4-4"/></svg>')
_SVG_PIN = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/>'
            '<circle cx="12" cy="10" r="2.5"/></svg>')
_SVG_CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>'
_SVG_ARROW = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15m-6-7 7 7-7 7"/></svg>'
_SVG_CHEV = ('<svg class="chev" viewBox="0 0 24 24" aria-hidden="true">'
             '<path d="m9 5 7 7-7 7"/></svg>')

# hero/chip/trust line icons
_SVG_CAT = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M4.5 9.5V4l4 3h7l4-3v5.5a7.5 7.5 0 0 1-15 0Z"/>'
            '<path d="M9.5 12h.01M14.5 12h.01M12 14.2v1.1"/></svg>')
_SVG_PAWLINE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5.6" cy="10.4" r="1.9"/>'
                '<circle cx="9.9" cy="6.2" r="1.9"/><circle cx="14.1" cy="6.2" r="1.9"/>'
                '<circle cx="18.4" cy="10.4" r="1.9"/>'
                '<path d="M12 12c-3 0-5.4 2.2-5.4 4.9 0 2 2.2 3.5 5.4 3.5s5.4-1.5 5.4-3.5c0-2.7-2.4-4.9-5.4-4.9Z"/></svg>')
_SVG_SCALE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.4 6.2a2.6 2.6 0 1 1 5.2 0"/>'
              '<path d="M5.2 6.2h13.6l1.5 12.3a2 2 0 0 1-2 2.3H5.7a2 2 0 0 1-2-2.3L5.2 6.2Z"/>'
              '<path d="M12 11v3.4"/></svg>')
_SVG_TAG = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M3.2 11.2V4.4a1.2 1.2 0 0 1 1.2-1.2h6.8l9.4 9.4-8 8-9.4-9.4Z"/>'
            '<circle cx="8" cy="8" r="1.5"/></svg>')
_SVG_SHIELDCHK = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
                  '<path d="M12 3 20 6v5.5c0 5-3 8.2-8 10.5-5-2.3-8-5.5-8-10.5V6l8-3Z"/>'
                  '<path d="m8.6 12 2.4 2.4 4.6-4.8"/></svg>')
_SVG_QUESTION = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
                 '<path d="M9.4 9.3a2.7 2.7 0 0 1 5.2.9c0 1.8-2.6 2.2-2.6 3.9"/>'
                 '<path d="M12 17.4h.01"/></svg>')
_SVG_CALENDAR = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
                 '<rect x="3.5" y="5" width="17" height="15.5" rx="2.4"/>'
                 '<path d="M3.5 9.6h17M8 3.2v3.4M16 3.2v3.4M7.6 13h2M11 13h2M14.4 13h2M7.6 16.6h2M11 16.6h2"/></svg>')

# fee icon -- deliberately neutral (see module docstring): a price tag, never
# a "$$" tier glyph, because no price band was ever verified.
_SVG_FEE = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="2.6" y="6.2" width="18.8" height="11.6" rx="2.2"/>'
            '<circle cx="12" cy="12" r="2.6"/><path d="M6 9.6v4.8M18 9.6v4.8"/></svg>')

# trip-card icons
_SVG_TREE = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
             '<path d="M12 3 6.8 10h2.6L5.4 15.6h5.2V21h2.8v-5.4h5.2L14.6 10h2.6L12 3Z"/></svg>')
_SVG_STETH = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
              '<path d="M6 3v5.2a4 4 0 0 0 8 0V3"/><path d="M6 3H4.4M14 3h1.6"/>'
              '<path d="M10 12.4v2.4a5 5 0 0 0 5 5 3.8 3.8 0 0 0 3.8-3.8v-1.6"/>'
              '<circle cx="18.8" cy="12.4" r="2.1"/></svg>')
_SVG_FORK = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
             '<path d="M7 3v5.6c0 1.6 1 2.8 2.4 2.8s2.4-1.2 2.4-2.8V3M9.4 3v18"/>'
             '<path d="M17.6 3c-1.9 1.5-2.4 4.2-2.4 6.6h2.4V21"/></svg>')

# "why" card icons
_SVG_CLIPBOARD = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
                  '<rect x="4.6" y="4.4" width="14.8" height="17" rx="2.2"/>'
                  '<path d="M9.2 4.4V3.2a1.2 1.2 0 0 1 1.2-1.2h3.2a1.2 1.2 0 0 1 1.2 1.2v1.2Z"/>'
                  '<path d="M8.6 10.2h.01M8.6 13.6h.01M8.6 17h.01M11.4 10.2h4.6M11.4 13.6h4.6M11.4 17h3"/></svg>')
_SVG_PEOPLE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11.4" cy="9.2" r="3.3"/>'
               '<path d="M4.8 20.4a6.6 6.6 0 0 1 13.2 0"/>'
               '<path d="M18.4 7.4 20 5.8M18.8 11.4l1.8 1.2M5.6 7.4 4 5.8M5.2 11.4 3.4 12.6"/></svg>')

_SKYLINE = ('<svg viewBox="0 0 300 70" aria-hidden="true"><path d="M2 66V46h10v20m0 0V30h8l2-8 2 8h8v36'
            'm0 0V40h12v26m0 0V22h6V14h6v8h6v44m0 0V50h14v16m0 0V34h10l2-10 2 10h10v32m0 0V44h12v22'
            'm0 0V18h5l3-12 3 12h5v48m0 0V52h12v14m0 0V38h10v28m0 0V26h7v-8h7v8h7v40m0 0V48h12v18'
            'm0 0V36h11v30m0 0V56h12v10m0 0V44h10v22M2 66h296"/></svg>')

# solid quick-start glyphs (filled, uncircled -- exactly as the mockup draws them)
_ICO_CAT_SOLID = ('<svg viewBox="0 0 32 32" aria-hidden="true">'
                  '<path d="M4 12.5V4l6 4.5h12L28 4v8.5a12 12 0 0 1-24 0Z"/>'
                  '<circle cx="12" cy="15" r="1.6" fill="#fff"/><circle cx="20" cy="15" r="1.6" fill="#fff"/>'
                  '<path d="M14.4 19h3.2l-1.6 2Z" fill="#fff"/></svg>')
_ICO_PAW_SOLID = ('<svg viewBox="0 0 32 32" aria-hidden="true">'
                  '<ellipse cx="16" cy="22" rx="8" ry="6.6"/>'
                  '<ellipse cx="6" cy="14" rx="3.4" ry="4.6" transform="rotate(-18 6 14)"/>'
                  '<ellipse cx="12.4" cy="7.6" rx="3.4" ry="4.6" transform="rotate(-7 12.4 7.6)"/>'
                  '<ellipse cx="19.6" cy="7.6" rx="3.4" ry="4.6" transform="rotate(7 19.6 7.6)"/>'
                  '<ellipse cx="26" cy="14" rx="3.4" ry="4.6" transform="rotate(18 26 14)"/></svg>')
_ICO_SCALE_SOLID = ('<svg viewBox="0 0 32 32" aria-hidden="true">'
                    '<path d="M12.4 8a3.6 3.6 0 1 1 7.2 0h5.2l2 18.6a2.6 2.6 0 0 1-2.6 2.9H7.8a2.6 2.6 0 0 1-2.6-2.9'
                    'L7.2 8h5.2Zm3.6-1.4A1.4 1.4 0 0 0 14.6 8h2.8A1.4 1.4 0 0 0 16 6.6Z"/>'
                    '<circle cx="16" cy="18" r="4.4" fill="#fff"/></svg>')
_ICO_TAG_SOLID = ('<svg viewBox="0 0 32 32" aria-hidden="true">'
                  '<path d="M3.4 14.4V5.2A1.8 1.8 0 0 1 5.2 3.4h9.2l14 14-10.8 10.8-14-14Z" '
                  'fill="none" stroke="currentColor" stroke-width="2.6" stroke-linejoin="round"/>'
                  '<circle cx="9.4" cy="9.4" r="2" fill="currentColor"/>'
                  '<path d="M16.6 14.2v6.4M14 16.4h5.2" fill="none" stroke="currentColor" '
                  'stroke-width="2.2" stroke-linecap="round"/></svg>')


# --------------------------------------------------------------------------- #
# Fact formatting (honest; copied from the committed package, never invented).
# --------------------------------------------------------------------------- #

def _fee(f: Dict[str, str]) -> str:
    fee = (f.get("pet_fee") or "").strip()
    if not fee:
        return "Fee not stated"
    b = (f.get("fee_basis") or "").lower()
    unit = ("night" if "night" in b else "day" if "day" in b else "stay" if "stay" in b
            else "week" if "week" in b else "")
    return "%s / %s" % (fee, unit) if unit else fee


def _pets(f: Dict[str, str]) -> str:
    c = (f.get("pet_count_limit") or "").strip()
    if not c:
        return "Pets not stated"
    return "%s pet" % c if c == "1" else "%s pets" % c


def _weight_lb(f: Dict[str, str]) -> str:
    w = (f.get("weight_limit") or "").strip()
    if not w:
        return ""
    m = re.search(r"(\d+)", w)
    if m and re.search(r"(lb|pound)", w, re.I):
        return "%s lb" % m.group(1)
    return w


def _facts_of(name: str, facts_map: Dict) -> Dict[str, str]:
    from scripts.pettripfinder.site_data import normalize_name
    entry = facts_map.get(normalize_name(name))
    return (entry or {}).get("facts", {}) if entry else {}


def _entry_of(name: str, facts_map: Dict) -> Dict:
    from scripts.pettripfinder.site_data import normalize_name
    return facts_map.get(normalize_name(name)) or {}


def _short_place(name: str) -> str:
    """Sidebar label: the real name minus a redundant standalone "Columbus".

    Purely subtractive -- nothing is added, reordered or paraphrased -- and the
    caller re-checks uniqueness across the chosen set before using the result,
    so two same-brand properties can never collapse into one ambiguous label.
    """
    short = re.sub(r"\s+", " ", re.sub(r"\bColumbus\b", " ", name)).strip()
    return short if len(short.split()) >= 2 else name


# --------------------------------------------------------------------------- #
# Data selection (real records only; deterministic).
# --------------------------------------------------------------------------- #

# Six recently verified places, chosen for corridor variety and fact richness
# (all fourteen stay one click away via "View all places"). Every entry is a
# real committed-package record; missing names back-fill deterministically.
_PREFERRED_FEATURED = (
    "Drury Inn & Suites Columbus Grove City",
    "Sonesta Columbus Downtown",
    "Hyatt Regency Columbus",
    "Drury Inn & Suites Columbus Dublin",
    "Hyatt Place Columbus OSU",
    "Home2 Suites by Hilton Columbus Dublin",
)

# The five glance rows: the records whose sources stated the most, across four
# distinct brands. The last row intentionally carries "Not stated" cells --
# that is the "Honest unknowns" promise the page makes, shown rather than told.
_GLANCE_PICKS = (
    "Drury Inn & Suites Columbus Grove City",
    "Drury Inn & Suites Columbus Dublin",
    "Hyatt Regency Columbus",
    "Hyatt Place Columbus OSU",
    "Sonesta Columbus Downtown",
)


def select_featured(hotel_rows: List[Dict], facts_map: Dict, limit: int = 6) -> List[Dict]:
    by_name = {r["name"]: r for r in hotel_rows}
    chosen: List[Dict] = []
    used = set()
    for pref in _PREFERRED_FEATURED:
        row = by_name.get(pref)
        if row and pref not in used:
            chosen.append(row)
            used.add(pref)
    if len(chosen) < limit:
        pool = sorted((r for r in hotel_rows if r["name"] not in used), key=lambda r: r["name"].lower())
        pool.sort(key=lambda r: (0 if _facts_of(r["name"], facts_map).get("pet_fee") else 1))
        for r in pool:
            if len(chosen) >= limit:
                break
            chosen.append(r)
            used.add(r["name"])
    return chosen[:limit]


def select_glance(hotel_rows: List[Dict], facts_map: Dict, limit: int = 5) -> List[Dict]:
    by_name = {r["name"]: r for r in hotel_rows}
    chosen = [by_name[n] for n in _GLANCE_PICKS if n in by_name][:limit]
    if len(chosen) < limit:
        used = {r["name"] for r in chosen}
        pool = sorted((r for r in hotel_rows if r["name"] not in used), key=lambda r: r["name"].lower())
        pool.sort(key=lambda r: (0 if _facts_of(r["name"], facts_map).get("pet_fee") else 1))
        chosen += pool[: limit - len(chosen)]
    return chosen


# --------------------------------------------------------------------------- #
# Sections.
# --------------------------------------------------------------------------- #

_EMERGENCY_ANCHOR = "#trip"

_NAV = (
    ("Places to Stay", "/pet-friendly-hotels/", True),
    ("Things to Do", "/pet-friendly-parks/", True),
    ("Eat &amp; Drink", "/pet-friendly-restaurants/", True),
    ("Emergency Pet Care", _EMERGENCY_ANCHOR, False),
    ("How we verify", "/methodology/", False),
)


def _header() -> str:
    nav = "".join(
        '<a href="%s">%s%s</a>' % (href, label, _SVG_CARET if caret else "")
        for label, href, caret in _NAV)
    return ('<header class="ph-top"><div class="wrap">'
            '<a class="brand" href="/">PetTripFinder<span class="dot">&middot;</span>'
            '<em>Columbus</em></a>'
            '<nav class="links" aria-label="Primary">%s</nav>'
            '<div class="nav-actions"><a class="saved" href="/pet-friendly-hotels/">%sSaved</a>'
            '<a class="btn btn-primary" href="/pet-friendly-hotels/policy-comparison/">'
            'Compare places</a>'
            '<button class="menu" aria-label="Open menu" aria-expanded="false">&#9776;</button>'
            '</div></div></header>') % (nav, _SVG_HEART)


# Browse/navigation chips -- each is a plain link into the real comparison
# table. No live filtering, availability or booking is implied.
_CHIPS = (
    (_SVG_CAT, "Cats accepted", "/pet-friendly-hotels/policy-comparison/"),
    (_SVG_PAWLINE, "Two or more pets", "/pet-friendly-hotels/policy-comparison/"),
    (_SVG_SCALE, "No stated weight limit", "/pet-friendly-hotels/policy-comparison/"),
    (_SVG_TAG, "Lower pet charges", "/pet-friendly-hotels/policy-comparison/"),
    (_SVG_SHIELDCHK, "Recently verified", "/methodology/"),
)


def _hero() -> str:
    chips = "".join('<a class="ph-chip" href="%s">%s%s</a>' % (href, icon, _e(label))
                    for icon, label, href in _CHIPS)
    search = (
        '<form class="ph-search" action="/pet-friendly-hotels/" method="get">'
        '<label class="ph-field">%s<input type="search" name="q" '
        'placeholder="Search places to stay, parks, patios, or corridors" '
        'aria-label="Search places to stay, parks, patios, or corridors"></label>'
        '<span class="ph-field loc">%s<b>Columbus, OH</b>%s</span>'
        '<button class="ph-go" type="submit">Search</button></form>'
    ) % (_SVG_SEARCH, _SVG_PIN, _SVG_CARET)

    return (
        '<section class="ph-hero">'
        '<div class="hero-media"><img src="assets/hero-right.jpg" '
        'alt="Traveler walking a dog along the Scioto riverfront in Columbus"></div>'
        '<div class="wrap hero-inner">'
        '<h1>Find a Columbus trip<br>that <em>actually</em> works<br>for your pet.</h1>'
        '<p class="sub">Compare pet charges, accepted species, pet limits, weight '
        'restrictions, and recently verified places before you book.</p>'
        '%s<div class="ph-chips">%s</div>'
        '<aside class="hero-badge"><b>%sColumbus, Ohio</b>'
        '<p>Pet-friendly travel starts with verified facts.</p></aside>'
        '</div></section>'
    ) % (search, chips, _SVG_PIN)


def _trust_strip() -> str:
    items = (
        (_SVG_SHIELDCHK, "Official-source policies"),
        (_SVG_QUESTION, "Honest unknowns"),
        (_SVG_CALENDAR, "Review dates you can trust"),
    )
    return '<div class="ph-trust">%s</div>' % "".join(
        "<span>%s%s</span>" % (icon, _e(label)) for icon, label in items)


# Quick-starts. Each is a plain browse link into the real comparison table,
# where species, pet counts, weight limits and charges sit side by side.
_START_CARDS = (
    (_ICO_CAT_SOLID, "g", "Traveling with a cat"),
    (_ICO_PAW_SOLID, "o", "Two or more pets"),
    (_ICO_SCALE_SOLID, "g", "Avoid weight limits"),
    (_ICO_TAG_SOLID, "o", "Compare pet charges"),
)


def _start_section() -> str:
    cards = "".join(
        '<a class="start-card" href="/pet-friendly-hotels/policy-comparison/">'
        '<span class="ico %s">%s</span>%s%s</a>' % (tone, icon, _e(label), _SVG_CHEV)
        for icon, tone, label in _START_CARDS)
    return ('<section class="section">'
            '<div class="sechead"><h2>Start with what matters to your trip</h2></div>'
            '<div class="start-grid">%s</div></section>') % cards


def _place_card(row: Dict, facts_map: Dict, photo: str) -> str:
    name = row["name"]
    entry = _entry_of(name, facts_map)
    f = entry.get("facts", {})
    verified = _friendly_date(entry.get("verified_at", "") or row.get("observed_at", ""))
    weight = _weight_lb(f)
    limits = _pets(f) + (" &middot; %s" % _e(weight) if weight else "")
    return (
        '<a class="place" href="/pet-friendly-hotels/%s/">'
        '<span class="photo" style="background-image:url(\'assets/%s\')"></span>'
        '<span class="body"><h3>%s</h3>'
        '<span class="fact">%s%s</span><span class="fact">%s%s</span>'
        '<span class="vline">%sVerified %s</span>'
        "</span></a>"
    ) % (_slug(name), _e(photo), _e(name), _SVG_FEE, _e(_fee(f)),
         _SVG_PAWLINE, limits, _SVG_CHECK, _e(verified))


def _featured(hotel_rows: List[Dict], facts_map: Dict) -> str:
    featured = select_featured(hotel_rows, facts_map, 6)
    photos = ["hotel1.jpg", "hotel2.jpg", "hotel3.jpg", "hotel4.jpg", "hotel5.jpg"]
    cards = "".join(_place_card(r, facts_map, photos[i % len(photos)])
                    for i, r in enumerate(featured))
    return (
        '<section id="hotels" class="section">'
        '<div class="sechead"><h2>Recently verified pet-friendly places</h2>'
        '<a href="/pet-friendly-hotels/">View all places %s</a></div>'
        '<div class="places">%s</div></section>'
    ) % (_SVG_ARROW, cards)


# The emergency-care card links to a plain Google Maps query deep-link -- the
# same no-API, no-fabrication doctrine the tracked /go/ directions pages use.
# Production carries no vet inventory, so no specific business is ever named.
_EMERGENCY_MAPS = ("https://www.google.com/maps/search/?api=1"
                   "&query=24+hour+emergency+veterinarian+Columbus+OH")


def _trip() -> str:
    cards = (
        ('<a class="trip-card" href="/pet-friendly-parks/">'
         '<img src="assets/trip1.jpg" alt="Dog playing in a Columbus park">'
         '<span class="trip-copy"><span class="ico g">%s</span><h3>Parks &amp; trails</h3>'
         "<p>Explore dog parks and pet-friendly outdoor spaces around Columbus.</p>"
         '<span class="go">Explore parks &rarr;</span></span></a>') % _SVG_TREE,
        ('<a class="trip-card" href="%s" rel="noopener" target="_blank">'
         '<img src="assets/trip3.jpg" alt="Traveler comforting a pet indoors">'
         '<span class="trip-copy"><span class="ico g">%s</span><h3>Emergency pet care</h3>'
         "<p>Find 24/7 veterinary hospitals and urgent care near you.</p>"
         '<span class="go">Find emergency care &rarr;</span></span></a>')
        % (_EMERGENCY_MAPS, _SVG_STETH),
        ('<a class="trip-card" href="/pet-friendly-restaurants/">'
         '<img src="assets/trip2.jpg" alt="Dog at a pet-friendly patio">'
         '<span class="trip-copy"><span class="ico o">%s</span><h3>Pet-friendly patios</h3>'
         "<p>Dine out with your dog at verified pet-friendly restaurants.</p>"
         '<span class="go">Browse patios &rarr;</span></span></a>') % _SVG_FORK,
    )
    return (
        '<section id="trip" class="section">'
        '<div class="sechead"><h2>Plan the rest of your pet-friendly trip in Columbus</h2></div>'
        '<div class="trip-grid">%s</div></section>') % "".join(cards)


def _band(browse_href: str) -> str:
    # ``browse_href`` is data-driven (PTF-CORRIDORS-002 Part E): the first
    # PUBLISHED corridor from the market configuration, falling back to the
    # hotels hub when no corridor publishes -- never a hard-coded corridor.
    return (
        '<div class="ph-band">'
        '<span class="pawcircle">%s</span>'
        "<div><h3>Travel better together.</h3>"
        "<p>Reliable info. Happy pets. Better trips.</p></div>"
        '<div class="actions">'
        '<a class="btn btn-primary" href="/pet-friendly-hotels/policy-comparison/">Compare places</a>'
        '<a class="btn btn-outline" href="%s">Browse by area</a></div>'
        '<span class="skyline">%s</span>'
        "</div>") % (_PAW_SOLID, _e(browse_href), _SKYLINE)


def _glance(hotel_rows: List[Dict], facts_map: Dict) -> str:
    picks = select_glance(hotel_rows, facts_map, 5)

    # Subtractive short labels only, and only when they stay unique -- otherwise
    # every row keeps its full committed name.
    labels = [_short_place(r["name"]) for r in picks]
    if len(set(labels)) != len(labels):
        labels = [r["name"] for r in picks]

    def species_cell(f: Dict[str, str], animal: str) -> str:
        if animal in (f.get("species_allowed") or "").lower():
            return '<td class="ok">%s</td>' % _SVG_CHECK
        return '<td class="ns">Not stated</td>'

    rows = []
    for row, label in zip(picks, labels):
        f = _facts_of(row["name"], facts_map)
        fee = _fee(f)
        rows.append(
            '<tr><td class="name"><a href="/pet-friendly-hotels/%s/" title="%s">%s</a></td>'
            "%s%s<td>%s</td><td>%s</td><td>%s</td></tr>"
            % (_slug(row["name"]), _e(row["name"]), _e(label),
               species_cell(f, "dog"), species_cell(f, "cat"),
               _e("Not stated" if fee == "Fee not stated" else fee),
               _e((f.get("pet_count_limit") or "").strip() or "Not stated"),
               _e(_weight_lb(f) or "Not stated")))

    return (
        '<section id="compare" class="side-card">'
        "<h3>Compare pet policies at a glance</h3>"
        '<table class="glance">'
        '<colgroup><col style="width:27%%"><col style="width:11%%"><col style="width:11%%">'
        '<col style="width:21%%"><col style="width:12%%"><col style="width:18%%"></colgroup>'
        "<thead><tr><th>Place</th><th>Dogs</th><th>Cats</th><th>Fee</th>"
        "<th>Max pets</th><th>Weight limit</th></tr></thead><tbody>%s</tbody></table>"
        '<a class="glance-more" href="/pet-friendly-hotels/policy-comparison/">'
        "Compare all verified places %s</a></section>"
    ) % ("".join(rows), _SVG_ARROW)


def _why() -> str:
    items = (
        (_SVG_CLIPBOARD, "Official-source research"),
        (_SVG_PEOPLE, "Unknowns shown honestly"),
        (_SVG_SHIELDCHK, "Policies rechecked over time"),
    )
    grid = "".join("<div>%s<span>%s</span></div>" % (icon, _e(label)) for icon, label in items)
    return ('<section class="why-card"><h3>Why PetTripFinder exists</h3>'
            "<p>We do the research so you can travel with fewer surprises.</p>"
            '<div class="why-grid">%s</div></section>') % grid


def _footer(corridor_nav: Sequence[Tuple[str, str]]) -> str:
    # Corridor links are data-driven (PTF-CORRIDORS-002 Part E): one link per
    # PUBLISHED, nav-visible corridor from the market configuration, in
    # configured display order. A corridor that did not publish gets no link.
    corridor_links = "".join(
        '<a href="%s">%s</a>' % (_e(route), _e(label)) for label, route in corridor_nav)
    return (
        '<footer class="footer"><div class="wrap footer-grid">'
        '<div><a class="brand" href="/">PetTripFinder<span class="dot">&middot;</span>'
        "<em>Columbus</em></a>"
        '<p class="note">Verified pet-travel guide for Columbus, Ohio. Temporary imagery shown for '
        "this review will be replaced by compliant Google Places media and approved city imagery.</p></div>"
        '<div><h4>Directory</h4><a href="/pet-friendly-hotels/">Places to stay</a>'
        '<a href="/pet-friendly-parks/">Parks &amp; trails</a>'
        '<a href="/pet-friendly-restaurants/">Eat &amp; drink</a></div>'
        '<div><h4>Planning</h4><a href="/pet-friendly-hotels/policy-comparison/">Compare policies</a>'
        + corridor_links +
        '<a href="/methodology/">How verification works</a></div>'
        '<div><h4>Company</h4><a href="/about/">About</a><a href="/contact/">Contact</a>'
        '<a href="/methodology/">Privacy</a></div></div></footer>')


# --------------------------------------------------------------------------- #
# Page.
# --------------------------------------------------------------------------- #

def render_home(hotel_rows: List[Dict], facts_map: Dict, *, hotel_count: int,
                park_count: int, restaurant_count: int,
                corridor_nav: Optional[Sequence[Tuple[str, str]]] = None) -> str:
    """Render the approved final homepage.

    ``hotel_count``/``park_count``/``restaurant_count`` are accepted to keep
    this renderer's published signature stable for the site generator. The
    approved final design states its trust promise qualitatively (the
    "Official-source policies / Honest unknowns / Review dates you can trust"
    strip) rather than through the earlier numeric inventory counter, so the
    counts are no longer surfaced on this page.

    ``corridor_nav`` (PTF-CORRIDORS-002 Part E): ordered (label, route)
    pairs for the market's PUBLISHED, nav-visible corridors. When None,
    they are derived here from the committed market configuration over the
    supplied ``hotel_rows`` -- corridor links are never hard-coded.
    """
    if corridor_nav is None:
        from scripts.pettripfinder.markets import (
            assign_hotels, corridor_navigation, default_market, load_markets,
        )
        market = default_market(load_markets())
        entries = corridor_navigation(market, assign_hotels(market, hotel_rows))
        corridor_nav = [(e.label, e.route) for e in entries]
    browse_href = corridor_nav[0][1] if corridor_nav else "/pet-friendly-hotels/"
    body = (
        '<a class="skip skip-link" href="#main">Skip to content</a>'
        + _header()
        + '<main id="main">'
        + _hero()
        + '<div class="wrap ph-body">'
        + '<div class="col-main">'
        + _trust_strip()
        + _start_section()
        + _featured(hotel_rows, facts_map)
        + _trip()
        + _band(browse_href)
        + "</div>"
        + '<aside class="col-side" aria-label="Policy comparison and how we verify">'
        + _glance(hotel_rows, facts_map)
        + _why()
        + ('<div class="side-skyline" aria-hidden="true">%s</div>' % _SKYLINE)
        + "</aside>"
        + "</div>"
        + "</main>"
        + _footer(corridor_nav)
        + _JS
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Pet-Friendly Travel in Columbus, Ohio | PetTripFinder</title>"
        '<meta name="description" content="Find a Columbus trip that actually works for your pet: '
        "compare verified pet charges, accepted species, pet limits and weight restrictions across "
        'places to stay, parks, patios and emergency pet care.">'
        '<meta name="robots" content="index, follow">'
        '<link rel="canonical" href="https://pettripfinder.com/">'
        "<style>%s</style></head><body>%s</body></html>"
    ) % (HOME_CSS, body)


def copy_assets(out_dir: Path) -> int:
    """Copy the approved temporary review assets into ``<out_dir>/assets/``.
    Returns the number of files copied."""
    dst = Path(out_dir) / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(_ASSETS_DIR.glob("*.jpg")):
        shutil.copyfile(p, dst / p.name)
        n += 1
    return n
