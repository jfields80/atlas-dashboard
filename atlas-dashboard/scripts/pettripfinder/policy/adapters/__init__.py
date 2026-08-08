"""Deterministic policy-observation adapters.

An adapter here is a PURE FUNCTION of text a capture already produced. It
never navigates, never fetches, and never decides truth: it recognises the
shapes one brand actually uses to state a pet policy, quotes the sentence it
found verbatim, and names the fields that sentence supports.

The rule every adapter in this package obeys, without exception:

    A field may only be populated when the quote it points at states it.

No brand defaults. No "Drury usually charges $50". If the page does not say
it, the observation does not carry it -- an absent field renders honestly as
"Not stated" downstream, and that is a correct answer.
"""
