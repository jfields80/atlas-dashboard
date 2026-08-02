"""The ADR's forbidden list, as data.

Prose in a document cannot fail a build. These constants can, and
``test_boundaries.py`` uses them to scan the source tree. Adding a technique
here is the mechanism for banning it -- there is deliberately no second place
to look.
"""

from __future__ import annotations

# Concealment, spoofing and evasion techniques. A source scan fails if any of
# these appears anywhere under the sprint's packages.
#
# Written as fragments rather than exact tokens so that near-misses
# (``playwright_stealth``, ``--proxy-server=...``) are caught too.
BANNED_AUTOMATION_MARKERS = (
    "playwright-stealth",
    "playwright_stealth",
    "undetected-chromedriver",
    "undetected_chromedriver",
    "puppeteer-extra",
    "puppeteer_extra",
    "selenium-stealth",
    "selenium_stealth",
    "AutomationControlled",
    "setUserAgentOverride",
    "--user-agent",
    "--proxy-server",
    "--headless",
    "--disable-web-security",
    "2captcha",
    "anticaptcha",
    "anti-captcha",
    "deathbycaptcha",
    "capsolver",
)

# Chrome flags the launcher is allowed to pass. An allowlist rather than a
# denylist: a new flag has to be argued for, not merely not-yet-banned.
PERMITTED_CHROME_FLAGS = (
    "--remote-debugging-port",
    "--user-data-dir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-sync",
    "--window-size",
    "--window-position",
)

# Pacing. A module constant, not a CLI flag, so a batch cannot be told to run
# flat out from the command line. Jitter is applied on top of the floor.
MIN_SECONDS_BETWEEN_HOTELS = 20.0
MAX_SECONDS_BETWEEN_HOTELS = 40.0

# Stop the batch after this many consecutive challenge pages. Continuing to
# request a brand that has started challenging us is the one behaviour that
# would genuinely look like abuse, so it is not a tunable.
CONSECUTIVE_CHALLENGE_LIMIT = 3

# How far the policy block may move, in PAGE coordinates, between the reading
# taken before the screenshot and the reading taken after it.
#
# Page coordinates, not viewport-relative, and the distinction is not academic.
# Chrome's captureScreenshot scrolls the page and then composites, so scrollY
# routinely changes across the call while the content stands still: on a real
# IHG page the policy sat at page-y 6233 before and after, and scrollY moved
# 106px. A viewport-relative test called that "drift" and refused three healthy
# captures in a row. What actually threatens the evidence is the CONTENT moving
# under the camera, which page coordinates measure and scroll offset does not.
#
# Sized from real measurements: on a healthy Marriott page the block reads
# identically across a screenshot and a three-second settle (0px across four
# probes), and two independent runs differed by 14px only because the scroll
# landed marginally differently.
POLICY_BOX_DRIFT_TOLERANCE_PX = 24.0

#: A reveal control may open a panel that animates into place. Measured on two
#: real property pages: the block reads 0x0 at the click, reaches its final
#: position between 0.5s and 1.0s, and then holds still indefinitely. Measuring
#: during that flight produced a 140-171px drift for a block that never moved
#: afterwards.
#:
#: The wait is for STABILITY, not a fixed sleep: two consecutive identical
#: reads, or give up and let the drift check do its job.
POLICY_SETTLE_TIMEOUT_SECONDS = 6.0
POLICY_SETTLE_POLL_SECONDS = 0.4
POLICY_SETTLE_STABLE_CHECKS = 2


# How long to wait for render and network quiet, in seconds.
NAVIGATION_TIMEOUT_SECONDS = 45.0
NETWORK_QUIET_SECONDS = 2.0
NETWORK_QUIET_TIMEOUT_SECONDS = 20.0

# Hydration readiness. `domContentEventFired` fires before a single-page app
# has rendered anything identity-bearing, and the runner used to take exactly
# one snapshot at that moment -- so a page that was merely slow read as a page
# with no identity at all. Aloft Columbus University District failed
# IDENTITY_UNVERIFIABLE after 7.2s, then succeeded unchanged on a later run.
#
# Bounded by construction: a maximum wait, a fixed poll interval, and a
# requirement that the signal hold still. No refresh, no re-navigation.
HYDRATION_TIMEOUT_SECONDS = 20.0
HYDRATION_POLL_SECONDS = 1.0

#: How many consecutive polls must show the same qualifying signal. Two is the
#: minimum that can distinguish "present" from "present and settled".
HYDRATION_STABLE_CHECKS = 2

#: Rendered text may still grow between the two qualifying checks by at most
#: this fraction. Beyond it the page is still assembling itself, and a snapshot
#: taken mid-assembly is not the page the screenshot will show.
HYDRATION_TEXT_DRIFT_TOLERANCE = 0.05

# The affirmation fields automation must never populate. Asserted by test
# against the emitted manifest and capture records.
OPERATOR_ONLY_FIELDS = (
    "address_confirmed", "address_observed",
    "phone_confirmed", "phone_observed",
    "operator_id", "attested_at", "statement",
)
