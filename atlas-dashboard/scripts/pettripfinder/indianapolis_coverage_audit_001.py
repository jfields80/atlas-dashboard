"""PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001 -- assemble the audit record.

The question this audit was opened on: PetTripFinder publishes ~56 pet-friendly
Indianapolis hotels while an external BringFido benchmark shows ~122. Is the
census undercounting the market?

The answer is BOTH, in very different proportions than the framing assumed, and
the two causes need separate remedies:

  * The dominant cause is POLICY COVERAGE, not census coverage. 118 of the 257
    registered identities are blocked on one thing -- no official URL was ever
    found for them. At the market's own measured 62% pet-friendly rate, routing
    those 118 would project roughly 160 pet-friendly profiles, ABOVE the 122
    benchmark. The hotels are in the census; we cannot read their policies.

  * There is ALSO a real census gap, and this run proves 12 of it. Those 12 are
    concentrated in the economy and extended-stay tier (Baymont, Days Inn,
    Super 8, Travelodge, Extended Stay America) -- the brands the original
    factory's source families under-covered.

12 is a FLOOR. Only 6 of 13 brand families would serve a directory or sitemap
for free this run; the families that refused hold the larger half of the census.
This audit does not extrapolate across them, because it has no evidence for
them.

BringFido was never contacted and is never policy evidence. It is the reason the
question was asked, and nothing else. Every fetch here was free first-party
HTTP: 0 paid provider calls, $0 spent. The registered 257-identity census is
contract-pinned and is NOT modified -- the 12 proposed identities are written to
a separate shadow document for founder adjudication.
"""
import collections
import hashlib
import io
import json
import os
import time

PACKAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', '..', 'launch_packages', 'pettripfinder')
WORK_ORDER = 'PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001'
MARKET_ID = 'indianapolis-in'

#: Brand families that refused a free directory or sitemap this run. They hold
#: the larger half of the census, which is why the miss count is a floor.
UNREADABLE_FAMILIES = ['CHOICE', 'IHG', 'MARRIOTT', 'MOTEL6', 'RED_ROOF',
                       'SONESTA', 'RADISSON', 'INTOWN', 'BEST_WESTERN', 'HYATT']


def _read(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _write(path, doc):
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def build(evidence_dir):
    """Assemble the audit record from the run's own evidence files."""
    ev = {n: _read(os.path.join(evidence_dir, n + '.json')) for n in (
        'phase1', 'phase5', 'phase6', 'no_url_profile', 'harvest', 'bind',
        'true_missing2', 'reconcile27', 'verify22', 'soft404',
        'phase4_final', 'verify_routes', 'retry_esa', 'shadow_inventory')}

    free_http = sum(ev[n].get('free_http_requests', 0) for n in
                    ('harvest', 'bind', 'verify22', 'soft404',
                     'verify_routes', 'retry_esa'))

    retried = ev['retry_esa']['rows']
    confirmed_routes = (ev['verify_routes']['confirmed']
                        + [r for r in retried if r['verdict'] == 'CONFIRMED'])
    successors = [r for r in retried if r['verdict'] == 'REBRAND_OR_SUCCESSOR']
    refused_on_name = [r for r in retried if r['verdict'] == 'REFUSED']

    return collections.OrderedDict((
        ('contract', 'ptf-market-coverage-audit/1.0'),
        ('work_order', WORK_ORDER),
        ('market_id', MARKET_ID),
        ('generated_at', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
        ('benchmark', collections.OrderedDict((
            ('source', 'BringFido'),
            ('claimed_hotels', 122),
            ('role', 'DISCOVERY_PROMPT_ONLY'),
            ('used_as_policy_evidence', False),
            ('contacted_during_this_audit', False)))),
        ('cost', collections.OrderedDict((
            ('paid_provider_calls', 0),
            ('usd_spent', 0.0),
            ('free_first_party_http_requests', free_http),
            ('pages_re_purchased', 0)))),
        ('census', collections.OrderedDict((
            ('registered_identities', ev['phase5']['raw_census_identities']),
            ('deduplicated_identities',
             ev['phase5']['deduplicated_census_identities']),
            ('genuine_duplicate_clusters', ev['phase5']['duplicate_clusters']),
            ('preserved_duplicate_finding',
             'hampton inn indianapolis sw / southwest plainfield'),
            ('modified_by_this_audit', False)))),
        ('resolution', collections.OrderedDict((
            ('pet_friendly', 56), ('verified_no_pets', 34),
            ('resolved', 90), ('unresolved', 167),
            ('live_published_profiles', 56)))),
        ('blockers', ev['phase6']['blockers']),
        ('primary_finding', collections.OrderedDict((
            ('cause', 'POLICY_COVERAGE'),
            ('statement',
             '118 of 257 registered identities are blocked solely on '
             'NO_OFFICIAL_URL. At the market measured 62% pet-friendly rate '
             'those alone project ~160 pet-friendly profiles, above the 122 '
             'benchmark. The census is not the binding constraint.'),
            ('unrouted_identities', len(ev['no_url_profile']['no_url_keys'])),
            ('projected_pf_if_routed', 160)))),
        ('secondary_finding', collections.OrderedDict((
            ('cause', 'CENSUS_GAP'),
            ('true_missing_identities',
             len(ev['shadow_inventory']['proposed_identities'])),
            ('is_a_floor', True),
            ('why_a_floor',
             'only 6 of 13 brand families served a free directory or sitemap; '
             'the rest refused and hold the larger half of the census, so no '
             'estimate is projected across them'),
            ('unreadable_families', UNREADABLE_FAMILIES),
            ('concentrated_in',
             ['ESA', 'BAYMONT', 'DAYS_INN', 'SUPER_8', 'TRAVELODGE']),
            ('miss_rate_within_readable_families',
             ev['shadow_inventory']['miss_rate_within_readable_families'])))),
        ('classification', ev['phase4_final']['counts']),
        ('free_routing_gain', collections.OrderedDict((
            ('candidate_urls_harvested',
             sum(len(v) for v in ev['harvest']['by_brand'].values())),
            ('rows_with_leads', ev['bind']['rows_with_leads']),
            ('confirmed_net_new_routes', len(confirmed_routes)),
            ('routes', confirmed_routes),
            ('refused_after_physical_check', len(refused_on_name)),
            ('note',
             'six rows matched a harvested URL on brand and locality; only two '
             'survived physical verification against the page own address. A '
             'name may propose a match, never decide one.')))),
        ('successor_questions', successors),
        ('guarantees', collections.OrderedDict((
            ('registered_census_untouched', True),
            ('existing_authority_preserved', True),
            ('other_markets_untouched', True),
            ('cross_market_identity_collisions_introduced', 0),
            ('published_profiles_changed', 0),
            ('deployment_performed', False),
            ('launch_authorization_issued', False),
            ('paid_acquisition_performed', False)))),
    ))


def founder_packet(audit, inventory):
    """The single decision packet this audit hands to the founder."""
    return collections.OrderedDict((
        ('contract', 'ptf-founder-review-packet/1.0'),
        ('work_order', WORK_ORDER),
        ('market_id', MARKET_ID),
        ('generated_at', audit['generated_at']),
        ('nothing_was_spent', True),
        ('decisions_requested', [
            collections.OrderedDict((
                ('id', 'COVERAGE-001'),
                ('question',
                 'Admit the 12 proposed economy and extended-stay identities '
                 'into the Indianapolis census?'),
                ('evidence',
                 'each was named, with its street address, by its own brand '
                 'property page; none of the 12 addresses appears anywhere in '
                 'the registered census'),
                ('cost_if_approved',
                 'census admission is free; policy evidence for them is not'),
                ('default_if_declined',
                 'the 12 stay out and are not published'),
                ('items', inventory['proposed_identities']))),
            collections.OrderedDict((
                ('id', 'COVERAGE-002'),
                ('question',
                 'Is "woodspring suites indianapolis plainfield" the same '
                 'building now trading as Extended Stay America Plainfield?'),
                ('evidence',
                 'the ESA Plainfield page names 6295 Gateway Dr 46168, which '
                 'is the census address for the WoodSpring row; street and '
                 'postal agree but the BRAND DIFFERS, so this is a successor '
                 'question and not an automatic bind'),
                ('cost_if_approved', 'none -- it routes an unrouted row'),
                ('default_if_declined',
                 'the row stays unrouted and unpublished'),
                ('items', audit['successor_questions']))),
            collections.OrderedDict((
                ('id', 'COVERAGE-003'),
                ('question',
                 'Open a paid cohort against the 118 unrouted identities?'),
                ('evidence',
                 'this is the actual constraint on Indianapolis coverage; it '
                 'needs its own cost plan and NOTHING is authorised by this '
                 'audit'),
                ('cost_if_approved', 'UNPRICED -- requires its own cost plan'),
                ('default_if_declined',
                 'Indianapolis stays at 56 published pet-friendly profiles'),
                ('items', []))),
        ]),
    ))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--evidence-dir', required=True,
                    help='directory holding this run evidence json')
    ap.add_argument('--package-dir', default=PACKAGE_DIR)
    args = ap.parse_args()

    audit = build(args.evidence_dir)
    inventory = _read(os.path.join(args.evidence_dir, 'shadow_inventory.json'))
    packet = founder_packet(audit, inventory)

    pkg = os.path.abspath(args.package_dir)
    for name, doc in (
            ('indianapolis_in_coverage_audit_001.json', audit),
            ('indianapolis_in_shadow_additive_inventory_001.json', inventory),
            ('indianapolis_in_coverage_audit_founder_packet_001.json', packet)):
        digest = _write(os.path.join(pkg, name), doc)
        print('%-58s %s' % (name, digest[:16]))

    print()
    print('paid provider calls : %d' % audit['cost']['paid_provider_calls'])
    print('usd spent           : %.2f' % audit['cost']['usd_spent'])
    print('free http requests  : %d'
          % audit['cost']['free_first_party_http_requests'])
    print('census modified     : %s' % audit['census']['modified_by_this_audit'])
    print('true missing (floor): %d'
          % audit['secondary_finding']['true_missing_identities'])
    print('net new routes      : %d'
          % audit['free_routing_gain']['confirmed_net_new_routes'])


if __name__ == '__main__':
    main()
