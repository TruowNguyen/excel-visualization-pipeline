"""Opt-in live AI smoke through the FastAPI application and committed read model.

The script prints only safe status metadata. It never prints the API key, provider
payload, narrative, project/entity labels, facts, or evidence references.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env", override=False)

from app import api as api_module
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository, OutputValidator
from excel_visualization_pipeline.ai.validation import NUMBER, _numeric_candidates


class RecordingAdapter:
    def __init__(self, delegate):
        self.delegate = delegate
        self.provider_name = delegate.provider_name
        self.model = delegate.model
        self.last_content: str | None = None

    def generate(self, *, system_prompt: str, payload: dict):
        result = self.delegate.generate(system_prompt=system_prompt, payload=payload)
        self.last_content = result.content
        return result

    def check_model(self):
        return self.delegate.check_model()


def unsupported_numeric_mentions(content: str | None, snapshot: dict) -> list[dict]:
    if not content:
        return []
    try:
        generated = json.loads(OutputValidator._strip_fence(content))
    except json.JSONDecodeError:
        return []
    facts = {item["factId"]: item for item in snapshot.get("facts", [])}
    blocks = [generated.get("summary"), *generated.get("insights", [])]
    unsupported: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("text"), str):
            continue
        refs = [ref for ref in block.get("factIds", []) if ref in facts]
        allowed = [float(facts[ref]["value"]) for ref in refs if isinstance(facts[ref].get("value"), (int, float))]
        temporal_errors: list[str] = []
        numeric_text = OutputValidator._strip_grounded_temporal_tokens(block["text"], snapshot, temporal_errors)
        for raw in NUMBER.findall(numeric_text):
            signed = raw.startswith(("+", "-"))
            if not any(math.isclose(number, candidate if signed else abs(candidate), rel_tol=0.000001, abs_tol=0.011) for number in _numeric_candidates(raw) for candidate in allowed):
                unsupported.append({"token": raw, "factIds": refs})
    return unsupported


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    configured_service = AIApplicationService.configured(repository=AnalysisSnapshotRepository(limit=100))
    recording_adapter = RecordingAdapter(configured_service.adapter)
    runtime_service = AIApplicationService(
        config=configured_service.config,
        adapter=recording_adapter,
        repository=AnalysisSnapshotRepository(limit=100),
    )
    api_module._ai_service = lambda: runtime_service
    client = TestClient(api_module.app)
    status = client.get("/api/ai/status").json()
    if not all(status.get(key) for key in ("enabled", "configured", "externalAllowed")):
        print("FAIL: feature/config/privacy gate chưa cùng ở trạng thái bật.")
        return 2

    projects_response = client.get("/api/bootstrap")
    if projects_response.status_code != 200:
        print(f"FAIL: bootstrap HTTP {projects_response.status_code}.")
        return 1
    projects = projects_response.json().get("projects", [])
    if not projects:
        print("FAIL: chưa có project committed để smoke runtime.")
        return 1

    project = projects[0]["label"]
    project_path = quote(project, safe="")
    workspace_response = client.get(
        f"/api/projects/{project_path}/workspace",
        params={"view": "overview", "mode": "recent", "count": 3, "scope": "node"},
    )
    if workspace_response.status_code != 200:
        print(f"FAIL: workspace HTTP {workspace_response.status_code}.")
        return 1
    workspace = workspace_response.json()
    entities_response = client.get(f"/api/projects/{project_path}/entities")
    if entities_response.status_code != 200:
        print(f"FAIL: entities HTTP {entities_response.status_code}.")
        return 1
    body = None
    for entity in entities_response.json().get("entities", []):
        request = {
            "entityRef": entity["entity_id"],
            "metricCode": "total",
            "start": workspace["window"]["start"],
            "end": workspace["window"]["end"],
            "groupBy": "day",
            "scope": "node",
        }
        response = client.post(f"/api/projects/{project_path}/ai/trend-summary", json=request)
        if response.status_code != 200:
            print(f"FAIL: trend-summary HTTP {response.status_code}.")
            return 1
        candidate = response.json()
        if len(candidate.get("series", [])) >= 2:
            body = candidate
            break
    if body is None:
        print("FAIL: không tìm thấy entity có ít nhất hai kỳ Tổng số trong window smoke.")
        return 1
    safe_evidence_kinds = sorted({item["target"]["kind"] for item in body.get("evidence", [])})
    safe_result = {
        "featureEnabled": status["enabled"],
        "privacyGate": status["externalAllowed"],
        "provider": body.get("provider", {}).get("name"),
        "configuredModel": status.get("model"),
        "responseModel": body.get("provider", {}).get("model"),
        "promptVersion": body.get("provider", {}).get("promptVersion"),
        "schemaVersion": body.get("schemaVersion"),
        "status": body.get("status"),
        "validation": body.get("validation", {}).get("status"),
        "validationErrors": body.get("validation", {}).get("errors", []),
        "narrativeMode": body.get("narrative", {}).get("mode"),
        "groupBy": body.get("window", {}).get("groupBy"),
        "periodCount": len(body.get("series", [])),
        "evidenceKinds": safe_evidence_kinds,
        "privacyMode": status.get("privacyMode"),
    }
    if body.get("validation", {}).get("status") == "rejected":
        safe_result["unsupportedNumericMentions"] = unsupported_numeric_mentions(
            recording_adapter.last_content, body
        )
    print(json.dumps(safe_result, ensure_ascii=False, sort_keys=True))
    passed = (
        body.get("status") == "ready"
        and body.get("validation", {}).get("status") == "accepted"
        and body.get("narrative", {}).get("mode") == "ai"
        and len(body.get("series", [])) >= 2
    )
    print("PASS: live normalized-data AI slice." if passed else "FAIL: live slice chưa đạt ready/accepted/ai.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
