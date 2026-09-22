"""HTTP read model for the TypeScript workspace; ingestion stays in the Python core."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from io import BytesIO
import json
import os
from pathlib import Path
import sys

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.aggregate_lineage import attach_aggregate_lineage

from excel_visualization_pipeline.config import ParserConfig
from excel_visualization_pipeline.date_ranges import aggregation_period_ranges, recent_data_range
from excel_visualization_pipeline.entity_selection import initial_entity_with_data
from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.storage import (
    LineageMismatchError,
    LineageNotFoundError,
    StorageImportError,
    import_pipeline_result,
    initialize_database,
    load_current_data,
    load_current_entities,
    load_import_history,
    lookup_audit_lineage,
    list_observation_revisions,
    resolve_import_run,
    resolve_observation_lineage,
)
from excel_visualization_pipeline.storage.aggregates import (
    list_aggregate_contributors,
    resolve_aggregate_provenance,
)
from excel_visualization_pipeline.visualization import (
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
    build_period_metric_combo_chart,
    build_period_statistics_chart,
)

SOURCE_KEY = os.environ.get("EVP_SOURCE_KEY", "cx_report_master")
DB_PATH = Path(os.environ.get("EVP_DATABASE", str(ROOT / "data/local/analytics.sqlite3")))
CONFIG_PATH = ROOT / "config/parser.yaml"
METRICS = ("Tổng số", "Báo sai/Lỗi", "% báo sai")
AUDIT_COLUMNS = (
    "date", "project_label", "entity_path", "entity_level", "effective_unit",
    "metric_original", "metric_normalized", "raw_value", "display_value", "chart_value",
    "value_kind", "data_note", "sheet_name", "cell_address", "number_format",
    "parser_rule", "parser_confidence", "validation_status",
)

app = FastAPI(title="CX Analytics API", version="1.0.0")


def _lineage_response(operation):
    try:
        return operation()
    except LineageNotFoundError as exc:
        raise HTTPException(
            404,
            {"code": "LINEAGE_NOT_FOUND", "message": str(exc), "retryable": False},
        ) from exc
    except LineageMismatchError as exc:
        raise HTTPException(
            409,
            {"code": "LINEAGE_REF_MISMATCH", "message": str(exc), "retryable": False},
        ) from exc


def _records(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _figure(figure) -> dict:
    return json.loads(figure.to_json())


def _source() -> tuple[pd.DataFrame, pd.DataFrame]:
    initialize_database(DB_PATH)
    return load_current_data(DB_PATH, SOURCE_KEY), load_current_entities(DB_PATH, SOURCE_KEY)


def _project(project: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    data, entities = _source()
    project_data = data[data["project_label"] == project].copy()
    if project_data.empty:
        raise HTTPException(404, "Project không tồn tại hoặc chưa có dữ liệu")
    return project_data, entities[entities["project_label"] == project].copy()


def _dates(project_data: pd.DataFrame) -> list[date]:
    chartable = project_data[project_data["chart_value"].notna()]
    return sorted(pd.to_datetime(chartable["date"]).dt.date.unique())


def _window(project_data: pd.DataFrame, mode: str, count: int, start: date | None,
            end: date | None) -> tuple[date, date, str | None]:
    dates = _dates(project_data)
    if not dates:
        raise HTTPException(422, "Project chưa có giá trị số để vẽ")
    if mode == "recent":
        recent = recent_data_range(dates, count=10)
        return recent.start, recent.end, None
    if mode in {"week", "month"}:
        ranges = aggregation_period_ranges(dates, mode)
        selected = ranges[-min(max(count, 1), len(ranges)):]
        return max(selected[0].start, dates[0]), min(selected[-1].end, dates[-1]), mode
    if mode == "custom" and start and end and dates[0] <= start <= end <= dates[-1]:
        return start, end, None
    raise HTTPException(422, "Khoảng thời gian không hợp lệ")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/bootstrap")
def bootstrap():
    data, entities = _source()
    projects = []
    for label in sorted(data["project_label"].dropna().unique()) if not data.empty else []:
        project_data = data[data["project_label"] == label]
        project_entities = entities[entities["project_label"] == label]
        dates = _dates(project_data)
        projects.append({
            "label": label,
            "records": len(project_data),
            "chartable": int(project_data["chart_value"].notna().sum()),
            "entities": len(project_entities),
            "units": int(project_entities["unit_normalized"].dropna().nunique()),
            "minDate": dates[0].isoformat() if dates else None,
            "maxDate": dates[-1].isoformat() if dates else None,
        })
    return {"projects": projects, "sourceKey": SOURCE_KEY}


@app.get("/api/projects/{project}/entities")
def project_entities(project: str):
    _, entities = _project(project)
    entities = entities.sort_values(["source_row", "entity_depth"])
    return {"entities": _records(entities[[
        "entity_id", "parent_entity_id", "entity_label", "entity_path", "entity_level",
        "entity_depth", "effective_unit", "source_row",
    ]])}


@app.get("/api/projects/{project}/workspace")
def workspace(
    project: str,
    mode: str = Query("recent", pattern="^(recent|week|month|custom)$"),
    count: int = Query(8, ge=1, le=60),
    start: date | None = None,
    end: date | None = None,
    entity: str | None = None,
    scope: str = Query("node", pattern="^(node|children)$"),
    statistics_group: str = Query("week", pattern="^(day|week|month|quarter)$"),
    statistics_mode: str = Query("both", pattern="^(both|sum|average)$"),
    include_incomplete: bool = True,
    statistics_count: int = Query(8, ge=1, le=3660),
    statistics_from: date | None = None,
    statistics_to: date | None = None,
    comparison_metric: str = "Báo sai/Lỗi",
    comparison_entities: str = "",
    audit_offset: int = Query(0, ge=0),
    audit_limit: int = Query(100, ge=1, le=500),
):
    project_data, entities = _project(project)
    entities = entities.sort_values(["source_row", "entity_depth"])
    entity_lookup = entities.set_index("entity_id")
    start_date, end_date, group_by = _window(project_data, mode, count, start, end)
    if entity is None:
        entity = initial_entity_with_data(entities, project_data, start_date, end_date, list(METRICS))
    if entity not in entity_lookup.index:
        raise HTTPException(422, "Entity không thuộc Project đã chọn")
    children = entities.loc[entities["parent_entity_id"] == entity, "entity_id"].tolist()
    scope_ids = children if scope == "children" and children else [entity]
    detail = project_data[project_data["entity_id"].isin(scope_ids)]
    metric_data = detail[detail["metric_normalized"].isin(METRICS)]
    metric_dates = pd.to_datetime(metric_data["date"]).dt.date
    range_data = metric_data[(metric_dates >= start_date) & (metric_dates <= end_date)]

    overview = []
    for entity_id in scope_ids:
        rows = range_data[range_data["entity_id"] == entity_id]
        if rows.empty:
            continue
        item = entity_lookup.loc[entity_id]
        title = f"{item['entity_label']} — {item['effective_unit']}"
        chart = (build_period_metric_combo_chart(rows, start_date, end_date, group_by, title)
                 if group_by else build_metric_combo_chart(rows, title))
        if group_by:
            attach_aggregate_lineage(
                DB_PATH, SOURCE_KEY, project, chart, rows, entities,
                kind="overview", group_by=group_by,
                start_date=start_date, end_date=end_date,
            )
        overview.append({"entityId": entity_id, "title": title, "figure": _figure(chart)})

    statistic_rows = metric_data[metric_data["metric_normalized"].isin(METRICS[:2])]
    statistic_dates = sorted(pd.to_datetime(statistic_rows["date"]).dt.date.unique())
    periods = aggregation_period_ranges(statistic_dates, statistics_group) if statistic_dates else []
    periods = [period for period in periods if include_incomplete or period.is_complete]
    if statistics_from or statistics_to:
        periods = [period for period in periods
                   if (not statistics_from or period.start >= statistics_from)
                   and (not statistics_to or period.start <= statistics_to)]
    else:
        periods = periods[-statistics_count:]
    modes = {"both": ["SUM", "AVG/ngày"], "sum": ["SUM"], "average": ["AVG/ngày"]}[statistics_mode]
    statistics = []
    if periods:
        period_start = max(periods[0].start, statistic_dates[0])
        period_end = min(periods[-1].end, statistic_dates[-1])
        for entity_id in scope_ids:
            rows = statistic_rows[statistic_rows["entity_id"] == entity_id]
            if rows.empty:
                continue
            item = entity_lookup.loc[entity_id]
            chart = build_period_statistics_chart(
                rows, period_start, period_end, statistics_group, modes,
                f"{item['entity_label']} — {statistics_group}", coverage_data=project_data,
            )
            attach_aggregate_lineage(
                DB_PATH, SOURCE_KEY, project, chart, rows, entities,
                kind="statistics", group_by=statistics_group,
                start_date=period_start, end_date=period_end,
                coverage_data=project_data,
            )
            statistics.append({
                "entityId": entity_id,
                "title": item["entity_label"],
                "figure": _figure(chart),
            })

    if comparison_metric not in METRICS:
        raise HTTPException(422, "Metric so sánh không hợp lệ")
    project_dates = pd.to_datetime(project_data["date"]).dt.date
    candidate_rows = project_data[
        (project_data["metric_normalized"] == comparison_metric)
        & project_data["chart_value"].notna()
        & (project_dates >= start_date) & (project_dates <= end_date)
    ]
    candidates = entities[
        entities["entity_id"].isin(candidate_rows["entity_id"])
        & entities["effective_unit"].notna()
    ]
    chosen = [value for value in comparison_entities.split(",") if value in set(candidates["entity_id"])]
    chosen = list(dict.fromkeys(chosen))[:3]
    comparison = None
    if len(chosen) >= 2:
        units = candidates[candidates["entity_id"].isin(chosen)]["effective_unit"].unique()
        if len(units) != 1:
            raise HTTPException(422, "Các entity so sánh phải cùng Effective Unit")
        rows = project_data[
            project_data["entity_id"].isin(chosen)
            & project_data["metric_normalized"].isin(METRICS)
            & (project_dates >= start_date) & (project_dates <= end_date)
        ]
        comparison_chart = build_multi_entity_metric_chart(
            rows, comparison_metric, f"So sánh {comparison_metric}",
            group_by=group_by, start_date=start_date, end_date=end_date,
        )
        if group_by:
            attach_aggregate_lineage(
                DB_PATH, SOURCE_KEY, project, comparison_chart, rows, entities,
                kind="comparison", group_by=group_by,
                start_date=start_date, end_date=end_date,
                comparison_metric=comparison_metric,
            )
        comparison = _figure(comparison_chart)

    audit = range_data.loc[:, AUDIT_COLUMNS].sort_values(
        ["entity_path", "date", "metric_normalized"]
    ).copy()
    audit["raw_value"] = audit["raw_value"].astype("string")
    return {
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "selectedEntity": entity,
        "scopeIds": scope_ids,
        "overview": overview,
        "statistics": statistics,
        "statisticsPeriods": [{"start": p.start.isoformat(), "label": p.label,
                              "complete": p.is_complete} for p in periods],
        "comparisonCandidates": _records(candidates[["entity_id", "entity_label", "effective_unit"]]),
        "comparison": comparison,
        "capabilities": {
            "lineage": {
                "contractVersion": 1,
                "exactObservation": True,
                "aggregateObservation": True,
            }
        },
        "audit": {"total": len(audit), "offset": audit_offset,
                  "rows": _records(audit.iloc[audit_offset:audit_offset + audit_limit])},
    }


@app.get("/api/projects/{project}/observations/{observation_ref}/provenance")
def observation_provenance(project: str, observation_ref: str, lineageRef: str = Query(...)):
    return _lineage_response(
        lambda: resolve_observation_lineage(
            DB_PATH, project, observation_ref, lineageRef
        )
    )


@app.get("/api/projects/{project}/audit/lookup")
def audit_lookup(
    project: str,
    observationRef: str = Query(...),
    lineageRef: str = Query(...),
):
    return _lineage_response(
        lambda: lookup_audit_lineage(
            DB_PATH, project, observationRef, lineageRef
        )
    )


@app.get("/api/projects/{project}/aggregates/{aggregate_ref}/provenance")
def aggregate_provenance(project: str, aggregate_ref: str):
    return _lineage_response(
        lambda: resolve_aggregate_provenance(DB_PATH, SOURCE_KEY, project, aggregate_ref)
    )


@app.get("/api/projects/{project}/aggregates/{aggregate_ref}/contributors")
def aggregate_contributors(
    project: str,
    aggregate_ref: str,
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = None,
):
    try:
        return list_aggregate_contributors(
            DB_PATH, SOURCE_KEY, project, aggregate_ref, limit=limit, cursor=cursor
        )
    except ValueError as exc:
        raise HTTPException(422, {"code": "INVALID_CONTRIBUTOR_CURSOR", "message": str(exc)}) from exc
    except LineageNotFoundError as exc:
        raise HTTPException(404, {"code": "AGGREGATE_NOT_FOUND", "message": str(exc)}) from exc


@app.get("/api/projects/{project}/observations/{observation_ref}/revisions")
def observation_revisions(project: str, observation_ref: str):
    return _lineage_response(
        lambda: list_observation_revisions(DB_PATH, project, observation_ref, SOURCE_KEY)
    )


@app.get("/api/projects/{project}/imports/{import_ref}")
def import_run_detail(project: str, import_ref: str):
    return _lineage_response(
        lambda: resolve_import_run(DB_PATH, project, import_ref, SOURCE_KEY)
    )


@app.get("/api/imports")
def imports():
    return {"items": _records(load_import_history(DB_PATH, SOURCE_KEY).head(100))}


async def _workbook(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(422, "Chỉ hỗ trợ file .xlsx")
    payload = await file.read(50 * 1024 * 1024 + 1)
    if len(payload) > 50 * 1024 * 1024:
        raise HTTPException(413, "File vượt giới hạn 50 MB")
    return payload


def _preview(payload: bytes, filename: str):
    source = BytesIO(payload)
    source.name = filename
    return run_pipeline(source, CONFIG_PATH)


@app.post("/api/imports/preview")
async def preview_import(file: UploadFile = File(...)):
    payload = await _workbook(file)
    try:
        result = _preview(payload, file.filename or "source.xlsx")
    except Exception as exc:
        raise HTTPException(422, f"Không đọc được workbook: {exc}") from exc
    return {"manifest": result.manifest, "valid": result.report.is_valid,
            "issues": [issue.as_dict() for issue in result.report.issues[:100]],
            "errorCount": len(result.report.errors), "warningCount": len(result.report.warnings)}


@app.post("/api/imports")
async def commit_import(file: UploadFile = File(...), mode: str = Form(...),
                        expected_hash: str = Form(...)):
    if mode not in {"full_snapshot", "incremental"}:
        raise HTTPException(422, "Chế độ import không hợp lệ")
    payload = await _workbook(file)
    try:
        result = _preview(payload, file.filename or "source.xlsx")
        if result.manifest["source_hash"] != expected_hash:
            raise HTTPException(409, "File đã thay đổi sau khi preview; hãy kiểm tra lại")
        if not result.report.is_valid:
            raise HTTPException(422, "Quality gate thất bại; không thể import")
        outcome = import_pipeline_result(
            DB_PATH, SOURCE_KEY, file.filename or "source.xlsx", payload, result,
            config=ParserConfig.from_yaml(CONFIG_PATH), mode=mode,
            display_name="CX Report Master",
        )
        return asdict(outcome)
    except HTTPException:
        raise
    except (ValueError, OSError, StorageImportError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/projects/{project}/export.csv")
def export_csv(project: str):
    data, _ = _project(project)
    return Response(data.to_csv(index=False), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="normalized-data.csv"'})


DIST = ROOT / "frontend/dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
