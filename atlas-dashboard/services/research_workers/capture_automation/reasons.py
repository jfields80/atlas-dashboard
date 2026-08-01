"""Every terminal reason a hotel can end on, and what to do about it.

One table. A reason that is not here cannot be recorded, which is what stops
the manifest filling up with free-text explanations nobody can aggregate.
"""

from __future__ import annotations

# Retry dispositions, carried into the manifest so a second run knows what is
# worth attempting again.
RETRY_NOW = "now"        # transient; a fresh run may well succeed
RETRY_MANUAL = "manual"  # a human with the extension can get this one
RETRY_NEVER = "never"    # re-running changes nothing

RETRY_DISPOSITIONS = (RETRY_NOW, RETRY_MANUAL, RETRY_NEVER)

# reason -> (retry disposition, one-line operator-facing explanation)
EXCEPTION_REASONS = {
    # -- navigation ------------------------------------------------------- #
    "CAPTCHA_OR_CHALLENGE": (
        RETRY_MANUAL,
        "The site served a bot challenge. Open it yourself and use the extension."),
    "ACCESS_DENIED": (
        RETRY_MANUAL,
        "The site refused the request outright."),
    "LOGIN_REQUIRED": (
        RETRY_NEVER,
        "The page demanded a sign-in. Credentialed browsing is forbidden."),
    "NAVIGATION_TIMEOUT": (
        RETRY_NOW,
        "The page did not finish rendering in time."),
    "NAVIGATION_FAILED": (
        RETRY_NOW,
        "Chrome could not load the URL."),
    "CONSENT_INTERACTION_UNSUPPORTED": (
        RETRY_MANUAL,
        "A consent banner covered the policy. Phase 1 never dismisses these."),

    # -- URL shape and identity ------------------------------------------- #
    "SEARCH_URL": (
        RETRY_NEVER,
        "The final URL is a search surface, which is never a stable citation."),
    "REDIRECTED_OFF_PROPERTY": (
        RETRY_NEVER,
        "Navigation ended somewhere other than the property page."),
    "PROPERTY_CODE_MISMATCH": (
        RETRY_NEVER,
        "The property code in the final URL is not the one the queue expected."),
    "IDENTITY_MISMATCH": (
        RETRY_NEVER,
        "The page identifies a different hotel than the queue entry."),
    "IDENTITY_UNVERIFIABLE": (
        RETRY_MANUAL,
        "The page carried too little identity evidence to confirm the hotel."),
    "PRIVATE_PARAMS_IN_CITATION": (
        RETRY_NOW,
        "The citable URL would carry a session or ad-tracking parameter."),

    # -- policy ------------------------------------------------------------ #
    "POLICY_NOT_FOUND": (
        RETRY_MANUAL,
        "No pet-policy anchor appeared in the rendered page."),
    "POLICY_OFF_SCREEN": (
        RETRY_NOW,
        "The policy block could not be brought into the screenshot viewport."),
    "INTERACTION_UNSUPPORTED": (
        RETRY_MANUAL,
        "The policy section stayed collapsed after every supported step."),
    "FEE_TERMS_CONFLICT": (
        RETRY_NEVER,
        "The source states conflicting fee terms; this will route REVIEW."),

    # -- capture and validation -------------------------------------------- #
    "INSUFFICIENT_TEXT": (
        RETRY_NOW,
        "The page rendered too little text to carry a policy."),
    "CAPTURE_WRITE_FAILED": (
        RETRY_NOW,
        "The capture files could not be written."),
    "SCREENSHOT_UNAVAILABLE": (
        RETRY_NOW,
        "Chrome would not produce a screenshot."),
    "VALIDATION_FAILED": (
        RETRY_NOW,
        "The written capture failed its own validation."),
    "DUPLICATE_CAPTURE": (
        RETRY_NEVER,
        "This exact page text has already been captured."),
    "FORBIDDEN_CONTENT": (
        RETRY_NEVER,
        "The capture carried a key the ingestion contract refuses."),

    # -- batch control ------------------------------------------------------ #
    "BATCH_ABORTED": (
        RETRY_NOW,
        "The batch stopped before reaching this hotel."),
    "ADAPTER_UNAVAILABLE": (
        RETRY_NEVER,
        "No brand adapter is registered for this hotel."),
    "UNEXPECTED_ERROR": (
        RETRY_NOW,
        "An unhandled error occurred; see the journal for the type."),
}

# Reasons that mean the brand is pushing back, which the kill switch counts.
CHALLENGE_REASONS = frozenset({"CAPTCHA_OR_CHALLENGE", "ACCESS_DENIED"})


def retry_for(reason: str) -> str:
    """Disposition for a reason. Unknown reasons are retryable-by-hand rather
    than silently dropped -- an unrecognised failure is exactly the kind a
    person should look at."""
    return EXCEPTION_REASONS.get(reason, (RETRY_MANUAL, ""))[0]


def explain(reason: str) -> str:
    return EXCEPTION_REASONS.get(reason, (RETRY_MANUAL, "Unrecognised reason."))[1]
