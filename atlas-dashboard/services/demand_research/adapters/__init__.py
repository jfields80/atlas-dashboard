"""Per-project inventory adapters (AES-SEO-001 §7.1, §22.2).

This directory is the ONLY place in the Demand Mapping subsystem where
project or domain names may appear. Each adapter maps one project's source
data into the generic record form (`engines.demand_mapping.contracts.records`);
the generic engine never sees the project's vocabulary.
"""
