"""Choice Hotels (Cambria, Comfort Suites and siblings).

PROVISIONAL. See redroof.py -- no Choice page is in the retained corpus, so this
adapter narrows nothing and exists only to let the brand be attempted under the
core locator.
"""

from __future__ import annotations

from .base import BaseAdapter


class ChoiceAdapter(BaseAdapter):
    brand = "choice"
