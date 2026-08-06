"""PTF-WORKERS-004 -- OpenAI web-research provider (Responses API + web_search).

WHAT THIS IS, PRECISELY
-----------------------
This is *web search grounding on a general-purpose model*: the Responses API
(``POST /v1/responses``) driving ``gpt-5.4`` with the built-in ``web_search``
tool, constrained to an operator-supplied allowlist of official domains.

It is NOT OpenAI's dedicated "deep research" product, and nothing here should
be described as such. That product's models are unavailable to this API
project -- ``GET /v1/models/o3-deep-research`` and
``GET /v1/models/o4-mini-deep-research`` both return HTTP 404
``model_not_found``. Naming this module after a product we cannot call would
misrepresent both the capability and its cost profile.

WHAT IT IS FOR
--------------
Discovery, not evidence -- and only on ESCALATION. PTF-WORKERS-003
(``source_retrieval``) can already turn an official URL into verified,
hash-bound, verbatim-quotable evidence, for free. This module must never be
called for a hotel that direct retrieval already handled; that rule is enforced
in ``research_escalation.require_escalation``, not left to discipline. This is
also not the default hotel worker: ``gpt-5.4`` is the FINAL fallback on the
ladder in ``research_escalation``, reached only after cheaper qualified tiers
are unavailable.

What retrieval cannot do is *find* the URL when the seed record has none, or
when the seed URL points at a directory page. That is the gap this module
fills:

    web_research  ->  candidate official URLs  ->  source_retrieval  ->  evidence

The model's narrative output is explicitly NOT evidence. It is recorded with
its own provenance (``V.SOURCE_MODEL_RESEARCH_REPORT``), which is excluded from
``V.OFFICIAL_SOURCE_TYPES``, so:

  * ``SourceDocument.is_usable_official`` is False for it, hence the evidence
    validator never draws a fact from it; and
  * ``routing`` carries a named backstop that forces REVIEW if such a document
    is ever cited by a supported fact or selected as a result's source.

Two independent mechanisms, either one sufficient. That redundancy is
deliberate: the cost of a model report being mistaken for a fetched official
page is a wrong published pet policy.

TWO RULES WORTH STATING OUTRIGHT
--------------------------------
1. **Discovered URLs come only from tool citations, never from model prose.**
   A URL the model types into its answer is a token sequence it generated and
   may be fabricated. A ``url_citation`` annotation (or a
   ``web_search_call.action.sources`` entry) is emitted by the search tool for
   a page it actually retrieved. Only the latter is read here.

2. **The domain allowlist is enforced twice.** Once as a server-side
   ``filters.allowed_domains`` on the tool, and again locally against every
   returned citation. The remote filter is a cost/quality control; the local
   re-check is the security boundary, because a provider-side filter is not
   something this system can verify.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from services.research_workers import vocabulary as V
from services.research_workers.contracts import SourceDocument, content_hash
from services.research_workers.providers import (
    LiveAuthorization, SpendingAirlockError, classify_provider_error,
    require_live_authorization, require_web_research_spend_authorization,
)
from services.research_workers.proposal import ProviderErrorDetail

WEB_RESEARCH_VERSION = "ptf-workers-004/1.0.0"

# The single approved model for this seam. Held as a constant and checked at
# request time so a live run can never be silently pointed at a different (and
# differently priced) model -- the same discipline as the Columbus pilot's
# approved-Nano guard.
APPROVED_MODEL = "gpt-5.4"

# Verified available on this project by unpaid probe: the Responses API accepts
# these tool types. `web_search` is the current name; the others are accepted
# aliases retained so an operator can pin a dated variant if behaviour drifts.
WEB_SEARCH_TOOL = "web_search"
ACCEPTED_WEB_SEARCH_TOOLS = frozenset({
    "web_search", "web_search_2025_08_26", "web_search_preview",
    "web_search_preview_2025_03_11",
})

# Server-validated enums (confirmed by unpaid 400 probes against this project).
SEARCH_CONTEXT_SIZES = ("low", "medium", "high")
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")

# The API's own floor for max_output_tokens; a smaller value is rejected.
MIN_OUTPUT_TOKENS = 16


# --------------------------------------------------------------------------- #
# Official-domain allowlist.
# --------------------------------------------------------------------------- #

def normalize_domain(value: str) -> str:
    """Bare, lowercase, port-free registrable host from a domain OR a full URL.

    Accepts what an operator will actually type -- "IHG.com",
    "https://www.ihg.com/staybridge/", "www.ihg.com:443" -- and yields
    "ihg.com" for all three. A leading "www." is stripped because the allowlist
    is matched suffix-wise (below), so keeping it would only ever narrow the
    match by accident.
    """
    v = (value or "").strip().lower()
    if not v:
        return ""
    if "//" in v:
        v = urlsplit(v).hostname or ""
    else:
        v = v.split("/")[0]
    v = v.split("@")[-1].split(":")[0].strip(".")
    if v.startswith("www."):
        v = v[4:]
    return v


def host_in_allowlist(host: str, allowed: Sequence[str]) -> bool:
    """Exact host match or a true subdomain of an allowed domain.

    Suffix matching is anchored on a dot ("." + domain) rather than a bare
    ``endswith``: without the dot, an allowlist entry of "ihg.com" would also
    admit "evil-ihg.com". It also sidesteps public-suffix guesswork entirely --
    no attempt is made to compute a registrable domain for multi-label TLDs,
    because the operator states the exact domains and we only ever descend into
    them.
    """
    h = normalize_domain(host)
    if not h:
        return False
    for d in allowed:
        d = normalize_domain(d)
        if d and (h == d or h.endswith("." + d)):
            return True
    return False


def official_domains_for(website_url: str, extra_domains: Sequence[str] = ()) -> Tuple[str, ...]:
    """Deterministic allowlist: the seed record's own official website domain,
    plus any operator-supplied additions (a brand domain, typically).

    Deliberately NOT inferred from the hotel's name or brand -- deriving
    "staybridge -> ihg.com" in code would embed a brand table that goes stale
    silently. The seed CSV already carries the authoritative website_url, and
    anything beyond it is an explicit operator decision recorded on the command
    line.
    """
    out: List[str] = []
    for candidate in (normalize_domain(website_url),) + tuple(
            normalize_domain(d) for d in extra_domains):
        if candidate and candidate not in out:
            out.append(candidate)
    return tuple(out)


# --------------------------------------------------------------------------- #
# Bounded request shape + exact cost ceiling.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class WebResearchCaps:
    """Every bound on one research call.

    ``max_tool_calls`` and ``max_output_tokens`` are SERVER-ENFORCED (both are
    validated request parameters -- confirmed by unpaid probe), so those two
    terms of the cost ceiling are hard limits rather than hopes.

    ``assumed_tokens_per_search_call`` is the one genuinely estimated term:
    there is no request parameter that caps how much retrieved page text the
    search tool feeds back into context. It is an operator-supplied
    conservative constant, and ``exact_max_cost_usd`` is honest about resting
    on it. Actual usage is always reported afterwards so the assumption can be
    checked against reality rather than trusted forever.
    """

    max_tool_calls: int = 4
    max_output_tokens: int = 3000
    search_context_size: str = "medium"
    reasoning_effort: str = "medium"
    assumed_prompt_tokens: int = 1500
    assumed_tokens_per_search_call: int = 12000
    timeout_s: float = 300.0
    max_retries: int = 0

    def validate(self) -> None:
        if self.max_tool_calls < 1:
            raise SpendingAirlockError("max_tool_calls must be >= 1")
        if self.max_output_tokens < MIN_OUTPUT_TOKENS:
            raise SpendingAirlockError(
                "max_output_tokens must be >= %d (API floor)" % MIN_OUTPUT_TOKENS)
        if self.search_context_size not in SEARCH_CONTEXT_SIZES:
            raise SpendingAirlockError(
                "search_context_size must be one of %s" % (SEARCH_CONTEXT_SIZES,))
        if self.reasoning_effort not in REASONING_EFFORTS:
            raise SpendingAirlockError(
                "reasoning_effort must be one of %s" % (REASONING_EFFORTS,))
        if self.assumed_prompt_tokens < 0 or self.assumed_tokens_per_search_call < 0:
            raise SpendingAirlockError("token assumptions must be non-negative")

    @property
    def max_input_tokens(self) -> int:
        """Worst-case billable input: the prompt, plus the most retrieved text
        the maximum number of searches could put into context."""
        return int(self.assumed_prompt_tokens
                   + self.max_tool_calls * self.assumed_tokens_per_search_call)


@dataclass(frozen=True)
class WebResearchPricing:
    """USD rates. Supplied by the operator at run time and never defaulted.

    This mirrors ``pricing.py``'s standing rule -- when no price is supplied,
    report the absence rather than a guessed number. There is no pricing
    endpoint on the API, so a hardcoded table here would be an unverifiable
    claim that silently goes stale, and it would be the number an operator
    reads before authorizing spend.
    """

    input_per_1k: float
    output_per_1k: float
    per_tool_call_usd: float = 0.0

    def validate(self) -> None:
        for name, val in (("input_per_1k", self.input_per_1k),
                          ("output_per_1k", self.output_per_1k),
                          ("per_tool_call_usd", self.per_tool_call_usd)):
            if val is None or val < 0:
                raise SpendingAirlockError("pricing %s must be >= 0" % name)


def exact_max_cost_usd(caps: WebResearchCaps, pricing: WebResearchPricing) -> float:
    """The worst-case cost of ONE research call, in USD.

    Every term is at its maximum: full input assumption, every output token
    spent, every permitted tool call made. Rounded UP to the cent so the
    displayed ceiling is never less than the arithmetic ceiling.
    """
    caps.validate()
    pricing.validate()
    raw = (caps.max_input_tokens / 1000.0 * pricing.input_per_1k
           + caps.max_output_tokens / 1000.0 * pricing.output_per_1k
           + caps.max_tool_calls * pricing.per_tool_call_usd)
    cents = int(raw * 100.0)
    if cents / 100.0 < raw:
        cents += 1                      # round up, never down, on a spend ceiling
    return round(cents / 100.0, 2)


def actual_cost_usd(usage: "WebResearchUsage", pricing: WebResearchPricing) -> float:
    """Metered cost from real usage (billable input excludes cached tokens)."""
    pricing.validate()
    billable_input = max(0, usage.input_tokens - usage.cached_input_tokens)
    return round(billable_input / 1000.0 * pricing.input_per_1k
                 + usage.output_tokens / 1000.0 * pricing.output_per_1k
                 + usage.search_calls * pricing.per_tool_call_usd, 6)


# --------------------------------------------------------------------------- #
# Result shapes.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class WebResearchUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    search_calls: int = 0
    latency_ms: int = 0

    def to_dict(self) -> Dict:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "cached_input_tokens": self.cached_input_tokens,
                "search_calls": self.search_calls, "latency_ms": self.latency_ms}


@dataclass(frozen=True)
class DiscoveredUrl:
    """One URL the SEARCH TOOL actually retrieved (never model prose)."""

    url: str
    title: str = ""
    origin: str = "url_citation"        # url_citation | search_sources

    def to_dict(self) -> Dict:
        return {"url": self.url, "title": self.title, "origin": self.origin}


@dataclass(frozen=True)
class WebResearchReport:
    """The complete, secret-free outcome of one web-research call."""

    listing_key: str
    listing_name: str
    ok: bool
    model: str
    allowed_domains: Tuple[str, ...]
    report_text: str = ""
    discovered_urls: Tuple[DiscoveredUrl, ...] = ()
    rejected_urls: Tuple[Dict[str, str], ...] = ()
    usage: WebResearchUsage = field(default_factory=WebResearchUsage)
    error: str = ""
    provider_error: Optional[ProviderErrorDetail] = None
    observed_at: str = ""
    # Audit trail for one paid call. ``response_status`` is the Responses API's
    # OWN status ("completed" / "incomplete"), which is not the same claim as
    # HTTP 200: a call can succeed at the transport layer and still be truncated
    # by max_output_tokens, and reporting only the HTTP status would hide that.
    request_id: str = ""
    http_status: int = 0
    response_status: str = ""
    incomplete_reason: str = ""

    @property
    def source_type(self) -> str:
        """Always model-research provenance. There is no code path on which a
        web-research report acquires an OFFICIAL_* type."""
        return V.SOURCE_MODEL_RESEARCH_REPORT

    def to_dict(self) -> Dict:
        return {
            "web_research_version": WEB_RESEARCH_VERSION,
            "listing_key": self.listing_key,
            "listing_name": self.listing_name,
            "ok": self.ok,
            "model": self.model,
            "source_type": self.source_type,
            "allowed_domains": list(self.allowed_domains),
            "report_text": self.report_text,
            "report_text_bytes": len(self.report_text.encode("utf-8")),
            "discovered_urls": [d.to_dict() for d in self.discovered_urls],
            "rejected_urls": [dict(r) for r in self.rejected_urls],
            "usage": self.usage.to_dict(),
            "error": self.error,
            "provider_error": (self.provider_error.to_dict()
                               if self.provider_error is not None else None),
            "observed_at": self.observed_at,
            "request_id": self.request_id,
            "http_status": self.http_status,
            "response_status": self.response_status,
            "incomplete_reason": self.incomplete_reason,
            "is_official_evidence": False,
            "publication_eligible": False,
        }


def research_report_document(report: WebResearchReport) -> SourceDocument:
    """Persist a report as a SourceDocument for audit.

    The URL is a synthetic URN, not one of the cited pages. Putting a real
    hotel URL here would be the exact confusion this whole module exists to
    prevent -- the document's content is the MODEL's prose, and labelling it
    with the hotel's URL would make a paraphrase look like a fetched page. The
    URN is content-addressed, so the same report always yields the same id.

    The returned document has ``source_type = MODEL_RESEARCH_REPORT``, so
    ``is_usable_official`` is False and the evidence validator will skip it.
    """
    text = report.report_text or ""
    encoded = text.encode("utf-8")
    if len(encoded) > V.SOURCE_CONTENT_CAP_BYTES:
        text = encoded[:V.SOURCE_CONTENT_CAP_BYTES].decode("utf-8", "ignore")
    digest = content_hash(text)
    return SourceDocument(
        source_url="urn:atlas:model-research-report:%s" % digest.split(":", 1)[1][:32],
        source_type=V.SOURCE_MODEL_RESEARCH_REPORT,
        retrieved_at=report.observed_at,
        title="Model research report: %s" % report.listing_name,
        content_text=text,
        content_hash=digest,
        retrieval_status=V.RETRIEVAL_OK,
    )


# --------------------------------------------------------------------------- #
# Per-claim provenance (PTF-WORKERS-004 provenance contract, rules 6 and 7).
# --------------------------------------------------------------------------- #
#
# The distinction this section exists to make unmissable:
#
#     a quote is verbatim IN THE REPORT   !=   the hotel's page says it
#
# ``evidence_validator._quote_verbatim`` answers the first question. When the
# document it checks is a MODEL_RESEARCH_REPORT, a passing check proves only
# that the model quoted itself -- the report is the model's own prose, so any
# sentence in it is trivially "verbatim" against it. Treating that as evidence
# would make a paraphrase indistinguishable from a fetched page.
#
# So the two facts are carried in two separate fields that cannot be conflated:
# ``report_quote`` (what the report said) and ``cited_source_quote_status``
# (what, if anything, independently confirmed it). The status starts UNVERIFIED
# and there is no code path that constructs it otherwise -- it is promoted only
# by the functions below, each of which demands real evidence.

# What, if anything, has independently confirmed the quote against the cited
# page. UNVERIFIED is the only value a fresh research claim may hold.
QUOTE_UNVERIFIED = "UNVERIFIED"
QUOTE_RETRIEVED_VERBATIM = "RETRIEVED_VERBATIM"    # we fetched + hashed the page
QUOTE_RENDERED_ATTESTED = "RENDERED_ATTESTED"      # a human captured the rendered page
QUOTE_DIRECTLY_CONFIRMED = "DIRECTLY_CONFIRMED"    # first-party hotel contact recorded
CITED_SOURCE_QUOTE_STATUSES = frozenset({
    QUOTE_UNVERIFIED, QUOTE_RETRIEVED_VERBATIM, QUOTE_RENDERED_ATTESTED,
    QUOTE_DIRECTLY_CONFIRMED,
})
# The three statuses that represent real independent confirmation. Membership
# here is necessary for promotion past REVIEW -- never sufficient on its own,
# because routing and operator approval still apply.
CONFIRMED_QUOTE_STATUSES = frozenset({
    QUOTE_RETRIEVED_VERBATIM, QUOTE_RENDERED_ATTESTED, QUOTE_DIRECTLY_CONFIRMED,
})


class ClaimProvenanceError(ValueError):
    """Raised when a claim would misrepresent where its evidence came from."""


@dataclass(frozen=True)
class ResearchClaim:
    """One statement a research report made, with its full provenance chain.

    A claim is a POINTER to evidence, never evidence. Even at
    ``DIRECTLY_CONFIRMED`` it does not publish anything: it records that some
    other approved evidence path verified the same fact, so the pipeline can
    stop asking. The published fact still comes from that other path's
    hash-bound document, not from here.
    """

    listing_key: str
    report_quote: str                 # exact excerpt, verbatim in the report
    cited_url: str                    # the official URL the SEARCH TOOL returned
    cited_page_title: str = ""
    report_retrieved_at: str = ""     # when the research call ran
    model: str = ""
    response_id: str = ""             # the API response id, for replay
    citation_origin: str = ""         # url_citation | search_sources
    cited_source_quote_status: str = QUOTE_UNVERIFIED
    independently_retrieved: bool = False
    confirmed_by: str = ""            # what performed the confirmation

    def __post_init__(self):
        if self.cited_source_quote_status not in CITED_SOURCE_QUOTE_STATUSES:
            raise ClaimProvenanceError(
                "unknown cited_source_quote_status %r" % self.cited_source_quote_status)
        # independently_retrieved is a claim about OUR retrieval specifically,
        # so it may be true only for the status that records our fetch. A human
        # capture or a phone call confirms the fact without Atlas retrieving
        # anything, and conflating the two would overstate the chain of custody.
        if self.independently_retrieved and (
                self.cited_source_quote_status != QUOTE_RETRIEVED_VERBATIM):
            raise ClaimProvenanceError(
                "independently_retrieved is true but status is %s; only "
                "%s records a page this system fetched"
                % (self.cited_source_quote_status, QUOTE_RETRIEVED_VERBATIM))

    @property
    def source_type(self) -> str:
        """Unconditionally model-research provenance.

        Deliberately not a stored field. A confirmed claim still ORIGINATED in a
        model report, and the published fact must be attributed to the document
        that confirmed it -- never to this claim.
        """
        return V.SOURCE_MODEL_RESEARCH_REPORT

    @property
    def is_confirmed(self) -> bool:
        return self.cited_source_quote_status in CONFIRMED_QUOTE_STATUSES

    @property
    def publication_eligible(self) -> bool:
        """Always False. A research claim never publishes a policy fact."""
        return False

    def to_dict(self) -> Dict:
        return {
            "listing_key": self.listing_key,
            "source_type": self.source_type,
            "report_quote": self.report_quote,
            "cited_url": self.cited_url,
            "cited_page_title": self.cited_page_title,
            "report_retrieved_at": self.report_retrieved_at,
            "model": self.model,
            "response_id": self.response_id,
            "citation_origin": self.citation_origin,
            "cited_source_quote_status": self.cited_source_quote_status,
            "independently_retrieved": self.independently_retrieved,
            "confirmed_by": self.confirmed_by,
            "is_confirmed": self.is_confirmed,
            "is_official_evidence": False,
            "publication_eligible": False,
        }


def report_quote_present(report: WebResearchReport, quote: str) -> bool:
    """Does ``quote`` appear verbatim in the REPORT text?

    Named for exactly what it proves. It is the report-scoped analogue of the
    validator's verbatim check, and it says nothing whatsoever about the cited
    hotel page -- see this section's header.
    """
    q = " ".join((quote or "").split())
    if not q:
        return False
    return q in " ".join((report.report_text or "").split())


def claim_from_report(report: WebResearchReport, *, report_quote: str,
                      cited_url: str) -> ResearchClaim:
    """Build an UNVERIFIED claim, refusing anything the report cannot support.

    Two integrity gates, both of which reject rather than downgrade:

    * the quote must actually appear in the report -- a claim assembled from a
      remembered or paraphrased sentence has no audit value; and
    * the URL must be one the SEARCH TOOL returned and the allowlist kept. A
      URL absent from ``discovered_urls`` was either fabricated in model prose
      or rejected as off-allowlist, and neither may acquire a citation here.
    """
    if not report.ok:
        raise ClaimProvenanceError(
            "cannot build a claim from a failed research call (%s)" % (report.error or "?"))
    if not report_quote_present(report, report_quote):
        raise ClaimProvenanceError(
            "report_quote does not appear verbatim in the report text")
    match = next((d for d in report.discovered_urls if d.url == cited_url), None)
    if match is None:
        rejected = any(r.get("url") == cited_url for r in report.rejected_urls)
        raise ClaimProvenanceError(
            "cited_url is not an allowlisted tool citation for this report (%s)"
            % ("rejected by the domain allowlist" if rejected
               else "absent from discovered_urls"))
    return ResearchClaim(
        listing_key=report.listing_key,
        report_quote=" ".join(report_quote.split()),
        cited_url=match.url,
        cited_page_title=match.title,
        report_retrieved_at=report.observed_at,
        model=report.model,
        response_id=report.request_id,
        citation_origin=match.origin,
    )


def confirm_claim_with_source(claim: ResearchClaim, document: SourceDocument,
                              *, status: str = QUOTE_RETRIEVED_VERBATIM
                              ) -> ResearchClaim:
    """Promote a claim once genuine official evidence confirms its quote.

    This is the code form of promotion rule 5. It refuses three ways:

    * a MODEL_RESEARCH_REPORT document cannot confirm a model research claim --
      that is the circularity the whole contract exists to prevent;
    * the document must be usable official evidence; and
    * the quote must appear verbatim in THAT document's text, not in the report.

    ``status`` selects which confirmation path is being recorded, so a human
    render capture is never mislabelled as a page this system fetched.
    """
    if status not in CONFIRMED_QUOTE_STATUSES:
        raise ClaimProvenanceError(
            "%r is not a confirmation status; expected one of %s"
            % (status, sorted(CONFIRMED_QUOTE_STATUSES)))
    if document.source_type in V.NON_PUBLISHABLE_SOURCE_TYPES:
        raise ClaimProvenanceError(
            "a %s document cannot confirm a research claim -- confirmation "
            "requires evidence from outside the model" % document.source_type)
    if not document.is_usable_official:
        raise ClaimProvenanceError(
            "confirming document is not usable official evidence (source_type=%s, "
            "retrieval_status=%s)" % (document.source_type, document.retrieval_status))
    haystack = " ".join((document.content_text or "").split())
    if claim.report_quote not in haystack:
        raise ClaimProvenanceError(
            "the quote does not appear verbatim in the confirming document; the "
            "report said something the official page does not")
    return ResearchClaim(
        listing_key=claim.listing_key,
        report_quote=claim.report_quote,
        cited_url=claim.cited_url,
        cited_page_title=claim.cited_page_title,
        report_retrieved_at=claim.report_retrieved_at,
        model=claim.model,
        response_id=claim.response_id,
        citation_origin=claim.citation_origin,
        cited_source_quote_status=status,
        independently_retrieved=(status == QUOTE_RETRIEVED_VERBATIM),
        confirmed_by=document.source_url,
    )


# --------------------------------------------------------------------------- #
# Prompt.
# --------------------------------------------------------------------------- #

RESEARCH_PROMPT_VERSION = "ptf-workers-004-research/1.0.0"

_INSTRUCTIONS = """\
You are a research assistant locating the OFFICIAL pet-policy page for one \
specific hotel property. You are a discovery aid: another system will fetch \
and verify whatever page you identify, so a correct URL matters far more than \
a confident summary.

Rules:
1. Search only the official domains you are permitted to search.
2. Identify the page that states THIS property's pet policy. If only a \
brand-wide policy exists, say so explicitly and do not present it as the \
property's own.
3. If a fact is not stated on a page you actually read, write "not stated". \
Never infer a fee, weight limit, or species permission from silence, from a \
sister property, or from general brand marketing.
4. Quote policy wording verbatim when you report it, and attribute each quote \
to the page it came from.
5. If you cannot find a property-specific policy page, say that plainly. \
"Not found" is a correct and useful answer; a guess is not.
"""


def build_research_prompt(listing_name: str, address: str, city: str, state: str,
                          allowed_domains: Sequence[str]) -> Tuple[str, str]:
    """(instructions, input) for the Responses API. Deterministic."""
    where = ", ".join(p for p in (address, city, state) if p)
    user = (
        "Hotel: %s\n"
        "Address: %s\n"
        "Permitted official domains: %s\n\n"
        "Find this property's official pet policy page and report:\n"
        "  - the URL of the page stating the policy\n"
        "  - whether that policy is property-specific or brand-wide\n"
        "  - pets allowed; dogs; cats; pet fee and its basis; refundable deposit; "
        "maximum pets; weight limit; breed restrictions; unattended-pet rule\n"
        "  - a verbatim quote for each fact you report\n"
        % (listing_name, where or "(not supplied)", ", ".join(allowed_domains) or "(none)")
    )
    return _INSTRUCTIONS, user


# --------------------------------------------------------------------------- #
# Response parsing.
# --------------------------------------------------------------------------- #

def _iter_output_items(payload: Dict):
    out = payload.get("output")
    return out if isinstance(out, list) else []


def extract_report_text(payload: Dict) -> str:
    """Concatenated assistant output_text. Reasoning items are ignored."""
    chunks: List[str] = []
    for item in _iter_output_items(payload):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                chunks.append(str(part.get("text") or ""))
    return "\n".join(c for c in chunks if c).strip()


def extract_tool_citations(payload: Dict) -> List[Tuple[str, str, str]]:
    """(url, title, origin) for every TOOL-PROVIDED url, in first-seen order.

    Two channels, both emitted by the search tool rather than by the model's
    token stream: ``url_citation`` annotations on the answer text, and (when
    ``web_search_call.action.sources`` is included) the raw source list of each
    search. Model prose is never scanned for URLs.
    """
    found: List[Tuple[str, str, str]] = []
    seen = set()

    def add(url, title, origin):
        u = (url or "").strip()
        if u and u not in seen:
            seen.add(u)
            found.append((u, (title or "").strip(), origin))

    for item in _iter_output_items(payload):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for part in item.get("content") or []:
                if not isinstance(part, dict):
                    continue
                for ann in part.get("annotations") or []:
                    if isinstance(ann, dict) and ann.get("type") == "url_citation":
                        add(ann.get("url"), ann.get("title"), "url_citation")
        elif item.get("type") == "web_search_call":
            action = item.get("action")
            if isinstance(action, dict):
                for src in action.get("sources") or []:
                    if isinstance(src, dict):
                        add(src.get("url"), src.get("title"), "search_sources")
                    elif isinstance(src, str):
                        add(src, "", "search_sources")
    return found


def count_search_calls(payload: Dict) -> int:
    return sum(1 for i in _iter_output_items(payload)
               if isinstance(i, dict) and i.get("type") == "web_search_call")


def extract_usage(payload: Dict) -> Tuple[int, int, int]:
    """(input_tokens, output_tokens, cached_input_tokens) -- Responses dialect.

    Distinct from ``providers.normalize_usage``, which speaks the
    chat-completions field names (prompt_tokens/completion_tokens). The
    Responses API reports input_tokens/output_tokens with cached tokens nested
    under input_tokens_details, so reusing that helper here would silently
    meter every call as zero.
    """
    usage = payload.get("usage") or {}
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens") or 0
    return (int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)),
            int(cached))


def partition_citations(citations: Sequence[Tuple[str, str, str]],
                        allowed_domains: Sequence[str]
                        ) -> Tuple[Tuple[DiscoveredUrl, ...], Tuple[Dict[str, str], ...]]:
    """Split tool citations into allowlisted and rejected.

    This is the LOCAL enforcement of the domain allowlist. The same restriction
    was sent to the API as ``filters.allowed_domains``, but a provider-side
    filter is not verifiable from here, so every returned URL is re-checked
    against the same list before it can reach the retrieval seam. A rejected
    URL is recorded with its reason rather than dropped silently.
    """
    kept: List[DiscoveredUrl] = []
    rejected: List[Dict[str, str]] = []
    for url, title, origin in citations:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            rejected.append({"url": url, "reason": "non_http_scheme"})
            continue
        if not host_in_allowlist(parts.hostname or "", allowed_domains):
            rejected.append({"url": url, "reason": "domain_not_in_allowlist"})
            continue
        kept.append(DiscoveredUrl(url=url, title=title, origin=origin))
    return tuple(kept), tuple(rejected)


# --------------------------------------------------------------------------- #
# The provider.
# --------------------------------------------------------------------------- #

class WebResearchProvider:
    """Responses API + web_search, constructed ONLY behind both airlocks.

    Construction enforces the standard live authorization (``--live``,
    ``--confirm-spend``, explicit provider/model, credential present). The
    SPEND authorization is enforced separately by the caller via
    ``require_web_research_spend_authorization`` against a computed maximum --
    kept separate because the maximum depends on caps and pricing this class
    does not own.
    """

    name = "openai-web-research"

    def __init__(self, auth: LiveAuthorization, *,
                 base_url: str = "https://api.openai.com/v1",
                 tool_type: str = WEB_SEARCH_TOOL):
        self._api_key_env = require_live_authorization(auth)   # raises unless authorized
        if auth.model != APPROVED_MODEL:
            raise SpendingAirlockError(
                "web research may target only the approved model %r (got %r)"
                % (APPROVED_MODEL, auth.model))
        if tool_type not in ACCEPTED_WEB_SEARCH_TOOLS:
            raise SpendingAirlockError("unsupported web search tool type: %r" % tool_type)
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._tool_type = tool_type

    def build_request_body(self, *, listing_name: str, address: str, city: str, state: str,
                           allowed_domains: Sequence[str], caps: WebResearchCaps) -> Dict:
        """The exact JSON body. Pure and deterministic -- tests assert on it
        without any network, which is how the bounds are verified rather than
        assumed."""
        caps.validate()
        if not allowed_domains:
            raise SpendingAirlockError(
                "web research requires a non-empty official-domain allowlist "
                "(an unrestricted web search is not an approved path)")
        instructions, user_input = build_research_prompt(
            listing_name, address, city, state, allowed_domains)
        return {
            "model": APPROVED_MODEL,
            "instructions": instructions,
            "input": user_input,
            "tools": [{
                "type": self._tool_type,
                "search_context_size": caps.search_context_size,
                "filters": {"allowed_domains": list(allowed_domains)},
            }],
            "tool_choice": "auto",
            "max_tool_calls": int(caps.max_tool_calls),
            "max_output_tokens": int(caps.max_output_tokens),
            "reasoning": {"effort": caps.reasoning_effort},
            "include": ["web_search_call.action.sources"],
            "truncation": "auto",
            "store": False,
        }

    def research(self, *, listing_key: str, listing_name: str, address: str, city: str,
                 state: str, allowed_domains: Sequence[str], caps: WebResearchCaps,
                 observed_at: str, post_json=None) -> WebResearchReport:
        """Run ONE research call. ``post_json`` is injectable so every test
        exercises this exact code path offline."""
        import os

        body = self.build_request_body(
            listing_name=listing_name, address=address, city=city, state=state,
            allowed_domains=allowed_domains, caps=caps)
        key = os.environ[self._api_key_env]          # read at call time only
        headers = {"Authorization": "Bearer %s" % key, "Content-Type": "application/json"}

        if post_json is None:
            from services.research_workers.providers import _post_json as post_json  # noqa: PLC0415

        import json as _json
        data = _json.dumps(body).encode("utf-8")
        url = self._base_url + "/responses"

        detail: Optional[ProviderErrorDetail] = None
        attempts = 0
        for _ in range(max(1, caps.max_retries + 1)):
            attempts += 1
            try:
                payload, latency_ms, rid = post_json(url, data, headers, caps.timeout_s)
            except Exception as exc:              # noqa: BLE001 -- classified, never swallowed
                detail = classify_provider_error(exc, attempts)
                if not detail.transient:
                    break
                continue

            text = extract_report_text(payload)
            citations = extract_tool_citations(payload)
            kept, rejected = partition_citations(citations, allowed_domains)
            inp, out, cached = extract_usage(payload)
            return WebResearchReport(
                listing_key=listing_key, listing_name=listing_name, ok=True,
                model=str(payload.get("model") or APPROVED_MODEL),
                allowed_domains=tuple(allowed_domains), report_text=text,
                discovered_urls=kept, rejected_urls=rejected,
                usage=WebResearchUsage(
                    input_tokens=inp, output_tokens=out, cached_input_tokens=cached,
                    search_calls=count_search_calls(payload), latency_ms=latency_ms),
                observed_at=observed_at, request_id=rid or "", http_status=200,
                response_status=str(payload.get("status") or ""),
                incomplete_reason=str((payload.get("incomplete_details") or {}).get("reason") or ""))

        slug = (detail.error_code or detail.error_type
                or ("http_%d" % detail.http_status)) if detail else "unknown"
        return WebResearchReport(
            listing_key=listing_key, listing_name=listing_name, ok=False,
            model=APPROVED_MODEL, allowed_domains=tuple(allowed_domains),
            error="provider_error:%s" % slug, provider_error=detail,
            observed_at=observed_at,
            request_id=(detail.request_id if detail else ""),
            http_status=(detail.http_status if detail else 0))


def build_web_research_provider(auth: LiveAuthorization, *, caps: WebResearchCaps,
                                pricing: WebResearchPricing,
                                base_url: str = "https://api.openai.com/v1",
                                tool_type: str = WEB_SEARCH_TOOL
                                ) -> Tuple[WebResearchProvider, float]:
    """Full airlock: live authorization AND the $5 web-research spend gate,
    both cleared before a client exists. Returns (provider, exact max cost).

    The spend gate is checked against ``exact_max_cost_usd`` -- the worst case
    for these caps and prices, not an expected value.
    """
    max_cost = exact_max_cost_usd(caps, pricing)
    require_web_research_spend_authorization(max_cost)
    return WebResearchProvider(auth, base_url=base_url, tool_type=tool_type), max_cost
