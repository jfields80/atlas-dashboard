"""The adapter contract.

Adapters are **pure functions of a DomSnapshot**. They return plans; they never
drive the browser. That is the single decision that makes the rest of this
package testable against saved DOMs with no Chrome anywhere, and it is not
negotiable for a Phase 2 brand either.

An adapter may NARROW: supply a better selector, add a brand-specific anchor,
know that Hilton states its policy in a notation carrying no anchor phrase.
An adapter may not WIDEN: ``BaseAdapter`` composes core-and-adapter with AND,
so no brand can lower a gate the core applies.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from ..contracts import DomSnapshot, InteractionStep, ObservedIdentity, PolicyLocation
from ..identity_check import observe_identity
from ..policy_locator import locate_policy

try:                                    # Protocol is 3.8+; the repo targets 3.11
    from typing import Protocol, runtime_checkable
except ImportError:                     # pragma: no cover - defensive only
    Protocol = object                   # type: ignore

    def runtime_checkable(cls):         # type: ignore
        return cls


@runtime_checkable
class BrandAdapter(Protocol):
    """What the runner requires of a brand."""

    brand: str

    def url_is_property_page(self, url: str) -> bool: ...

    def extract_identity(self, dom: DomSnapshot,
                         known_codes: Sequence[str] = ()) -> ObservedIdentity: ...

    def locate_policy(self, dom: DomSnapshot) -> Optional[PolicyLocation]: ...

    def interaction_plan(self, dom: DomSnapshot,
                         location: Optional[PolicyLocation]) -> Tuple[InteractionStep, ...]: ...

    def consent_selectors(self) -> Tuple[str, ...]: ...

    def policy_container_selectors(self) -> Tuple[str, ...]: ...


class BaseAdapter:
    """Brand-neutral behaviour. Subclasses override the narrow parts only."""

    brand = "generic"

    #: Extra phrases this brand uses that the core anchor list does not carry.
    extra_anchors: Tuple[str, ...] = ()

    #: Selectors likely to contain the policy, best first. Used to scroll and
    #: to give the screenshot something to aim at.
    container_selectors: Tuple[str, ...] = ()

    #: Controls worth clicking to reveal a collapsed policy, by selector.
    expand_selectors: Tuple[str, ...] = ()

    #: Controls identified by their LABEL rather than a stable id, as
    #: ``(selector, label)``. Needed where a brand's tab index varies by
    #: property but its wording does not.
    expand_text_controls: Tuple[Tuple[str, str], ...] = ()

    def url_is_property_page(self, url: str) -> bool:
        from ...source_retrieval import URL_SHAPE_PROPERTY, classify_url_shape
        return classify_url_shape(url) == URL_SHAPE_PROPERTY

    def extract_identity(self, dom: DomSnapshot,
                         known_codes: Sequence[str] = ()) -> ObservedIdentity:
        return observe_identity(dom, known_codes=known_codes)

    def locate_policy(self, dom: DomSnapshot) -> Optional[PolicyLocation]:
        selector = self.container_selectors[0] if self.container_selectors else ""
        return locate_policy(dom, extra_anchors=self.extra_anchors, selector=selector)

    def interaction_plan(self, dom: DomSnapshot,
                         location: Optional[PolicyLocation]) -> Tuple[InteractionStep, ...]:
        """Phase 1 is deliberately thin: click the brand's known expanders if
        they are present, then scroll the policy into view. The accordion
        library is Phase 2 and this returns nothing clever until then."""
        steps: list = []
        html = dom.html or ""
        for sel in self.expand_selectors:
            # Only propose a click for something the page actually contains.
            token = sel.split("[")[0].lstrip(".#") or sel
            if token and token in html:
                steps.append(InteractionStep(
                    action="click", selector=sel,
                    reason="expand_policy_section", optional=True))
        for sel, label in self.expand_text_controls:
            if label in html:
                steps.append(InteractionStep(
                    action="click_text", selector=sel, text=label,
                    reason="reveal_policy_panel", optional=True))
        if location is not None and location.selector:
            steps.append(InteractionStep(
                action="scroll_into_view", selector=location.selector,
                reason="bring_policy_into_viewport", optional=False))
        return tuple(steps)

    def consent_selectors(self) -> Tuple[str, ...]:
        """Phase 1 never dismisses a consent banner -- the operator ruled it an
        exception. Returning empty is that ruling, in code."""
        return ()

    def policy_container_selectors(self) -> Tuple[str, ...]:
        return self.container_selectors
