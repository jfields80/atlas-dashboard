"""Component bind-time validation (AES-WEB-002A skeleton; §29.1, §21.1).

Physical package skeleton authorized and created for AES-WEB-002A exit
(AES-WEB-002 §31 "New files"). The production bind-time semantic validators
(``binding_validators.py``, sourced from the §21.1 contract gates that run at
Component Engine bind time) are a later wave and are deliberately NOT
implemented here — 002A adds no production validation behavior. Registration-
time definition validation (naming grammar, complexity budget, compatibility
axes, lifecycle rules) already lives in ``components/registry.py`` per §15.2.
"""
