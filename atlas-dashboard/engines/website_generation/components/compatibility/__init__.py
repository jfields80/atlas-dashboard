"""Component compatibility-range evaluation (AES-WEB-002A skeleton; §29.1, §22).

Physical package skeleton authorized and created for AES-WEB-002A exit
(AES-WEB-002 §31 "New files"). The production compatibility-range evaluator
(``ranges.py`` — pure semver range logic consumed by the §14.2 compatibility
filter at selection time) is a later wave and is deliberately NOT implemented
here — 002A adds no production compatibility behavior. Registration-time
validation that ``compatibility_range`` declares only known axes already
lives in ``components/registry.py`` per §22.1/§15.2.
"""
