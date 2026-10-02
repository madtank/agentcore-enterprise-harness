# MVP backlog

Scope: internal knowledge and business operations; non-sensitive development data; one managed harness; fixed tools and model. No AWS resources have been deployed. The local foundation is supplied and validated in this package.

| ID | Task | Depends on | Owner role | Acceptance evidence |
| --- | --- | --- | --- | --- |
| L01 | Download documentation and pinned example source | — | Platform | Source/hash manifests; offline documentation |
| L02 | Define architecture, profiles, and promotion controls | L01 | Platform / Security | Plan, control matrix, release contract |
| L03 | Validate local request boundary and SDK models | L02 | Application | Unit tests and no-network SDK validation pass |
| D01 | Select dev AWS account, Region, and approved model | L02 | Platform | Authorized account, correct model route and budget |
| D02 | Create deployment/caller/harness/Gateway roles | D01 | Platform / Security | Resource-scoped policies; no command/control permissions in normal caller |
| D03 | Provision short-term Memory without extraction strategies | D02 | Platform | Per-user/session events isolated; expiry and deletion demonstrated |
| D04 | Create development Registry on agent-registry namespace | D02 | Platform | IAM discovery; no automatic approval; publisher and curator roles |
| D05 | Prepare development knowledge corpus and ingest it | D01 | Data owner | Source IDs, versions and a reviewed ground-truth question set |
| D06 | Create authenticated Gateway and retrieval target | D02, D05 | Platform | IAM/JWT auth; actual tools/list names captured |
| D07 | Add narrow sandbox operations reads/draft preparation | D06 | Integration | Schema-valid outputs; no real business writes |
| D08 | Attach ENFORCE policy to actual Gateway schema | D06, D07 | Security | Allowed read/draft calls work; arbitrary calls denied |
| D09 | Publish reviewed skills to immutable S3 release prefixes | L02, D02 | Platform | Artifact digests; released paths cannot be overwritten |
| D10 | Create harness using explicit model/tools/memory/limits | D03, D08, D09 | Platform | READY; shell excluded; bounded invocation completes |
| D11 | Create named DEV endpoint and profile release lock | D10 | Platform | Endpoint targets recorded immutable version |
| D12 | Configure local client and verify live invocation | L03, D11 | Application | HARNESS_ARN set; selectors verified; source-backed answer |
| D13 | Publish records and approve reviewed revisions | D04, D11 | Curator | New namespace/schema; approved discovery verified with retry |
| D14 | Enable tracing, data-event audit, budgets and pilot dashboard | D10 | Operations | A run can be traced and its usage measured |
| D15 | Run 60-case pilot evaluation and review failure clusters | D12, D14 | Evaluation / Data owner | Deterministic access checks plus human/LLM quality scores |
| P01 | Add verified corporate user authentication | D15 | Application / Identity | Authenticated user-to-session binding; direct override bypass denied |
| P02 | Add real knowledge ACL context and cache/history revocation | P01 | Data / Integration | Cross-user, changed-ACL and deletion tests pass |
| P03 | Verify user-scoped credential delegation where required | P01 | Identity | OAuth/OBO scope behavior established end to end |
| P04 | Enforce content controls and final-output handling | P02 | Security / Application | Tool-content and output leakage adversarial suite passes |
| P05 | Add approved write executor if required | P03, P04 | Integration | Exact-payload approval, expiry, replay protection and receipts |
| P06 | Production account/network/keys/retention setup | D14, P02 | Platform / Security | Threat model and actual emitted telemetry reviewed |
| P07 | Introduce release gates and production Registry scope | D13, D15, P06 | Platform | Approved metadata compliance, artifact/schema locks, named endpoint |
| P08 | Exercise revoke, stop, rollback and restore | P05, P07 | Operations | Recorded drill with RTO/RPO and named responders |

Local tasks L01–L03 are complete. Tasks D01 onward require an AWS account and live resources. The supplied scripts do not silently deploy the upstream tutorials.

Suggested delivery sequence: D01–D03, then D04–D09 in work streams as staffing permits, then D10–D15. Promotion work starts only after a useful, measured pilot. Parallel work streams describe team planning; no delegated agents were used to produce this package.

Keep the first pilot small: 5–10 developers, a development corpus and sandbox operations data. Expand capabilities only after the profile's evaluation and authorization checks pass.
