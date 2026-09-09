"""PetTripFinder demo-media: the ZERO-IMAGE FALLBACK claim (AES-WEB-002M.3 G).

ATLAS-THROUGHPUT-007 moved this claim into its own module. Its INPUT is
genuinely different -- the chain runs with no media manifest at all -- so it
cannot read the with-media fixture, and running it alongside the consumer
assertions simply chained one 265 s execution behind another.

The defect this catches: a generator that assumes media exists. A market with
no authorized imagery must still produce a complete, valid site with zero
``<img>`` tags and an empty asset set, not a broken page or a build failure.
Every market in the factory except the two demo illustrations is in exactly
that state, so this is the ordinary case rather than the edge case.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pettripfinder_demo_chain import IMG_TAG_RE, real_chain  # noqa: E402


@pytest.fixture(scope="module")
def no_media_chain(tmp_path_factory):
    """One real chain built with no media mapping."""
    root = tmp_path_factory.mktemp("demo_media_fallback")
    return real_chain(root, with_media=False)


class TestZeroImageFallback:
    def test_no_media_mapping_yields_zero_img(self, no_media_chain):
        dataset, rendered, bundle, _ = no_media_chain
        assert all(l.assets == () for l in dataset.listings)
        assert bundle.assets == ()
        for page in rendered.page_details:
            assert "<img" not in page.html

    def test_the_site_is_still_complete_without_media(self, no_media_chain):
        """Zero images must mean a text-only site, not a truncated one: the
        same pages, the same listings, just no imagery."""
        dataset, rendered, bundle, _ = no_media_chain
        assert dataset.listings, "the no-media chain still publishes every listing"
        assert rendered.page_details, "the no-media chain still renders every page"
        assert bundle.file_map, "the no-media chain still assembles a bundle"
        assert not any(IMG_TAG_RE.findall(p.html) for p in rendered.page_details)
