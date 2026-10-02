#!/usr/bin/env python3
"""Snapshot selected official sample source at an immutable commit; never execute it."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "sources" / "github"
DEST = ROOT / "examples" / "upstream"
REPO = "awslabs/amazon-bedrock-agentcore-samples"


def main():
    tree = json.loads((CATALOG / "sample-files.tree.json").read_text())
    commit = tree["sha"]
    prefixes = json.loads((CATALOG / "selected-prefixes.json").read_text())
    files = [entry for entry in tree["tree"] if entry["type"] == "blob"
             and any(entry["path"].startswith(prefix) for prefix in prefixes)
             and not entry["path"].endswith((".png", ".jpg", ".jpeg", ".pdf", ".ipynb"))]
    files.extend(entry for entry in tree["tree"]
                 if entry["path"] in ("LICENSE", "NOTICE", "README.md"))
    policy_prefix = "01-features/07-centralize-and-govern-your-ai-infrastructure/02-policy/"
    files.extend(entry for entry in tree["tree"]
                 if entry["type"] == "blob" and entry["path"].startswith(policy_prefix)
                 and ("/" not in entry["path"][len(policy_prefix):]
                      or entry["path"][len(policy_prefix):].startswith("utils/")))
    files = list({entry["path"]: entry for entry in files}.values())

    def fetch(entry):
        path = entry["path"]
        url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"
        record = {"repository": REPO, "commit": commit, "path": path, "url": url}
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            target = DEST / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        except Exception as error:
            record["error"] = str(error)
        return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        records = list(pool.map(fetch, files))
    (CATALOG / "example-manifest.json").write_text(json.dumps(records, indent=2))
    failures = [record for record in records if "error" in record]
    print(json.dumps({"downloaded": len(records) - len(failures), "failures": failures}, indent=2))


if __name__ == "__main__":
    main()
