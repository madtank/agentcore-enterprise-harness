#!/usr/bin/env python3
"""Development-only application boundary for a managed AgentCore harness.

prepare/validate use no AWS network calls. invoke calls an existing harness using
the configured SDK credential chain; it never creates or deletes AWS resources.
User labels are trusted local developer inputs, NOT authentication credentials.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

HERE = Path(__file__).resolve().parent


def load_profile(path, live=False):
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    if profile.get("schemaVersion") != 1 or profile.get("environment") != "development":
        raise ValueError("This starter supports schema v1 development profiles only.")
    if profile.get("businessWritesEnabled") is not False:
        raise ValueError("Business writes must remain disabled in this development starter.")
    if profile.get("dataClassification") != "development_non_sensitive":
        raise ValueError("This starter is for non-sensitive development data.")
    tools = profile.get("allowedTools", [])
    if not isinstance(tools, list) or not tools:
        raise ValueError("An explicit non-empty tool allowlist is required.")
    for name in tools:
        if (not isinstance(name, str) or not re.fullmatch(r"@[A-Za-z0-9_-]+/[A-Za-z0-9_:.\-]+", name)
                or name.startswith("@builtin/") or any(term in name.lower() for term in ("shell", "commit", "delete"))):
            raise ValueError("Tools must be exact Gateway tool selectors; shell and business commits are excluded.")
    limits = profile.get("limits", {})
    for key, maximum in (("maxIterations", 12), ("timeoutSeconds", 120), ("maxTokens", 4096)):
        value = limits.get(key)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"Invalid development limit: {key}.")
    if profile.get("harnessArn") == "${HARNESS_ARN}" and os.environ.get("HARNESS_ARN"):
        profile["harnessArn"] = os.environ["HARNESS_ARN"]
    if not isinstance(profile.get("region"), str) or not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", profile["region"]):
        raise ValueError("An explicit commercial AWS Region is required.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,47}", profile.get("endpointName", "")):
        raise ValueError("A named harness endpoint is required.")
    if profile["endpointName"] == "DEFAULT":
        raise ValueError("Use a named endpoint so changes to DEFAULT do not silently change this client.")
    if live:
        expected = rf"arn:aws:bedrock-agentcore:{re.escape(profile['region'])}:\d{{12}}:harness/[A-Za-z][A-Za-z0-9_]{{0,39}}-[A-Za-z0-9]{{10}}"
        if not re.fullmatch(expected, profile.get("harnessArn", "")):
            raise ValueError("Set HARNESS_ARN to the existing dev harness ARN in the configured Region.")
    return profile


def bind_session(database, user, profile_id, session_id=None):
    if not isinstance(user, str) or not user.strip() or len(user) > 200:
        raise ValueError("A non-empty trusted development user label is required.")
    user = user.strip()
    session_id = session_id or str(uuid.uuid4())
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{32,99}", session_id):
        raise ValueError("Session IDs must be 33–100 safe characters; use a UUID.")
    actor_id = "dev_" + hashlib.sha256(user.encode("utf-8")).hexdigest()
    database = Path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, actor TEXT NOT NULL, profile TEXT NOT NULL)")
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute("SELECT actor, profile FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if existing is not None and existing != (actor_id, profile_id):
            raise ValueError("Session belongs to a different user or profile.")
        connection.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)", (session_id, actor_id, profile_id))
    return session_id, actor_id


def build_request(profile, payload, session_id, actor_id):
    # A product caller supplies one plain-text message. Never forward an arbitrary
    # caller dictionary into InvokeHarness, including config/identity overrides.
    if not isinstance(payload, dict) or set(payload) != {"message"}:
        raise ValueError("Only the message field is accepted from the caller.")
    message = payload["message"]
    if not isinstance(message, str) or not message.strip() or len(message) > 20000:
        raise ValueError("Message must be non-empty text of at most 20,000 characters.")
    return {
        "harnessArn": profile["harnessArn"],
        "qualifier": profile["endpointName"],
        "runtimeSessionId": session_id,
        "actorId": actor_id,
        "allowedTools": list(profile["allowedTools"]),
        **profile["limits"],
        "messages": [{"role": "user", "content": [{"text": message}]}],
    }


def sdk_validate(request):
    # Uses only the locally installed botocore models, never credentials/network.
    from botocore.session import Session
    from botocore.validate import validate_parameters
    session = Session()
    model = session.get_service_model("bedrock-agentcore").operation_model("InvokeHarness")
    validate_parameters(request, model.input_shape)
    for service, operation in (("bedrock-agentcore-control", "CreateHarness"),
                               ("agent-registry", "SearchDiscoverableRegistryRecords"),
                               ("agent-registry-control", "CreateRegistryRecord")):
        session.get_service_model(service).operation_model(operation)


def invoke(profile, request):
    import boto3
    from botocore.config import Config
    client = boto3.Session(region_name=profile["region"]).client(
        "bedrock-agentcore",
        config=Config(read_timeout=180, connect_timeout=10, tcp_keepalive=True,
                      retries={"total_max_attempts": 1}),
    )
    text_parts = []
    metadata = []
    last_stop = None
    response = client.invoke_harness(**request)
    stream = response["stream"]
    try:
        for event in stream:
            for key in event:
                if key.endswith("Exception") or key == "runtimeClientError":
                    # Do not print raw service payloads/trace contents into user output.
                    raise RuntimeError(f"Harness execution failed: {key}.")
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    text_parts.append(delta["text"])
            if "messageStop" in event:
                last_stop = event["messageStop"].get("stopReason")
            if "metadata" in event:
                # Keep usage only; omit arbitrary metadata, reasoning and tool payloads.
                metadata.append(event["metadata"].get("usage", {}))
    finally:
        stream.close()
    if last_stop != "end_turn":
        raise RuntimeError(f"Harness did not complete normally ({last_stop or 'missing final status'}); output withheld.")
    # Buffered output makes a future final-output guardrail possible. No content
    # classification/PII enforcement is implemented in this non-sensitive MVP client.
    return {"sessionId": request["runtimeSessionId"], "stopReason": last_stop,
            "text": "".join(text_parts), "usage": metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "prepare", "invoke"))
    parser.add_argument("--profile", default=str(HERE / "profile.dev.json"))
    parser.add_argument("--user", default="local-developer")
    parser.add_argument("--message", default="Summarize the development runbook and cite sources.")
    parser.add_argument("--session-id")
    parser.add_argument("--state", default=str(HERE / ".state" / "sessions.sqlite3"))
    args = parser.parse_args()
    profile = load_profile(args.profile, live=args.command == "invoke")
    if args.command == "validate":
        request = build_request(profile, {"message": args.message}, str(uuid.uuid4()), "dev_validation")
        sdk_validate(request)
        print(json.dumps({"status": "offline_validation_passed", "profile": profile["profileId"],
                          "awsCallsMade": 0, "liveConfigured": "${" not in profile["harnessArn"],
                          "remaining": ["Create AWS dev resources", "Set HARNESS_ARN", "Verify deployed tool selectors", "Run live integration checks"]}, indent=2))
        return
    session_id, actor_id = bind_session(args.state, args.user, profile["profileId"], args.session_id)
    request = build_request(profile, {"message": args.message}, session_id, actor_id)
    sdk_validate(request)
    result = request if args.command == "prepare" else invoke(profile, request)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
