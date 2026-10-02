# Local development starter

This is a narrow application-boundary client for an **existing** AWS managed AgentCore harness. Create a local virtual environment from the repository root using the commands below. It validates requests offline, binds sessions to trusted local developer labels in SQLite, and can invoke a harness after AWS setup.

It is not a deployed enterprise application. It has no SSO, live retrieval adapter, content classifier, approval executor, or production audit ledger. The default profile supports only non-sensitive development data and rejects production/write-enabled profiles.

## Run locally

After installing dependencies, from the repository root:

```bash
.venv/bin/python starter/harness_client.py validate
.venv/bin/python -m unittest discover -s starter -v
.venv/bin/python starter/harness_client.py prepare --user alice --message "Summarize the development runbook and cite sources."
```

`validate` and `prepare` make **zero AWS calls**. `prepare` prints the bounded `InvokeHarness` request, including a newly generated session ID. Reuse that ID for the same user/profile using `--session-id`; another user cannot reuse it.

First install dependencies with Python 3.10+:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python starter/harness_client.py validate
.venv/bin/python -m unittest discover -s starter -v
```

`requirements.lock.txt` pins the runtime client dependencies validated for this snapshot. Report-rendering dependencies are recorded separately.

## Configure AWS after provisioning

1. Choose a dev AWS account and confirm the approved model route in `us-east-1` or another mutually supported Region.
2. Create the scoped execution/caller/Gateway roles and short-term Memory without long-term extraction strategies.
3. Set up the development knowledge source and authenticated Gateway targets. Capture the **actual** tool names from `tools/list`. The selectors in `profile.dev.json` are illustrative and must match those names.
4. Apply and validate the Gateway policy against its generated schema in `ENFORCE` mode. A read-only prompt cannot substitute for these permissions.
5. Publish the skill directories from `blueprints/skills/` into immutable S3 prefixes and create the harness from the substituted blueprint. Inspect `blueprints/README.md` for the required permission scopes and template boundaries.
6. Create a `DEV` harness endpoint targeting the reviewed harness version. Give the client the required invoke actions on the harness and endpoint, without shell/terminal or control-plane permissions.
7. Authenticate using the normal configured AWS SDK credential chain, and set `HARNESS_ARN` to the real resource. No secrets belong in the profile.

Example after resources exist:

```bash
export AWS_PROFILE=your-configured-dev-profile
export HARNESS_ARN=arn:aws:bedrock-agentcore:us-east-1:111122223333:harness/InternalKnowledgeOps-AbCdEf0123
.venv/bin/python starter/harness_client.py invoke --user alice --message "Summarize our development runbook and cite sources."
```

Replace the illustrative ARN/account/profile. `invoke` makes a real inference request and incurs normal AWS/model charges. It does not provision resources. It uses the configured fixed profile, buffers text, withholds incomplete runs, and omits raw tool results and model reasoning from CLI output. Buffering is preparation for a later content check; this starter does not classify or redact output.

The local `--user` label scopes conversation state only. It is trusted developer input, not a verified employee identity and not downstream OAuth delegation. All users of a shared dev service role must be allowed to access the entire pilot dataset. SQLite is local session state, not a distributed authorization store.

Inline functions are intentionally not handled by this starter. If a harness requests a handoff, it fails without executing an external action. Add an authenticated pending-action workflow before supporting those tools.

## Current AWS tooling

For resource scaffolding, prefer the current Node-based CLI: `@aws/agentcore`, Node.js 20+. The downloaded getting-started sample pins `0.30.0`; verify the version you choose and retain it in your project lockfile. The older Python starter toolkit also installs an `agentcore` command, so isolate it if maintaining legacy workflows.

The CLI's `agentcore dev` first deploys resources to AWS. Its name does not mean an entirely offline agent loop. The local `prepare`/`validate` path above is the offline setup in this package.

Use `EXAMPLES-REVIEW.md` to choose an upstream tutorial. None of its deployment, cleanup, user-creation, or notification scripts was run for this setup.
