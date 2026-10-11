# Registry Runtime Discovery — Design Addendum

**Status:** Draft for review
**Extends:** `ENTERPRISE-HARNESS-PLAN.md` — this addendum does not replace the release-time
profile/release-lock model. It adds a *runtime* discovery path that operates inside the
envelope that model defines.
**Companion artifacts:** `blueprints/` (registry + SKILL record examples), `CONTROL-MATRIX.csv`
(C15–C18), `MVP-BACKLOG.md` (D04), `EXAMPLES-REVIEW.md` (sample dispositions).

---

## 1. Decision summary

The agent does **not** start with every tool descriptor and skill attached, and users do
**not** pick and attach capabilities per task. Instead:

1. The agent boots with a minimal context: the harness built-ins, a small set of
   **meta-tools** for discovery, and lightweight metadata cards (~100 tokens each) for the
   skills in its profile.
2. Per task, the agent **searches the AWS Agent Registry** (`SearchDiscoverableRegistryRecords`,
   or the Registry MCP endpoint) for approved capabilities matching the task.
3. It **activates only what it needs, only within its profile envelope**:
   - **Skills** are resolved to *our own* immutable, digest-pinned S3 artifacts and passed
     as an `InvokeHarness` skills override.
   - **MCP servers** are reached *only* through the pre-built AgentCore Gateway — never by
     connecting to a URL taken from a record descriptor.
4. Enforcement never depends on the catalog. The Registry governs **discovery**; IAM,
   Gateway + Cedar policy, `allowedTools`, and the execution role govern **execution**.

The release pipeline still decides what *may* be activated (approved records, pinned
artifact digests, the profile envelope). Runtime discovery decides what *is* activated for
this task. Release-time pinning and runtime discovery compose; neither replaces the other.

## 2. Why: context economics

Tool schemas are paid on **every model request in the loop**, not once per session. The
harness's two built-in tools alone cost ~900 input tokens per request. Skills, by
contrast, use progressive disclosure: ~100 tokens of metadata per skill up front, full
instructions loaded on demand — 100 skills ≈ 10k metadata tokens, versus an order of
magnitude more for 100 tool schemas.

Anthropic's published measurements for deferred tool loading (Nov 2025) make the same
point at MCP scale: a 58-tool library (~55k tokens of definitions) dropped to ~8.7k tokens
in their worked example — an ~85% reduction — and tool-selection accuracy *improved*
(Opus 4: 49% → 74%; Opus 4.5: 79.5% → 88.1%). Pre-loading everything is not just wasteful;
past ~10 tools / ~10k tool tokens it actively degrades selection quality.

## 3. Fit with the existing architecture

| Existing component | Role under runtime discovery |
|---|---|
| AWS Agent Registry (D04) | Discovery source of truth. Discovery APIs return **APPROVED revisions only**, so runtime search can only ever surface curated records. |
| Profile resolver / release pipeline | Becomes the **envelope**: the set of records, artifact digests, and Gateway targets a profile may activate. Still runs at release time. |
| Release lock (`release-lock.example.json`) | The activation pins. The runtime resolver may only resolve a record to the S3 URI + sha256 recorded here (or in the record's metadata, §5). |
| Git + immutable S3 skill artifacts | The **only** skill delivery channel. Registry records point at governance metadata; bytes come from S3 (§4.1). |
| AgentCore Gateway | The **only** path to MCP tools. Discovered MCP records resolve to pre-governed Gateway targets (§4.2). |
| Cedar policy (blueprints) | List-filtering + call-time enforcement on the Gateway; the revocation kill switch (§7). |
| **New: runtime resolver** | Small component in the application backend: takes discovered record IDs, checks them against the envelope/release lock, verifies digests, and produces the `InvokeHarness` overrides. This is the one genuinely new component this addendum introduces. |

What changes relative to the base plan: skills move from *profile-fixed* to
*profile-bounded, per-invocation*. `CreateHarness` defaults remain the baseline profile;
`InvokeHarness` overrides (appended after create-time config; on a name clash the
invoke-time version wins) do the per-task tailoring. Tools, skills, model, and limits are
all overridable per invocation, so no harness rebuild is needed per task shape.

## 4. Runtime flow

Per request (or per session where noted):

1. **Boot context.** Harness built-ins (`shell`, `file_operations`), the three Registry
   discovery tools (via the Registry MCP endpoint: `search_…`, `list_…`, `batch_get_…` —
   discovery only; the endpoint never proxies discovered tools), and skill metadata cards
   for the profile. Nothing else.
2. **Search.** Agent calls `SearchDiscoverableRegistryRecords` with a short
   natural-language query (≤256 chars) plus a structured `recordType` filter. One registry
   per call; max 20 results; discovery APIs are throttled at **10 TPS account-wide** —
   cache results per task type and back off; do not search in a tight loop.
3. **Shortlist.** `BatchGetDiscoverableRegistryRecord` fetches full descriptors for the
   shortlist (authorised via the `GetDiscoverableRegistryRecord` IAM action).
4. **Resolve (envelope check).** The runtime resolver verifies each candidate against the
   profile envelope and release lock: record approved, `name`+`recordVersion` pinned,
   artifact digest matches. Anything outside the envelope is not activatable, however
   relevant it looks.
5. **Activate.** Skills → S3 source override on the next `InvokeHarness` (§4.1).
   MCP → confirm the corresponding Gateway target exists and is in the profile; scope the
   invocation with `allowedTools` (`@server/tool` globs) so only the discovered tools
   enter the model's context (§4.2).
6. **Execute.** All tool calls flow through the Gateway, where Cedar policy and
   interceptors apply. The Registry plays no further role.

### 4.1 Skill activation

- There is **no native Registry skill source** in the harness and the Registry **does not
  store skill files** (SKILL.md is discovery metadata only). The translation
  record → `{s3: {uri}}` is our code (the resolver), following the AWS governed-platform
  pattern: Registry = governance source of truth, S3 = artifact store.
- The artifact is the CI-published, immutable, versioned object for the *approved
  revision* — never the repository URL from the record. The resolver verifies the sha256
  (§5) before activation.
- Skills are fetched **once per session** and persist on the session filesystem; a changed
  skills configuration is picked up on a new invocation, and removed skills are a session
  concern (see revocation, §7). Execution happens inside the harness microVM — never on an
  operator workstation.
- Git-source skills are disabled for production profiles at the execution-role/network
  layer; S3 (execution-role `s3:GetObject`+`s3:ListBucket` scoped to the skills prefix,
  VPC endpoint, ≤1 GB/skill) is the only channel.

### 4.2 MCP activation

- One Gateway fronts all MCP servers into a single `tools/list`, tools namespaced
  `targetName___toolName`. Discovered MCP records resolve to **pre-built targets** —
  govern the endpoint first, register it second, discover it third. The agent never
  instantiates a client against a descriptor URL.
- Selective exposure, three layers: target configuration (`toolFilters`/`toolOverrides`
  where supported), Cedar list-filtering (`PartiallyAuthorizeActions` removes denied tools
  from `tools/list` entirely — invisible to the model, and a token saving), and
  per-invocation `allowedTools`.
- For very large catalogs, a Gateway created with `searchType = SEMANTIC` exposes the
  built-in `x_amz_bedrock_agentcore_search` tool (25 search TPM — cache per task type).
  This is a **creation-time** decision; assume it cannot be retrofitted.
- Listing-mode caution: *default* listing serves from a cache refreshed on target
  create/update or `SynchronizeGatewayTargets` (revocation impact, §7); *dynamic* listing
  forwards live under the caller's identity but cannot use semantic search.

## 5. Record and metadata conventions

- Pin consumers to **`name` + `recordVersion`**, never name alone. Editing an APPROVED
  record creates a new DRAFT revision while the approved revision stays discoverable;
  discovery flips only when the new revision is approved.
- The AgentSkills schema (v0.1.0) has **no integrity/digest field**. Carry `artifactUri`
  and `artifactDigest` in the record's custom metadata (consistent with
  `blueprints/registry-metadata-schema.json`) and mirror them in the release lock. The
  resolver treats descriptor content as a *hint* and the lock as the *pin*.
- Custom-metadata limits are **not published** by AWS — keep metadata flat and small, and
  treat any third-party number as unverified (Open Questions, §9).
- URL-synced records create new revisions; in manual-approval registries a synced revision
  is *unreviewed until approved*. Never enable auto-approval outside isolated dev accounts.

## 6. Security controls

Discovery moves trust from build time to data fetched at run time (record metadata,
SKILL.md text, descriptor schemas). These controls re-establish build-time-grade trust;
they extend `CONTROL-MATRIX.csv` rather than replacing it.

| Control | Where it lives | Maps to |
|---|---|---|
| Approved-only discovery; publisher/curator role split; manual approval in prod | Registry config + IAM | C16 |
| Metadata compliance gate before promotion (incl. digest present) | Release resolver / approval pipeline | C17 |
| Least-privilege discovery consumer: 4 data-plane actions (`Search…`, `List…`, `Get…` — covers BatchGet — plus `InvokeRegistryMcp`) scoped to one registry ARN | Execution role | C16 |
| Digest verification at activation; S3-only skill channel; immutable versioned keys | Runtime resolver + CI | C15 |
| MCP only via Gateway; Cedar ENFORCE (roll out LOG_ONLY → ENFORCE); input conditions on sensitive tools | Gateway + Policy engine | C18 |
| Per-invocation `allowedTools` scoping to discovered tools only | Application backend | new |
| Skill/MCP content scanning in the approval pipeline (the AWS admin-approval sample scans **A2A records only** — MCP schemas and CUSTOM payloads are unscanned there; we extend it) | Approval workflow (EventBridge `aws.agent-registry`) | C16/C17 |
| Code execution only inside harness/Runtime microVM or Code Interpreter, SANDBOX/VPC networking, never PUBLIC | Harness config | C15 |

Deliberately **not** adopted from the AWS samples:

- The dynamic-discovery sample's loader (download from the record's GitHub repo, install
  PyPI dependencies with ambient credentials, execute on the local host). We keep its
  *shape* (search → load → execute) and replace the loader wholesale.
- Direct `remote_mcp` connections to descriptor URLs (bypasses Gateway/Cedar).
- The runtime-discovery sample's IAM policy (`bedrock-agentcore:*` on `*`). Derive from
  the four-action consumer grant instead.
- Strands hot-reload / directory auto-loading of tools in production (Strands' own
  production guidance: keep disabled, specify tools explicitly).

## 7. Revocation runbook

Rejecting or deprecating a record stops **new discovery only**. The Registry does not
proxy calls, hold MCP connections, or store skill files, so it cannot terminate a running
agent — and three caches compound this: the discovery search index (the AWS sample waits
100 s after approval for indexing; assume a symmetric window on revoke until measured),
the Gateway default-listing cache, and per-session materialised skills.

Revocation is therefore three steps, in order:

1. **Catalog:** `UpdateRegistryRecordStatus` → REJECTED (temporary hide; reversible) or
   DEPRECATED (terminal).
2. **Execution boundary (the actual kill switch):** remove/disable the Gateway target or
   add a Cedar `forbid`; revoke the credential grant / allowed target in the backend.
3. **Artifacts & sessions:** overwrite/revoke the S3 artifact version; stop or expire
   affected sessions (skills already materialised persist for the session's life).

Step 2 must not wait for search indexing. Drill this runbook and *measure* the discovery
APIs' revocation latency (Open Questions, §9) — it is currently undocumented.

## 8. Proposed backlog additions

For `MVP-BACKLOG.md` (follow-up PR; IDs continue the D-series):

- **R01** Runtime resolver component: envelope check + digest verification producing
  `InvokeHarness` overrides. Depends on D04.
- **R02** Wire the Registry MCP endpoint as the agent's discovery surface in the starter;
  verify the starter's existing `SearchDiscoverableRegistryRecords` validation against the
  GA `agent-registry` namespace (preview `bedrock-agentcore` namespace is discontinued
  **30 Oct 2026**).
- **R03** Gateway decision record: default vs dynamic listing, and whether a separate
  SEMANTIC-search Gateway is warranted.
- **R04** Revocation drill: measure per-API revocation latency and running-session effect;
  record results in `VERIFICATION.md`.
- **R05** Extend the approval-workflow scanning to MCP tool schemas and CUSTOM payloads
  (prompt-injection / schema scan), closing the A2A-only gap in the AWS sample.

## 9. Open questions (live-account tests only)

Condensed from the research report; none of these are answerable from public docs.

1. Measured revocation latency per discovery API, and effect on live harness sessions /
   connected MCP clients.
2. Custom metadata size limits and whether custom fields are filterable via the discovery
   `filters` JSON.
3. Whether the discovery authoriser type (IAM vs JWT) is truly immutable after
   `CreateRegistry`.
4. Harness caps: max skills/tools per invocation; per-tool token overhead; whether a
   changed skills list *evicts* removed skills from the session filesystem.
5. Gateway semantic search: creation-lock confirmation; whether Cedar filtering applies to
   search results as it does to `tools/list`.
6. Whether Anthropic `defer_loading` / Tool Search is honoured via Bedrock Converse for
   our models/Region, or deferral must stay client-side (Registry/Gateway filtering).
7. Cedar schema growth against the 400 KB/engine cap with the real tool catalog;
   `PartiallyAuthorizeActions` latency at scale.

## 10. Sources

- AWS Bedrock AgentCore Developer Guide (accessed 2026-10-11): `registry-concepts`,
  `registry-record-lifecycle`, `registry-supported-record-types`, `registry-iam-permissions`,
  `registry-faq`, `registry-key-capabilities`, `registry-mcp-endpoint`,
  `bedrock-agentcore-limits`, `harness`, `harness-skills`, `harness-tools`, `gateway`,
  `policy`. AgentRegistry Data Plane API (2025-12-01).
- AWS ML Blog: *Amazon Bedrock AgentCore harness is now generally available* (Jun 2026);
  *Extending MCP support for Amazon Bedrock AgentCore Gateway* (19 May 2026);
  *Manage agents, tools and skills at scale with AWS Agent Registry* (~Sep 2026).
- Official samples (`awslabs/agentcore-samples`, verified 2026-10-11):
  `01-features/07-centralize-and-govern-your-ai-infrastructure/03-registry/` —
  `01-registry-end-to-end`, `03-advanced/admin-approval-workflow`,
  `03-advanced/registry-skills-dynamic-discovery`,
  `03-advanced/discovery-and-invocation-at-runtime`,
  `03-advanced/strands-mcp-ecs-registry`.
- Anthropic, *Introducing advanced tool use on the Claude Developer Platform* (Nov 2025) —
  tool search / deferred loading measurements.
- aws-samples governed inference platform, ADR-0017 (Sep 2026) — Registry as governance,
  S3 as sha256-pinned artifact store.
- Full research report with per-claim citations: maintained alongside this addendum's
  working notes (AgentCore registry runtime-discovery research, 2026-10-11).
