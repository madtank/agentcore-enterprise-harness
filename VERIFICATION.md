# Verification and setup state

Completed locally on 2 October 2026.

The documentation and upstream hash checks below were run against the complete downloaded research archive. This public repository contains the authored deliverables, source manifests, and pinned retrieval inventory; it does not check in the full AWS corpus or upstream source. A fresh clone can run the client tests and template checks below independently of those downloads.

| Check | Result |
| --- | --- |
| Official guide download | 577/577 linked pages downloaded; SHA-256 and byte counts verified |
| Supplemental references | 6/6 raw pages downloaded and verified; pricing page retained as HTML |
| Complete official PDF | Valid PDF; 3,562 pages; raw hash matches the download manifest |
| Upstream example snapshot | 304 selected source/license files at an immutable commit; hashes verified |
| Local request-boundary tests | 15 tests passed; no live AWS calls |
| Current SDK support | boto3/botocore 1.43.107 include harness and independent Registry APIs |
| Template validation | Harness, lifecycle hooks, Registry creation and SKILL-record payload shapes pass local SDK validation |
| Local request preparation | Produces bounded text-only InvokeHarness request and bound UUID session |
| Architecture PDF | 14 pages; required sections present; first page and architecture page visually inspected |
| Report formats | Markdown, printable PDF, self-contained HTML, simplified SVG and full Mermaid source |

The local virtual environment is installed in `.venv/`; runtime dependencies are pinned in `requirements.lock.txt`. Report/verification dependencies are pinned in `requirements-render.lock.txt`. Virtual environments and ephemeral SQLite state are excluded from downloadable archives.

The 15 tests cover request override rejection, non-text/tool-block rejection, session ownership across users/profiles, persisted resume, session format, bounded SDK-valid requests, broad/shell tool denial, production/write profile denial, raised/boolean limit rejection, unresolved/wrong-Region live ARNs, named endpoint requirements, omission of raw reasoning/tool payloads/metadata, withholding incomplete/inline-handoff output, and omission of raw service error payloads.

Local SDK validation checks structure, types and modeled constraints. It does not establish that IAM permissions, resource ARNs, approved models, tool names, policy semantics, skill loading or integrations will work in a real account. The Cedar template has not been validated by the live Policy service. No content/PII classification is implemented in the local client.

No AWS resources were created, modified or deleted. No upstream deployment/cleanup script or agent execution tool was run. No messages or notifications were sent through sample integrations. AWS deployment and end-to-end acceptance tasks are explicitly listed as remaining in `MVP-BACKLOG.md`.

To reproduce local checks:

```bash
.venv/bin/python starter/harness_client.py validate
.venv/bin/python -m unittest discover -s starter -v
.venv/bin/python scripts/verify_blueprints.py
```

To regenerate the report, install the rendering lockfile if needed:

```bash
.venv/bin/python -m pip install -r requirements-render.lock.txt
.venv/bin/python scripts/render_report.py
```

The PDF renderer uses the DejaVu fonts from `/usr/share/fonts/truetype/dejavu`; another environment may need those fonts installed or the paths adjusted.
