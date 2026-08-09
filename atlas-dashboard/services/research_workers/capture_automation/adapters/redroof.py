"""Red Roof.

PROVISIONAL, and deliberately empty of brand-specific tuning.

Red Roof is not in the retained corpus: no Red Roof page has ever reached this
package, because the registry refused the brand before navigation. So there is
nothing measured to encode here, and inventing selectors from memory is exactly
the "half-tuned adapter" the registry docstring warns produces a quiet stream of
low-confidence captures.

What this class asserts is therefore narrow and honest: Red Roof is permitted to
be *attempted*, using the core anchors and the core policy locator with no
narrowing at all. BaseAdapter composes core-and-adapter with AND, so an adapter
that adds nothing cannot weaken any gate -- it can only decline to sharpen one.
If the core cannot find the policy, the worker reports POLICY_NOT_FOUND, which
is a true statement about this brand rather than a guess dressed as one.

Any selector added here later must cite a capture that shows it.
"""

from __future__ import annotations

from .base import BaseAdapter


class RedRoofAdapter(BaseAdapter):
    brand = "redroof"
