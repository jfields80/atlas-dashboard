"""PTF-CONTRACT-FOUNDATION-001 -- the frozen PetTripFinder production contracts.

Phase A of the Ohio hardening program (PTF-OHIO-CONTRACT-FREEZE-001). Every
module here is a CONTRACT: a closed vocabulary, a validator, or a pure
derivation. Nothing in this package reads a network, writes a file, renders
HTML, or mutates committed authority.

Why the package exists
----------------------
Four markets each grew their own spelling of the same intent. Columbus writes
``per_room`` and Cleveland writes ``"per room"``; Columbus keeps withheld fees
in ``facts.fee_conflict`` and Dayton keeps them in a ``withheld_fields`` prose
map; ``weight_limit_operator`` holds ``lt``, ``lte`` AND ``combined``, which is
two type systems in one field. None of that was careless -- each market solved
the problem in front of it -- but a fact that means one thing in Dayton and
another in Columbus cannot be rendered, compared, or searched by shared code.

These modules define the one shape all four markets converge on, and the
compatibility readers that let today's records be read as that shape without
rewriting a single committed byte.

What Phase A deliberately does NOT do
-------------------------------------
No record is rewritten. No census or partition is created. No renderer, route,
market config or gate changes. The validators here are callable but no build
step calls them yet -- they are advisory in Phase A by construction, because
nothing invokes them. That sequencing is the point: the contract lands and is
proven against real data before anything starts depending on it.

Reading order
-------------
``enums``          the closed vocabularies everything else references
``identity_key``   the one identity normaliser (the join key for every layer)
``policy_schema``  the 1.2 facts block and its structural validator
``fee_computation``when a fee may safely be turned into a number
``withholding``    what "we are not publishing this" means and requires
``evidence``       what may back a published fact
``census``         market identity rosters
``partition``      the disposition of every identity, exactly once
``compat_readers`` today's 1.0/1.1 records, read as 1.2
"""
