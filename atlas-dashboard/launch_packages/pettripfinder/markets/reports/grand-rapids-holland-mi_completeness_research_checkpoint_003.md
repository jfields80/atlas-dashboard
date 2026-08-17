# Grand Rapids–Holland Census Closure 003 — Research Checkpoint

Date: 2026-08-17

## Preflight

- Branch: `grok/ptf-grand-rapids-holland-market-001`
- Starting branch commit: `d792fb8feeeb7396236b32dc52f4fc98f9dba38e`
- Current `origin/main`: `2469391ae24c4ca08bad2fdae7fe3e35e53da64c`
- `origin/main` advanced after the prior checkpoint.  The merge-base comparison found no
  direct changed-path overlap with this Grand Rapids–Holland worktree, so this
  census-only closure continued without rebasing or merging.

## Final legacy identity dispositions

- **Hawthorn Suites by Wyndham Grand Rapids** — `SOURCE_LISTING_ALREADY_ACCOUNTED_FOR`.
  The historical Experience Grand Rapids listing identifies `2701 E Beltline Ave SE`,
  Grand Rapids, MI 49546, phone `616-957-8111`.  The current first-party Affordable
  Suites site has the same address and phone.  The canonical current identity is
  **Affordable Suites**; its prior census address was corrected from 2710 to 2701.
- **Ramada Plaza GRR shuttle roster** — `SOURCE_LISTING_ALREADY_ACCOUNTED_FOR`.
  The official GRR ground-transport page retains the historic Ramada name and phone
  `616-949-9222` at the airport cluster.  The exact 3333 28th St SE location is now
  corroborated as **The Center Hotel Grand Rapids Airport** by its current Choice
  property page.  The historic Sonesta alias is retained in the closure ledger as
  `CLOSED_OR_CONVERTED` rather than silently removed.

## Holland / Zeeland closure inventory

The official Holland hotel directory remains dynamically rendered and therefore is
still `PARTIAL` in the global source registry.  A dedicated closure pass reconciled
the directory, current official brand property pages, and current first-party
property sites.  It added the following address-bound transient-lodging identities:

- Days Inn by Wyndham Holland
- TownePlace Suites by Marriott Holland
- Microtel Inn & Suites by Wyndham Holland
- Wooden Shoe Motel
- WoodSpring Suites Holland Grand Rapids
- Residence Inn by Marriott Holland
- SpringHill Suites by Marriott Holland
- avid hotel Zeeland
- Baymont Inn & Suites by Wyndham Holland
- White Pines Inn & Suites Holland

The pass kept Saugatuck/Douglas, Grand Haven, Muskegon, and South Haven outside the
market boundary.  Holland tourism materials also continue to distinguish B&B/inn
inventory from the hotel category, supporting the existing category rule.

## Kent County roster closure

The official Kent County hotel/motel-tax roster was reconciled for relevant
in-boundary lodging-looking rows.  The closure pass added 14 address-bound transient
hotel/motel identities, including the Best Western Executive Inn & Suites and
SpringHill Suites Grand Rapids West, plus the remaining named motel inventory in the
Grand Rapids, Wyoming, Walker, Kentwood, and Grandville cells.  Colonial Motel,
Pine Lodge Motel, and Grand Motel are explicit boundary exclusions; Brauhaus Inn and
Prince Conference Center are category exclusions.

The registry remains `PARTIAL`: the shared vocabulary only supports `COMPLETE`,
`PARTIAL`, and `UNUSABLE`, and the source as a whole contains out-of-scope rentals,
apartments, aliases, and non-lodging taxpayers.  This pass is complete for the
relevant in-scope lodging reconciliation; it does not falsely claim the entire tax
roster is a fully enumerable hotel directory.

## Airport and independent checks

The airport sanity check found no new unexplained cluster gap.  The Affordable Suites
address correction moves that identity from the airport corridor to East Grand
Rapids/Ada, and the historic Ramada/Sonesta location is represented by The Center
Hotel Grand Rapids Airport.  The dedicated independent scan added the two Holland
independents above (Wooden Shoe Motel and White Pines Inn & Suites Holland) and no
new, address-proven independent in the other specified market cells.

No pet-policy content was captured or assessed during this work.
