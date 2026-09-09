# ATLAS-THROUGHPUT-006 — CI policy

**Provider: GitHub Actions**, `.github/workflows/ptf-broad-validation.yml`, `workflow_dispatch` only.
The repository's only remote is GitHub and it had no CI configuration of any kind. The workflow is committed
and complete; it was **not executed**, because the GitHub CLI is absent here and no API token is available, so
neither Actions' availability nor its billing could be established from this checkout. Dispatching a run would
be provisioning infrastructure without authorisation. **REMOTE_EXECUTION_NOT_PROVEN.**

The point of the policy is what does NOT run:

| release surface | scope | why |
|---|---|---|
| SHARED_SCHEMA_CHANGE | ALL | a schema is read by every market and every renderer |
| SHARED_RUNTIME_CHANGE | ALL | shared runtime is what eleven markets derive from |
| ASSEMBLER_CHANGE | ALL | the assembler composes every market's bytes, and the modules that prove per-market output are spread across every shard by the duration balance |
| DEPLOYMENT_CHANGE | DEPLOYMENT | manifests, participation, authorizations and records: only the shards holding deployment-architecture modules |
| CLASSIFIER_TEST_INFRA_CHANGE | ALL | the classifier decides what runs, so it cannot narrow its own validation |

A proven data-only market authority change requests **zero** remote jobs. A remote runner that executes 17,000
tests on every release is the old waste with a bigger bill.

No acquisition provider is reachable from CI and none may be called: no Firecrawl, no Bright Data, no browser
research, no paid provider of any kind.
