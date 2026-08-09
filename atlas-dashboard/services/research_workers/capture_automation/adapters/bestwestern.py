"""Best Western.

PROVISIONAL. See redroof.py -- the same reasoning applies verbatim: no Best
Western page is in the retained corpus, so this adapter narrows nothing and
exists only to let the brand be attempted at all under the core locator.
"""

from __future__ import annotations

from .base import BaseAdapter


class BestWesternAdapter(BaseAdapter):
    brand = "bestwestern"
