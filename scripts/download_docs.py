#!/usr/bin/env python3
"""Download the official AgentCore developer-guide HTML and extract readable text.

Uses only Python's standard library. No AWS credentials or AWS resource calls.
"""
import concurrent.futures
import datetime
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
BASE_URL = "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/"


class MainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.depth = 0
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("id") == "main-col-body":
            self.active = True
            self.depth = 1
            return
        if not self.active:
            return
        if tag == "div":
            self.depth += 1
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "tr", "pre", "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag == "div":
            self.depth -= 1
            if self.depth == 0:
                self.active = False
        if tag in ("p", "li", "h1", "h2", "h3", "h4", "tr", "pre", "td"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.active and not self.skip:
            self.parts.append(data)

    def result(self):
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def walk(node):
    if isinstance(node, dict):
        if "href" in node:
            yield {"title": node.get("title", ""), "href": node["href"]}
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def download(item):
    filename = item["href"]
    url = BASE_URL + filename
    record = {**item, "url": url}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AgentCoreArchitectureResearch/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
            record.update(http_status=response.status, resolved_url=response.url)
        parser = MainText()
        parser.feed(data.decode("utf-8"))
        extracted = parser.result()
        if not extracted:
            raise ValueError("No main documentation content found")
        (SOURCES / "html" / filename).write_bytes(data)
        (SOURCES / "text" / filename.replace(".html", ".txt")).write_text(
            f"Source: {url}\n\n{extracted}\n", encoding="utf-8")
        record.update(
            bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
            local_html=f"html/{filename}", local_text=f"text/{filename.replace('.html', '.txt')}",
            retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as error:
        record["error"] = str(error)
    return record


def main():
    for name in ("html", "text"):
        (SOURCES / name).mkdir(parents=True, exist_ok=True)
    toc = json.loads((SOURCES / "agentcore-toc.json").read_text())
    pages = list({item["href"]: item for item in walk(toc)}.values())
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        records = list(pool.map(download, pages))
    (SOURCES / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    failures = [r for r in records if "error" in r]
    print(json.dumps({"pages": len(records), "downloaded": len(records) - len(failures), "failures": failures}, indent=2))


if __name__ == "__main__":
    main()
