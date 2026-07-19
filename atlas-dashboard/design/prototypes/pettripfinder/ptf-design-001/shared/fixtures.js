/*
 * PTF-DESIGN-001 -- canonical fixture data record.
 *
 * These are the EXACT, repository-authorized facts the prototype pages render.
 * They are transcribed from real verified importer candidates + the promoted
 * production seed CSV (AES-DATA-004G / 004I). No fact here is invented,
 * enriched, or sourced from outside the repository. The three main concept
 * pages hardcode the `rich` fixture (Drury) as static HTML for robustness;
 * this file is the single source of truth the operator can diff those pages
 * against, and it documents every field's support state.
 *
 * Provenance for each fixture is noted inline. "supported: false" means the
 * official reviewed source did not state that field -- it is shown to users
 * as "Not stated by the reviewed source", NEVER guessed or defaulted to "no".
 */

const PTF_FIXTURES = {
  // -------------------------------------------------------------------- //
  // 1. RICH VERIFIED -- the most complete supported policy in the corpus.
  //    Source: druryhotels.com official property page, verified 2026-07-18,
  //    11 evidence entries, EXACT_ENTITY_DOMAIN. Promoted to production.
  // -------------------------------------------------------------------- //
  rich: {
    state: "VERIFIED_PET_FRIENDLY",
    name: "Drury Inn & Suites Columbus Grove City",
    area: "Grove City corridor",
    address: "4109 Parkway Centre Drive",
    city: "Grove City", region: "OH", postal: "43123",
    phone: "614-875-7000",
    official_url: "https://www.druryhotels.com/locations/columbus-oh/drury-inn-and-suites-columbus-grove-city",
    source_name: "Official Drury Hotels property website",
    verified_at: "July 18, 2026",
    evidence_count: 11,
    // Supported policy fields (each read directly from the official source).
    dogs: "Accepted",
    cats: "Accepted",
    pet_fee: "$50",
    fee_basis: "Per room, per day",
    max_pets: "2",
    weight_limit: "80 lb combined",
    deposit: null,            // not stated by the reviewed source
    breed_restrictions: null, // not stated
    unattended: null,         // not stated
    evidence_quote:
      "Dogs and cats are accepted. A $50 fee applies per room per day. " +
      "A maximum of 2 pets is allowed. Pets may not exceed 80 lb.",
    has_photo: false          // no approved photography for any hotel
  },

  // -------------------------------------------------------------------- //
  // 2. SPARSE VERIFIED -- verified pet-friendly, but the official source
  //    stated only that pets are welcome (no fee/limit/species detail).
  //    Source: daysinncolumbusohio.com, verified 2026-07-18. Production row.
  // -------------------------------------------------------------------- //
  sparse: {
    state: "VERIFIED_PET_FRIENDLY",
    name: "Days Inn by Wyndham Grove City Columbus South",
    area: "Grove City corridor",
    address: "1849 Stringtown Rd",
    city: "Grove City", region: "OH", postal: "43123",
    phone: "614-871-0440",
    official_url: "https://www.daysinncolumbusohio.com",
    source_name: "Official Days Inn property website",
    verified_at: "July 18, 2026",
    evidence_count: 7,
    dogs: null, cats: null, pet_fee: null, fee_basis: null,
    max_pets: null, weight_limit: null, deposit: null,
    breed_restrictions: null, unattended: null,
    evidence_quote:
      "The property's official website identifies it as pet-friendly. It did " +
      "not state a fee, pet limit, or weight limit.",
    has_photo: false
  },

  // -------------------------------------------------------------------- //
  // 4. CONFIRMED NO-PETS -- the official source explicitly excludes pets
  //    (service animals handled as a separate legal category).
  //    Source: columbushilliardhotel.com, verified 2026-07-18. Evidence-
  //    backed REJECT(no_pets); intentionally NOT in the pet-friendly set.
  // -------------------------------------------------------------------- //
  noPets: {
    state: "VERIFIED_NO_PETS",
    name: "Columbus Hilliard Hotel",
    area: "West Hilliard corridor",
    address: "2350 Westbelt Dr",
    city: "Columbus", region: "OH", postal: "",
    phone: "",
    official_url: "https://www.columbushilliardhotel.com",
    source_name: "Official property website",
    verified_at: "July 18, 2026",
    evidence_count: 3,
    evidence_quote: "NO Pets Allowed, Service Animals Welcome.",
    service_animal_note:
      "The official source states service animals are welcome. Service " +
      "animals are a legal access category, not a pet-policy exception.",
    has_photo: false
  },

  // -------------------------------------------------------------------- //
  // 5. UNVERIFIED -- real, identifiable property, but its official source
  //    could not be reviewed (the chain site blocked automated access with
  //    HTTP 403). Identity is shown; NO pet policy is asserted.
  //    Source: Hampton Inn Columbus-Airport discovery record (REVIEW).
  // -------------------------------------------------------------------- //
  unverified: {
    state: "POLICY_UNVERIFIED",
    name: "Hampton Inn Columbus-Airport",
    area: "Airport corridor",
    address: "",
    city: "Columbus", region: "OH", postal: "",
    phone: "",
    official_url: "https://www.hilton.com/en/hotels/cmhaphx-hampton-columbus-airport/",
    source_name: "Official chain website (access blocked)",
    verified_at: null,
    evidence_count: 0,
    block_reason:
      "This property's official website blocked automated review, so its pet " +
      "policy has not been verified. Please confirm directly with the property.",
    has_photo: false
  }
};

// No coordinates exist in the production schema, so distance-based "nearby"
// is unavailable for every fixture. The honest fallback is used everywhere.
const PTF_COORDINATES_AVAILABLE = false;

if (typeof module !== "undefined") { module.exports = { PTF_FIXTURES, PTF_COORDINATES_AVAILABLE }; }
