#!/usr/bin/env python3
"""Validate local JSON and current AWS request shapes without AWS calls."""
import json
from pathlib import Path

from botocore.session import Session
from botocore.validate import validate_parameters

ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in (ROOT / "blueprints").glob("*.json"):
        json.loads(path.read_text())
    json.loads((ROOT / "starter" / "profile.dev.json").read_text())
    session = Session()
    control = session.get_service_model("bedrock-agentcore-control")
    harness = json.loads((ROOT / "blueprints" / "create-harness.example.json").read_text())
    validate_parameters(harness, control.operation_model("CreateHarness").input_shape)
    harness["hooks"] = json.loads((ROOT / "blueprints" / "hooks.example.json").read_text())
    validate_parameters(harness, control.operation_model("CreateHarness").input_shape)
    registry = session.get_service_model("agent-registry-control")
    for filename, operation in (("create-registry.example.json", "CreateRegistry"),
                                ("create-skill-record.example.json", "CreateRegistryRecord")):
        request = json.loads((ROOT / "blueprints" / filename).read_text())
        validate_parameters(request, registry.operation_model(operation).input_shape)
    print(json.dumps({"awsTemplateShapes": "passed", "awsCallsMade": 0}))


if __name__ == "__main__":
    main()
