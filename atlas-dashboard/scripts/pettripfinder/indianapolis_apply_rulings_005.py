"""PTF-INDIANAPOLIS-APPLY-RULINGS-005 -- apply the founder's three rulings.

Applies to the SHADOW admission census only. The pinned production census, the
release contract, the final partition and the global deployment manifest are all
untouched, for the reason established in PTF-INDIANAPOLIS-CENSUS-ADMISSION-002:
moving the pinned census moves the release contract, which invalidates the
deployment manifest, which is a deployment step.

WHAT EACH RULING DOES TO THE COUNT
----------------------------------
Ruling 1 (WoodSpring Plainfield -> ESA Plainfield) and Ruling 2 (ESA Castleton
address) are SUPERSESSIONS. They correct rows in place. Neither adds a row, and
neither may add one: creating a second identity is precisely the error both
rulings exist to prevent. Only Ruling 3 changes the count, by +3.

The final count is DERIVED here and then checked against the founder's stated
expectation. It is not forced to 268: if the arithmetic disagrees with the
expectation, that is a finding, not something to paper over.

LINEAGE IS PRESERVED, NOT REWRITTEN
-----------------------------------
A superseded row keeps its former identity key, its former name, its former
address and its original provenance, in a ``supersession`` block on the row that
replaces it. Nothing is deleted. A later reader can always ask what this row used
to be and which work order changed it.

ROUTES ARE BOUND, POLICY IS NOT
-------------------------------
Both superseded rows gain a first-party official_url and telephone. Neither gains
a policy: the founder was explicit that a known route is not evidence of a pet
policy, and the free-lane check (PHASE 6) found a property-specific affirmative
carrying no operative term, which the committed reader scores as neither an allow
nor a refusal. Both stay POLICY_NOT_VERIFIED.

Nothing here fetches, spends, publishes, deploys, or writes authority.
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
from scripts.pettripfinder.markets.contract import normalize_name     # noqa: E402

WORK_ORDER = 'PTF-INDIANAPOLIS-APPLY-RULINGS-005'
MARKET_ID = 'indianapolis-in'
FOUNDER = 'PTF-FOUNDER-001'

#: Ruling 3: exactly these three, assigned explicitly. This list is the whole
#: authority for the change -- it must never be widened into a ZIP rule.
EXPLICIT_ASSIGNMENTS = collections.OrderedDict((
    ('extended stay america indianapolis lawrence', 'indianapolis-in__keystone-castleton'),
    ('baymont by wyndham indianapolis northeast', 'indianapolis-in__keystone-castleton'),
    ('baymont by wyndham indianapolis', 'indianapolis-in__east-i70'),
))


def _read(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


def _write(path, doc):
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def supersede(row, *, new_name=None, new_address=None, new_postal=None,
              url, phone, ruling, verdict, why, evidence):
    """Correct a row in place, keeping everything it used to be."""
    was = collections.OrderedDict((
        ('identity_key', row['identity_key']),
        ('canonical_name', row.get('canonical_name')),
        ('address', row.get('address')),
        ('postal_code', row.get('postal_code')),
        ('official_url', row.get('official_url') or ''),
        ('phone', row.get('phone') or ''),
        ('provenance', row.get('provenance')),
        ('source', row.get('source')),
        ('source_id', row.get('source_id')),
        ('observed_at', row.get('observed_at')),
    ))
    out = copy.deepcopy(row)
    if new_name:
        out['canonical_name'] = new_name
        out['display_name'] = new_name
        out['identity_key'] = ptf_identity_key(new_name)
        out['slug'] = re.sub(r'[^a-z0-9]+', '-', out['identity_key']).strip('-')
    if new_address:
        out['address'] = new_address
    if new_postal:
        out['postal_code'] = new_postal
    out['official_url'] = url
    out['phone'] = phone
    # A route is not a policy. The founder said so explicitly, and the free-lane
    # check found an affirmative with no operative term.
    out['policy_state'] = 'POLICY_NOT_VERIFIED'
    out['supersession'] = collections.OrderedDict((
        ('work_order', WORK_ORDER),
        ('ruling', ruling),
        ('decided_by', FOUNDER),
        ('verdict', verdict),
        ('was', was),
        ('why', why),
        ('evidence', evidence),
        ('lineage_preserved', True),
        ('second_identity_created', False),
        ('policy_published', False),
    ))
    return out


def build(package_dir):
    pkg = os.path.abspath(package_dir)
    shadow_path = os.path.join(pkg, 'identity_census_admission', MARKET_ID + '.json')
    shadow = _read(shadow_path)
    pinned = _read(os.path.join(pkg, 'identity_census', MARKET_ID + '.json'))
    packet = _read(os.path.join(pkg, 'indianapolis_in_founder_packet_004.json'))
    decisions = {d['id']: d for d in packet['decisions_requested']}

    rows = {h['identity_key']: h for h in shadow['hotels']}
    before = len(shadow['hotels'])
    key_map, applied = collections.OrderedDict(), []

    # ---- Ruling 1: WoodSpring Plainfield is now ESA Plainfield --------------
    d1 = decisions['IDR-002-001']
    old1 = d1['current_identity']['identity_key']
    p1 = d1['proposed_action']
    src = rows[old1]
    new1 = supersede(
        src, new_name=p1['new_canonical_name'],
        url=p1['new_official_url'], phone=p1['telephone_to_record'],
        ruling='FOUNDER RULING 1 -- SAME_IDENTITY_REBRAND_SUCCESSOR',
        verdict='SAME_IDENTITY_REBRAND_SUCCESSOR',
        why='one continuing hotel identity at 6295 Gateway Drive; the building '
            'rebranded from WoodSpring to Extended Stay America',
        evidence=d1['first_party_evidence'])
    key_map[old1] = new1['identity_key']
    applied.append(('IDR-002-001', old1, new1['identity_key'], 'RENAME_AND_ROUTE'))

    # ---- Ruling 2: ESA Castleton address is stale ---------------------------
    d2 = decisions['IDR-002-002']
    old2 = d2['current_identity']['identity_key']
    p2 = d2['proposed_action']
    addr2 = p2['new_address'].split(',')[0].strip()
    new2 = supersede(
        rows[old2], new_address=addr2,
        url=p2['new_official_url'], phone=p2['telephone_to_record'],
        ruling='FOUNDER RULING 2 -- ADDRESS_SUPERSESSION',
        verdict='ADDRESS_STALE_IDENTITY_CORRECT',
        why='ESA operates exactly one Castleton identity and current first-party '
            'evidence binds it to Shadeland. Free evidence CANNOT prove an ESA '
            'never historically operated at 8280 Bash Street; that address is '
            'preserved here rather than erased.',
        evidence=d2['first_party_evidence'])
    key_map[old2] = new2['identity_key']   # unchanged: an address move, not a rename
    applied.append(('IDR-002-002', old2, new2['identity_key'], 'ADDRESS_SUPERSESSION'))

    # ---- Ruling 3: the three explicit assignments ---------------------------
    d3 = decisions['IDR-002-003']
    admitted = []
    for cand in d3['candidates']:
        key = ptf_identity_key(cand['page_name'])
        corridor = EXPLICIT_ASSIGNMENTS[key]
        admitted.append(collections.OrderedDict((
            ('identity_key', key),
            ('canonical_name', cand['page_name']),
            ('display_name', cand['page_name']),
            ('slug', re.sub(r'[^a-z0-9]+', '-', key).strip('-')),
            ('market_id', MARKET_ID),
            ('address', cand['address']),
            ('city', cand['city']), ('state', 'IN'),
            ('postal_code', cand['postal_code']),
            ('phone', cand['telephone']),
            ('identity_state', 'IDENTITY_CONFIRMED'),
            ('lodging_state', 'LODGING_BY_NAME'),
            ('policy_state', 'POLICY_NOT_VERIFIED'),
            ('collision_state', 'NONE'),
            # the brand directory named the BUILDING; it is not a route
            ('official_url', ''),
            ('corridor', corridor),
            ('assignment_basis', 'explicit'),
            ('assignment_value', key),
            ('source', 'brand_directory'),
            ('observed_at', time.strftime('%Y-%m-%d')),
            ('provenance', 'PTF-INDIANAPOLIS-HARDENED-COVERAGE-AUDIT-001:BRAND_DIRECTORY'),
            ('admission', collections.OrderedDict((
                ('work_order', WORK_ORDER),
                ('ruling', 'FOUNDER RULING 3 -- EXPLICIT_HOTEL_ASSIGNMENT'),
                ('decided_by', FOUNDER),
                ('corridor_basis', 'explicit_hotel_ids -- this ruling covers ONLY '
                                   'this identity and must never admit a future '
                                   'hotel merely for sharing its ZIP'),
                ('evidence_url', cand['url']),
                ('policy_evidence', 'NONE -- a directory names a building, not a policy'),
            ))),
        )))

    # ---- assemble ----------------------------------------------------------
    out_rows = []
    for h in shadow['hotels']:
        k = h['identity_key']
        if k == old1:
            out_rows.append(new1)
        elif k == old2:
            out_rows.append(new2)
        else:
            out_rows.append(h)
    out_rows.extend(admitted)
    out_rows.sort(key=lambda r: r['identity_key'])

    doc = copy.deepcopy(shadow)
    doc['hotels'] = out_rows
    doc['count'] = len(out_rows)
    doc['work_order'] = WORK_ORDER
    doc['captured_at'] = time.strftime('%Y-%m-%d')
    doc['identity_state_counts'] = dict(
        collections.Counter(r['identity_state'] for r in out_rows))
    doc['rulings_005'] = collections.OrderedDict((
        ('decided_by', FOUNDER),
        ('applied_at', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
        ('supersessions', [
            {'ruling': a[0], 'from': a[1], 'to': a[2], 'action': a[3]}
            for a in applied]),
        ('explicit_admissions', [r['identity_key'] for r in admitted]),
        ('identity_key_map', key_map),
        ('count_before', before), ('count_after', len(out_rows)),
        ('count_delta', len(out_rows) - before),
        ('why_the_delta_is_three',
         'the two identity rulings are SUPERSESSIONS and correct rows in place; '
         'only the three explicit admissions add rows'),
        ('pinned_census_touched', False),
        ('policy_published', 0),
    ))
    return doc, shadow_path, pinned, admitted, applied, before


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--package-dir', default=os.path.join(
        _REPO_ROOT, 'atlas-dashboard', 'launch_packages', 'pettripfinder'))
    ap.add_argument('--expect-count', type=int, default=268)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    pkg = os.path.abspath(args.package_dir)
    doc, shadow_path, pinned, admitted, applied, before = build(pkg)

    print('=== PHASE 2: identity supersessions ===')
    for ruling, old, new, action in applied:
        arrow = old if old == new else '%s -> %s' % (old, new)
        print('  %-14s %-22s %s' % (ruling, action, arrow))

    print()
    print('=== PHASE 3: explicit corridor assignments ===')
    for r in admitted:
        print('  %-46s %-6s %s (%s)' % (r['identity_key'][:46], r['postal_code'],
                                        r['corridor'], r['assignment_basis']))

    # ---- checks ------------------------------------------------------------
    keys = [r['identity_key'] for r in doc['hotels']]
    dup_keys = [k for k, n in collections.Counter(keys).items() if n > 1]

    def na(a):
        a = (a or '').lower().rstrip('.')
        for x, y in (('street', 'st'), ('avenue', 'ave'), ('road', 'rd'),
                     ('drive', 'dr'), ('boulevard', 'blvd'), ('parkway', 'pkwy')):
            a = re.sub(r'\b%s\b' % x, y, a)
        return re.sub(r'[^a-z0-9 ]+', ' ', re.sub(r'\s+', ' ', a)).strip()

    before_dupes = {a for a, n in collections.Counter(
        na(h.get('address')) for h in pinned['hotels']).items() if n > 1 and a}
    after_dupes = {a for a, n in collections.Counter(
        na(r.get('address')) for r in doc['hotels']).items() if n > 1 and a}
    new_dupes = sorted(after_dupes - before_dupes)

    import glob
    cross = []
    for p in glob.glob(os.path.join(pkg, 'markets', '*.json')):
        if MARKET_ID in os.path.basename(p):
            continue
        blob = io.open(p, encoding='utf-8', errors='replace').read().lower()
        for r in admitted:
            if r['identity_key'] in blob:
                cross.append((r['identity_key'], os.path.basename(p)))

    pinned_keys = {h['identity_key'] for h in pinned['hotels']}
    lost = sorted(pinned_keys - set(keys))
    superseded = {a[1] for a in applied if a[1] != a[2]}
    lost_unexpected = [k for k in lost if k not in superseded]

    print()
    print('=== PHASE 4: shadow census rebuilt ===')
    print('  count before / after      : %d -> %d (delta %+d)'
          % (before, doc['count'], doc['count'] - before))
    print('  founder expectation       : %d  -> %s'
          % (args.expect_count,
             'AGREES' if doc['count'] == args.expect_count else 'DISAGREES'))
    print('  duplicate identity keys   : %s' % (dup_keys or 'none'))
    print('  NEW duplicate addresses   : %s' % (new_dupes or 'none'))
    print('  cross-market collisions   : %s' % (cross or 'none'))
    print('  pinned identities lost    : %s'
          % (lost_unexpected or 'none (only the renamed key changed, by ruling)'))
    print('  pinned census touched     : False')

    issues = CENSUS.validate(doc, market_states=('IN',))
    print('  census contract issues    : %d' % len(issues))
    for i in issues[:8]:
        print('     %s %s %s' % (i.path, i.code, i.message))

    ok = (not dup_keys and not new_dupes and not cross and not lost_unexpected
          and not issues and doc['count'] == args.expect_count)
    if not ok:
        print()
        print('REFUSING TO WRITE -- a check failed above.')
        return 2

    if not args.write:
        print()
        print('DRY RUN -- nothing written. Re-run with --write.')
        return 0

    digest = _write(shadow_path, doc)
    print()
    print('shadow admission census written: %d identities, sha %s'
          % (doc['count'], digest[:16]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
