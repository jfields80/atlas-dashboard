"""Component analytics constants (AES-WEB-002A; AES-WEB-002 §18.2).

Names only in MVP. No analytics SDK, script, or network call exists
anywhere in the component system — these identifiers are emitted as inert
``data-`` attributes and consumed by future deployment-layer
instrumentation (a later authority document). Constants only; stdlib-only
per the AES-WEB-001 §3.2 dependency matrix.
"""

# Event registry (AES-WEB-002 §18.2). MVP events plus the P3 events whose
# names are reserved now so future instrumentation binds without markup
# changes.
ANALYTICS_EVENTS = (
    "component_impression",
    "component_interaction",
    "cta_click",
    "form_start",
    "form_complete",
    "form_fail",
    "phone_click",
    "outbound_click",
    "listing_click",
    "sponsored_listing_click",
    "filter_use",
    "search_submit",
    "zero_results_view",
    "pagination_click",
    "map_interaction",  # P3
    "save",  # P3
    "share",  # P3
    "review_expand",
    "claim_start",
    "sponsor_inquiry_start",
    "submission_start",
    "correction_start",
)

# Payload field names, registered now (§18.2). No personally identifying
# data appears in any identifier or payload field (§18.3).
ANALYTICS_PAYLOAD_FIELDS = (
    "event",
    "component_id",
    "component_version",
    "variant",
    "label",
    "listing_kind",
    "page_role",
    "registry_version",
    "build_id",
)

# Emitted data-attribute names (§18.1) — reserved; emitters are a later wave.
ANALYTICS_DATA_ATTRIBUTES = (
    "data-atlas-c",  # component id
    "data-atlas-v",  # component version
    "data-atlas-var",  # variant
    "data-atlas-e",  # event name (interactive elements)
    "data-atlas-l",  # label
    "data-atlas-k",  # listing kind (paid/organic separator)
)
