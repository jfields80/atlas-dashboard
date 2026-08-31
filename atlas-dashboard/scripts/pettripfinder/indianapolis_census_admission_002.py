"""PTF-INDIANAPOLIS-CENSUS-ADMISSION-002 -- admit the founder-approved identities.

COVERAGE-001 of the founder's ruling on PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001
approved the 12 TRUE_MISSING_IDENTITY rows into the Indianapolis census, under
four conditions: census addition only, no policy publication without first-party
evidence, identity proof preserved, and no duplicate or cross-market collision.

EIGHT are admitted. FOUR are withheld. One of those four would have broken the
fourth condition outright:

    Extended Stay America, 7940 N. Shadeland Ave, 46250.

    ESA's own directory lists exactly ONE Castleton property and that page names
    7940 N. Shadeland Ave. Our census already carries "extended stay america
    indianapolis castleton" at 8280 Bash Street in the same ZIP. Both cannot be
    right. Either the census row's address is stale or wrong -- in which case the
    fix is an ADDRESS SUPERSESSION on the row we already have -- or 8280 Bash
    Street closed. Admitting a second row would manufacture the duplicate the
    founder forbade, so this one is withheld to identity review beside the
    WoodSpring/ESA Plainfield successor question.

WHAT AN ADMITTED ROW CARRIES
----------------------------
Its own brand page named it, and that page was read three times across this
work: once to find the address, once to prove no census row held that address,
and once more here for the property's OWN name, telephone and postal address.
All three readings agree. That trio plus the URL is the row's identity evidence.

No admitted row carries a policy. Every one lands POLICY_NOT_VERIFIED with an
empty official_url-derived policy state, because a brand directory naming a
building is evidence of the BUILDING, never of its pet policy.

CORRIDORS
---------
Corridor membership is the corridor registry's decision, not this script's.
Three rows sit in ZIPs (46236, 46239) that no declared Indianapolis corridor
covers, and this market holds every census row to exactly one corridor. They are
therefore WITHHELD too, not admitted corridor-less: widening the registry decides
which corridor PAGE a hotel appears on, which is a market-contract change and a
separate founder decision. Guessing one here would publish a hotel into a
neighbourhood nobody chose.

So ELEVEN were approved, EIGHT are admitted, and FOUR are withheld to review.

WHY THIS WRITES A SHADOW AND NOT THE PINNED CENSUS
--------------------------------------------------
The registered census is pinned by the release contract's ``expected_count``,
and that contract's hash is pinned in turn by the consumed deployment
authorization behind the LIVE Indianapolis deploy. Moving the pinned census
therefore forces the release contract to move, which invalidates the global
deployment manifest and demands a fresh assembly and authorization -- a
deployment step, which COVERAGE-001 explicitly forbade.

The founder's approval and the founder's "no deployment" condition are jointly
satisfiable in exactly one way, and it is the one this project already
prescribes: apply the admission to a COPY. The shadow carries the full admitted
universe and its evidence; promoting it into the pinned census is a separate,
deployment-bearing step that must be authorised with the next assembly.

Nothing here fetches, spends, publishes, deploys or writes authority, and the
pinned census is not touched.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import io
import json
import os
import re
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          '..', '..'))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.pettripfinder.contracts import census as CENSUS          # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = 'PTF-INDIANAPOLIS-CENSUS-ADMISSION-002'
AUDIT_ORDER = 'PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001'
MARKET_ID = 'indianapolis-in'

#: The one identity withheld, and why. Keyed by the address its page named.
WITHHELD = {
    '7940 N. Shadeland Ave.': (
        'ADDRESS_SUPERSESSION_REVIEW',
        "ESA lists exactly one Castleton property and it names this address, "
        "while census row 'extended stay america indianapolis castleton' "
        "carries 8280 Bash Street in the same ZIP. Admitting this would create "
        "the duplicate COVERAGE-001 forbids; the open question is whether the "
        "EXISTING row's address is stale."),
}

#: A brand-line name that names no building. Qualified with the locality the
#: brand's own URL uses, because two of these would otherwise key identically.
GENERIC_NAMES = re.compile(r'^(extended stay america select suites|'
                           r'all non-smoking suites|extended stay america)$', re.I)


def _read(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _write(path, doc):
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def clean_name(raw, url):
    """The property's own name, made into one line without inventing anything."""
    name = re.sub(r'\s*[-/]\s*', ' ', raw or '').strip()
    name = re.sub(r'\s{2,}', ' ', name)
    if GENERIC_NAMES.match(name) or not name:
        base = 'Extended Stay America Select Suites' if 'select' in (raw or '').lower() \
            else 'Extended Stay America'
        loc = url.rstrip('/').rsplit('/', 1)[-1].replace('-', ' ').title()
        name = '%s Indianapolis %s' % (base, loc)
    return name


def corridor_for(postal, corridors):
    for c in corridors:
        if postal and postal in (c.get('included_postal_codes') or []):
            return c['corridor_id']
    return ''


def build(package_dir, evidence):
    pkg = os.path.abspath(package_dir)
    census_path = os.path.join(pkg, 'identity_census', MARKET_ID + '.json')
    shadow_dir = os.path.join(pkg, 'identity_census_admission')
    census = _read(census_path)
    prior_rows = census['hotels']
    prior_keys = {h['identity_key'] for h in prior_rows}
    contract = _read(os.path.join(pkg, 'markets', MARKET_ID + '.json'))
    corridors = contract['corridors']

    admitted, withheld = [], []
    for r in evidence['rows']:
        addr = r['page_address'] or r['audit_address']
        if addr in WITHHELD:
            state, why = WITHHELD[addr]
            withheld.append(collections.OrderedDict((
                ('address', addr), ('url', r['url']), ('page_name', r['page_name']),
                ('review_state', state), ('why', why))))
            continue
        if not r['address_reconfirmed']:
            withheld.append(collections.OrderedDict((
                ('address', addr), ('url', r['url']),
                ('review_state', 'EVIDENCE_NOT_RECONFIRMED'),
                ('why', 'the page did not re-state this address on the naming read'))))
            continue

        name = clean_name(r['page_name'], r['url'])
        key = ptf_identity_key(name)
        postal = r['page_postal'] or r['audit_postal']
        corridor = corridor_for(postal, corridors)
        if not corridor:
            # The market holds every census row to exactly one registry
            # corridor. A row in a ZIP no corridor covers cannot be admitted
            # without first widening the corridor registry -- and that is a
            # market-contract change, i.e. a decision about which corridor PAGE
            # a hotel appears on. COVERAGE-001 authorised a census addition, not
            # a geography change, so these go back to the founder instead.
            withheld.append(collections.OrderedDict((
                ('address', addr), ('url', r['url']), ('page_name', r['page_name']),
                ('postal_code', postal),
                ('review_state', 'CORRIDOR_REGISTRY_REVIEW'),
                ('why', 'ZIP %s is covered by no declared Indianapolis corridor. '
                        'Admitting it would break the market invariant that every '
                        'census row belongs to exactly one corridor; widening the '
                        'registry is a market-contract decision.' % postal))))
            continue
        row = collections.OrderedDict((
            ('identity_key', key),
            ('canonical_name', name),
            ('display_name', name),
            ('slug', re.sub(r'[^a-z0-9]+', '-', key).strip('-')),
            ('market_id', MARKET_ID),
            ('address', addr),
            ('city', r['page_city'] or 'Indianapolis'),
            ('state', 'IN'),
            ('postal_code', postal),
            ('phone', r['page_phone'] or ''),
            ('identity_state', 'IDENTITY_CONFIRMED'),
            ('lodging_state', 'LODGING_BY_NAME'),
            ('policy_state', 'POLICY_NOT_VERIFIED'),
            ('collision_state', 'NONE'),
            # The brand page named the BUILDING. It is not policy evidence, and
            # it is not a route: routing is a separate, evidenced decision.
            ('official_url', ''),
            ('corridor', corridor),
            ('source', 'brand_directory'),
            ('observed_at', time.strftime('%Y-%m-%d')),
            ('provenance', '%s:BRAND_DIRECTORY' % AUDIT_ORDER),
            ('admission', collections.OrderedDict((
                ('work_order', WORK_ORDER),
                ('founder_decision', 'COVERAGE-001 APPROVED'),
                ('evidence_url', r['url']),
                ('page_named', r['page_name']),
                ('page_address', r['page_address']),
                ('page_postal', r['page_postal']),
                ('page_telephone', r['page_phone']),
                ('address_read_three_times', True),
                ('name_basis', 'the brand page in the same JSON-LD object as the '
                               'verified address'),
                ('policy_evidence', 'NONE -- a directory names a building, not a '
                                    'policy')))),
        ))
        row['assignment_basis'] = 'postal_code'
        row['assignment_value'] = postal
        admitted.append(row)
    return (census, census_path, shadow_dir, prior_rows, prior_keys, admitted,
            withheld)


def collisions(admitted, prior_keys, package_dir):
    """No duplicate, and no cross-market collision -- COVERAGE-001's condition."""
    out = []
    seen = collections.Counter(r['identity_key'] for r in admitted)
    for k, n in seen.items():
        if n > 1:
            out.append(('DUPLICATE_WITHIN_ADMISSION', k, '%d rows' % n))
    for r in admitted:
        if r['identity_key'] in prior_keys:
            out.append(('COLLIDES_WITH_CENSUS', r['identity_key'], 'already registered'))
    import glob
    for p in sorted(glob.glob(os.path.join(package_dir, 'markets', '*.json'))):
        if MARKET_ID in os.path.basename(p):
            continue
        blob = io.open(p, encoding='utf-8', errors='replace').read().lower()
        for r in admitted:
            if r['identity_key'] in blob:
                out.append(('CROSS_MARKET_COLLISION', r['identity_key'],
                            os.path.basename(p)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--package-dir', default=os.path.join(
        _REPO_ROOT, 'atlas-dashboard', 'launch_packages', 'pettripfinder'))
    ap.add_argument('--evidence', required=True)
    ap.add_argument('--write', action='store_true',
                    help='write the SHADOW admission census; the pinned census '
                         'is never touched by this script')
    args = ap.parse_args(argv)

    pkg = os.path.abspath(args.package_dir)
    evidence = _read(args.evidence)
    (census, census_path, shadow_dir, prior_rows, prior_keys, admitted,
     withheld) = build(pkg, evidence)

    print('=== COVERAGE-001 admission ===')
    print('prior census identities : %d' % len(prior_rows))
    print('admitted                : %d' % len(admitted))
    print('withheld                : %d' % len(withheld))
    for w in withheld:
        print('   WITHHELD %-28s %s' % (w['address'], w['review_state']))
    print()
    for r in admitted:
        print('   %-52s %-28s %-6s %s'
              % (r['identity_key'][:52], r['address'][:28], r['postal_code'],
                 r.get('corridor') or 'CORRIDOR_UNASSIGNED'))

    bad = collisions(admitted, prior_keys, pkg)
    print()
    print('collision checks: %s' % ('CLEAN' if not bad else 'FAILED'))
    for kind, key, detail in bad:
        print('   %-28s %-46s %s' % (kind, key, detail))
    if bad:
        return 2

    # Every prior identity must survive, unchanged. A promotion ACCOUNTS for the
    # rows it inherits; it never overwrites them.
    promoted = copy.deepcopy(census)
    promoted['hotels'] = prior_rows + admitted
    promoted['count'] = len(promoted['hotels'])
    kept = {h['identity_key']: h for h in promoted['hotels']}
    unchanged = all(kept.get(h['identity_key']) == h for h in prior_rows)
    print('every prior identity survives unchanged: %s' % unchanged)
    if not unchanged:
        return 2

    prior_sha = _sha(census_path)
    promoted['schema'] = census['schema']
    promoted['what_this_is'] = (
        'a SHADOW admission census: the pinned census with the founder-approved '
        'COVERAGE-001 identities added. The pinned census is UNTOUCHED. '
        'Promoting this into it moves the release contract and therefore the '
        'deployment manifest, so promotion is a deployment-bearing step and is '
        'not performed here.')
    promoted['work_order'] = WORK_ORDER
    promoted['captured_at'] = time.strftime('%Y-%m-%d')
    promoted['identity_state_counts'] = dict(
        collections.Counter(h['identity_state'] for h in promoted['hotels']))
    promoted['admission'] = collections.OrderedDict((
        ('what_this_is',
         'the pinned census with the founder-approved COVERAGE-001 additions '
         'applied; every prior identity is carried forward byte-identical'),
        ('pinned_census_touched', False),
        ('promotion_is_a_separate_deployment_bearing_step', True),
        ('work_order', WORK_ORDER),
        ('founder_decision_source', AUDIT_ORDER),
        ('supersedes', collections.OrderedDict((
            ('work_order', census.get('work_order')),
            ('count', len(prior_rows)),
            ('sha256', prior_sha)))),
        ('added', len(admitted)),
        ('withheld', withheld),
        ('policy_published_by_this_admission', 0),
        ('deployment', 'NONE'),
    ))

    issues = CENSUS.validate(promoted, market_states=('IN',))
    hard = [i for i in issues if getattr(i, 'code', '') not in ('',)]
    print('census contract issues: %d' % len(hard))
    for i in hard[:10]:
        print('   %s %s %s' % (i.path, i.code, i.message))
    if hard:
        return 2

    if not args.write:
        print()
        print('DRY RUN -- nothing written. Re-run with --write.')
        return 0

    if not os.path.isdir(shadow_dir):
        os.makedirs(shadow_dir)
    shadow_path = os.path.join(shadow_dir, MARKET_ID + '.json')
    digest = _write(shadow_path, promoted)
    print()
    print('SHADOW admission census written: %d -> %d identities'
          % (len(prior_rows), promoted['count']))
    print('  pinned census   : UNTOUCHED at %d (%s)'
          % (len(prior_rows), prior_sha[:16]))
    print('  shadow sha256   : %s' % digest[:16])
    print('  shadow path     : %s'
          % os.path.relpath(shadow_path, _REPO_ROOT).replace(os.sep, '/'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
