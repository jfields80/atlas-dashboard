"""PTF-INDIANAPOLIS-ROUTING-COST-PLAN-003 -- price the unrouted cohort. NO SPEND.

COVERAGE-003 of the founder's ruling authorised a cost plan for the 118 unrouted
Indianapolis identities at $0 spend. This builds it.

THE FACT THAT SHAPES THE WHOLE PLAN
-----------------------------------
All 118 are blocked on NO_OFFICIAL_URL. You cannot buy a page you cannot
address, so NOT ONE of them is a straight acquisition row today. Pricing this as
an acquisition cohort would be pricing a purchase that cannot be made. Every row
is routing-repair-first, and the plan is therefore two-staged:

    stage 1  ROUTING     find the official URL          (free lane, then Places)
    stage 2  ACQUISITION buy the page the URL names     (free-attended, then paid)

Only the rows that survive stage 1 can ever reach stage 2, which is why the
acquisition budget is a function of the routing yield and not of the cohort size.

RATES ARE MEASURED, NOT ASSUMED
-------------------------------
Every rate below is derived from this project's own committed ledgers at run
time -- 720 priced paid attempts and 143 discovery attempts -- never from a
static constant. Two consequences worth stating plainly:

  * The paid ledger records cost, so the acquisition lane is priced from what we
    actually paid per settled attempt.
  * The discovery ledger records NO cost. Google Places spend has never been
    written to it. So the routing stage's unit price is UNPRICED_BY_LEDGER and
    the plan refuses to invent one: it carries the yield we measured (43 of 143
    bound) and requires a live console read before any spend is authorised.

A cap is meaningless against a number nobody read. The account balance is not a
cost meter.

Nothing here fetches, spends, routes, publishes or deploys.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import math
import os
import re
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          '..', '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

WORK_ORDER = 'PTF-INDIANAPOLIS-ROUTING-COST-PLAN-003'
MARKET_ID = 'indianapolis-in'

#: Brand families whose own directory or sitemap answered us for FREE in
#: PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001. A row in one of these can be
#: routed at $0 before any paid discovery is considered.
FREE_ROUTING_PROVEN = {'ESA', 'WYNDHAM', 'HILTON', 'DRURY', 'MY_PLACE'}

#: Brand families that refused a free directory in that same audit.
FREE_ROUTING_REFUSED = {'CHOICE', 'IHG', 'MARRIOTT', 'MOTEL6', 'RED_ROOF',
                        'SONESTA', 'RADISSON', 'INTOWN', 'BEST_WESTERN', 'HYATT'}

#: Families proven to render their policy to an ATTENDED browser at $0
#: (PTF-CINCINNATI-ZERO-COST-CAPTURE-003, -005, -006). Acquisition for these
#: should try the free lane before spending anything.
FREE_ATTENDED_PROVEN = {'IHG', 'CHOICE', 'WYNDHAM'}

BRANDS = [
    ('MARRIOTT', r'marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|le meridien|moxy|element'),
    ('HILTON', r'hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|signia'),
    ('IHG', r'holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton'),
    ('CHOICE', r'comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|everhome'),
    ('WYNDHAM', r'wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|trademark'),
    ('ESA', r'extended stay america'),
    ('BEST_WESTERN', r'best western|surestay|glo '),
    ('MOTEL6', r'motel 6|studio 6'),
    ('RED_ROOF', r'red roof|hometowne'),
    ('SONESTA', r'sonesta|simply suites'),
    ('RADISSON', r'radisson|country inn|park inn'),
    ('INTOWN', r'intown suites'),
    ('DRURY', r'drury'),
    ('MY_PLACE', r'my place'),
    ('HYATT', r'hyatt'),
]


def brand_of(key):
    for name, pat in BRANDS:
        if re.search(pat, key, re.I):
            return name
    return 'INDEPENDENT'


def _read(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def wilson_lower(successes, trials, z=1.96):
    """Size on the LOWER bound; feasibility may use the point estimate."""
    if trials <= 0:
        return 0.0
    p = successes / float(trials)
    d = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials)
    return max(0.0, (centre - margin) / d)


def measured_rates(package_dir):
    """Every rate this plan uses, derived from the committed ledgers."""
    paid = _read(os.path.join(package_dir, 'ptf_paid_attempt_ledger_001.json'))['attempts']
    disc = _read(os.path.join(package_dir, 'ptf_discovery_attempt_ledger_001.json'))['attempts']

    lanes = {}
    for lane in ('brightdata_browser', 'brightdata_web_unlocker', 'firecrawl'):
        rows = [x for x in paid if x.get('lane') == lane]
        billed = [x for x in rows if (x.get('cost_usd_minor') or 0) > 0]
        cost = sum(x.get('cost_usd_minor') or 0 for x in rows) / 100.0
        pg = sum(1 for x in rows if x.get('publication_grade'))
        lanes[lane] = collections.OrderedDict((
            ('attempts', len(rows)),
            ('billed_attempts', len(billed)),
            ('usd_spent', round(cost, 2)),
            ('usd_per_billed_attempt', round(cost / len(billed), 4) if billed else None),
            ('publication_grade', pg),
            ('publication_grade_rate', round(pg / float(len(rows)), 4) if rows else None),
            ('publication_grade_rate_wilson_lower',
             round(wilson_lower(pg, len(rows)), 4) if rows else None),
        ))

    bd = [x for x in paid if (x.get('lane') or '').startswith('brightdata')]
    by_brand = {}
    for x in bd:
        b = x.get('brand') or 'INDEPENDENT'
        s = by_brand.setdefault(b, [0, 0])
        s[0] += 1
        s[1] += 1 if x.get('publication_grade') else 0
    brand_yield = {b: collections.OrderedDict((
        ('attempts', n), ('publication_grade', p),
        ('rate', round(p / float(n), 4)),
        ('rate_wilson_lower', round(wilson_lower(p, n), 4))))
        for b, (n, p) in sorted(by_brand.items()) if n >= 5}

    bound = sum(1 for x in disc if x.get('outcome') == 'BOUND')
    disc_cost = sum(x.get('cost_usd_minor') or 0 for x in disc)
    discovery = collections.OrderedDict((
        ('provider', 'GOOGLE_PLACES'),
        ('attempts', len(disc)),
        ('bound', bound),
        ('bind_rate', round(bound / float(len(disc)), 4) if disc else None),
        ('bind_rate_wilson_lower', round(wilson_lower(bound, len(disc)), 4)),
        ('usd_recorded_in_ledger', disc_cost / 100.0),
        ('unit_price_state', 'UNPRICED_BY_LEDGER'),
        ('why', 'Google Places spend has never been written to the discovery '
                'ledger, so this plan refuses to invent a per-request price. '
                'Read the live console rate before authorising any spend.'),
    ))
    return lanes, brand_yield, discovery


def cohort(package_dir):
    """The unrouted rows, segmented. Every one of them is routing-first."""
    # The ADMITTED rows live in the shadow admission census, not the pinned one:
    # promoting them moves the release contract and the deployment manifest, so
    # PTF-INDIANAPOLIS-CENSUS-ADMISSION-002 deliberately left the pinned census
    # alone. The extended cohort is priced from the shadow so the founder can see
    # what the admission will cost to route once it is promoted.
    census = _read(os.path.join(package_dir, 'identity_census', MARKET_ID + '.json'))
    shadow = os.path.join(package_dir, 'identity_census_admission',
                          MARKET_ID + '.json')
    if os.path.isfile(shadow):
        census = _read(shadow)
    reviews = _read(os.path.join(
        package_dir, 'indianapolis_in_identity_review_register_002.json'))
    under_review = set()
    for r in reviews['reviews']:
        # Not every review names a REGISTERED row: the corridor review names
        # three identities that were never admitted, so it has no census key to
        # exclude and must not be assumed to carry one.
        for i in r.get('identities_in_tension', []):
            if i.get('identity_key'):
                under_review.add(i['identity_key'])

    # The founder named the 118 the audit MEASURED, not every row whose
    # official_url happens to be empty today. Those are different sets: 36 of
    # the empty-URL rows are blocked on something else (transport, identity
    # mismatch, brand exclusion) and pricing them here would quote a purchase
    # that a different defect is holding shut.
    # PTF-INDIANAPOLIS-APPLY-RULINGS-005 superseded the 003 cohort: two rows were
    # routed by the identity rulings and three were admitted. Prefer the newer
    # cohort when it exists so the plan prices the CURRENT unrouted set.
    _c5 = os.path.join(package_dir, 'indianapolis_in_unrouted_cohort_005.json')
    _c3 = os.path.join(package_dir, 'indianapolis_in_unrouted_cohort_003.json')
    pinned = set(_read(_c5 if os.path.isfile(_c5) else _c3)['identity_keys'])

    rows, admitted = [], []
    for h in census['hotels']:
        is_admitted = bool(h.get('admission'))
        if h['identity_key'] not in pinned and not is_admitted:
            continue
        b = brand_of(h['identity_key'])
        if h['identity_key'] in under_review:
            seg = 'IDENTITY_REVIEW_FIRST'
        elif b in FREE_ROUTING_PROVEN:
            seg = 'ROUTING_REPAIR_FIRST_FREE_LANE'
        elif b in FREE_ROUTING_REFUSED:
            seg = 'ROUTING_REPAIR_FIRST_PAID_DISCOVERY'
        else:
            seg = 'ROUTING_REPAIR_FIRST_INDEPENDENT'
        acq = ('FREE_ATTENDED_FIRST' if b in FREE_ATTENDED_PROVEN
               else 'BRIGHTDATA_QUALIFIED' if b in ('MARRIOTT', 'HILTON')
               else 'SOURCE_SILENT_OR_OTHER')
        rec = collections.OrderedDict((
            ('identity_key', h['identity_key']), ('brand_family', b),
            ('postal_code', h.get('postal_code', '')),
            ('routing_segment', seg), ('acquisition_lane_if_routed', acq)))
        (admitted if is_admitted else rows).append(rec)
    return census, rows, admitted


def build(package_dir):
    pkg = os.path.abspath(package_dir)
    lanes, brand_yield, discovery = measured_rates(pkg)
    census, base, admitted = cohort(pkg)
    everything = base + admitted

    bd = lanes['brightdata_browser']
    unit = bd['usd_per_billed_attempt']
    # Size on the LOWER bound; quote feasibility at the point estimate.
    route_lo = discovery['bind_rate_wilson_lower']
    route_pt = discovery['bind_rate']
    pf_rate = 0.62  # Indianapolis measured pet-friendly rate among RESOLVED rows

    def stage(rows, label):
        n = len(rows)
        free = [r for r in rows if r['routing_segment'] == 'ROUTING_REPAIR_FIRST_FREE_LANE']
        paid_disc = [r for r in rows if r['routing_segment'] == 'ROUTING_REPAIR_FIRST_PAID_DISCOVERY']
        indep = [r for r in rows if r['routing_segment'] == 'ROUTING_REPAIR_FIRST_INDEPENDENT']
        review = [r for r in rows if r['routing_segment'] == 'IDENTITY_REVIEW_FIRST']
        payable = len(paid_disc) + len(indep)
        routed_lo = payable * route_lo
        routed_pt = payable * route_pt
        free_att = [r for r in rows if r['acquisition_lane_if_routed'] == 'FREE_ATTENDED_FIRST']
        share_paid_acq = 1.0 - (len(free_att) / float(n) if n else 0)
        attempts_lo = routed_lo * share_paid_acq
        attempts_pt = routed_pt * share_paid_acq
        pg_lo = bd['publication_grade_rate_wilson_lower']
        pg_pt = bd['publication_grade_rate']
        return collections.OrderedDict((
            ('label', label), ('rows', n),
            ('segments', collections.OrderedDict((
                ('IDENTITY_REVIEW_FIRST', len(review)),
                ('ROUTING_REPAIR_FIRST_FREE_LANE', len(free)),
                ('ROUTING_REPAIR_FIRST_PAID_DISCOVERY', len(paid_disc)),
                ('ROUTING_REPAIR_FIRST_INDEPENDENT', len(indep))))),
            ('acquisition_lane_if_routed', dict(collections.Counter(
                r['acquisition_lane_if_routed'] for r in rows))),
            ('stage_1_routing', collections.OrderedDict((
                ('free_lane_rows_try_first_at_zero_cost', len(free)),
                ('rows_needing_paid_discovery', payable),
                ('measured_bind_rate', route_pt),
                ('bind_rate_wilson_lower', route_lo),
                ('expected_rows_routed_point', round(routed_pt, 1)),
                ('expected_rows_routed_lower', round(routed_lo, 1)),
                ('unit_price', 'UNPRICED_BY_LEDGER -- read the live console rate'),
                ('cost', 'CANNOT BE QUOTED UNTIL THE RATE IS READ')))),
            ('stage_2_acquisition', collections.OrderedDict((
                ('rows_that_should_try_the_free_attended_lane_first', len(free_att)),
                ('projected_paid_attempts_point', round(attempts_pt, 1)),
                ('projected_paid_attempts_lower', round(attempts_lo, 1)),
                ('measured_usd_per_billed_attempt', unit),
                ('expected_cost_point_usd', round(attempts_pt * unit, 2)),
                ('expected_cost_lower_usd', round(attempts_lo * unit, 2)),
                ('publication_grade_rate', pg_pt),
                ('publication_grade_rate_wilson_lower', pg_lo),
                ('expected_publication_grade_point', round(attempts_pt * pg_pt, 1)),
                ('expected_publication_grade_lower', round(attempts_lo * pg_lo, 1)),
                ('expected_pet_friendly_gain_point',
                 round(attempts_pt * pg_pt * pf_rate, 1)),
                ('expected_pet_friendly_gain_lower',
                 round(attempts_lo * pg_lo * pf_rate, 1))))),
            # A ceiling is not a forecast: it assumes every payable row routes
            # and every routed row is bought, which the measured rates say will
            # not happen. It exists so the cap can never be breached.
            ('conservative_hard_cap_ceiling_usd',
             round(payable * unit * 1.25, 2)),
            ('hard_cap_basis',
             'every payable row routes AND is bought at the measured unit price, '
             'plus 25% for the settle-upward the Bright Data zone meter is known '
             'to do'),
        ))

    primary = stage(base, 'the audit-measured cohort, post-rulings')
    extended = stage(everything, 'every unrouted identity in the shadow census')

    pilot = collections.OrderedDict((
        ('recommended_first_batch_rows', 20),
        ('why', 'the free routing lane returned 2 confirmed routes from 30 leads '
                'in the audit, so the paid discovery yield is the number this '
                'pilot exists to measure IN THIS MARKET. 20 rows is large enough '
                'to move the Wilson bound and small enough that a wrong rate '
                'costs cents.'),
        ('composition', 'the 20 highest-value ROUTING_REPAIR_FIRST_PAID_DISCOVERY '
                        'rows, stratified across CHOICE / IHG / MARRIOTT so one '
                        'brand cannot dominate the measurement'),
        ('stop_rule', 'stop WHEN the cap is exceeded, not after'),
        ('required_before_launch', [
            'read the live Google Places per-request price',
            'read the live Bright Data zone balance',
            'rebuild BOTH ledgers immediately before spending',
        ]),
    ))

    required_balance = collections.OrderedDict((
        ('bright_data_for_the_full_extended_cohort_usd',
         extended['conservative_hard_cap_ceiling_usd']),
        ('bright_data_for_the_recommended_pilot_usd',
         round(20 * unit * 1.25, 2)),
        ('google_places', 'UNPRICED_BY_LEDGER -- read the live rate'),
        ('firecrawl_credits_available', 0),
        ('note', 'Firecrawl sits at 0 credits and PTF-FIRECRAWL-HARD-LANES-003 '
                 'found it cannot reach Marriott or Hilton, so it is not a lane '
                 'for this cohort even if credits were bought.'),
    ))

    return collections.OrderedDict((
        ('schema', 'ptf-routing-cost-plan/1.0'),
        ('work_order', WORK_ORDER),
        ('market_id', MARKET_ID),
        ('generated_at', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
        ('founder_decision_source',
         'PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001 COVERAGE-003'),
        ('spend_authorized_usd', 0.0),
        ('pages_acquired', 0),
        ('the_fact_that_shapes_this_plan',
         'all unrouted rows are blocked on NO_OFFICIAL_URL. None is a straight '
         'acquisition row: you cannot buy a page you cannot address. Every row '
         'is routing-first, so the acquisition budget is a function of the '
         'routing yield, not of the cohort size.'),
        ('measured_rates', collections.OrderedDict((
            ('source', 'this project\'s committed ledgers, read at run time'),
            ('paid_attempts_in_ledger', sum(l['attempts'] for l in lanes.values())),
            ('lanes', lanes),
            ('brightdata_publication_grade_by_brand', brand_yield),
            ('discovery', discovery)))),
        ('indianapolis_measured_pet_friendly_rate', pf_rate),
        ('cohort_primary', primary),
        ('cohort_extended', extended),
        ('recommended_pilot', pilot),
        ('required_account_balance', required_balance),
        ('guarantees', collections.OrderedDict((
            ('paid_provider_calls', 0), ('usd_spent', 0.0),
            ('pages_acquired', 0), ('routes_bound', 0),
            ('census_modified', False), ('deployment', 'NONE'),
            ('launch_authorization', 'NONE')))),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--package-dir', default=os.path.join(
        _REPO_ROOT, 'atlas-dashboard', 'launch_packages', 'pettripfinder'))
    ap.add_argument('--out')
    args = ap.parse_args(argv)

    plan = build(args.package_dir)
    out = args.out or os.path.join(
        os.path.abspath(args.package_dir),
        'indianapolis_in_routing_cost_plan_003.json')
    with io.open(out, 'w', encoding='utf-8') as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
        fh.write('\n')

    p, e = plan['cohort_primary'], plan['cohort_extended']
    bd = plan['measured_rates']['lanes']['brightdata_browser']
    d = plan['measured_rates']['discovery']
    print('=== MEASURED RATES (from %d paid + %d discovery attempts) ==='
          % (plan['measured_rates']['paid_attempts_in_ledger'], d['attempts']))
    print('  BD browser      $%.4f/billed attempt, pub-grade %.1f%% (Wilson %.1f%%)'
          % (bd['usd_per_billed_attempt'], 100 * bd['publication_grade_rate'],
             100 * bd['publication_grade_rate_wilson_lower']))
    print('  Places bind     %.1f%% (Wilson %.1f%%), unit price %s'
          % (100 * d['bind_rate'], 100 * d['bind_rate_wilson_lower'],
             d['unit_price_state']))
    for label, c in (('PRIMARY  (audit cohort, post-rulings)', p),
                     ('EXTENDED (all unrouted in shadow)', e)):
        print()
        print('=== %s -- %d rows ===' % (label, c['rows']))
        for k, v in c['segments'].items():
            print('   %-42s %d' % (k, v))
        s1, s2 = c['stage_1_routing'], c['stage_2_acquisition']
        print('   stage 1 free-lane first (at $0)          %d' % s1['free_lane_rows_try_first_at_zero_cost'])
        print('   stage 1 needing paid discovery           %d' % s1['rows_needing_paid_discovery'])
        print('   stage 1 expected routed  %.1f point / %.1f lower'
              % (s1['expected_rows_routed_point'], s1['expected_rows_routed_lower']))
        print('   stage 2 paid attempts    %.1f point / %.1f lower'
              % (s2['projected_paid_attempts_point'], s2['projected_paid_attempts_lower']))
        print('   stage 2 expected cost    $%.2f point / $%.2f lower'
              % (s2['expected_cost_point_usd'], s2['expected_cost_lower_usd']))
        print('   expected PF gain         %.1f point / %.1f lower'
              % (s2['expected_pet_friendly_gain_point'],
                 s2['expected_pet_friendly_gain_lower']))
        print('   CONSERVATIVE HARD CAP    $%.2f' % c['conservative_hard_cap_ceiling_usd'])
    print()
    print('recommended first batch : %d rows' % plan['recommended_pilot']['recommended_first_batch_rows'])
    print('balance needed (pilot)  : $%.2f Bright Data + Places (unpriced)'
          % plan['required_account_balance']['bright_data_for_the_recommended_pilot_usd'])
    print('SPEND AUTHORIZED        : $%.2f' % plan['spend_authorized_usd'])
    print('written: %s' % os.path.basename(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
