# Blueprint boundaries

These are reviewable templates, not provisioned AWS resources.

- `create-harness.example.json` follows the current `CreateHarness` request shape. Replace every `${...}` reference and validate actual account/Region permissions before using it. It deliberately uses a fixed Bedrock model, Gateway, S3 skills, explicit tools, and BYO short-term Memory.
- `hooks.example.json` follows current lifecycle-hook shapes. Implement and deploy the validator Lambdas first, grant exact invoke permissions, then attach hooks. They are not included in the base creation payload.
- `read-only-policy.example.cedar` is a Cedar authorization template for an IAM-authenticated Gateway. Substitute the stable principal ID, Gateway ARN and generated action names; validate with the Policy authoring/validation APIs. It does not perform document ACL checks or inspect the draft's business semantics.
- `registry-metadata-schema.json` uses the documented restricted flat schema. Pass it as a serialized JSON string in `customMetadataSchemaConfiguration.defaultSchema` when creating a Registry. Do not add `$schema`, nested fields or unsupported field-level keywords.
- `create-registry.example.json` includes IAM discovery, manual review and that serialized metadata schema. `create-skill-record.example.json` demonstrates the current SKILL descriptor and serialized custom metadata; replace its registry/artifact references before publishing.
- `release-lock.example.json` is an application contract, not an AWS API request. CI resolves every placeholder and verifies digests/approved revisions before promotion.
- `skills/` contains two instruction-only AgentSkills examples. Skill loading/helper-tool access must be verified with the actual managed harness; do not broaden the built-in allowlist without reviewing the need.

Permission responsibilities:

| Role | Intended scope |
| --- | --- |
| Deployment | Create/update explicit dev resources; tightly scoped iam:PassRole; separate from the runtime caller |
| Harness execution | Chosen model routes, exact Gateway, Memory, skills prefix, image pull and required telemetry |
| Gateway service | Exact retrieval/business targets and configured credential providers |
| Application caller | Invoke selected harness/endpoint plus required underlying runtime invoke permission |
| Registry publisher | Create/edit records and submit; cannot self-approve |
| Registry curator | Review/approve/reject/deprecate scoped records |
| Registry consumer | Approved discovery only; no publishing or curation |

Do not copy the official documentation's broad sample execution role unchanged. Some AWS operations require resource `*`; separate them from resource-scoped actions and add supported conditions. Check service trust policies and confused-deputy protection against current documentation.

Live checks still required: actual action/tool names, all necessary role permissions, skill loader behavior with shell excluded, policy schema validation, source authorization, limits, lifecycle hooks and endpoint rollout behavior.
