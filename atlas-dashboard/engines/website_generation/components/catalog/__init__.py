"""Component catalog — ComponentDefinition data, one module per family.

AES-WEB-002 §29.1: the catalog holds declarative ``ComponentDefinition``
data (one module per family), importing only ``contracts/`` and
``constants/``. AES-WEB-002A ships the empty-but-governed catalog: no family
modules and no component definitions exist yet — they are authored per wave
(Wave 1 layout/atom primitives arrive in AES-WEB-002B). The registry's
``REGISTERED_COMPONENTS`` tuple is therefore empty at 002A exit.
"""
