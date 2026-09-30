from __future__ import annotations

import base64
from datetime import date
import struct

from fastapi.testclient import TestClient
from openpyxl import load_workbook
import pandas as pd
import pytest

from app import api


def test_contextual_period_status_explains_missing_rate_numerator():
    rows = []
    for observed, total, rate in [
        ("2026-09-07", 100, 10), ("2026-09-08", 200, 20)
    ]:
        for metric, value, kind in [
            ("Tổng số", total, "numeric"),
            ("Báo sai/Lỗi", None, "not_recorded"),
            ("% báo sai", rate, "numeric"),
        ]:
            rows.append({
                "entity_id": "entity", "parent_entity_id": "parent",
                "entity_label": "Nội dung", "entity_level": "item",
                "effective_unit": "lượt", "metric_normalized": metric,
                "date": observed, "chart_value": value, "value_kind": kind,
            })
    data = pd.DataFrame(rows)

    keys, reason = api._comparison_period_status(
        data, "% báo sai", "week",
        date(2026, 9, 7), date(2026, 9, 13), coverage_data=data,
    )

    assert keys == set()
    assert reason == "RATE_NUMERATOR_MISSING"


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
    assert body["dataVersion"]["committedImportRef"].startswith("imp_")

    assert body["dataVersion"]["committedAt"]
    assert body["window"]["end"] == "2026-09-13"
    assert body["overview"]
    assert body["statistics"]
    assert body["audit"]["total"] > 0
    assert body["capabilities"]["lineage"] == {
        "contractVersion": 1,
        "exactObservation": True,
        "aggregateObservation": True,
    }
    overview_only = client.get(
        "/api/projects/Alpha/workspace", params={"mode": "week", "view": "overview"}
    )
    assert overview_only.status_code == 200
    assert overview_only.json()["overview"]
    assert overview_only.json()["statistics"] == []
    assert overview_only.json()["comparisonCandidates"] == []
    assert overview_only.json()["audit"]["total"] == 0
    cached_overview = client.get(
        "/api/projects/Alpha/workspace", params={"mode": "week", "view": "overview"}
    )
    assert "cache;desc=hit" in cached_overview.headers["server-timing"]
    statistics_only = client.get(
        "/api/projects/Alpha/workspace", params={"mode": "week", "view": "statistics"}
    ).json()
    assert statistics_only["overview"] == []
    assert statistics_only["statistics"]
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
    old_data_version = workspace["dataVersion"]
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

    refreshed_workspace = client.get(
        "/api/projects/Alpha/workspace", params={"mode": "recent"}
    ).json()
    assert refreshed_workspace["dataVersion"]["committedImportRef"] != old_data_version["committedImportRef"]
    assert refreshed_workspace["dataVersion"]["committedAt"] >= old_data_version["committedAt"]

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
    assert body["import"]["importRef"] == old_data_version["committedImportRef"]
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


def test_statistics_inferred_zero_lineage_uses_total_coverage(
    monkeypatch, storage_workspace, sample_workbook
):
    database = storage_workspace / "analytics.sqlite3"
    monkeypatch.setattr(api, "DB_PATH", database)
    monkeypatch.setattr(api, "SOURCE_KEY", "sample-inferred-zero")
    client = TestClient(api.app)

    workbook = load_workbook(sample_workbook)
    for cell in ("E7", "H7", "F7", "I7"):
        workbook.active[cell] = None
    workbook.save(sample_workbook)
    payload = sample_workbook.read_bytes()
    preview = client.post(
        "/api/imports/preview", files={"file": ("sample.xlsx", payload)}
    ).json()
    committed = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", payload)},
        data={"mode": "incremental", "expected_hash": preview["manifest"]["source_hash"]},
    )
    assert committed.status_code == 200

    workspace = client.get(
        "/api/projects/Alpha/workspace",
        params={"view": "statistics", "statistics_group": "week", "statistics_mode": "sum"},
    ).json()
    error_trace = next(
        trace
        for chart in workspace["statistics"]
        for trace in chart["figure"]["data"]
        if trace.get("name") == "Tổng · Báo sai/Lỗi"
    )
    aggregate_ref = next(
        ref
        for ref in error_trace["meta"]["lineage"]["aggregateRefs"]
        if ref
    )
    provenance_response = client.get(
        f"/api/projects/Alpha/aggregates/{aggregate_ref}/provenance"
    )
    assert provenance_response.status_code == 200, provenance_response.json()
    provenance = provenance_response.json()

    assert provenance["result"]["chartValue"] == 0
    assert provenance["aggregation"]["inferredZero"] is True
    assert provenance["aggregation"]["valueObservationCount"] == 0
    assert provenance["aggregation"]["coverageObservationCount"] > 0


def test_contextual_comparison_contract_filters_siblings_and_keeps_legacy_api(
    monkeypatch, storage_workspace, sample_workbook
):
    database = storage_workspace / "analytics.sqlite3"
    monkeypatch.setattr(api, "DB_PATH", database)
    monkeypatch.setattr(api, "SOURCE_KEY", "contextual-comparison")
    client = TestClient(api.app)

    workbook = load_workbook(sample_workbook)
    sheet = workbook.active
    # Production VSO shape: the parent owns Tổng số while direct children own
    # Báo sai/Lỗi and the source percentage.
    sheet["C6"] = "Cảnh báo"
    sheet["D6"] = 100
    sheet["G6"] = 120
    sheet["D7"] = None
    sheet["G7"] = None
    sheet.append([None, "- Sensor", "Cảnh báo", None, 0, 0, None, 0, 0])
    sheet.append([None, "- Gateway", "Cảnh báo", None, 4, 0.04, None, 5, 5 / 120])
    sheet.append([None, "- Router", "Cảnh báo", None, 3, 0.03, None, 2, 2 / 120])
    sheet.append([None, "- Phiên đăng nhập", "Lượt", None, 1, 0.01, None, 1, 1 / 120])
    workbook.save(sample_workbook)
    payload = sample_workbook.read_bytes()
    preview = client.post(
        "/api/imports/preview", files={"file": ("sample.xlsx", payload)}
    ).json()
    committed = client.post(
        "/api/imports",
        files={"file": ("sample.xlsx", payload)},
        data={"mode": "incremental", "expected_hash": preview["manifest"]["source_hash"]},
    )
    assert committed.status_code == 200

    entities = client.get("/api/projects/Alpha/entities").json()["entities"]
    by_label = {item["entity_label"]: item for item in entities}
    parent_id = by_label["1.1. Chất lượng cảnh báo"]["entity_id"]
    camera_id = by_label["Camera"]["entity_id"]
    sensor_id = by_label["Sensor"]["entity_id"]
    gateway_id = by_label["Gateway"]["entity_id"]
    router_id = by_label["Router"]["entity_id"]
    other_unit_id = by_label["Phiên đăng nhập"]["entity_id"]

    contextual = client.get(
        "/api/projects/Alpha/workspace",
        params={
            "view": "comparison",
            "entity": parent_id,
            "scope": "children",
            "comparison_anchor": camera_id,
            "comparison_metric": "% báo sai",
            "comparison_entities": ",".join(
                [camera_id, sensor_id, gateway_id, router_id, other_unit_id]
            ),
            "statistics_group": "quarter",
            "include_incomplete": "true",
        },
    )
    assert contextual.status_code == 200
    body = contextual.json()
    assert body["comparisonContext"]["anchor"]["entityId"] == camera_id
    assert body["comparisonContext"]["grain"] == "quarter"
    assert body["comparisonContext"]["calculation"] == "weighted_rate"
    assert body["comparisonSelection"]["accepted"] == [camera_id, sensor_id, gateway_id]
    assert {item["reason"] for item in body["comparisonSelection"]["removed"]} == {
        "LIMIT_REACHED", "UNIT_MISMATCH"
    }
    candidate_by_id = {item["entity_id"]: item for item in body["comparisonCandidates"]}
    assert candidate_by_id[sensor_id]["eligible"] is True
    assert candidate_by_id[sensor_id]["comparablePeriodCount"] == 1
    assert candidate_by_id[other_unit_id]["eligible"] is False
    assert candidate_by_id[other_unit_id]["reason"] == "UNIT_MISMATCH"
    assert body["comparison"] is not None
    assert body["comparison"]["layout"]["xaxis"]["title"]["text"] == "Quý"
    comparison_values = body["comparison"]["data"][0]["y"]
    if isinstance(comparison_values, dict):
        raw = base64.b64decode(comparison_values["bdata"])
        comparison_values = struct.unpack(f"<{len(raw) // 8}d", raw)
    assert comparison_values == pytest.approx([14 / 220 * 100])
    aggregate_ref = body["comparison"]["data"][0]["meta"]["lineage"]["aggregateRefs"][0]
    assert aggregate_ref
    contributors_response = client.get(
        f"/api/projects/Alpha/aggregates/{aggregate_ref}/contributors"
    )
    assert contributors_response.status_code == 200, contributors_response.json()
    contributors = contributors_response.json()
    denominator_values = [
        member["contributionValue"] for member in contributors["items"]
        if member["role"] == "denominator" and member["included"]
    ]
    assert denominator_values == [100, 120]
    assert body["dataVersion"]["committedImportRef"].startswith("imp_")

    statistics_comparison = client.get(
        "/api/projects/Alpha/workspace",
        params={
            "view": "comparison",
            "entity": parent_id,
            "scope": "children",
            "comparison_anchor": camera_id,
            "comparison_lens": "statistics",
            "comparison_metric": "Báo sai/Lỗi",
            "comparison_calculation": "average_per_day",
            "comparison_entities": f"{camera_id},{gateway_id}",
            # Hai ngày tạo hai điểm, khóa regression cho Plotly/Numpy trace.x.
            "statistics_group": "day",
            "include_incomplete": "true",
        },
    )
    assert statistics_comparison.status_code == 200, statistics_comparison.json()
    statistics_body = statistics_comparison.json()
    assert statistics_body["comparisonContext"]["lens"] == "statistics"
    assert statistics_body["comparisonContext"]["metric"] is None
    assert statistics_body["comparisonContext"]["metrics"] == ["Tổng số", "Báo sai/Lỗi"]
    assert statistics_body["comparisonContext"]["calculation"] == "average_per_day"
    assert statistics_body["comparisonSelection"]["accepted"] == [camera_id, gateway_id]
    assert statistics_body["comparison"] is not None
    assert statistics_body["comparisonTable"]["rows"]
    assert all(
        row["aggregateRef"] for row in statistics_body["comparisonTable"]["rows"]
    )
    assert {
        row["entityId"] for row in statistics_body["comparisonTable"]["rows"]
    } == {camera_id, gateway_id}
    assert {
        row["metric"] for row in statistics_body["comparisonTable"]["rows"]
    } == {"Báo sai/Lỗi"}
    assert all(
        row["eligibleDays"] <= row["calendarDays"]
        for row in statistics_body["comparisonTable"]["rows"]
    )
    cached_reordered = client.get(
        "/api/projects/Alpha/workspace",
        params={
            "view": "comparison", "entity": parent_id, "scope": "children",
            "comparison_anchor": camera_id, "comparison_lens": "statistics",
            "comparison_metric": "Báo sai/Lỗi",
            "comparison_calculation": "average_per_day",
            "comparison_entities": f"{gateway_id},{camera_id}",
            "statistics_group": "day", "include_incomplete": "true",
        },
    )
    assert "cache;desc=hit" in cached_reordered.headers["server-timing"]
    assert cached_reordered.json()["comparisonSelection"]["accepted"] == [camera_id, gateway_id]
    for row in statistics_body["comparisonTable"]["rows"]:
        evidence = client.get(
            f"/api/projects/Alpha/aggregates/{row['aggregateRef']}/provenance"
        )
        assert evidence.status_code == 200, evidence.json()
        assert evidence.json()["context"]["entity"]["ref"] == row["entityId"]
        assert evidence.json()["aggregation"]["ruleCode"] == "sum_divided_by_eligible_days"
        evidence_members = client.get(
            f"/api/projects/Alpha/aggregates/{row['aggregateRef']}/contributors"
        )
        assert evidence_members.status_code == 200, evidence_members.json()
        included_roles = {
            item["role"] for item in evidence_members.json()["items"] if item["included"]
        }
        assert {"value", "coverage"}.issubset(included_roles)

    ignored_statistics_metric = client.get(
        "/api/projects/Alpha/workspace",
        params={
            "view": "comparison", "entity": parent_id, "scope": "children",
            "comparison_anchor": camera_id, "comparison_lens": "statistics",
            "comparison_metric": "% báo sai",
        },
    )
    assert ignored_statistics_metric.status_code == 200
    assert ignored_statistics_metric.json()["comparisonContext"]["metric"] is None

    invalid_anchor = client.get(
        "/api/projects/Alpha/workspace",
        params={
            "view": "comparison", "entity": parent_id, "scope": "children",
            "comparison_anchor": parent_id,
        },
    )
    assert invalid_anchor.status_code == 422
    assert invalid_anchor.json()["detail"]["code"] == "CONTEXTUAL_ANCHOR_OUT_OF_SCOPE"

    legacy = client.get(
        "/api/projects/Alpha/workspace",
        params={"view": "comparison", "comparison_entities": f"{camera_id},{sensor_id}"},
    )
    assert legacy.status_code == 200
    assert legacy.json()["comparisonContext"] is None
    assert legacy.json()["comparisonSelection"] is None
