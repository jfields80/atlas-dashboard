# ADR-PTF-AUTOMATED-BROWSING — visible-browser automation for official capture

- **Status:** ACCEPTED (operator decision, PTF-CAPTURE-003 Phase 1)
- **Supersedes:** the "no automated browsing" clause in `background.js` (header
  comment) and `CAPTURE_GUIDE.md`, *for the controller only*
- **Does not change:** the Chrome extension, which remains byte-for-byte as it
  was and continues to honour the original rule

## Context

Six major hotel brands refuse this project's automated fetchers. The manual
capture path (PTF-WORKERS-003/006) answered that by having a human open the
public page in their everyday browser and click one button. That path works,
and every hotel published so far came through it.

It does not scale. Twenty-five hotels cost the operator twenty-five rounds of
find-URL, open, hunt for the policy, scroll, click, then a ten-flag CLI
invocation. The cost is not the click; it is the hunting.

The original doctrine stated, as a hard rule:

> No stealth, evasion, proxying, user-agent spoofing or automated browsing.
> It reads the page the human already opened, once.

The lawfulness argument rested on the last clause: a founder opening a public
page **is an ordinary visitor**, and no access control is touched. Automating
navigation and scrolling does not touch an access control either — but it does
make "the page the human already opened" false as written. Redefining that
sentence silently would be the kind of quiet erosion this project's gates exist
to prevent, so it is amended explicitly, by version, here.

## Decision

Automation is permitted to **drive** a visible browser through pages the
operator is entitled to view. It is never permitted to **conceal** that it is
automation, to defeat an access control, or to represent an unreviewed page as
attested.

### Permitted

- Navigating to a public property URL supplied in an operator-authored queue
- Waiting for render and network quiet
- Reading the rendered DOM, text, JSON-LD, canonical URL
- Expanding a policy section through its own visible control
- Scrolling a located policy block into the viewport
- Screenshotting the visible tab
- Hashing, validating, deduplicating, and writing manifests

### Forbidden, by name

| Technique | Why |
|---|---|
| Stealth plugins (`playwright-stealth`, `undetected-chromedriver`, `puppeteer-extra-plugin-stealth`, equivalents) | Concealment |
| `--disable-blink-features=AutomationControlled` and equivalents | Concealment |
| User-agent spoofing / `Network.setUserAgentOverride` | Misrepresentation |
| Proxy rotation, `--proxy-server` | Evasion |
| CAPTCHA or challenge solving, of any kind, including manual relay | Access-control bypass |
| Credentialed browsing, sign-in, cookie injection | Access-control bypass |
| The operator's normal Chrome profile | Exposes their live sessions to CDP |
| Headless mode | Removes supervision, and is itself a concealment signal |
| Consent-banner auto-dismissal (Phase 1) | Deferred pending an explicit ruling |

The forbidden list is not prose only. `BANNED_AUTOMATION_MARKERS` in
`services/research_workers/capture_automation/doctrine.py` carries it as data,
and a boundary test fails the build if any marker appears in the source tree.

### Human affirmation is unchanged

`OperatorAffirmation.address_confirmed` and `.phone_confirmed` are a *person's*
statement that they looked at the page and saw those values. Automation may not
produce them. The controller therefore stops at a validated capture plus a
manifest; attestation, approval, promotion and deployment remain exactly as
they were, performed by a human through the existing CLI.

This is the load-bearing boundary of the whole sprint. A machine that both
gathers evidence and vouches for it has no evidence, only output.

## Consequences

**Accepted:** a program now visits brand sites on a schedule. Pacing minimums, a
three-consecutive-challenge kill switch, and a visible window are the mitigations;
none of them makes the change invisible, and none is meant to.

**Rejected outright:** any response to a challenge page other than stopping. If a
brand starts challenging us, the correct behaviour is to stop asking, not to ask
more cleverly.

**Preserved:** the extension. It is now the documented fallback for every
exception the controller raises, and the reason the fallback is credible is that
it never changed.
