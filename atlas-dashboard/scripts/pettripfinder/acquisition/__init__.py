"""Provider-neutral acquisition for PetTripFinder.

The three Bright Data pilots established what this package generalises: a
managed browser reaches most hotel property pages, one brand refuses it and
answers a different provider, and one brand keeps its policy in DOM the page
never paints. None of those facts is about Bright Data. They are facts about
ACQUISITION, and this package is where they live so that adding a provider is a
row in a registry rather than a rewrite.

WHAT THIS PACKAGE IS
--------------------
An orchestrator that, given a property, chooses an acquisition lane, runs it,
validates what came back, and returns exactly one final state. It owns the
choosing and the accounting. It owns none of the deciding:

    ROUTER -> EVIDENCE -> STRUCTURED PROPOSAL -> FOUNDER REVIEW -> AUTHORITY

The router never publishes, never promotes, and never writes a market
authority. Provider success is not evidence success, and this package keeps
those two words apart on purpose.

TWO AXES, DELIBERATELY UNCOUPLED
--------------------------------
A PROVIDER answers "how did we get the page". A READER answers "how do we
understand this page". Bright Data's browser serves Marriott and Wyndham with
different readers; a Choice reader will serve the Web Unlocker today and
anything else tomorrow. Coupling them would make every new provider a rewrite
of every reader.

Module map
----------
``failures``  the closed failure vocabulary, and which failures may escalate.
``envelope``  the normalised acquisition result -- the boundary between
              acquisition and interpretation.
``readers``   reader registry: how a page is understood.
``providers`` provider registry: how a page is fetched.
``registry``  brand/domain/property routes, data-driven and versioned.
``budget``    per-property ceilings on attempts, cost and time.
``journal``   durable per-property record, resume, idempotency, locking.
``router``    the orchestrator.
"""
