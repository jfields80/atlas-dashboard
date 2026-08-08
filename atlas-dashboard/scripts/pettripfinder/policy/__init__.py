"""PTF-POLICY-P0-001 -- the policy observation layer.

The sibling of ``scripts/pettripfinder/discovery`` on the policy side of the
Membrane. Discovery answers "which hotel is this"; this package answers "what
did this source say about this hotel's pet policy, and exactly where did it
say it" -- and stops there.

Three layers, never conflated:

    observation  what a source said, with an exact quote  (this package)
    normalized   that observation mapped into the production vocabulary
    fact         the record the site may publish          (existing authority)

Nothing here can write a published fact. There is deliberately no function in
this package that opens ``hotel_policy_facts.json`` for writing, no promotion
path, and no call into the publication guard. An observation is evidence about
truth; it is not truth, and two observations that disagree are data rather
than an error.

Modules:

- ``policy_observation`` -- the ptf-policy-observation/1.0 contract
- ``policy_membrane``    -- M1..M12, the rules that keep weak evidence out
- ``readiness``          -- explicit readiness states + mapping to existing ones
- ``evidence_bundle``    -- ladder transcript / per-attempt evidence bundle
- ``worker_bridge``      -- read-only bridge from the existing capture worker
- ``adapters.drury``     -- deterministic Drury observation adapter
- ``pilots.sonesta``     -- bounded 10-property pilot framework (not run here)
"""
