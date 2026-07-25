"""Atlas Directory — reusable page-family renderers (niche-agnostic).

Each renderer takes a ``DirectoryConfig`` plus a typed view model and produces a
complete page. No market, geography term, category, or domain field is hardcoded
here; rich domain content arrives as pre-escaped ``*_html`` fragments on the VMs.
"""

from __future__ import annotations

import html
from typing import Sequence

from scripts.atlas_directory import theme
from scripts.atlas_directory.config import DirectoryConfig
from scripts.atlas_directory.media import render_media
from scripts.atlas_directory.viewmodels import (
    Action, CardVM, ComparisonVM, EditorialVM, HomeVM, ListingVM, ProfileVM,
)


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


IC_PIN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
          'stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
          '<circle cx="12" cy="10" r="2.6"/></svg>')
IC_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="m20 6-11 11-5-5"/></svg>')
IC_X = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>')
IC_ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px">'
            '<path d="M5 12h14M13 6l6 6-6 6"/></svg>')
IC_CHECK_MINI = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
                 'style="width:13px;height:13px;color:#2f7a52;display:inline-block;vertical-align:-1px">'
                 '<path d="m20 6-11 11-5-5"/></svg>')


def render_card(vm: CardVM) -> str:
    pill = theme.badge_pill(vm.badge) if vm.badge else ""
    pill_html = '<span class="pt-card-pill">%s</span>' % pill if pill else ""
    chips = "".join('<span class="pt-fact%s">%s</span>' % ((" is-dim" if c.dim else ""), c.html)
                    for c in vm.chips)
    chips_html = '<div class="pt-card-facts">%s</div>' % chips if chips else ""
    area = '<span class="pt-card-area">%s</span>' % _e(vm.area_label) if vm.area_label else ""
    body = vm.body_html or ""
    foot = ('<span class="pt-card-vdate">%s %s</span>' % (IC_CHECK_MINI, _e(vm.footnote))
            if vm.footnote else "")
    return (
        '<article class="pt-card"><div class="pt-card-media">%s%s</div>'
        '<div class="pt-card-body">%s'
        '<h3 class="pt-card-name"><a href="%s">%s</a></h3>%s%s'
        '<div class="pt-card-foot"><a class="pt-card-link" href="%s">%s %s</a>%s</div>'
        '</div></article>'
    ) % (pill_html, render_media(vm.media, ratio="4x3", variant="card", label=False),
         area, vm.route, _e(vm.title), chips_html, body, vm.route, _e(vm.link_label), IC_ARROW, foot)


def _sec_head(vm) -> str:
    cls = "pt-sec-head center" if vm.center else "pt-sec-head"
    eb = theme.eyebrow(vm.eyebrow) if vm.eyebrow else ""
    lead = '<p class="pt-lead">%s</p>' % vm.lead if vm.lead else ""
    return '<div class="%s">%s<h2 class="pt-h2">%s</h2>%s</div>' % (cls, eb, _e(vm.heading), lead)


def render_home(config: DirectoryConfig, vm: HomeVM, *, css_href: str = "/styles.css",
                head_extra: str = "", title: str = "", description: str = "") -> str:
    h = vm.hero
    trust = "".join('<span>%s%s</span>' % (IC_CHECK, _e(t)) for t in h.trust_points)
    hero = (
        '<div class="pt-hero-copy"><span class="pt-hero-loc">%s %s</span>'
        '<h1>%s</h1><p class="pt-hero-sub">%s</p>'
        '<div class="pt-hero-actions">%s%s</div>'
        '<div class="pt-hero-trust">%s</div></div>'
        '<div class="pt-hero-media">%s'
        '<div class="pt-hero-badge"><b>%s</b><span>%s</span></div></div>'
    ) % (IC_PIN, _e(h.location_label), _e(h.headline), _e(h.subcopy),
         theme.action_btn(h.primary), theme.action_btn(h.secondary), trust,
         render_media(h.media, ratio="hero", variant="hero", label=False),
         _e(h.badge_value), _e(h.badge_label))

    s = vm.search
    fields = []
    for f in s.fields:
        if f.kind == "chips":
            chips = "".join('<a class="pt-chip" href="%s">%s</a>' % (a.href, _e(a.label)) for a in f.chips)
            inner = '<div class="pt-petchips">%s</div>' % chips
        else:
            inner = '<div class="pt-fake">%s</div>' % f.static_html
        fields.append('<div class="pt-field"><label>%s</label>%s</div>' % (_e(f.label), inner))
    search = (
        '<div class="pt-search"><div class="pt-search-card"><div class="pt-search-row">%s%s</div>'
        '<p class="pt-search-note">%s</p></div></div>'
    ) % ("".join(fields), theme.action_btn(s.cta, block=True), _e(s.note))

    stats = '<div class="pt-stats">%s</div>' % "".join(
        '<div class="pt-stat"><b>%s</b><span>%s</span></div>' % (_e(st.value), _e(st.label)) for st in vm.stats)

    featured = (
        '<section class="pt-section pt-band"><div class="pt-container">%s'
        '<div class="pt-grid pt-grid--3" style="margin-top:34px">%s</div>'
        '<div style="margin-top:34px">%s</div></div></section>'
    ) % (_sec_head(vm.featured_head), "".join(render_card(c) for c in vm.featured_cards),
         theme.action_btn(vm.featured_cta))

    cats = "".join(
        '<a class="pt-cat" href="%s">%s<div class="pt-cat-in"><h3>%s</h3><p>%s</p>'
        '<span class="pt-cat-go">%s %s</span></div></a>'
        % (c.href, render_media(c.media, ratio="1x1", variant="tile", label=False),
           _e(c.title), _e(c.desc), _e(c.cta_label), IC_ARROW)
        for c in vm.categories)
    categories = (
        '<section class="pt-section"><div class="pt-container">%s'
        '<div class="pt-grid pt-grid--4" style="margin-top:30px">%s</div></div></section>'
    ) % (_sec_head(vm.categories_head), cats)

    v = vm.verify
    gen_li = "".join('<li><span class="pt-vs-ic">%s</span>%s</li>' % (IC_X, t) for t in v.generic.items)
    ours_li = "".join('<li><span class="pt-vs-ic">%s</span>%s</li>' % (IC_CHECK, t) for t in v.ours.items)
    verify_cta = ('<div class="pt-sec-head center" style="margin-top:30px">%s</div>'
                  % theme.action_btn(v.cta)) if v.cta else ""
    verify = (
        '<section class="pt-section pt-band"><div class="pt-container">%s<div class="pt-vs">'
        '<div class="pt-vs-card is-generic"><h3><span class="pt-vs-tag">%s</span></h3>'
        '<ul class="pt-vs-list">%s</ul></div>'
        '<div class="pt-vs-mid"><span>vs.</span></div>'
        '<div class="pt-vs-card is-ptf"><h3><span class="pt-vs-tag">%s</span></h3>'
        '<ul class="pt-vs-list">%s</ul></div></div>%s</div></section>'
    ) % (_sec_head(v.head), _e(v.generic.tag), gen_li, _e(v.ours.tag), ours_li, verify_cta)

    ex = vm.explore
    rows = "".join(
        '<a class="pt-corridor" href="%s"><span><b>%s</b><span>%s</span></span>'
        '<span class="pt-corridor-go">%s</span></a>' % (i.href, _e(i.title), _e(i.subtitle), IC_ARROW)
        for i in ex.items)
    explore = (
        '<section class="pt-section"><div class="pt-container"><div class="pt-explore">'
        '<div class="pt-explore-map">%s</div><div>%s<ul class="pt-corridors">%s</ul></div>'
        '</div></div></section>'
    ) % (render_media(ex.media, ratio="4x3", variant="card"), _sec_head(ex.head), rows)

    cb = vm.cta_band
    band = (
        '<section class="pt-section"><div class="pt-container"><div class="pt-ctaband">%s'
        '<div class="pt-ctaband-in"><h2>%s</h2><p>%s</p><div class="pt-ctaband-actions">%s</div>'
        '</div></div></div></section>'
    ) % (render_media(cb.media, ratio="16x9", variant="hero", glyph=False, label=False),
         _e(cb.headline), _e(cb.sub), "".join(theme.action_btn(a) for a in cb.actions))

    body = (
        '<div class="pt-hero"><div class="pt-hero-bg"></div><div class="pt-hero-scrim"></div>'
        '<div class="pt-container pt-hero-in">%s</div></div>'
        '<div class="pt-container">%s</div>'
        '<section class="pt-section--tight"><div class="pt-container">%s</div></section>'
        '%s%s%s%s%s'
    ) % (hero, search, stats, featured, categories, verify, explore, band)
    return theme.page(config, title=title, description=description, route=config.home_route,
                      body=body, active="", head_extra=head_extra, css_href=css_href)


def render_listing(config: DirectoryConfig, vm: ListingVM, *, active: str = "", route: str,
                   title: str, description: str, css_href: str = "/styles.css",
                   head_extra: str = "") -> str:
    note = '<div class="pt-note">%s</div>' % vm.note_html if vm.note_html else ""
    grid = "".join(render_card(c) for c in vm.cards)
    lead = '<p class="pt-lead">%s</p>' % vm.head.lead if vm.head.lead else ""
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s<h1>%s</h1>%s</div></div>'
        '<section class="pt-section--tight"><div class="pt-container">%s'
        '<div class="pt-grid pt-grid--3"%s>%s</div></div></section>'
    ) % (theme.crumbs(vm.head.crumbs), _e(vm.head.title), lead, note,
         ' style="margin-top:22px"' if note else "", grid)
    return theme.page(config, title=title, description=description, route=route, body=body,
                      active=active, head_extra=head_extra, css_href=css_href)


def render_profile(config: DirectoryConfig, vm: ProfileVM, *, css_href: str = "/styles.css",
                   head_extra: str = "") -> str:
    actions = "".join(theme.action_btn(a) for a in vm.actions)
    nearby = ""
    if vm.nearby:
        groups = []
        for g in vm.nearby:
            if not g.items:
                continue
            items = "".join(
                '<a class="pt-corridor" href="%s"><span><b>%s</b><span>%s</span></span>'
                '<span class="pt-corridor-go">%s</span></a>' % (i.href, _e(i.title), _e(i.subtitle), IC_ARROW)
                for i in g.items)
            groups.append('<div><h2 class="pt-h3" style="margin-bottom:12px">%s</h2>'
                          '<div class="pt-corridors">%s</div></div>' % (_e(g.title), items))
        if groups:
            nearby = ('<section class="pt-section--tight" style="grid-column:1/-1">'
                      '<div class="pt-grid pt-grid--2">%s</div></section>' % "".join(groups))
    body = (
        '<div class="pt-container" style="padding-top:22px">%s</div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-explore" style="align-items:start">'
        '<div class="pt-explore-map">%s</div>'
        '<div><span class="pt-card-area">%s &middot; %s</span>'
        '<h1 class="pt-h2" style="margin:6px 0 12px">%s</h1>%s%s%s'
        '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:22px">%s</div></div>'
        '%s</div></section>'
    ) % (theme.crumbs(vm.crumbs, on_dark=False), render_media(vm.media, ratio="4x3", variant="card"),
         _e(vm.area_label), _e(vm.kind_label), _e(vm.title), vm.intro_html, vm.evidence_html,
         vm.detail_html, actions, nearby)
    return theme.page(config, title=vm.title_tag or vm.title, description=vm.meta_description,
                      route=vm.route, body=body, active=vm.active_nav, head_extra=head_extra,
                      css_href=css_href)


def render_comparison(config: DirectoryConfig, vm: ComparisonVM, *, route: str, title: str,
                      description: str, active: str = "", css_href: str = "/styles.css",
                      head_extra: str = "") -> str:
    header = "".join('<th scope="col">%s</th>' % _e(l) for _, l in vm.columns)
    body_rows = []
    for r in vm.rows:
        cells = ['<th scope="row"><a href="%s">%s</a></th>' % (r["route"], _e(r["name"]))]
        for key, _ in vm.columns:
            val = (r.get(key) or "").strip()
            cells.append("<td>%s</td>" % (_e(val) if val
                         else '<span class="pt-ns">%s</span>' % _e(vm.not_stated_label)))
        body_rows.append("<tr>%s</tr>" % "".join(cells))
    table = (
        '<div class="pt-table-wrap"><table class="pt-table"><caption>%s</caption>'
        '<thead><tr><th scope="col">%s</th>%s</tr></thead><tbody>%s</tbody></table></div>'
    ) % (_e(vm.caption), _e(vm.identity_label), header, "".join(body_rows))
    lead = '<p class="pt-lead">%s</p>' % vm.head.lead if vm.head.lead else ""
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s<h1>%s</h1>%s</div></div>'
        '<section class="pt-section--tight"><div class="pt-container">%s</div></section>'
    ) % (theme.crumbs(vm.head.crumbs), _e(vm.head.title), lead, table)
    return theme.page(config, title=title, description=description, route=route, body=body,
                      active=active, head_extra=head_extra, css_href=css_href)


def render_editorial(config: DirectoryConfig, vm: EditorialVM, *, route: str, title: str,
                     description: str, active: str = "", css_href: str = "/styles.css",
                     head_extra: str = "") -> str:
    lead = '<p class="pt-lead">%s</p>' % vm.head.lead if vm.head.lead else ""
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s<h1>%s</h1>%s</div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-prose">%s</div></div></section>'
    ) % (theme.crumbs(vm.head.crumbs), _e(vm.head.title), lead, vm.prose_html)
    return theme.page(config, title=title, description=description, route=route, body=body,
                      active=active, head_extra=head_extra, css_href=css_href)


def _strip(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s or "")
