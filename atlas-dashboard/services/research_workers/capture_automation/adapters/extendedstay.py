"""Extended Stay America.

PROVISIONAL, and deliberately empty of brand-specific tuning -- the same
reasoning as redroof.py: no Extended Stay America page has ever reached this package, because
the registry refused the brand before navigation. There is nothing measured to
encode, and a selector written from memory is the half-tuned adapter the
registry docstring warns about.

This class asserts only that the brand may be ATTEMPTED, under the core anchors
and the core policy locator with no narrowing. BaseAdapter composes
core-and-adapter with AND, so an adapter that adds nothing cannot weaken a gate.
If the core cannot find the policy the worker reports POLICY_NOT_FOUND, which is
a true statement about this brand and the evidence a real adapter is built from.
"""

from __future__ import annotations

from .base import BaseAdapter


class ExtendedStayAdapter(BaseAdapter):
    brand = "extendedstay"
