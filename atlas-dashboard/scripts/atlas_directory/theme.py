"""Atlas Directory — design system + config-driven shell (niche-agnostic).

One stylesheet (``DIRECTORY_CSS``) and the shared page shell (header/footer/page)
driven entirely by ``DirectoryConfig``. No brand, market, category, or nav label
is hardcoded here; every visible string comes from the config or a view model.
"""

from __future__ import annotations

import html
from typing import Optional

from scripts.atlas_directory.config import DirectoryConfig
from scripts.atlas_directory.viewmodels import Action, Badge, Crumb


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _ea(s: str) -> str:
    return html.escape(s or "", quote=True)


_BRAND_MARK = ('<span class="pt-brand-mark" aria-hidden="true">'
               '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
               'stroke-linecap="round" stroke-linejoin="round"><path d="M3 11.5 12 4l9 7.5"/>'
               '<path d="M5 10v9h14v-9"/><path d="M10 19v-4.5a2 2 0 0 1 4 0V19"/></svg></span>')


def _brand(config: DirectoryConfig, foot: bool = False) -> str:
    return ('<a class="pt-brand%s" href="%s">%s<span class="pt-brand-text">%s<b>&nbsp;&middot;&nbsp;%s</b>'
            '</span></a>' % (" pt-brand--foot" if foot else "", config.home_route, _BRAND_MARK,
                             _e(config.brand_name), _e(config.brand_qualifier)))


def action_btn(a: Action, *, block: bool = False, small: bool = False) -> str:
    style = {"accent": "btn-accent", "ever": "btn-ever", "ghost": "btn-ghost",
             "onhero": "btn-onhero"}.get(a.style, "btn-accent")
    cls = "btn %s%s%s" % (style, " btn-block" if block else "", " btn-sm" if small else "")
    rel = ' rel="%s"' % _ea(a.rel) if a.rel else ""
    tgt = ' target="_blank"' if a.external else ""
    return '<a class="%s" href="%s"%s%s>%s</a>' % (cls, _ea(a.href), rel, tgt, _e(a.label))


def site_header(config: DirectoryConfig, active: str = "") -> str:
    links = "".join(
        '<a class="pt-nav-link%s" href="%s"%s>%s</a>'
        % (" is-active" if n.key == active else "", n.route,
           ' aria-current="page"' if n.key == active else "", _e(n.label))
        for n in config.nav)
    cta = config.header_cta
    return (
        '<header class="pt-header pt-header--solid"><div class="pt-container pt-header-in">'
        '%s'
        '<input class="pt-navtoggle" id="pt-navtoggle" type="checkbox" aria-hidden="true">'
        '<label class="pt-burger" for="pt-navtoggle" aria-label="Open menu">'
        '<span></span><span></span><span></span></label>'
        '<nav class="pt-nav" aria-label="Primary">%s'
        '<a class="pt-nav-cta btn btn-accent" href="%s">%s</a></nav>'
        '</div></header>'
    ) % (_brand(config), links, _ea(cta.href), _e(cta.label))


def _footer_col(title, links) -> str:
    lis = "".join('<li><a href="%s">%s</a></li>' % (r, _e(n)) for n, r in links)
    return '<div class="pt-foot-col"><h3>%s</h3><ul>%s</ul></div>' % (_e(title), lis)


def site_footer(config: DirectoryConfig) -> str:
    cols = "".join(_footer_col(c.title, c.links) for c in config.footer_columns)
    return (
        '<footer class="pt-footer"><div class="pt-container pt-foot-top">'
        '<div class="pt-foot-brand">%s<p>%s</p></div>%s</div>'
        '<div class="pt-container pt-foot-bottom"><p>%s</p>'
        '<p class="pt-foot-disc">%s</p></div></footer>'
    ) % (_brand(config, foot=True), _e(config.footer_tagline), cols,
         _e(config.footer_copyright), _e(config.footer_disclosure))


def page(config: DirectoryConfig, *, title: str, description: str, route: str, body: str,
         active: str = "", head_extra: str = "", robots: str = "index, follow",
         css_href: str = "/styles.css") -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s</title><meta name="description" content="%s">'
        '<meta name="robots" content="%s"><link rel="canonical" href="%s">'
        '<link rel="stylesheet" href="%s">%s</head><body class="pt">'
        '<a class="pt-skip skip-link" href="#main">Skip to main content</a>'
        '%s<main id="main">%s</main>%s</body></html>'
    ) % (_ea(title), _ea(description), robots, _ea(config.base_url + route), css_href,
         head_extra, site_header(config, active), body, site_footer(config))


# --------------------------------------------------------------------------- #
# Shared atoms.
# --------------------------------------------------------------------------- #

def eyebrow(text: str) -> str:
    return '<p class="pt-eyebrow">%s</p>' % _e(text)


def badge_pill(b: Badge) -> str:
    return ('<span class="pt-pill pt-pill--%s"><span class="pt-dot" aria-hidden="true"></span>%s</span>'
            % (b.state, _e(b.text)))


def crumbs(items, *, on_dark: bool = True) -> str:
    cls = "pt-crumbs" if on_dark else "pt-crumbs pt-crumbs--ink"
    lis = "".join(
        ('<li><a href="%s">%s</a></li>' % (c.href, _e(c.label)) if c.href
         else '<li aria-current="page">%s</li>' % _e(c.label)) for c in items)
    return '<nav aria-label="Breadcrumb"><ol class="%s">%s</ol></nav>' % (cls, lis)


# --------------------------------------------------------------------------- #
# The design system stylesheet (generic class names; no niche selectors).
# --------------------------------------------------------------------------- #

DIRECTORY_CSS = r"""
/* ===== Atlas Directory design system (reusable) ===== */
:root{
  --ever:#1c3a2e;--ever-700:#163025;--ever-300:#2f5a48;--ever-100:#e7efe9;
  --terra:#c65f3c;--terra-600:#b04f30;--terra-100:#f6e3d8;--coral:#e08a63;--gold:#b98a3e;
  --bg:#f6f1e7;--bg-2:#f1e9da;--card:#fffdf8;--card-2:#fbf6ec;
  --ink:#22201b;--ink-2:#544d42;--muted:#7c7365;--faint:#9a9182;--line:#e9dfcd;--line-2:#ded2bd;--inverse:#fbf7ef;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,"Times New Roman",serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,"Apple Color Emoji","Segoe UI Emoji",sans-serif;
  --r-sm:9px;--r:14px;--r-lg:22px;--r-xl:28px;--pill:999px;
  --sh-1:0 1px 2px rgba(38,34,26,.06);--sh-2:0 14px 34px -18px rgba(30,42,32,.30);--sh-3:0 26px 60px -28px rgba(30,42,32,.40);
  --container:1200px;--prose:44rem;--focus:0 0 0 3px rgba(28,58,46,.18),0 0 0 1.5px var(--ever);
}
*,*::before,*::after{box-sizing:border-box}
body.pt{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:17px;line-height:1.62;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;overflow-x:hidden;-webkit-text-size-adjust:100%}
.pt img{max-width:100%;display:block}
.pt a{color:var(--ever-300);text-underline-offset:2px}
.pt h1,.pt h2,.pt h3,.pt h4{font-family:var(--serif);color:var(--ink);line-height:1.12;letter-spacing:-.012em;margin:0;font-weight:600}
.pt p{margin:0 0 1em}
.pt-container{width:100%;max-width:var(--container);margin-inline:auto;padding-inline:clamp(18px,4vw,44px)}
.pt-skip{position:absolute;left:-9999px;top:0;z-index:200;background:var(--ever);color:var(--inverse);padding:10px 18px;border-radius:0 0 var(--r-sm) 0}
.pt-skip:focus{left:0;top:0}
.pt :where(a,button,input,summary,label):focus-visible{outline:none;box-shadow:var(--focus);border-radius:6px}
.btn{--bg:var(--ever);--fg:var(--inverse);--bd:transparent;display:inline-flex;align-items:center;justify-content:center;gap:.5em;
  font:600 15.5px/1 var(--sans);letter-spacing:.005em;padding:14px 22px;min-height:48px;border-radius:var(--pill);
  border:1.5px solid var(--bd);background:var(--bg);color:var(--fg);text-decoration:none;cursor:pointer;
  transition:transform .12s ease,box-shadow .18s ease,background .18s ease;box-shadow:var(--sh-1)}
.btn:hover{transform:translateY(-1px);box-shadow:var(--sh-2)}.btn:active{transform:translateY(0)}
.btn-accent{--bg:var(--terra);--fg:#fff}.btn-accent:hover{--bg:var(--terra-600)}
.btn-ever{--bg:var(--ever);--fg:var(--inverse)}.btn-ever:hover{--bg:var(--ever-700)}
.btn-ghost{--bg:transparent;--fg:var(--ever);--bd:var(--line-2);box-shadow:none}.btn-ghost:hover{--bg:var(--card);--bd:var(--ever-300)}
.btn-onhero{--bg:rgba(255,255,255,.12);--fg:#fff;--bd:rgba(255,255,255,.5);box-shadow:none;backdrop-filter:blur(4px)}.btn-onhero:hover{--bg:rgba(255,255,255,.2)}
.btn-sm{min-height:42px;padding:10px 18px;font-size:14.5px}.btn-block{width:100%}
.pt-pill{display:inline-flex;align-items:center;gap:7px;font:600 13px/1 var(--sans);padding:7px 13px 7px 11px;border-radius:var(--pill);white-space:nowrap}
.pt-pill .pt-dot{width:7px;height:7px;border-radius:50%;background:currentColor;flex:none}
.pt-pill--ok{background:var(--ever-100);color:#1f5138}.pt-pill--neutral{background:#efe9dd;color:var(--muted)}.pt-pill--stop{background:#f7e4df;color:#a8412a}
.pt-chip{display:inline-flex;align-items:center;gap:6px;font:500 13.5px/1 var(--sans);color:var(--ink-2);background:var(--card);border:1px solid var(--line-2);padding:8px 13px;border-radius:var(--pill)}
.pt-eyebrow{font:700 12.5px/1 var(--sans);letter-spacing:.14em;text-transform:uppercase;color:var(--terra-600);margin:0 0 14px}
.pt-header{position:sticky;top:0;z-index:100}
.pt-header-in{display:flex;align-items:center;gap:20px;min-height:72px}
.pt-header--solid{background:var(--ever);color:var(--inverse);box-shadow:var(--sh-1)}
.pt-brand{display:inline-flex;align-items:center;gap:11px;text-decoration:none;color:inherit;font-family:var(--serif);font-size:22px;font-weight:600;letter-spacing:-.01em;margin-right:auto}
.pt-brand-mark{display:inline-flex;width:34px;height:34px;align-items:center;justify-content:center;border-radius:10px;background:rgba(255,255,255,.14);color:#fff}
.pt-brand-mark svg{width:20px;height:20px}.pt-brand-text b{font-weight:600;color:var(--coral)}
.pt-nav{display:flex;align-items:center;gap:6px}
.pt-nav-link{color:inherit;text-decoration:none;font:600 14.5px/1 var(--sans);padding:10px 12px;border-radius:8px;opacity:.92;transition:opacity .15s,background .15s}
.pt-nav-link:hover{opacity:1;background:rgba(255,255,255,.1)}.pt-nav-link.is-active{opacity:1}
.pt-nav-link.is-active::after{content:"";display:block;height:2px;margin-top:5px;border-radius:2px;background:var(--coral)}
.pt-nav-cta{margin-left:10px}.pt-navtoggle,.pt-burger{display:none}
@media(max-width:920px){
  .pt-burger{display:inline-flex;flex-direction:column;gap:5px;justify-content:center;width:46px;height:46px;border-radius:10px;cursor:pointer;align-items:center;background:rgba(255,255,255,.12)}
  .pt-burger span{width:20px;height:2px;background:currentColor;border-radius:2px;transition:.2s}
  .pt-nav{position:fixed;inset:0 0 0 auto;width:min(84vw,340px);flex-direction:column;align-items:stretch;gap:4px;background:var(--ever);color:var(--inverse);padding:88px 22px 28px;transform:translateX(100%);transition:transform .26s ease;box-shadow:var(--sh-3);z-index:120}
  .pt-nav-link{padding:14px 12px;font-size:16px;border-radius:10px;opacity:1}.pt-nav-link:hover{background:rgba(255,255,255,.1)}
  .pt-nav-cta{margin:14px 0 0}
  .pt-navtoggle:checked ~ .pt-nav{transform:translateX(0)}
  .pt-navtoggle:checked ~ .pt-burger span:nth-child(1){transform:translateY(7px) rotate(45deg)}
  .pt-navtoggle:checked ~ .pt-burger span:nth-child(2){opacity:0}
  .pt-navtoggle:checked ~ .pt-burger span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
}
.pm{position:relative;margin:0;overflow:hidden;border-radius:var(--r);background:var(--card-2);isolation:isolate}
.pm--r-4-3{aspect-ratio:4/3}.pm--r-3-2{aspect-ratio:3/2}.pm--r-16-9{aspect-ratio:16/9}.pm--r-1-1{aspect-ratio:1/1}.pm--r-hero{aspect-ratio:16/10}
.pm-wash{position:absolute;inset:0;z-index:0}
.pm-inner{position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-end;padding:18px;gap:10px;color:#fff}
.pm-glyph{width:30px;height:30px;opacity:.9;margin-bottom:auto}
.pm-mono{position:absolute;top:14px;right:16px;font-family:var(--serif);font-size:34px;font-weight:600;letter-spacing:.02em;color:rgba(255,255,255,.34);z-index:1}
.pm-label{display:flex;flex-direction:column;gap:2px;text-shadow:0 1px 10px rgba(0,0,0,.28)}
.pm-name{font-family:var(--serif);font-size:19px;font-weight:600;line-height:1.15}
.pm-sub{font:600 12px/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;opacity:.85}
.pm--primary .pm-wash{background:radial-gradient(120% 90% at 85% 10%,rgba(255,255,255,.16),transparent 55%),linear-gradient(150deg,#24463a 0%,#2f5a48 52%,#1c3a2e 100%)}
.pm--nature .pm-wash{background:radial-gradient(120% 90% at 85% 12%,rgba(255,255,255,.16),transparent 55%),linear-gradient(150deg,#2e5a3b 0%,#3f7a4e 55%,#255233 100%)}
.pm--warm .pm-wash{background:radial-gradient(120% 90% at 85% 12%,rgba(255,255,255,.18),transparent 55%),linear-gradient(150deg,#b8552f 0%,#c9663a 48%,#8f4021 100%)}
.pm--city .pm-wash,.pm--brand .pm-wash{background:radial-gradient(120% 90% at 80% 10%,rgba(255,255,255,.16),transparent 55%),linear-gradient(150deg,#1f4034 0%,#2c5545 55%,#182f26 100%)}
.pm-wash::after{content:"";position:absolute;inset:0;opacity:.5;background-image:radial-gradient(rgba(255,255,255,.10) 1px,transparent 1.4px);background-size:18px 18px;mix-blend-mode:soft-light}
.pm--tile .pm-mono{font-size:26px}
.pm--thumb{border-radius:var(--r-sm)}.pm--thumb .pm-mono{font-size:20px;top:8px;right:10px}.pm--thumb .pm-inner{padding:10px}.pm--thumb .pm-glyph{width:22px;height:22px}
.pt-section{padding:clamp(48px,7vw,88px) 0}.pt-section--tight{padding:clamp(34px,5vw,56px) 0}
.pt-band{background:var(--bg-2)}
.pt-sec-head{max-width:var(--prose)}.pt-sec-head.center{margin-inline:auto;text-align:center}
.pt-h2{font-size:clamp(28px,3.6vw,40px)}.pt-h3{font-size:clamp(21px,2.4vw,26px)}
.pt-lead{font-size:clamp(17px,2vw,19.5px);color:var(--ink-2);margin-top:6px}
.pt-sec-head .pt-lead{max-width:38rem}.pt-sec-head.center .pt-lead{margin-inline:auto}
.pt-hero{position:relative;color:#fff;isolation:isolate;overflow:clip}
.pt-hero-bg{position:absolute;inset:0;z-index:-2;background:radial-gradient(90% 120% at 78% 0%,#2f5a48 0%,transparent 55%),linear-gradient(160deg,#1f4034 0%,#163025 60%,#132a21 100%),var(--ever)}
.pt-hero-bg::after{content:"";position:absolute;inset:0;opacity:.4;background-image:radial-gradient(rgba(255,255,255,.10) 1px,transparent 1.5px);background-size:22px 22px}
.pt-hero-scrim{position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(19,42,33,.35) 0%,rgba(19,42,33,.05) 30%,rgba(19,42,33,.55) 100%)}
.pt-hero-in{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:clamp(28px,5vw,64px);align-items:center;padding:clamp(120px,15vw,150px) 0 clamp(56px,7vw,86px)}
.pt-hero-copy{max-width:36rem}
.pt-hero h1{font-size:clamp(38px,6vw,64px);color:#fff;letter-spacing:-.02em;line-height:1.04}
.pt-hero-sub{font-size:clamp(17px,2.1vw,20px);color:rgba(255,255,255,.9);margin-top:18px;max-width:32rem}
.pt-hero-loc{display:inline-flex;align-items:center;gap:9px;font:600 13px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.82);margin-bottom:20px}
.pt-hero-loc svg{width:16px;height:16px}
.pt-hero-actions{display:flex;flex-wrap:wrap;gap:14px;margin-top:28px}
.pt-hero-trust{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:26px;color:rgba(255,255,255,.85);font:500 14px/1.4 var(--sans)}
.pt-hero-trust span{display:inline-flex;align-items:center;gap:8px}.pt-hero-trust svg{width:16px;height:16px;color:var(--coral);flex:none}
.pt-hero-media{position:relative}
.pt-hero-media .pm{box-shadow:var(--sh-3);border-radius:var(--r-lg);transform:rotate(1.2deg)}
.pt-hero-media .pm::before{content:"";position:absolute;inset:0;z-index:2;border-radius:inherit;box-shadow:inset 0 0 0 1px rgba(255,255,255,.14)}
.pt-hero-badge{position:absolute;left:-14px;bottom:26px;z-index:3;background:var(--card);color:var(--ink);border-radius:var(--r);padding:14px 18px;box-shadow:var(--sh-3);max-width:230px;transform:rotate(-1.2deg)}
.pt-hero-badge b{display:block;font-family:var(--serif);font-size:26px;color:var(--ever);line-height:1}
.pt-hero-badge span{font:500 13px/1.4 var(--sans);color:var(--muted)}
.pt-search{position:relative;z-index:2;margin-top:-38px}
.pt-search-card{background:var(--card);border-radius:var(--r-lg);box-shadow:var(--sh-3);border:1px solid var(--line);padding:clamp(18px,2.5vw,26px)}
.pt-search-row{display:grid;grid-template-columns:1.4fr 1.2fr auto;gap:14px;align-items:end}
.pt-field{display:flex;flex-direction:column;gap:7px}
.pt-field label{font:700 12px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pt-field .pt-fake{display:flex;align-items:center;gap:10px;min-height:50px;padding:0 15px;border:1.5px solid var(--line-2);border-radius:12px;background:var(--card-2);color:var(--ink);font-weight:600}
.pt-field .pt-fake svg{width:18px;height:18px;color:var(--ever-300);flex:none}.pt-field .pt-fake small{color:var(--muted);font-weight:500}
.pt-petchips{display:flex;gap:8px;flex-wrap:wrap}.pt-petchips a{text-decoration:none}
.pt-search-note{margin:14px 2px 0;font-size:13.5px;color:var(--muted)}
.pt-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:clamp(16px,3vw,34px);padding:clamp(26px,4vw,40px) 0}
.pt-stat{border-left:2px solid var(--line-2);padding-left:18px}
.pt-stat b{display:block;font-family:var(--serif);font-size:clamp(30px,4vw,44px);color:var(--ever);line-height:1}
.pt-stat span{display:block;margin-top:6px;font-size:14.5px;color:var(--ink-2);font-weight:500}
.pt-grid{display:grid;gap:clamp(18px,2.5vw,26px)}
.pt-grid--3{grid-template-columns:repeat(3,1fr)}.pt-grid--2{grid-template-columns:repeat(2,1fr)}.pt-grid--4{grid-template-columns:repeat(4,1fr)}
@media(max-width:1000px){.pt-grid--3,.pt-grid--4{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.pt-grid--2,.pt-grid--3,.pt-grid--4{grid-template-columns:1fr}}
.pt-card{position:relative;display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden;box-shadow:var(--sh-1);transition:transform .16s ease,box-shadow .2s ease,border-color .2s}
.pt-card:hover{transform:translateY(-3px);box-shadow:var(--sh-2);border-color:var(--line-2)}
.pt-card-media{position:relative}.pt-card-media .pm{border-radius:0}
.pt-card-pill{position:absolute;left:14px;top:14px;z-index:3;box-shadow:var(--sh-1)}
.pt-card-body{display:flex;flex-direction:column;gap:12px;padding:18px 20px 20px;flex:1}
.pt-card-area{font:600 12px/1 var(--sans);letter-spacing:.07em;text-transform:uppercase;color:var(--terra-600)}
.pt-card-name{font-family:var(--serif);font-size:20.5px;font-weight:600;line-height:1.16}
.pt-card-name a{color:var(--ink);text-decoration:none}.pt-card-name a::after{content:"";position:absolute;inset:0;z-index:2}
.pt-card:hover .pt-card-name a{color:var(--ever)}
.pt-card-facts{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}
.pt-fact{display:inline-flex;align-items:baseline;gap:6px;font:500 13.5px/1.2 var(--sans);color:var(--ink-2);background:var(--card-2);border:1px solid var(--line);padding:7px 11px;border-radius:10px}
.pt-fact b{font-weight:700;color:var(--ink)}.pt-fact.is-dim{color:var(--faint);font-style:italic}
.pt-card-foot{margin-top:auto;padding-top:6px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.pt-card-link{position:relative;z-index:3;font:600 14.5px/1 var(--sans);color:var(--ever);text-decoration:none}.pt-card-link:hover{color:var(--terra-600)}
.pt-card-vdate{font:500 12.5px/1 var(--sans);color:var(--muted)}
.pt-cat{position:relative;display:flex;flex-direction:column;justify-content:flex-end;min-height:230px;border-radius:var(--r-lg);overflow:hidden;padding:22px;color:#fff;text-decoration:none;box-shadow:var(--sh-1);transition:transform .16s,box-shadow .2s}
.pt-cat:hover{transform:translateY(-3px);box-shadow:var(--sh-2)}.pt-cat .pm{position:absolute;inset:0;border-radius:0}
.pt-cat-in{position:relative;z-index:2}.pt-cat-in h3{color:#fff;font-size:23px}.pt-cat-in p{margin:6px 0 0;color:rgba(255,255,255,.9);font-size:14.5px}
.pt-cat-in .pt-cat-go{display:inline-flex;align-items:center;gap:7px;margin-top:14px;font:700 13px/1 var(--sans);letter-spacing:.02em;color:#fff}
.pt-vs{display:grid;grid-template-columns:1fr auto 1fr;gap:clamp(16px,3vw,30px);align-items:stretch;margin-top:8px}
.pt-vs-card{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);padding:26px 26px 28px}
.pt-vs-card.is-generic{background:var(--card-2);border-style:dashed}
.pt-vs-card h3{font-size:19px;display:flex;align-items:center;gap:10px}
.pt-vs-tag{font:700 11px/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;padding:5px 9px;border-radius:var(--pill)}
.is-generic .pt-vs-tag{background:#efe7d8;color:var(--muted)}.is-ptf .pt-vs-tag{background:var(--ever-100);color:#1f5138}
.pt-vs-list{list-style:none;margin:16px 0 0;padding:0;display:flex;flex-direction:column;gap:12px}
.pt-vs-list li{display:flex;gap:11px;font-size:15px;color:var(--ink-2);line-height:1.45}
.pt-vs-ic{flex:none;width:20px;height:20px;margin-top:1px}.is-generic .pt-vs-ic{color:var(--faint)}.is-ptf .pt-vs-ic{color:#2f7a52}
.pt-vs-mid{display:flex;align-items:center;justify-content:center}.pt-vs-mid span{font-family:var(--serif);font-style:italic;font-size:19px;color:var(--muted)}
@media(max-width:820px){.pt-vs{grid-template-columns:1fr}.pt-vs-mid{padding:4px 0}}
.pt-explore{display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(24px,4vw,48px);align-items:center}
.pt-explore-map .pm{box-shadow:var(--sh-2);border-radius:var(--r-lg)}
.pt-corridors{list-style:none;margin:18px 0 0;padding:0;display:flex;flex-direction:column;gap:10px}
.pt-corridor{display:flex;align-items:center;justify-content:space-between;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:15px 18px;text-decoration:none;color:var(--ink);transition:border-color .18s,transform .14s,box-shadow .2s}
.pt-corridor:hover{border-color:var(--ever-300);transform:translateX(3px);box-shadow:var(--sh-1)}
.pt-corridor b{font-family:var(--serif);font-size:18px;font-weight:600}
.pt-corridor span{font-size:13.5px;color:var(--muted);display:block;margin-top:2px}.pt-corridor .pt-corridor-go{color:var(--ever-300);font-weight:700;flex:none}
@media(max-width:820px){.pt-explore{grid-template-columns:1fr}}
.pt-ctaband{position:relative;overflow:hidden;border-radius:var(--r-xl);padding:clamp(36px,6vw,64px);color:#fff;text-align:center;box-shadow:var(--sh-2)}
.pt-ctaband .pm{position:absolute;inset:0;border-radius:0;z-index:0}.pt-ctaband-in{position:relative;z-index:2;max-width:40rem;margin-inline:auto}
.pt-ctaband h2{color:#fff;font-size:clamp(28px,4vw,42px)}.pt-ctaband p{color:rgba(255,255,255,.9);margin-top:12px;font-size:18px}
.pt-ctaband-actions{display:flex;flex-wrap:wrap;gap:14px;justify-content:center;margin-top:26px}
.pt-footer{background:var(--ever);color:var(--inverse)}
.pt-foot-top{display:grid;grid-template-columns:1.4fr repeat(3,1fr);gap:clamp(24px,4vw,44px);padding:clamp(44px,6vw,66px) 0 clamp(30px,4vw,40px)}
.pt-brand--foot{color:var(--inverse);font-size:21px;margin:0 0 14px}
.pt-foot-brand p{color:rgba(251,247,239,.72);max-width:26rem;font-size:15px}
.pt-foot-col h3{font-family:var(--sans);font-size:12.5px;letter-spacing:.1em;text-transform:uppercase;color:rgba(251,247,239,.6);margin:6px 0 14px;font-weight:700}
.pt-foot-col ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:11px}
.pt-foot-col a{color:rgba(251,247,239,.9);text-decoration:none;font-size:15px}.pt-foot-col a:hover{color:#fff;text-decoration:underline}
.pt-foot-bottom{border-top:1px solid rgba(255,255,255,.12);padding:22px 0 34px;display:flex;flex-direction:column;gap:8px}
.pt-foot-bottom p{margin:0;color:rgba(251,247,239,.62);font-size:13px}.pt-foot-disc{max-width:52rem}
@media(max-width:820px){.pt-foot-top{grid-template-columns:1fr 1fr}}@media(max-width:520px){.pt-foot-top{grid-template-columns:1fr}}
.pt-prose{max-width:var(--prose);margin-inline:auto}
.pt-prose h2{font-size:26px;margin:2em 0 .5em}.pt-prose h3{font-size:20px;margin:1.6em 0 .4em}
.pt-prose ul{padding-left:1.1em;margin:0 0 1em}.pt-prose li{margin:.4em 0}.pt-prose a{color:var(--ever-300);text-decoration:underline}
.pt-pagehead{background:var(--ever);color:var(--inverse);padding:clamp(38px,6vw,64px) 0 clamp(30px,4vw,46px)}
.pt-pagehead h1{color:#fff;font-size:clamp(30px,4.4vw,46px);max-width:20ch}.pt-pagehead .pt-lead{color:rgba(251,247,239,.88);max-width:44rem}
.pt-crumbs{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0 0 16px;padding:0;font-size:13.5px;color:rgba(251,247,239,.7)}
.pt-crumbs a{color:rgba(251,247,239,.82);text-decoration:none}.pt-crumbs a:hover{text-decoration:underline}
.pt-crumbs li:not(:last-child)::after{content:"/";margin-left:6px;color:rgba(251,247,239,.4)}
.pt-crumbs--ink{color:var(--muted)}.pt-crumbs--ink a{color:var(--ever-300)}.pt-crumbs--ink li:not(:last-child)::after{color:var(--line-2)}
.pt-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:var(--r-lg);box-shadow:var(--sh-1);background:var(--card)}
.pt-table{width:100%;min-width:760px;border-collapse:collapse}
.pt-table caption{caption-side:bottom;text-align:left;padding:14px 18px;color:var(--muted);font-size:13.5px}
.pt-table th,.pt-table td{padding:14px 16px;text-align:left;border-bottom:1px solid var(--line);font-size:14.5px;white-space:nowrap}
.pt-table thead th{background:var(--card-2);font:700 12px/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);position:sticky;top:0}
.pt-table tbody tr:last-child td,.pt-table tbody tr:last-child th{border-bottom:0}
.pt-table tbody tr:hover{background:var(--card-2)}
.pt-table th[scope=row]{font-weight:600}.pt-table th[scope=row] a{color:var(--ever);text-decoration:none}.pt-table th[scope=row] a:hover{color:var(--terra-600);text-decoration:underline}
.pt-ns{color:var(--faint);font-style:italic}
.pt-note{background:var(--card-2);border:1px solid var(--line);border-left:3px solid var(--terra);border-radius:var(--r);padding:16px 20px;color:var(--ink-2);font-size:15px;margin:20px 0}
@media(max-width:920px){
  .pt-hero-in{grid-template-columns:1fr;gap:34px;padding-top:clamp(104px,22vw,132px)}
  .pt-hero-media{max-width:520px}.pt-search-row{grid-template-columns:1fr}.pt-stats{grid-template-columns:1fr 1fr}
}
@media(max-width:520px){body.pt{font-size:16px}.pt-stats{grid-template-columns:1fr 1fr}.pt-hero-badge{left:auto;right:14px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto!important}.pt-hero-media .pm{transform:none}.pt-hero-badge{transform:none}}
@media (prefers-color-scheme:dark){:root{color-scheme:light}}
"""
