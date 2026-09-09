"""PetTripFinder demo-media: the DETERMINISM claim (AES-WEB-002M.3 F).

ATLAS-THROUGHPUT-007 moved this claim into its own module. It is the one
demo-media claim that genuinely needs TWO independent executions of the real
chain, so it cannot share a fixture with the consumer assertions and must not
be memoised: comparing a build against itself proves nothing.

The pair is built ONCE for the module and both assertions read it. That is not
a weakening -- the claim is about two independent executions, and there are
two. Running the pair per assertion would simply buy a third and fourth
execution that assert the same thing.

Measured cost: about 265 s per execution, 530 s for the pair, and that pair is
the module's irreducible floor. It is separated so the OTHER demo-media claims,
which all read one artifact, are no longer trapped behind it: before 007 a
single module ran the chain five times for 1,375.7 s and set the floor under
every sharded remote run.

The defect this catches: a generator that embeds a timestamp, a dict iteration
order, a temp path or any other run-varying value in the published bytes. That
would make every downstream identity claim -- the 004 bundle cache key, the 005
candidate digest, the 006 artifact handoff -- meaningless, because two builds of
the same inputs would no longer be the same artifact.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pettripfinder_demo_chain import real_chain  # noqa: E402


@pytest.fixture(scope="module")
def independent_pair(tmp_path_factory):
    """Two genuinely independent cold executions of the real chain.

    Separate roots, separate content-addressed stores, no cache between them.
    """
    root = tmp_path_factory.mktemp("demo_media_determinism")
    first = real_chain(root / "a", with_media=True)
    second = real_chain(root / "b", with_media=True)
    return first, second, root


class TestDeterminism:
    def test_repeated_real_build_identical(self, independent_pair):
        (_, rendered_a, bundle_a, _), (_, rendered_b, bundle_b, _), _root = independent_pair
        assert bundle_a.bundle_hash == bundle_b.bundle_hash
        assert bundle_a.assets == bundle_b.assets
        for pa, pb in zip(rendered_a.page_details, rendered_b.page_details):
            assert pa.html == pb.html

    def test_the_two_builds_were_genuinely_independent(self, independent_pair):
        """The claim above is only worth its cost if the two executions really
        were separate. They write to different content-addressed stores, so a
        memoised second 'build' would leave the second store empty."""
        (_, _, bundle_a, cas_a), (_, _, bundle_b, cas_b), root = independent_pair
        assert (root / "a" / "cas").is_dir() and (root / "b" / "cas").is_dir()
        assert cas_a is not cas_b
        assert bundle_a.assets, "the with-media chain must produce assets to compare"
        for asset in bundle_a.assets:
            assert cas_a.get_bytes(asset.asset_hash) == cas_b.get_bytes(asset.asset_hash)
