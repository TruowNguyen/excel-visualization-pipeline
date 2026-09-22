from __future__ import annotations

import base64
import struct

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import api


def test_workspace_api_reads_imported_sqlite_without_reparsing(
    monkeypatch, storage_workspace, sample_workbook
):
    database = storage_workspace / "analytics.sqlite3"
    monkeypatch.setattr(api, "DB_PATH", database)
    monkeypatch.setattr(api, "SOURCE_KEY", "sample")
    client = TestClient(api.app)

    assert client.get("/api/bootstrap").json()["projects"] == []
    payload = sample_workbook.read_bytes()
    preview = client.post(
        "/api/imports/preview",
        files={"file": ("sample.xlsx", payload)},
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["manifest"]["observed_date_min"] == "2026-09-12"
    assert preview.json()["manifest"]["observed_date_max"] == "2026-09-13"

    changed_hash = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", payload)},
        data={"mode": "incremental", "expected_hash": "wrong"},
    )
    assert changed_hash.status_code == 409
    assert client.get("/api/bootstrap").json()["projects"] == []

    committed = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", payload)},
        data={"mode": "incremental", "expected_hash": preview.json()["manifest"]["source_hash"]},
    )
    assert committed.status_code == 200
    assert committed.json()["status"] == "committed"
    assert client.get("/api/bootstrap").json()["projects"][0]["records"] == 6

    entities = client.get("/api/projects/Alpha/entities").json()["entities"]
    assert len(entities) == 3
    workspace = client.get("/api/projects/Alpha/workspace", params={"mode": "week"})
    assert workspace.status_code == 200
    body = workspace.json()
    assert body["window"]["end"] == "2026-09-13"
    assert body["overview"]
    assert body["statistics"]
    assert body["audit"]["total"] > 0
    assert body["capabilities"]["lineage"] == {
        "contractVersion": 1,
        "exactObservation": True,
        "aggregateObservation": True,
    }
    aggregate_trace = next(
        trace for trace in body["overview"][0]["figure"]["data"]
        if trace.get("meta", {}).get("lineage", {}).get("kind") == "aggregate"
        and trace["meta"]["lineage"]["selectable"]
    )
    aggregate_ref = next(ref for ref in aggregate_trace["meta"]["lineage"]["aggregateRefs"] if ref)
    assert aggregate_ref.startswith("agg_")
    aggregate = client.get(f"/api/projects/Alpha/aggregates/{aggregate_ref}/provenance")
    assert aggregate.status_code == 200
    chart_values = aggregate_trace["y"]
    if isinstance(chart_values, dict):
        raw = base64.b64decode(chart_values["bdata"])
        chart_values = struct.unpack(f"<{len(raw) // 8}d", raw)
    assert aggregate.json()["result"]["chartValue"] in chart_values
    assert aggregate.json()["aggregation"]["valueObservationCount"] > 0
    assert any(
        trace.get("meta", {}).get("lineage", {}).get("selectable")
        for chart in body["statistics"] for trace in chart["figure"]["data"]
    )
    comparison_ids = [item["entity_id"] for item in body["comparisonCandidates"][:2]]
    if len(comparison_ids) == 2:
        comparison = client.get(
            "/api/projects/Alpha/workspace",
            params={"mode": "week", "comparison_entities": ",".join(comparison_ids)},
        )
        assert comparison.status_code == 200
        assert any(
            trace.get("meta", {}).get("lineage", {}).get("selectable")
            for trace in comparison.json()["comparison"]["data"]
        )
    first_page = client.get(
        f"/api/projects/Alpha/aggregates/{aggregate_ref}/contributors", params={"limit": 1}
    )
    assert first_page.status_code == 200
    assert first_page.json()["items"][0]["lineageRef"].startswith("lin_")
    if first_page.json()["nextCursor"]:
        next_page = client.get(
            f"/api/projects/Alpha/aggregates/{aggregate_ref}/contributors",
            params={"limit": 1, "cursor": first_page.json()["nextCursor"]},
        )
        assert next_page.status_code == 200
        assert next_page.json()["items"][0]["lineageRef"] != first_page.json()["items"][0]["lineageRef"]
    assert client.get(
        f"/api/projects/Alpha/aggregates/{aggregate_ref}/contributors",
        params={"cursor": "tampered"},
    ).status_code == 422
    assert client.get(f"/api/projects/Other/aggregates/{aggregate_ref}/provenance").status_code == 404

    exact_workspace = client.get("/api/projects/Alpha/workspace", params={"mode": "recent"})
    assert exact_workspace.status_code == 200
    exact_body = exact_workspace.json()
    selectable = next(
        trace
        for trace in exact_body["overview"][0]["figure"]["data"]
        if trace.get("meta", {}).get("lineage", {}).get("selectable")
    )
    observation_ref = selectable["ids"][0]
    lineage_ref = selectable["meta"]["lineage"]["lineageRefs"][0]
    assert observation_ref.startswith("obs_")
    assert lineage_ref.startswith("lin_")

    provenance = client.get(
        f"/api/projects/Alpha/observations/{observation_ref}/provenance",
        params={"lineageRef": lineage_ref},
    )
    assert provenance.status_code == 200
    provenance_body = provenance.json()
    assert provenance_body["observationRef"] == observation_ref
    assert provenance_body["lineageRef"] == lineage_ref
    assert provenance_body["source"]["cellReference"]
    assert provenance_body["revision"]["state"] == "current"
    assert provenance_body["revision"]["revisionRef"].startswith("rev_")
    assert provenance_body["import"]["importRef"].startswith("imp_")
    assert provenance_body["import"]["attemptRef"].startswith("att_")
    revision_history = client.get(f"/api/projects/Alpha/observations/{observation_ref}/revisions")
    assert revision_history.status_code == 200
    assert revision_history.json()["items"][0]["revisionRef"] == provenance_body["revision"]["revisionRef"]
    import_run = client.get(f'/api/projects/Alpha/imports/{provenance_body["import"]["importRef"]}')
    assert import_run.status_code == 200
    assert import_run.json()["attemptRef"] == provenance_body["import"]["attemptRef"]

    audit_lookup = client.get(
        "/api/projects/Alpha/audit/lookup",
        params={"observationRef": observation_ref, "lineageRef": lineage_ref},
    )
    assert audit_lookup.status_code == 200
    audit_body = audit_lookup.json()
    assert audit_body["row"]["cell_address"] == provenance_body["source"]["cell"]
    assert audit_body["row"]["chart_value"] == provenance_body["values"]["chart"]

    mismatched_lineage = selectable["meta"]["lineage"]["lineageRefs"][1]
    mismatch = client.get(
        f"/api/projects/Alpha/observations/{observation_ref}/provenance",
        params={"lineageRef": mismatched_lineage},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "LINEAGE_REF_MISMATCH"
    assert client.get("/api/imports").json()["items"][0]["attempt_status"] == "committed"
    assert client.get("/api/projects/Alpha/export.csv").status_code == 200
    assert client.get("/api/projects/Unknown/workspace").status_code == 404
    assert client.get("/api/projects/Alpha/workspace", params={"entity": "invalid"}).status_code == 422


def test_lineage_ref_pins_revision_after_a_new_import(
    monkeypatch, storage_workspace, sample_workbook
):
    database = storage_workspace / "analytics.sqlite3"
    monkeypatch.setattr(api, "DB_PATH", database)
    monkeypatch.setattr(api, "SOURCE_KEY", "sample")
    client = TestClient(api.app)

    first_payload = sample_workbook.read_bytes()
    first_preview = client.post(
        "/api/imports/preview", files={"file": ("sample.xlsx", first_payload)}
    ).json()
    committed = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", first_payload)},
        data={"mode": "incremental", "expected_hash": first_preview["manifest"]["source_hash"]},
    )
    assert committed.status_code == 200

    workspace = client.get("/api/projects/Alpha/workspace", params={"mode": "recent"}).json()
    error_trace = next(
        trace
        for trace in workspace["overview"][0]["figure"]["data"]
        if trace.get("name") == "Báo sai/Lỗi"
    )
    observation_ref = error_trace["ids"][1]
    lineage_ref = error_trace["meta"]["lineage"]["lineageRefs"][1]
    initial_provenance = client.get(
        f"/api/projects/Alpha/observations/{observation_ref}/provenance",
        params={"lineageRef": lineage_ref},
    )
    assert initial_provenance.status_code == 200
    old_value = initial_provenance.json()["values"]["chart"]
    old_week = client.get("/api/projects/Alpha/workspace", params={"mode": "week"}).json()
    old_aggregate_ref = next(
        ref for trace in old_week["overview"][0]["figure"]["data"]
        if trace.get("name") == "Báo sai/Lỗi"
        for ref in trace.get("meta", {}).get("lineage", {}).get("aggregateRefs", []) if ref
    )
    old_aggregate = client.get(f"/api/projects/Alpha/aggregates/{old_aggregate_ref}/provenance").json()

    workbook = load_workbook(sample_workbook)
    workbook.active["H7"] = 7
    workbook.save(sample_workbook)
    second_payload = sample_workbook.read_bytes()
    second_preview = client.post(
        "/api/imports/preview", files={"file": ("sample.xlsx", second_payload)}
    ).json()
    second = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", second_payload)},
        data={"mode": "incremental", "expected_hash": second_preview["manifest"]["source_hash"]},
    )
    assert second.status_code == 200

    provenance = client.get(
        f"/api/projects/Alpha/observations/{observation_ref}/provenance",
        params={"lineageRef": lineage_ref},
    )
    assert provenance.status_code == 200
    body = provenance.json()
    assert body["values"]["chart"] == old_value
    assert body["revision"]["state"] == "superseded"
    assert body["freshness"]["newerSnapshotAvailable"] is True
    assert body["import"]["importRef"] == initial_provenance.json()["import"]["importRef"]
    revisions = client.get(f"/api/projects/Alpha/observations/{observation_ref}/revisions").json()
    assert len(revisions["items"]) == 2
    assert revisions["items"][0]["state"] == "current"
    assert revisions["items"][1]["state"] == "superseded"
    stale_aggregate = client.get(f"/api/projects/Alpha/aggregates/{old_aggregate_ref}/provenance").json()
    assert stale_aggregate["result"] == old_aggregate["result"]
    assert stale_aggregate["freshness"]["newerDataAvailable"] is True

    audit = client.get(
        "/api/projects/Alpha/audit/lookup",
        params={"observationRef": observation_ref, "lineageRef": lineage_ref},
    )
    assert audit.status_code == 200
    assert audit.json()["row"]["chart_value"] == old_value
