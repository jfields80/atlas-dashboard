# Capture for PetTripFinder

A deliberately tiny Chrome extension that saves the official hotel page you are
looking at as a `ptf-official-capture/1.0` JSON file, for the PetTripFinder
manual attestation path.

## Why it exists

IHG, Hilton, Marriott, Red Roof, Best Western and Choice all refuse this
project's automated fetchers (403, or a silent timeout). Every technique that
would defeat that — stealth plugins, UA spoofing, proxy rotation, challenge
solving — is forbidden by the mission.

The lawful route is a person. You opening a public hotel page in your everyday
browser is an ordinary visitor, and no access control is touched. This
extension carries what your browser already rendered into the committed
pipeline, where it goes through the *same* identity, evidence and routing gates
automatic retrieval would have applied.

## What it does, and only this

* Runs **only** when you click the toolbar button. No content script, no
  automatic injection, no background activity.
* Reads the current tab's URL, title, canonical URL, full HTML, visible text
  and any JSON-LD blocks.
* Takes one screenshot of the visible tab.
* Writes both to `Downloads/ptf-capture/`.

It makes **no network request of its own** — no `fetch`, no analytics, no
telemetry. It requests no cookie, storage, history or credential permission, so
it cannot reach them. It contains no stealth, evasion or automated-browsing
behaviour. It never approves or submits anything.

## Install (unpacked, local only)

1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select this directory
3. Pin "Capture for PetTripFinder" to the toolbar

## Use

1. Sign **out** of the hotel brand's site first. The capture stores the DOM you
   see; a signed-in session can embed your personal details in it.
2. Open the property's official page — the page that actually states the pet
   policy, not a search result or a city listing.
3. Scroll so the pet-policy text is visible (the screenshot captures the
   visible area only).
4. Click the toolbar button. The badge shows `OK` or `ERR`.
5. You get two files in `Downloads/ptf-capture/`:
   `<host-path>-<timestamp>.json` and the matching `.png`.

Click again after scrolling to collect additional screenshots.

## Then hand it to the pipeline

```
python -m services.research_workers attest-official-page \
  --hotel "<exact seed name>" \
  --capture  Downloads/ptf-capture/<file>.json \
  --screenshot Downloads/ptf-capture/<file>.png \
  --after-retrieval <path to that hotel's retrieval artifact> \
  --operator-id <your handle> \
  --attested-at <ISO> --observed-at <ISO> --timezone America/New_York \
  --address-confirmed --address-observed "<address on the page>" \
  --phone-confirmed   --phone-observed   "<phone on the page>"
```

That produces a **PENDING, unpublishable** attestation. Publication needs a
separate, explicitly recorded approval:

```
python -m services.research_workers approve-attestation \
  --attestation <path> --approver-id <handle> \
  --approved-at <ISO> --record-id <APR-nnnn>
```

## What the capture is not

It is not proof of approval, and it is not automatically official evidence.
Ingestion re-derives every hash, re-checks property identity, re-applies the
brand-vs-property rule, and refuses the capture outright if it is a challenge
page, a login wall, an access-denied page, or too thin to carry policy text.
Attested records are always routed **REVIEW**, never READY.
