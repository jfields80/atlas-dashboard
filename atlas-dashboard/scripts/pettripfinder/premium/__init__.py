"""PETTRIPFINDER-DESIGN-002 -- premium presentation layer.

A self-contained, deterministic set of full-page renderers + one shared design
system that replace the prototype-era base-bundle presentation with a
consumer-grade pet-travel marketplace look. This layer is pure presentation:

  * it invents no facts -- every hotel policy value comes from the committed
    launch package (via the caller), parks/restaurants use their real recorded
    ``pet_policy`` sentence, and an unstated field is always "Not stated by the
    reviewed source", never guessed;
  * it renders no real photography -- an intentional premium placeholder system
    (``media.py``) fills every media slot, with a view-model already shaped for a
    later Google Places media phase;
  * it never changes route structure, inclusion/exclusion, evidence links, or
    the committed policy package.

No network, no external font/asset dependency, no new frontend framework.
"""
