# Official source inventory

The research snapshot was downloaded on 2 October 2026 from public official AWS documentation and public official GitHub repositories. No private enterprise documents were used.

This public repository keeps source URLs, timestamps, byte counts, hashes, and pinned example references. The full downloaded AWS corpus and upstream source are excluded from Git history. `verification-results.json` records verification of the original research archive, not a claim that every downloaded artifact is present in a fresh clone.

| Inventory | Contents |
| --- | --- |
| `agentcore-toc.json` | Official guide table of contents captured for the research |
| `manifest.json` | 577 guide-page URLs, snapshot hashes, and original local paths |
| `initial-manifest.json` | Overview, TOC, and full official PDF URLs and hashes |
| `supplemental-manifest.json` | Three API references, Guardrails, Knowledge Bases, and pricing |
| `github/repository-manifest.json` | Five official repositories and reviewed commits |
| `github/example-manifest.json` | The 304 selected upstream source/license files and their hashes |
| `github/selected-prefixes.json` | Reviewed example groups |
| `github/sample-files.tree.json` | Selected-file tree used by the downloader; not the full upstream tree |
| `github/readme-manifest.json` | Provenance of the supporting repository README snapshots reviewed during research |

## Read or download the official documentation

- [AgentCore developer guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [Full official developer-guide PDF](https://docs.aws.amazon.com/pdfs/bedrock-agentcore/latest/devguide/bedrock-agentcore-dg.pdf)
- [Official sample repository at the reviewed commit](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/4cd43c71c642ce2428a39c6b025a73b686c74f8f)

To download the guide HTML pages and extract readable text:

```bash
python scripts/download_docs.py
```

This uses the saved TOC, downloads guide pages into git-ignored `sources/html/` and `sources/text/`, and **updates `sources/manifest.json`** with new timestamps and hashes. Review the manifest diff before committing a refreshed snapshot. The script does not download the full PDF or the six supplemental references; those URLs are recorded in their manifests. AWS's `latest` URLs can change, so this is a fresh retrieval rather than a guarantee of reconstructing the original snapshot.

To retrieve the reviewed upstream source:

```bash
python scripts/download_examples.py
```

This fetches the selected files at an immutable commit, includes their original LICENSE/NOTICE files, and updates `github/example-manifest.json` with retrieval details. It never imports or executes upstream scripts. Review licensing and implementation before reusing them.

Hashes establish downloaded-file identity and integrity. They are not an AWS signature or production certification. AWS retains rights in its documentation; downloaded upstream files retain their original licenses.
