# PTF-DALLAS-FORT-WORTH-TX-MARRIOTT-CLOSURE-WINDOW-002 — FINAL

Market `dallas-fort-worth-tx`, branch `worker/ptf-dallas-fort-worth-tx-market-001`, worktree
`C:\Atlas-Dallas-Fort-Worth-TX-Hardened-V1`. Starting HEAD `0dca730a` (origin == HEAD, tree clean, verified).

**Result:** the founder's one new paced Marriott window read **all 31** held rows. No Akamai denial occurred.
- Pet-friendly: 21 rows.
- Verified no-pets: 10 rows.
- Identity or policy holds: 0.
- Marriott actionable remaining: 0. Actionable unresolved: 0.

The data changed, so a **successor** package was sealed: `pkg-dallas-fort-worth-tx-b6dc951150886520`.
- FAST 15/15, eligible; Rule J 2,735 files / 2,719 HTML; Rule K BYTE_IDENTICAL.
- An independent reproduction matched it byte for byte.
- It supersedes `pkg-dallas-fort-worth-tx-e8a841396faeffec`. The predecessor's package and receipt stay on disk unchanged, and its receipt is still eligible for its own digest.

**COVERAGE READY stays FOUNDER DECISION.** The 25 paid-Places-only rows and the 4 founder-ruling rows are untouched by a Marriott window, and this order authorizes neither new spend nor rulings. Nothing was registered, authorized or deployed.

| Commit | Contents |
|---|---|
| `c0fc0194` | window-002 inputs: 31 recorder lines (seq 803–833), Beeman same-premises fold, pipeline outputs at a fixed point, staged tree, successor lineage in the shadow helper |
| `d85eb7ed` | successor package + receipt + shadow report |
| this report's commit | this report + superseded banner on the source-ready report |

---

## Phase 1 — current state verified
- Worktree, branch and HEAD `0dca730ae6f3344e6d7bb9631c266a6bc69557cd` were confirmed, with origin == HEAD and a clean tree.
- `pkg-dallas-fort-worth-tx-e8a841396faeffec` was in place:
  - Receipt `821f46f2…` eligible through `FL.eligible_receipts(..., receipts_dir=shadow_receipts)`: 1 eligible.
  - FAST 15/15 and reproducibility were proven in the source-ready order.
- The predecessor was never overwritten. The successor has its own package id and file names.

## Phase 2 — the 31-row hold set (mechanically derived)
**Derivation:**
- Taken from the committed `dallas_fort_worth_tx_actionability_001.json` at `0dca730a`: every row whose reason carries `MARRIOTT_AUTHORIZED_WINDOW_CLOSED`.
- That gives 31 rows: 24 ACCESS_BLOCKED and 7 ROUTING_HOLD, all AUTHORIZED_ROUTER_EXHAUSTED.
- Each row was cross-checked against the recorder for any earlier read of its property code. None of the 31 had one ("never opened").

**Counts:**
- MARRIOTT HELD ROWS BEFORE = 31.
- UNIQUE PREMISES BEFORE = 31: no repeated property code and no repeated house number + ZIP.
- ALIASES / DUPLICATES BEFORE = 0 within the set. dfwts already carried the folded "Tps Fort Worth" permit as a DUPLICATE_AT; that was not reintroduced.

**Order and exclusions:**
- Queue order = derivation order, with dalnb (Beeman / Hotel Mockingbird) moved to row 1 because of its identity question.
- Four Points Arlington (dfwfa) is not in the set; it was not reread.
- No resolved Marriott row was requeued.
- dalsh (SpringHill Suites Addison Quorum) is **not** in the set. It was the page Akamai denied at seq 802 in the previous window, so it was attempted rather than untouched, and this authorization is limited to the 31.

### Starting queue (31 rows, derived from the committed actionability report at 0dca730a)

| # | Census ID (before) | Trade name (census) | Code | Street | City | ZIP | Marriott URL | Prior attempt | Prior blocker |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `beeman hotel` | Beeman Hotel | dalnb | 6070 6070 N US 75 Centrail Expy #1000 | Dallas | 75206 | https://www.marriott.com/en-us/hotels/dalnb-hotel-mockingbird-dallas-a-tribute-portfolio-hotel/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 2 | `springhill suites dallas central expressway` | SpringHill Suites Dallas Central Expressway | dalsx | 10111 N Central Expy | Dallas | 75231 | https://www.marriott.com/en-us/hotels/dalsx-springhill-suites-dallas-central-expressway/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 3 | `springhill suites dallas dfw airport east las colinas` | Springhill Suites Dallas DFW Airport East/Las Colinas | dalir | 5800 High Point Dr | Irving | 75038 | https://www.marriott.com/en-us/hotels/dalir-springhill-suites-dallas-dfw-airport-east-las-colinas-irving/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 4 | `springhill suites dallas lewisville` | SpringHill Suites Dallas Lewisville | dalvl | 720 E Vista Ridge Mall Dr | Lewisville | 75067 | https://www.marriott.com/en-us/hotels/dalvl-springhill-suites-dallas-lewisville/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 5 | `springhill suites dallas mansfield` | SpringHill Suites Dallas Mansfield | dalsf | 3126 E Broad St | Mansfield | 76063 | https://www.marriott.com/en-us/hotels/dalsf-springhill-suites-dallas-mansfield/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 6 | `springhill suites dallas mckinney allen` | SpringHill Suites Dallas McKinney/Allen | dalsk | 2660 S Central Expy | McKinney | 75070 | https://www.marriott.com/en-us/hotels/dalsk-springhill-suites-dallas-mckinney-allen/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 7 | `the ricardo marriott dfw westlake` | The Ricardo Marriott DFW Westlake | dalwl | 1301 Solana Boulevard | Westlake | 76262 | https://www.marriott.com/en-us/hotels/dalwl-the-ricardo-marriott-dfw-westlake/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 8 | `the sinclair autograph collection` | The Sinclair, Autograph Collection | dalsn | 512 Main St | Fort Worth | 76102 | https://www.marriott.com/en-us/hotels/dalsn-the-sinclair-autograph-collection/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 9 | `the stoneleigh autograph collection` | The Stoneleigh, Autograph Collection | dalkl | 2927 Maple Avenue | Dallas | 75201 | https://www.marriott.com/en-us/hotels/dalkl-the-stoneleigh-autograph-collection/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 10 | `the westin dallas park central` | The Westin Dallas Park Central | dalwi | 12720 Merit Dr | Dallas | 75251 | https://www.marriott.com/en-us/hotels/dalwi-the-westin-dallas-park-central/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 11 | `the westin dallas southlake` | The Westin Dallas Southlake | dalws | 1200 E State Highway 114 | Southlake | 76092 | https://www.marriott.com/en-us/hotels/dalws-the-westin-dallas-southlake/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 12 | `the westin dallas stonebriar golf resort and spa` | The Westin Dallas Stonebriar Golf Resort & Spa | dalsb | 1549 Legacy Dr | Frisco | 75034 | https://www.marriott.com/en-us/hotels/dalsb-the-westin-dallas-stonebriar-golf-resort-and-spa/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 13 | `towneplace suites by marriott dallas plano legacy` | TownePlace Suites by Marriott Dallas Plano/Legacy | daltp | 5005 Whitestone Ln | Plano | 75024 | https://www.marriott.com/en-us/hotels/daltp-towneplace-suites-by-marriott-dallas-plano-legacy/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 14 | `towneplace suites by marriott dfw airport north irving` | TownePlace Suites by Marriott DFW Airport North/Irving | dfwti | 4800 Plaza Dr | Irving | 75063 | https://www.marriott.com/en-us/hotels/dfwti-towneplace-suites-dallas-dfw-airport-north-irving/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 15 | `towneplace suites dallas las colinas` | TownePlace Suites Dallas - Las Colinas | dalts | 900 W Walnut Hill Ln | Irving | 75038 | https://www.marriott.com/en-us/hotels/dalts-towneplace-suites-dallas-las-colinas/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 16 | `towneplace suites dallas lewisville` | TownePlace Suites Dallas Lewisville | daltl | 731 E Vista Ridge Mall Dr | Lewisville | 75067 | https://www.marriott.com/en-us/hotels/daltl-towneplace-suites-dallas-lewisville/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 17 | `towneplace suites dallas plano richardson` | TownePlace Suites Dallas Plano/Richardson | dalsp | 545 K Avenue | Plano | 75074 | https://www.marriott.com/en-us/hotels/dalsp-towneplace-suites-dallas-plano-richardson/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 18 | `towneplace suites downtown` | TownePlace Suites - Downtown | dfwtd | 805 E Belknap St | Fort Worth | 76102 | https://www.marriott.com/en-us/hotels/dfwtd-towneplace-suites-fort-worth-downtown/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 19 | `towneplace suites fort worth nw lake worth` | TownePlace Suites Fort Worth NW Lake Worth | dfwtw | 2925 Royalty Ln | Fort Worth | 76135 | https://www.marriott.com/en-us/hotels/dfwtw-towneplace-suites-fort-worth-northwest-lake-worth/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 20 | `towneplace suites fort worth university medical center` | TownePlace Suites - Fort Worth University Medical Center | dfwtu | 3450 W Vickery Blvd | Fort Worth | 76107 | https://www.marriott.com/en-us/hotels/dfwtu-towneplace-suites-fort-worth-university-medical-center/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 21 | `towneplace suites marriott hotel` | TownePlace Suites Marriott Hotel | dfwta | 1709 E Lamar Blvd | Arlington | 76006 | https://www.marriott.com/en-us/hotels/dfwta-towneplace-suites-marriott-hotel/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 22 | `towneplace suites southwest` | TownePlace Suites - Southwest | dfwts | 4200 International Plaza | Fort Worth | 76109 | https://www.marriott.com/en-us/hotels/dfwts-towneplace-suites-fort-worth-southwest/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 23 | `westin dallas fort worth airport` | Westin Dallas Fort Worth Airport | dfwwa | 4545 W John Carpenter Fwy | Irving | 75063 | https://www.marriott.com/en-us/hotels/dfwwa-the-westin-dallas-fort-worth-airport/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 24 | `westin irving convention center las colinas` | Westin Irving Convention Center Las Colinas | daliw | 400 Las Colinas Blvd W | Irving | 75039 | https://www.marriott.com/en-us/hotels/daliw-the-westin-irving-convention-center-at-las-colinas/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 25 | `worthington renaissance hotel` | Worthington Renaissance Hotel | dfwdt | 200 Main St | Fort Worth | 76102 | https://www.marriott.com/en-us/hotels/dfwdt-the-worthington-renaissance-fort-worth-hotel/overview/ | never opened | ACCESS_BLOCKED / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 26 | `courtyard by marriott dallas northwest` | Courtyard by Marriott Dallas Northwest | dalnw | 2930 Forest Ln | Dallas | 75234 | https://www.marriott.com/dalnw | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 27 | `four points sheraton plano by marriott` | Four Points Sheraton Plano by Marriott | dalpu | 6624 Communications Pkwy | Plano | 75024 | https://www.marriott.com/en-us/hotels/dalpu-four-points-plano/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 28 | `hall park hotel` | HALL Park Hotel | dalok | 3220 Internet Blvd | Frisco | 75034 | https://www.marriott.com/en-us/hotels/dalok-hall-park-hotel-autograph-collection/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 29 | `le meridien dallas by the galleria` | Le Meridien Dallas by the Galleria | dalmd | 13402 Noel Rd | Dallas | 75240 | https://www.marriott.com/en-us/hotels/dalmd-le-meridien-dallas-by-the-galleria/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 30 | `le meridien hotel fort worth downtown` | Le Meridien Hotel Fort Worth Downtown | dalwm | 811 Commerce St | Fort Worth | 76102 | https://www.marriott.com/en-us/hotels/dalwm-le-meridien-fort-worth-downtown/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |
| 31 | `w dallas victory` | W Dallas - Victory | dalwh | 2430 Victory Park Ln | Dallas | 75219 | https://www.marriott.com/en-us/hotels/dalwh-w-dallas/overview/ | never opened | ROUTING_HOLD / MARRIOTT_AUTHORIZED_WINDOW_CLOSED (seq 802) |

### Reads (attempt order = queue order)

| # | Seq | Captured (UTC) | Code | Page trade name | Page address | Result | Operative pet quote (verbatim) | Published fee | New census ID |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 803 | 2026-10-10T16:47:02Z | dalnb | Hotel Mockingbird, Dallas, a Tribute Portfolio Hotel | 6070 North Central Expressway, Dallas, Texas, USA, 75206 | PET-FRIENDLY | Pet Policy / Pets Welcome / 2 pet max per room with 100 USD non-refundable fee per room per stay / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2 | none published | `hotel mockingbird dallas a tribute portfolio hotel` |
| 2 | 804 | 2026-10-10T16:47:02Z | dalsx | SpringHill Suites by Marriott Dallas Central Expressway | 10111 North Central Expressway, Dallas, Texas, USA, 75231 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `springhill suites by marriott dallas central expressway` |
| 3 | 805 | 2026-10-10T16:51:42Z | dalir | SpringHill Suites by Marriott Dallas DFW Airport East/Las Colinas Irving | 5800 High Point Drive, Irving, Texas, USA, 75038 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `springhill suites by marriott dallas dfw airport east las colinas irving` |
| 4 | 806 | 2026-10-10T16:51:42Z | dalvl | SpringHill Suites by Marriott Dallas Lewisville | 720 East Vista Ridge Mall Drive, Lewisville, Texas, USA, 75067 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `springhill suites by marriott dallas lewisville` |
| 5 | 807 | 2026-10-10T16:51:42Z | dalsf | SpringHill Suites by Marriott Dallas Mansfield | 3126 East Broad Street, Mansfield, Texas, USA, 76063 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `springhill suites by marriott dallas mansfield` |
| 6 | 808 | 2026-10-10T16:55:10Z | dalsk | SpringHill Suites by Marriott Dallas McKinney/Allen | 2660 South Central Expressway, McKinney, Texas, USA, 75070 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed / Pets not allowed-Service animals only | n/a (no pets) | `springhill suites by marriott dallas mckinney allen` |
| 7 | 809 | 2026-10-10T16:55:10Z | dalwl | The Ricardo Marriott DFW Westlake | 1301 Solana Boulevard, Building 3, Westlake, Texas, USA, 76262 | PET-FRIENDLY | Pet Policy / Pets Welcome. / Up to 70 lbs, 2 pets max, non-refundable deposit of 150 USD. / Non-Refundable Pet Fee Per Stay: $150.00 / Maximum Pet Weight: 70.0lbs / Maximum Number of Pets in Room: 2 | $150 per stay | `the ricardo marriott dfw westlake` |
| 8 | 810 | 2026-10-10T16:58:21Z | dalsn | The Sinclair, Autograph Collection | 512 Main Street, Fort Worth, Texas, USA, 76102 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `the sinclair autograph collection` |
| 9 | 811 | 2026-10-10T16:58:21Z | dalkl | The Stoneleigh, Autograph Collection | 2927 Maple Avenue, Dallas, Texas, USA, 75201 | PET-FRIENDLY | Pet Policy / Pets Welcome. / 2 pets per room / Non-Refundable Pet Fee Per Night: $50.00 / Maximum Pet Weight: 80.0lbs / Maximum Number of Pets in Room: 2 | $50 per night | `the stoneleigh autograph collection` |
| 10 | 812 | 2026-10-10T17:02:26Z | dalwi | The Westin Dallas Park Central | 12720 Merit Drive, Dallas, Texas, USA, 75251 | PET-FRIENDLY | Pet Policy / Pets Welcome / Per room/2 dogs 40 pounds max with USD 50 per night fee and signed waiver / Non-Refundable Pet Fee Per Night: $50.00 / Maximum Pet Weight: 40.0lbs / Maximum Number of Pets in Room: 2 | $50 per night | `the westin dallas park central` |
| 11 | 813 | 2026-10-10T17:02:26Z | dalws | The Westin Dallas Southlake | 1200 East State Highway 114, Southlake, Texas, USA, 76092 | PET-FRIENDLY | Pet Policy / Pets Welcome / $25 per day / Non-Refundable Pet Fee Per Night: $25.00 / Maximum Pet Weight: 25.0lbs / Maximum Number of Pets in Room: 2 | $25 per day | `the westin dallas southlake` |
| 12 | 814 | 2026-10-10T17:05:09Z | dalsb | The Westin Dallas Stonebriar Golf Resort & Spa | 1549 Legacy Drive, Frisco, Texas, USA, 75034 | PET-FRIENDLY | Pet Policy / Pets Welcome. / Guests are required to sign a pet policy waiver at check-in / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 40.0lbs / Maximum Number of Pets in Room: 1 | $100 per stay | `the westin dallas stonebriar golf resort and spa` |
| 13 | 815 | 2026-10-10T17:05:09Z | daltp | TownePlace Suites by Marriott Dallas Plano/Legacy | 5005 Whitestone Lane, Plano, Texas, USA, 75024 | PET-FRIENDLY | Pet Policy / Pets Welcome / 2 pets 150 pounds max per room with USD 150 non-refundable fee per room per stay / Non-Refundable Pet Fee Per Stay: $150.00 / Maximum Pet Weight: 150.0lbs / Maximum Number of Pets in Room: 2 | $150 per stay per room | `towneplace suites by marriott dallas plano legacy` |
| 14 | 816 | 2026-10-10T17:08:25Z | dfwti | TownePlace Suites by Marriott Dallas DFW Airport North/Irving | 4800 Plaza Drive, Irving, Texas, USA, 75063 | PET-FRIENDLY | Pet Policy / Pets Welcome / USD $100 per stay. Maximum 2 pets per room. / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 30.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott dallas dfw airport north irving` |
| 15 | 817 | 2026-10-10T17:08:25Z | dalts | TownePlace Suites by Marriott Dallas Las Colinas | 900 West Walnut Hill Lane, Irving, Texas, USA, 75038 | PET-FRIENDLY | Pet Policy / Pets Welcome / $100 non refundable pet cleaning fee / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 100.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott dallas las colinas` |
| 16 | 818 | 2026-10-10T17:11:41Z | daltl | TownePlace Suites by Marriott Dallas Lewisville | 731 East Vista Ridge Mall Drive, Lewisville, Texas, USA, 75067 | PET-FRIENDLY | Pet Policy / Pets Welcome / $100 Pet Fee required (non-refunable) / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 40.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott dallas lewisville` |
| 17 | 819 | 2026-10-10T17:11:41Z | dalsp | TownePlace Suites by Marriott Dallas Plano/Richardson | 545 K Avenue, Plano, Texas, USA, 75074 | PET-FRIENDLY | Pet Policy / Pets Welcome / 2 small pets per room allowed with nonrefundable fee of USD 100.00 per stay / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott dallas plano richardson` |
| 18 | 820 | 2026-10-10T17:15:00Z | dfwtd | TownePlace Suites by Marriott Fort Worth Downtown | 805 East Belknap Street, Fort Worth, Texas, USA, 76102 | PET-FRIENDLY | Pet Policy / Pets Welcome / We are pleased to welcome guests traveling with their pets. / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 80.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott fort worth downtown` |
| 19 | 821 | 2026-10-10T17:15:00Z | dfwtw | TownePlace Suites by Marriott Fort Worth Northwest/Lake Worth | 2925 Royalty Lane, Lake Worth, Texas, USA, 76135 | PET-FRIENDLY | Pet Policy / Pets Welcome / 1 pet 50 pounds max per room with 75USD non-refundable fee per room per stay / Non-Refundable Pet Fee Per Stay: $75.00 / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2 | $75 per stay per room | `towneplace suites by marriott fort worth northwest lake worth` |
| 20 | 822 | 2026-10-10T17:18:19Z | dfwtu | TownePlace Suites by Marriott Fort Worth University Area/Medical Center | 3450 West Vickery Boulevard, Fort Worth, Texas, USA, 76107 | PET-FRIENDLY | Pet Policy / Pets Welcome / $100.00 fee per stay. Property charges a $5 daily cleaning fee. / Non-Refundable Pet Fee Per Stay: $100.00 / Non-Refundable Pet Fee Per Night: $5.00 / Maximum Number of Pets in Room: 2 | WITHHELD (multi-amount / tiered) | `towneplace suites by marriott fort worth university area medical center` |
| 21 | 823 | 2026-10-10T17:18:19Z | dfwta | TownePlace Suites by Marriott Dallas Arlington North | 1709 East Lamar Boulevard, Arlington, Texas, USA, 76006 | PET-FRIENDLY | Pet Policy / Pets Welcome / Pets 30 pounds or less allowed with USD 50 non-refundable fee per stay / Non-Refundable Pet Fee Per Stay: $50.00 / Maximum Pet Weight: 60.0lbs / Maximum Number of Pets in Room: 2 | WITHHELD (STAY_LENGTH_CONDITION) | `towneplace suites by marriott dallas arlington north` |
| 22 | 824 | 2026-10-10T17:21:36Z | dfwts | TownePlace Suites by Marriott Fort Worth Southwest/TCU Area | 4200 International Plaza, Fort Worth, Texas, USA, 76109 | PET-FRIENDLY | Pet Policy / Pets Welcome / USD $100 non-refundable fee per stay / Non-Refundable Pet Fee Per Stay: $100.00 / Maximum Pet Weight: 35.0lbs / Maximum Number of Pets in Room: 2 | $100 per stay | `towneplace suites by marriott fort worth southwest tcu area` |
| 23 | 825 | 2026-10-10T17:21:36Z | dfwwa | The Westin Dallas Fort Worth Airport | 4545 W. John Carpenter Freeway, Irving, Texas, USA, 75063 | PET-FRIENDLY | Pet Policy / Pets Welcome / Pets accepted up to 50 pounds and $50 Non-Refundable Pet fee per night / Non-Refundable Pet Fee Per Night: $50.00 / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2 | $50 per night | `the westin dallas fort worth airport` |
| 24 | 826 | 2026-10-10T17:24:44Z | daliw | The Westin Irving Convention Center at Las Colinas | 400 West Las Colinas Boulevard, Irving, Texas, USA, 75039 | PET-FRIENDLY | Pet Policy / Pets Welcome / 2 dogs at 50 pounds max per room. $50 fee per day up to $150 / Non-Refundable Pet Fee Per Night: $50.00 / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2 | WITHHELD (multi-amount / tiered) | `the westin irving convention center at las colinas` |
| 25 | 827 | 2026-10-10T17:24:44Z | dfwdt | The Worthington Renaissance Fort Worth Hotel | 200 Main Street, Fort Worth, Texas, USA, 76102 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `the worthington renaissance fort worth hotel` |
| 26 | 828 | 2026-10-10T17:28:03Z | dalnw | Courtyard by Marriott Dallas Northwest | 2930 Forest Lane, Dallas, Texas, USA, 75234 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `courtyard by marriott dallas northwest` |
| 27 | 829 | 2026-10-10T17:28:03Z | dalpu | Four Points by Sheraton Plano | 6624 Communications Parkway, Plano, Texas, USA, 75024 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `four points by sheraton plano` |
| 28 | 830 | 2026-10-10T17:31:57Z | dalok | HALL Park Hotel, Autograph Collection | 3220 Internet Boulevard, Frisco, Texas, USA, 75034 | PET-FRIENDLY | Pet Policy / Pets Welcome / 1 pet 60lbs max per pet per room with 150USD nonrefundable fee per room per stay / Maximum Pet Weight: 60.0lbs / Maximum Number of Pets in Room: 1 | none published | `hall park hotel autograph collection` |
| 29 | 831 | 2026-10-10T17:31:57Z | dalmd | Le Méridien Dallas by the Galleria | 13402 Noel Road, Dallas, Texas, USA, 75240 | PET-FRIENDLY | Pet Policy / Pets Welcome / Pets under 50 pounds permitted. Non refundable cleaning fee of $75 per room. / Non-Refundable Pet Fee Per Night: $50.00 / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 1 | WITHHELD (multi-amount / tiered) | `le meridien dallas by the galleria` |
| 30 | 832 | 2026-10-10T17:34:33Z | dalwm | Le Méridien Fort Worth Downtown | 811 Commerce Street, Fort Worth, Texas, USA, 76102 | VERIFIED NO-PETS | Pet Policy / Pets Not Allowed | n/a (no pets) | `le meridien fort worth downtown` |
| 31 | 833 | 2026-10-10T17:34:33Z | dalwh | W Dallas | 2440 Victory Park Lane, Dallas, Texas, USA, 75219 | PET-FRIENDLY | Pet Policy / Pets Welcome. / Guests must sign an authorization form and pay a nonrefundable fee at check-in. / Non-Refundable Pet Fee Per Stay: $175.00 / Maximum Pet Weight: 75.0lbs / Maximum Number of Pets in Room: 2 | $175 per stay | `w dallas` |

Timestamps are the recorder's real-clock stamps. The recorder stamps each recorded batch (3–5 reads), so neighbouring rows share a stamp.
- The browser agent's own navigations ran from about 16:44:31Z to 17:34:02Z.
- Navigations were at least 90 s apart, one tab, one navigation per hotel.

Each record's `note` carries the page phone and the content reference: usually HOTEL INFORMATION > Pet Policy rows, node text by `read_page` ref. Fee amounts that the accessibility tree cut to "…" were read from a full-resolution screenshot of the rendered page, and the note says so.

## Phase 3 — special identity notes
**BEEMAN HOTEL / HOTEL MOCKINGBIRD (dalnb), recorder seq 803.**

| Field | Value |
|---|---|
| CURRENT TRADE NAME | Hotel Mockingbird, Dallas, a Tribute Portfolio Hotel |
| CURRENT ADDRESS | 6070 North Central Expressway, Dallas, Texas, USA, 75206 (page), phone +1 214-750-6060 |
| CURRENT PROPERTY CODE | dalnb (final URL unchanged) |
| CURRENT MARRIOTT PAGE | https://www.marriott.com/en-us/hotels/dalnb-hotel-mockingbird-dallas-a-tribute-portfolio-hotel/overview/ |
| SAME PREMISES AS BEEMAN | **YES** (see the evidence below) |
| CURRENT POLICY BINDS | **YES**, to the Hotel Mockingbird identity: "Pet Policy / Pets Welcome / 2 pet max per room with 100 USD non-refundable fee per room per stay / Maximum Pet Weight: 50.0lbs / Maximum Number of Pets in Room: 2" |

The same-premises finding rests on more than the address:
- **The permit:** "Beeman Hotel" is a Texas Comptroller permit at "6070 6070 N US 75 Centrail Expy #1000" 75206, with responsibility from 2024-10-03. It has the same house number and ZIP; US 75 is Central Expressway.
- **Google Places:** Places names the dalnb Hotel Mockingbird page as the website for that permit row's own premises pin (the row's prior ROUTING_HOLD reason quoted that link).
- **Marriott's own page:** the dalnb page files its own reviews under "The Beeman Hotel": "Read reviews for The Beeman Hotel", and every review card is labelled that way.
- **No rename statement:** the page prints no "formerly" or "previously the Beeman" wording. The browser agent checked the whole tree and the expanded description.

What happened in the census:
- The read first minted a separate Hotel Mockingbird row beside the Beeman permit row, making the census 966. That is two identities for one premises.
- The permit row is now a market-owned `DUPLICATE_AT[("beeman hotel", "6070 6070")]` → DUPLICATE_OF_SAME_PREMISES, and the census is back to 965.

**No Beeman-era evidence was migrated.** The Beeman row carried no policy. The published policy is the dalnb page's own, read in this window. The profile publishes under the current trade name, Hotel Mockingbird. No fee is published: the fee appears only in prose, and the reader extracted no structured fee from it.

**FOUR POINTS ARLINGTON (dfwfa):** not in the queue and not reread. It stays CLEAN_VERIFIED_NO_PETS from the earlier redirect to Marriott's own page.

**DFWTS:**
- Read once, at seq 824: TownePlace Suites by Marriott Fort Worth Southwest/TCU Area, 4200 International Plaza 76109.
- It is now one PF identity under its page title.
- The "Tps Fort Worth" permit remains a DUPLICATE_AT of it. No duplicate was reintroduced.

**Other page-vs-queue differences, all within the same property code:**
- **dfwta:** the queue name "TownePlace Suites Marriott Hotel" is "TownePlace Suites by Marriott Dallas Arlington North" at the same address.
- **dalwh:**
  - The page prints **2440** Victory Park Lane; the census row had the permit's 2430.
  - The published identity is "W Dallas" at 2440, whose coordinates fall inside the City of Dallas boundary.
  - The 2430 permit row split off as an unpublished IDENTITY_REVIEW node with a 75219 municipality hold. It is not admitted and not counted.
- **dfwtw:**
  - The page's mailing city is "Lake Worth, Texas" 76135.
  - The market places municipality by the premises' Census TIGER boundary (32.8025, -97.43339 → Fort Worth), and the Texas permit also says Fort Worth.
  - The row publishes as Fort Worth. SUBURBAN HOTELS MISLABELED FORT WORTH stays 0.
- **dalwl:** the browser tab title is "Marriott Dallas/Fort Worth Westlake", but the page heading is "The Ricardo Marriott DFW Westlake", which is what publishes. The address adds "Building 3".

## Phases 4–5 — window execution and the Akamai stop rule
- Attempted 31 / 31 sequentially, recorder seq 803–833.
- The last attempted row was row 31, dalwh (W Dallas).
- Outcomes: READ 31; no denial, error, retired route, out-of-market, timeshare, pre-opening or closure page.
- **Akamai: none.** Row 1 showed a blank "Powered and protected by" loader for about 8 s, then loaded without a reload. It was not a denial, so no recheck was used.
- No bypass of any kind:
  - no JS extraction, relay, proxy, IP or fingerprint change, or hidden API;
  - no cookie tricks or retries;
  - no find-tool summaries quoted.
- Untouched after a block: 0. No denial means no stop point.

## Phase 6 — policy safety
- **The 10 refusals:** each quote is "Pet Policy / Pets Not Allowed". dalsk adds "Pets not allowed-Service animals only".
  - Each is VERIFIED NO-PETS.
  - The page's separate accessibility line "Service Animals are welcome without a fee or documentation" was never read as acceptance.
- **The 21 acceptances:** each comes from the page's own Pet Policy rows ("Pets Welcome"). None rests on a fee, chip, FAQ question, service-animal sentence or brand text.
- After adjudication, PET-FRIENDLY WITH EXPLICIT REFUSAL = 0, QUESTION-ONLY PET-FRIENDLY = 0 and SERVICE-ANIMAL-ONLY ACCEPTANCE = 0. Source: the publication safety audit, `all_zero = True`.

## Phase 7 — fee safety
**Published fees:**
- **Per night:**
  - dalkl $50; dalwi $50 ("USD 50 per night fee"); dfwwa $50 ("$50 Non-Refundable Pet fee per night").
  - These have a single amount and a stated nightly basis.
- **Per day:** dalws $25 ("$25 per day"; the structured row says the same $25 per night). It renders "per day".
- **Per stay:**
  - daltp $150 (per room), dfwtw $75 (per room), dalwl $150, dalwh $175, dalsb $100, dalts $100, daltl $100, dalsp $100, dfwtd $100, dfwti $100, dfwts $100.

**Withheld:**
- **daliw:** "$50 fee per day up to $150", a nightly amount plus a cap. Not flattened.
- **dalmd:** the prose says "$75 per room"; the structured row says "Per Night: $50.00". Two different amounts.
- **dfwtu:** "$100.00 fee per stay" plus a "$5 daily cleaning fee", a multi-amount structure.
- **dfwta:** STAY_LENGTH_CONDITION by the reader.
- **No fee published:** dalnb and dalok state the amount only in prose; nothing was extracted.

**Self-contradicting pages (the conflicting field is not published):**
- **dfwtw:** "1 pet" vs "Maximum Number of Pets in Room: 2". No pet count is published.
- **dfwta:** "30 pounds or less" vs "60.0lbs". No weight is published.

MISLEADING SINGLE FEES = 0 (fee withholding report and publication safety audit).

## Phase 8 — Marriott accounting after the window
| Field | Value |
|---|---|
| MARRIOTT HELD ROWS BEFORE | 31 |
| MARRIOTT ATTEMPTED THIS WINDOW | 31 |
| MARRIOTT SUCCESSFUL READS | 31 |
| MARRIOTT PET-FRIENDLY ADDED | 21 |
| MARRIOTT VERIFIED NO-PETS ADDED | 10 |
| MARRIOTT IDENTITY HOLDS | 0 (among the 31) |
| MARRIOTT POLICY HOLDS | 0 (among the 31) |
| MARRIOTT ACCESS-BLOCKED REMAINING | 0 (among the 31) |
| MARRIOTT UNTOUCHED AFTER BLOCK | 0 |
| MARRIOTT ACTIONABLE REMAINING | **0** |

The market-wide Marriott accounting changed as follows:
- **Census:** 166 → 167. The Mockingbird identity carries brand MARRIOTT; the folded Beeman permit row had no brand.
- **Browser:** attempted 179 (170 distinct routes), read 168, challenge-denied 11 (all from earlier windows).
- **Resolved:** 159 (98 PF / 61 NP).
- **Terminal holds:** 38 → **8**:
  - **6 founder rulings:**
    - 4 dual-brand holds: AC Hotel Dallas Downtown, Residence Inn Dallas Downtown, Courtyard Irving Las Colinas, Residence Inn Irving Las Colinas;
    - the 2 Fairfield DFW Airport North title-collision rows.
  - **dalsh**, the denied page itself in the previous window, outside this authorization.
  - **SpringHill Suites Fort Worth Vickery**, opening 10/1/2027, with no first-party route.

## Phase 9 — re-adjudication (fixed point)
- The market-owned pipeline (`scratchpad/pipeline.ps1`) was run twice, detached.
- The second pass changed **0** files. This held both before and after the Beeman fold; each two-pass run ended `CHANGED_BETWEEN_PASSES 0`.
- Only rows the new evidence touched moved: the 31, the Beeman permit fold, the 2430 W Dallas permit split, and 16 brand-name-only review nodes absorbed into the read rows.
- No resolved row was reopened.

| | Before (e8a84139) | After (b6dc9511) |
|---|---|---|
| QUALIFYING CENSUS | 965 | **965** |
| PET-FRIENDLY | 440 | **461** |
| VERIFIED NO-PETS | 200 | **210** |
| RESOLVED | 640 | **671** |
| UNRESOLVED | 325 | **294** |
| RESOLUTION RATE | 66.32% | **69.53%** |
| ACTIONABLE UNRESOLVED | 0 | **0** |
| holds | ACCESS_BLOCKED 39, ROUTING_HOLD 146, EVIDENCE 50, IDENTITY_MISMATCH 41, SOURCE_SILENT 49 | ACCESS_BLOCKED 15, ROUTING_HOLD 139, EVIDENCE 50, IDENTITY_MISMATCH 41, SOURCE_SILENT 49 |
| actionability | EXHAUSTED 275, NEW_SPEND 25, FOUNDER 21, PREOPENING 4 | EXHAUSTED 244, NEW_SPEND 25, FOUNDER 21, PREOPENING 4 |

## Phase 10 — other coverage blockers (unchanged; verified identical key sets vs `0dca730a`)
**A. PAID-PLACES-ONLY ROWS = 25.** These have no authorized free route, and Places' free Enterprise allowance is spent (215 / 215). They are held; this order authorizes no paid spend.
- 183 Motel; Americas Best Value Inn and Suites - Fort Worth South; Benbrook Inn & Suites; Best Budget Suites; Bingham 1883, Lp; Comfort Suites - Lake Worth.
- Dude Inn Motel; Gold Inn; Golden Inn; Golden Inn Dallas; Intown Suites Rufe Snow Llc; La Mirage Inn; Linfield Inn.
- Mesquite Inn; Mm Inn and Suites; Motel 6 Bedford, TX - Fort Worth; Plaza Motel; Romantic Inn & Suites; Royal Inn & Suites.
- Scottis Inn & Suites; Shamrock Motel; Shangrila Courts; Studio 6 Burleson; West Worth Inn & Suites; Western Skies Motel.

**B. FOUNDER-RULING ROWS = 4:**
- Executive Inn and Sonesta Select Fort Worth Fossil Creek: ROUTE_DOMAIN_CONFLICT, two first-party sites each.
- The two Fairfield by Marriott Inn & Suites Dallas DFW Airport North rows (Irving; Coppell Grapevine): they share their first 60 characters.

**Fairfield duplicate-title result: NOT AFFECTED.**
- Window 002 read no Fairfield page. dfwti, which matches a Fairfield row by house number and ZIP, is the TownePlace Suites DFW Airport North/Irving.
- No new Marriott evidence settles either Fairfield identity. The naming decision remains the founder's.

The other 17 REQUIRES_FOUNDER rows (13 dual-brand rows and 3 shared-reader refusals among them) remain safely held, as before. No ruling was invented.

## Phase 11 — coverage decision
- TECHNICAL SOURCE READY = **YES**.
- COVERAGE READY = **FOUNDER DECISION**. All 8 coverage conditions hold: actionable 0, no material identity gap, no material unexplained policy gap, lanes exhausted, Marriott terminally resolved or exhausted, browser-required brands bounded, publication set safe, package deterministic and FAST-clean.
- The 29 gated rows still need what this order cannot give:
  - 25 rows need new Places spend.
  - 4 need a founder routing or naming ruling.
- Marriott being exhausted does not change that, so COVERAGE READY was not forced to YES.

## Phase 12 — successor package
| | |
|---|---|
| SUPERSEDED PACKAGE | `pkg-dallas-fort-worth-tx-e8a841396faeffec` (sha256:e8a841396faeffecd1e4b15d94fdde0949ac75e2729a80f0322be8c1bd768f9d, from `df4da832`, sealed 2026-10-10T03:31:52Z, receipt `821f46f2…`, bundle `8dd45272…`, 440 PF / 200 NP / 325 unresolved) |
| NEW PACKAGE | `pkg-dallas-fort-worth-tx-b6dc951150886520` |
| DIGEST | `sha256:b6dc9511508865208f13c6be21b3a752f14461c1c7f9a11386f58c2cc6390241` |
| created_from_source_sha | `c0fc019473a751ed40cf3f5dfee805db2eecc85e` |
| sealed_at | 2026-10-10T17:55:40Z (after the window's last capture 17:34:33Z, set from the real clock) |
| execution_zone | SHADOW_UNTIL_REGISTERED |
| counts | census 965, PF 461, NP 210, unresolved 294, declared routes 488 |
| partition | PUBLISHED_PET_FRIENDLY 461, VERIFIED_NO_PETS 210, ACCESS_BLOCKED 15, AWAITING_OFFICIAL_URL 139, AWAITING_POLICY_OBSERVATION 99, AWAITING_ROUTING_REPLACEMENT 41 |
| first-party gate | 671 evaluated / 671 eligible / 0 ineligible |
| package file SHA-256 | `95121C18…FEDD752` |

**Lineage:**
- The shadow helper's report carries a `supersedes` block with the predecessor's id, digest, source sha, sealed_at, receipt digest, bundle hash and counts.
- Its `work_order` is this order.
- The predecessor's package and receipt files stay in `shadow_packages/` and `shadow_receipts/` untouched.
- Parent live state is unchanged: the FORT MYERS live release.

## Phase 13 — FAST
- 15/15 PASS (A–O). FAILED 0, UNKNOWN 0. FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES.
- Receipt `pkg-dallas-fort-worth-tx-b6dc951150886520-4fc4b73cc72c7212.json`, RECEIPT_DIGEST `sha256:4fc4b73c…`. It is currently eligible: `eligible_receipts` returns 1.
- **Rule J:** file_count 2,735, html_count 2,719, output_present True, bundle `34b61319c3a88897…`.
- **Rule K:** BYTE_IDENTICAL, 4 cold builds, 0 reuse hits.
- Work dir: the short absolute forward-slash path `C:/t/dfw1`.

## Phase 14 — memory safety
- Seal + FAST ran detached and alone, from 17:57:45Z to 18:09:36Z.
- It exited before the reproduction started. Free memory afterwards was 3.8 GB of 16.3 GB, with no python left but the pre-existing 14180.
- The reproduction ran alone afterwards, from 18:10:23Z to 18:26:09Z. No whole-site build ran beside accounting.

## Phase 15 — independent reproduction
- **Setup:**
  - Separate process.
  - Separate detached worktree `C:/t/dfwr` at `c0fc0194`.
  - Separate work dir `C:/t/dfw2`.
  - The full 40-character source sha.
- **Results:**
  - PACKAGE DIGEST MATCH = YES.
  - Package file bytes are identical (`95121c18…` both).
  - DATA DIFFERENCES = 0 (pet-friendly, no-pets, census, partition, unresolved, delta).
  - SITE DIFFERENCES = 0 (bundle `34b61319…` both; 2,735 / 2,719 both).
  - BYTE IDENTICAL = YES.
  - The two receipts differ only in TIMESTAMPS, ENVIRONMENT and PERFORMANCE, plus `seconds` / `build_seconds` / `compare_seconds` inside RESULTS. Every rule status is identical.
- The worktree was removed afterwards (`git worktree remove`, `prune`).

## Phase 17 — commit / push
Only DFW-owned files changed. Every changed path matches `dallas[-_]fort[-_]worth`:
- `dallas_fort_worth_tx_*` scripts;
- the DFW census, reports and staging;
- this report and the source-ready report's banner.

**Code changes:**
- Market-owned only: a `DUPLICATE_AT` entry in `dallas_fort_worth_tx_census_reconciliation_001.py`, and `SEALED_AT` + `SUPERSEDES` in `dallas_fort_worth_tx_shadow_package_001.py`.
- Shared factory code changed: NO. Shared reader changed: NO. Broad regression runs: 0.

**Spend and processes:**
- No paid spend: no Places, no Firecrawl; the protected reserve was not touched.
- The only processes created were the browser agent, the two-pass pipelines, the seal and the reproduction. All have exited. The pre-existing python 14180 was left alone.

---

## FINAL ANSWERS

1. STARTING MARRIOTT HELD ROWS = 31
2. UNIQUE MARRIOTT PREMISES = 31 (0 aliases / duplicates in the set)
3. ATTEMPTED THIS WINDOW = 31
4. SUCCESSFUL READS = 31
5. PET-FRIENDLY ADDED = 21
6. VERIFIED NO-PETS ADDED = 10
7. ACCESS DENIAL OCCURRED = NO
8. ACCESS DENIAL REFERENCE = none in this window (the prior window's 18.8a89cc17.1791602447.af47e47 at dalsh, seq 802, is unchanged)
9. UNTOUCHED AFTER DENIAL = 0
10. MARRIOTT TERMINAL HOLDS = 8:
    - 6 founder rulings (4 dual-brand, 2 Fairfield title);
    - dalsh, denied in the previous window and outside this authorization;
    - SpringHill Vickery, pre-opening 2027 with no route.
    - The 31-row set has 0 terminal holds.
11. MARRIOTT ACTIONABLE REMAINING = 0
12. BEEMAN / HOTEL MOCKINGBIRD RESULT = SAME PREMISES. The current trade name is Hotel Mockingbird, Dallas, a Tribute Portfolio Hotel (dalnb, 6070 North Central Expressway 75206).
    - The binding rests on the permit's house number + ZIP, Places naming the dalnb page as the permit pin's website, and the dalnb page filing its reviews under "The Beeman Hotel".
    - The page prints no "formerly" wording.
    - The current policy binds: PET-FRIENDLY, no fee published.
    - The Beeman permit row is a same-premises duplicate. No Beeman-era evidence was migrated.
13. FAIRFIELD DUPLICATE-TITLE RESULT = NOT AFFECTED. No Fairfield page was read; both rows remain a founder naming decision.
14. TOTAL QUALIFYING CENSUS = 965
15. PET-FRIENDLY = 461
16. VERIFIED NO-PETS = 210
17. RESOLVED = 671
18. UNRESOLVED = 294
19. RESOLUTION RATE = 69.53%
20. ACTIONABLE UNRESOLVED = 0
21. PAID-PLACES-ONLY ROWS = 25
22. FOUNDER-RULING ROWS = 4
23. MATERIAL IDENTITY GAP = NO
24. MATERIAL POLICY GAP = NO
25. MISLEADING SINGLE FEES = 0
26. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
27. QUESTION-ONLY PET-FRIENDLY = 0
28. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
29. SUPERSEDED PACKAGE = pkg-dallas-fort-worth-tx-e8a841396faeffec
30. SUCCESSOR PACKAGE = pkg-dallas-fort-worth-tx-b6dc951150886520
31. SUCCESSOR PACKAGE DIGEST = sha256:b6dc9511508865208f13c6be21b3a752f14461c1c7f9a11386f58c2cc6390241
32. RULE J = PASS (2,735 files / 2,719 html, output present)
33. RULE K = PASS (BYTE_IDENTICAL, 4 cold builds)
34. FAST = 15/15 PASS (0 failed, 0 unknown, ELIGIBLE)
35. PACKAGE REPRODUCIBLE = YES (independent worktree, byte identical)
36. TECHNICAL SOURCE READY = YES
37. COVERAGE READY = FOUNDER DECISION (25 paid-Places-only rows + 4 founder rulings)
38. NEW PAID SPEND = $0
39. FACTORY CODE CHANGED = NO
40. SHARED READER CHANGED = NO
41. BROAD REGRESSION RUNS = 0
42. DFW REGISTERED = NO
43. DFW AUTHORIZED = NO
44. DFW DEPLOYED = NO
45. origin == HEAD = YES
46. tree clean = YES

DFW MARRIOTT WINDOW = PASS
MARRIOTT ACTIONABLE REMAINING = 0
ACTIONABLE UNRESOLVED = 0
PAID-PLACES-ONLY ROWS = 25
FOUNDER-RULING ROWS = 4
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
MISLEADING SINGLE FEES = 0
TECHNICAL SOURCE READY = YES
DALLAS-FORT WORTH COVERAGE READY = FOUNDER DECISION
FACTORY CODE CHANGED = NO
SHARED READER CHANGED = NO
NEW PAID SPEND = $0
BROAD REGRESSION RUNS = 0
DALLAS-FORT WORTH REGISTERED = NO
DALLAS-FORT WORTH DEPLOYED = NO

STOP.
