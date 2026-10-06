"""HTTP read model for the TypeScript workspace; ingestion stays in the Python core."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict
from datetime import date
from io import BytesIO
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
from threading import RLock
from time import perf_counter

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env", override=False)

from app.aggregate_lineage import attach_aggregate_lineage

from excel_visualization_pipeline.config import ParserConfig
from excel_visualization_pipeline.date_ranges import aggregation_period_ranges, recent_data_range
from excel_visualization_pipeline.entity_selection import initial_entity_with_data, same_parent_siblings
from excel_visualization_pipeline.pipeline import run_pipeline
from excel_visualization_pipeline.storage import (
    LineageMismatchError,
    LineageNotFoundError,
    StorageImportError,
    import_pipeline_result,
    initialize_database,
    latest_committed_version,
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
    build_multi_entity_statistics_chart,
    build_period_metric_combo_chart,
    build_period_statistics_chart,
    prepare_period_metric_summary,
    prepare_period_statistics,
    display_entity_label,
)
from excel_visualization_pipeline.ai import AIApplicationService, AnalysisSnapshotRepository
from excel_visualization_pipeline.ai.context import context_summary, resolve_members, check_context_budget
from excel_visualization_pipeline.overview_summary import build_overview_summary, build_statistics_summary
from excel_visualization_pipeline.storage.repository import load_current_snapshot
from excel_visualization_pipeline.reporting.composer import compose, public_document, revise, summary_blocks
from excel_visualization_pipeline.reporting.repository import ReportRepository, ReportConflict, checksum, report_lock
from excel_visualization_pipeline.reporting.export import render as render_report, RENDERER_VERSION, CONTENT_TYPES
from excel_visualization_pipeline.ai.context import narrate_context

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
AI_DATA_COLUMNS = (
    "entity_id", "date", "metric_normalized", "metric_code", "chart_value",
    "value_kind", "effective_unit", "observation_ref", "lineage_ref",
)
AI_ENTITY_COLUMNS = ("entity_id", "entity_label", "entity_path", "effective_unit")

app = FastAPI(title="Automated CX Report API", version="1.0.0")
_AI_SNAPSHOTS = AnalysisSnapshotRepository(limit=100)


class TrendSummaryRequest(BaseModel):
    entityRef: str = Field(min_length=1)
    metricCode: str = Field(pattern="^(all|total|error|error_rate)$")
    start: date
    end: date
    groupBy: str = Field(default="day", pattern="^(day|week|month)$")
    scope: str = Field(default="node", pattern="^node$")


class ContextInsightRequest(BaseModel):
    schemaVersion: str = Field(default="ai-context-request-v1", pattern="^ai-context-request-v1$")
    view: str = Field(pattern="^(overview|statistics)$")
    parentEntityRef: str = Field(min_length=1)
    selection: str = Field(default="node", pattern="^(node|selected|all)$")
    entityRefs: list[str] = Field(default_factory=list, max_length=500)
    metricCode: str = Field(default="all", pattern="^(all|total|error|error_rate)$")
    start: date | None = None
    end: date | None = None
    groupBy: str = Field(default="day", pattern="^(day|week|month|quarter)$")
    calculation: str = Field(default="sum", pattern="^(sum|average_per_day|both)$")
    rangeMode: str = Field(default="recent", pattern="^(recent|all|custom)$")
    periodCount: int = Field(default=8, ge=1, le=3660)
    periodFrom: date | None = None
    periodTo: date | None = None
    includeIncomplete: bool = True
    expectedImportRef: str | None = None


class ReportCreateRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    context: ContextInsightRequest
    title: str = Field(default='Báo cáo diễn biến KPI', min_length=1, max_length=200)
    requestId: str = Field(min_length=8, max_length=100, pattern='^[a-zA-Z0-9_-]+$')


class ReportRevisionRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    baseRevision: int = Field(ge=1)
    requestId: str = Field(min_length=8, max_length=100, pattern='^[a-zA-Z0-9_-]+$')
    title: str | None = Field(default=None, min_length=1, max_length=200)
    userNotes: str | None = Field(default=None, max_length=5000)
    selectedFindingIds: list[str] | None = Field(default=None, max_length=5)
    narrativeEdits: dict[str, str] = Field(default_factory=dict, max_length=24)


class ReportRegenerateRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    baseRevision: int = Field(ge=1)
    requestId: str = Field(min_length=8, max_length=100, pattern='^[a-zA-Z0-9_-]+$')


class ReportExportRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    format: str = Field(pattern='^(pdf|docx)$')


class ReportDeleteRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    baseRevision: int = Field(ge=1)


def _ai_service() -> AIApplicationService:
    return AIApplicationService.configured(repository=_AI_SNAPSHOTS)


@app.middleware("http")
async def add_server_timing(request: Request, call_next):
    """Expose end-to-end API timing without changing response payload contracts."""
    started = perf_counter()
    response = await call_next(request)
    total_ms = (perf_counter() - started) * 1000
    existing = response.headers.get("Server-Timing")
    total_metric = f"total;dur={total_ms:.1f}"
    response.headers["Server-Timing"] = f"{existing}, {total_metric}" if existing else total_metric
    return response


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


_SOURCE_CACHE_LOCK = RLock()
_WORKSPACE_CACHE_LOCK = RLock()
_WORKSPACE_CACHE: OrderedDict[tuple, dict] = OrderedDict()
_WORKSPACE_CACHE_LIMIT = 24


@lru_cache(maxsize=4)
def _load_source_snapshot(db_path: str, source_key: str, revision: int | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    version, data, entities = load_current_snapshot(db_path, source_key)
    if (version.run_id if version else None) != revision:
        raise _SnapshotChanged()
    return data, entities


class _SnapshotChanged(Exception):
    pass


def _source_versioned():
    for _ in range(3):
        version = latest_committed_version(DB_PATH, SOURCE_KEY)
        revision = version.run_id if version else None
        try:
            with _SOURCE_CACHE_LOCK:
                data, entities = _load_source_snapshot(str(DB_PATH.resolve()), SOURCE_KEY, revision)
            return version, data, entities
        except _SnapshotChanged:
            continue
    raise HTTPException(503, "Dữ liệu đang được cập nhật. Vui lòng thử lại.")


def _source() -> tuple[pd.DataFrame, pd.DataFrame]:
    _, data, entities = _source_versioned()
    return data, entities


def _project(project: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    data, entities = _source()
    project_data = data[data["project_label"] == project].copy()
    if project_data.empty:
        raise HTTPException(404, "Dự án không tồn tại hoặc chưa có dữ liệu")
    return project_data, entities[entities["project_label"] == project].copy()


def _dates(project_data: pd.DataFrame) -> list[date]:
    chartable = project_data[project_data["chart_value"].notna()]
    return sorted(pd.to_datetime(chartable["date"]).dt.date.unique())


def _window(project_data: pd.DataFrame, mode: str, count: int, start: date | None,
            end: date | None) -> tuple[date, date, str | None]:
    dates = _dates(project_data)
    if not dates:
        raise HTTPException(422, "Dự án chưa có giá trị số để vẽ")
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


def _statistics_period_window(
    metric_data: pd.DataFrame,
    group_by: str,
    include_incomplete: bool,
    count: int,
    period_from: date | None,
    period_to: date | None,
) -> tuple[list, list[date], date | None, date | None]:
    """Resolve one shared Statistics range for charts and contextual comparison."""
    statistic_rows = metric_data[metric_data["metric_normalized"].isin(METRICS[:2])]
    statistic_dates = sorted(pd.to_datetime(statistic_rows["date"]).dt.date.unique())
    periods = aggregation_period_ranges(statistic_dates, group_by) if statistic_dates else []
    periods = [period for period in periods if include_incomplete or period.is_complete]
    if period_from or period_to:
        periods = [
            period for period in periods
            if (not period_from or period.start >= period_from)
            and (not period_to or period.start <= period_to)
        ]
    else:
        periods = periods[-count:]
    if not periods:
        return periods, statistic_dates, None, None
    return (
        periods,
        statistic_dates,
        max(periods[0].start, statistic_dates[0]),
        min(periods[-1].end, statistic_dates[-1]),
    )


def _comparison_period_keys(
    rows: pd.DataFrame,
    metric: str,
    group_by: str | None,
    start_date: date,
    end_date: date,
    coverage_data: pd.DataFrame | None = None,
) -> set[date]:
    """Return periods that have a comparable value under existing calculations."""
    return _comparison_period_status(
        rows, metric, group_by, start_date, end_date, coverage_data
    )[0]


def _comparison_period_status(
    rows: pd.DataFrame,
    metric: str,
    group_by: str | None,
    start_date: date,
    end_date: date,
    coverage_data: pd.DataFrame | None = None,
) -> tuple[set[date], str | None]:
    """Return comparable periods and a precise reason when aggregation is unavailable."""
    if rows.empty:
        return set(), None
    if group_by is None:
        dates = pd.to_datetime(rows["date"]).dt.date
        values = rows[
            (rows["metric_normalized"] == metric)
            & rows["chart_value"].notna()
            & (dates >= start_date)
            & (dates <= end_date)
        ]
        return set(pd.to_datetime(values["date"]).dt.date), None

    summary = prepare_period_metric_summary(
        rows, start_date, end_date, group_by, coverage_data=coverage_data
    )
    if summary.empty:
        return set(), None
    value_column = {
        METRICS[0]: "total_sum",
        METRICS[1]: "error_sum",
        METRICS[2]: "error_rate",
    }[metric]
    available = summary[summary[value_column].notna()]
    reason = None
    if (
        metric == METRICS[2]
        and available.empty
        and "rate_unavailable_reason" in summary.columns
        and summary["rate_unavailable_reason"].eq(
            "MISSING_ERROR_WITH_POSITIVE_SOURCE_RATE"
        ).any()
    ):
        reason = "RATE_NUMERATOR_MISSING"
    return set(pd.to_datetime(available["period_start"]).dt.date), reason


def _contextual_comparison_contract(
    *,
    project_data: pd.DataFrame,
    entities: pd.DataFrame,
    scope_ids: list[str],
    anchor_id: str,
    metric: str,
    requested_entities: str,
    group_by: str | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[dict], list[str], list[dict], dict]:
    """Validate same-parent eligibility and normalize the contextual selection."""
    if anchor_id not in set(scope_ids):
        raise HTTPException(422, {
            "code": "CONTEXTUAL_ANCHOR_OUT_OF_SCOPE",
            "message": "Nội dung được chọn phải nằm ngay dưới nội dung cấp trên trong phạm vi Thống kê hiện tại.",
        })
    try:
        siblings = same_parent_siblings(entities, anchor_id)
    except ValueError as exc:
        raise HTTPException(422, {
            "code": "CONTEXTUAL_ANCHOR_INVALID", "message": str(exc),
        }) from exc

    entity_lookup = entities.set_index("entity_id")
    anchor = entity_lookup.loc[anchor_id]
    anchor_unit = anchor.get("effective_unit")
    anchor_unit_known = pd.notna(anchor_unit) and str(anchor_unit).strip() != ""
    if start_date is None or end_date is None:
        anchor_keys: set[date] = set()
        anchor_availability_reason = None
    else:
        anchor_rows = project_data[
            project_data["entity_id"].eq(anchor_id)
            & project_data["metric_normalized"].isin(METRICS)
        ]
        anchor_keys, anchor_availability_reason = _comparison_period_status(
            anchor_rows, metric, group_by, start_date, end_date,
            coverage_data=project_data,
        )

    candidates: list[dict] = []
    eligibility_by_id: dict[str, dict] = {}
    for _, candidate in siblings.sort_values(["source_row", "entity_depth"], kind="stable").iterrows():
        candidate_id = str(candidate["entity_id"])
        unit = candidate.get("effective_unit")
        unit_known = pd.notna(unit) and str(unit).strip() != ""
        reason = None
        comparable_count = 0
        if not anchor_unit_known or not unit_known:
            reason = "UNIT_UNKNOWN"
        elif str(unit) != str(anchor_unit):
            reason = "UNIT_MISMATCH"
        elif not anchor_keys:
            reason = "ANCHOR_NO_VALUE"
        elif start_date is not None and end_date is not None:
            candidate_rows = project_data[
                project_data["entity_id"].eq(candidate_id)
                & project_data["metric_normalized"].isin(METRICS)
            ]
            candidate_keys, candidate_availability_reason = _comparison_period_status(
                candidate_rows, metric, group_by, start_date, end_date,
                coverage_data=project_data,
            )
            comparable_count = len(anchor_keys.intersection(candidate_keys))
            if not candidate_keys:
                reason = candidate_availability_reason or "NO_METRIC_VALUE"
            elif comparable_count == 0:
                reason = "NO_OVERLAPPING_PERIOD"
        eligible = reason is None
        item = {
            "entity_id": candidate_id,
            "entity_label": str(candidate["entity_label"]),
            "effective_unit": None if pd.isna(unit) else str(unit),
            "eligible": eligible,
            "reason": reason,
            "comparablePeriodCount": comparable_count,
        }
        candidates.append(item)
        eligibility_by_id[candidate_id] = item

    candidate_order = {
        str(item["entity_id"]): index for index, item in enumerate(candidates)
    }
    requested = sorted(
        set(value for value in requested_entities.split(",") if value),
        key=lambda value: (candidate_order.get(value, len(candidate_order)), value),
    )
    accepted = [anchor_id]
    removed: list[dict] = []
    for candidate_id in requested:
        if candidate_id == anchor_id:
            continue
        candidate = eligibility_by_id.get(candidate_id)
        if candidate is None:
            removed.append({"entityId": candidate_id, "reason": "NOT_SIBLING"})
        elif not candidate["eligible"]:
            removed.append({"entityId": candidate_id, "reason": candidate["reason"]})
        elif len(accepted) >= 3:
            removed.append({"entityId": candidate_id, "reason": "LIMIT_REACHED"})
        else:
            accepted.append(candidate_id)

    context = {
        "lens": "metric",
        "anchor": {
            "entityId": anchor_id,
            "entityLabel": str(anchor["entity_label"]),
            "parentEntityId": None if pd.isna(anchor["parent_entity_id"]) else str(anchor["parent_entity_id"]),
            "effectiveUnit": None if pd.isna(anchor_unit) else str(anchor_unit),
        },
        "metric": metric,
        "calculation": "weighted_rate" if metric == METRICS[2] else "sum",
        "grain": "day" if group_by is None else group_by,
        "range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "anchorEligible": bool(anchor_unit_known and anchor_keys),
        "anchorReason": None if anchor_unit_known and anchor_keys else (
            "UNIT_UNKNOWN" if not anchor_unit_known
            else anchor_availability_reason or "ANCHOR_NO_VALUE"
        ),
    }
    return candidates, accepted, removed, context


def _prepare_contextual_statistics(
    project_data: pd.DataFrame,
    entity_ids: list[str],
    start_date: date,
    end_date: date,
    group_by: str,
) -> pd.DataFrame:
    prepared: list[pd.DataFrame] = []
    for entity_id in entity_ids:
        rows = project_data[
            project_data["entity_id"].eq(entity_id)
            & project_data["metric_normalized"].isin(METRICS[:2])
        ]
        if rows.empty:
            continue
        summary = prepare_period_statistics(
            rows,
            start_date,
            end_date,
            group_by,
            coverage_data=project_data,
            semantic_data=project_data,
        )
        if not summary.empty:
            prepared.append(summary)
    return pd.DataFrame.from_records([
        record
        for summary in prepared
        for record in summary.to_dict(orient="records")
    ]) if prepared else pd.DataFrame()


def _statistics_period_status(
    summary: pd.DataFrame,
    entity_id: str,
    calculation: str,
) -> tuple[set[tuple[str, date]], str | None]:
    rows = summary[summary["entity_id"].eq(entity_id)]
    if rows.empty:
        return set(), "STATISTIC_VALUE_MISSING"
    value_column = "period_sum" if calculation == "sum" else "average_per_day"
    available = rows[rows[value_column].notna()]
    if not available.empty:
        return {
            (str(row.metric_normalized), pd.Timestamp(row.period_start).date())
            for row in available.itertuples(index=False)
        }, None
    if rows.get("semantic_unavailable_reason", pd.Series(dtype=str)).eq(
        "MISSING_ERROR_WITH_POSITIVE_SOURCE_RATE"
    ).any():
        return set(), "RATE_NUMERATOR_MISSING"
    if calculation == "average_per_day" and rows["eligible_day_count"].fillna(0).le(0).all():
        return set(), "NO_ELIGIBLE_DAYS"
    return set(), "STATISTIC_VALUE_MISSING"


def _contextual_statistics_contract(
    *,
    project_data: pd.DataFrame,
    entities: pd.DataFrame,
    scope_ids: list[str],
    anchor_id: str,
    calculation: str,
    requested_entities: str,
    group_by: str,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[dict], list[str], list[dict], dict, pd.DataFrame]:
    if anchor_id not in set(scope_ids):
        raise HTTPException(422, {
            "code": "CONTEXTUAL_ANCHOR_OUT_OF_SCOPE",
            "message": "Nội dung được chọn phải nằm ngay dưới nội dung cấp trên trong phạm vi Thống kê hiện tại.",
        })
    try:
        siblings = same_parent_siblings(entities, anchor_id)
    except ValueError as exc:
        raise HTTPException(422, {
            "code": "CONTEXTUAL_ANCHOR_INVALID", "message": str(exc),
        }) from exc

    entity_lookup = entities.set_index("entity_id")
    anchor = entity_lookup.loc[anchor_id]
    anchor_unit = anchor.get("effective_unit")
    anchor_unit_known = pd.notna(anchor_unit) and str(anchor_unit).strip() != ""
    candidate_ids = [str(value) for value in siblings["entity_id"].tolist()]
    summary = (
        _prepare_contextual_statistics(
            project_data, [anchor_id, *candidate_ids], start_date, end_date, group_by
        )
        if start_date is not None and end_date is not None else pd.DataFrame()
    )
    anchor_keys, anchor_reason = _statistics_period_status(
        summary, anchor_id, calculation
    ) if not summary.empty else (set(), "STATISTIC_VALUE_MISSING")

    candidates: list[dict] = []
    eligibility_by_id: dict[str, dict] = {}
    for _, candidate in siblings.sort_values(["source_row", "entity_depth"], kind="stable").iterrows():
        candidate_id = str(candidate["entity_id"])
        unit = candidate.get("effective_unit")
        unit_known = pd.notna(unit) and str(unit).strip() != ""
        reason = None
        comparable_count = 0
        if not anchor_unit_known or not unit_known:
            reason = "UNIT_UNKNOWN"
        elif str(unit) != str(anchor_unit):
            reason = "UNIT_MISMATCH"
        elif not anchor_keys:
            reason = "ANCHOR_NO_VALUE"
        else:
            candidate_keys, candidate_reason = _statistics_period_status(
                summary, candidate_id, calculation
            )
            comparable_keys = anchor_keys.intersection(candidate_keys)
            comparable_count = len({period for _, period in comparable_keys})
            if not candidate_keys:
                reason = candidate_reason
            elif comparable_count == 0:
                reason = "NO_OVERLAPPING_PERIOD"
        item = {
            "entity_id": candidate_id,
            "entity_label": str(candidate["entity_label"]),
            "effective_unit": None if pd.isna(unit) else str(unit),
            "eligible": reason is None,
            "reason": reason,
            "comparablePeriodCount": comparable_count,
        }
        candidates.append(item)
        eligibility_by_id[candidate_id] = item

    candidate_order = {
        str(item["entity_id"]): index for index, item in enumerate(candidates)
    }
    requested = sorted(
        set(value for value in requested_entities.split(",") if value),
        key=lambda value: (candidate_order.get(value, len(candidate_order)), value),
    )
    accepted = [anchor_id]
    removed: list[dict] = []
    for candidate_id in requested:
        if candidate_id == anchor_id:
            continue
        candidate = eligibility_by_id.get(candidate_id)
        if candidate is None:
            removed.append({"entityId": candidate_id, "reason": "NOT_SIBLING"})
        elif not candidate["eligible"]:
            removed.append({"entityId": candidate_id, "reason": candidate["reason"]})
        elif len(accepted) >= 3:
            removed.append({"entityId": candidate_id, "reason": "LIMIT_REACHED"})
        else:
            accepted.append(candidate_id)

    context = {
        "lens": "statistics",
        "anchor": {
            "entityId": anchor_id,
            "entityLabel": str(anchor["entity_label"]),
            "parentEntityId": None if pd.isna(anchor["parent_entity_id"]) else str(anchor["parent_entity_id"]),
            "effectiveUnit": None if pd.isna(anchor_unit) else str(anchor_unit),
        },
        "metric": None,
        "metrics": list(METRICS[:2]),
        "calculation": calculation,
        "grain": group_by,
        "range": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        },
        "coveragePolicy": "nearest_ancestor_total",
        "anchorEligible": bool(anchor_unit_known and anchor_keys),
        "anchorReason": None if anchor_unit_known and anchor_keys else (
            "UNIT_UNKNOWN" if not anchor_unit_known else anchor_reason
        ),
    }
    return candidates, accepted, removed, context, summary


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ai/status")
def ai_status():
    """Return safe server-side configuration state; never expose credentials."""
    return _ai_service().status()


@app.post("/api/ai/provider/check")
def ai_provider_check():
    """Explicit operator action; this never sends business data to the provider."""
    return _ai_service().check_provider()


@app.post("/api/projects/{project}/ai/trend-summary")
def create_trend_summary(project: str, request: TrendSummaryRequest):
    project_data, entities = _project(project)
    try:
        return _ai_service().trend_summary(
            db_path=DB_PATH,
            source_key=SOURCE_KEY,
            project=project,
            entity_ref=request.entityRef,
            metric_code=request.metricCode,
            start=request.start,
            end=request.end,
            group_by=request.groupBy,
            data=project_data.loc[:, AI_DATA_COLUMNS].copy(),
            entities=entities.loc[:, AI_ENTITY_COLUMNS].copy(),
        )
    except PermissionError as exc:
        raise HTTPException(
            409,
            {"code": "AI_FEATURE_DISABLED", "message": str(exc), "retryable": False},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            422,
            {"code": "AI_REQUEST_INVALID", "message": str(exc), "retryable": False},
        ) from exc


@app.post("/api/projects/{project}/ai/context-insight")
def create_context_insight(project: str, request: ContextInsightRequest):
    project_data, entities = _project(project)
    if not _ai_service().config.enabled:
        raise HTTPException(409, {"code": "AI_FEATURE_DISABLED", "message": 'Tính năng phân tích đang tắt trong cấu hình hệ thống.', "retryable": False})
    return _build_context_bundle(project, request, project_data, entities, _ai_service())


def _build_context_bundle(project: str, request: ContextInsightRequest, project_data: pd.DataFrame,
                          entities: pd.DataFrame, service, *, generate_narrative: bool = True,
                          retain_snapshots: bool = False, persist_analysis: bool = True):
    """Shared scope/prepared-chart contract for Insight and pinned reports."""
    try:
        members = resolve_members(entities, request.parentEntityRef, request.selection, request.entityRefs)
        context = request.model_dump(mode="json", exclude={"entityRefs"})
        prepared = None
        if request.view == "overview":
            if not request.start or not request.end or request.start > request.end:
                raise ValueError("Hãy chọn khoảng ngày hợp lệ.")
            if request.groupBy == "quarter" or request.calculation != "sum":
                raise ValueError("Tổng quan hỗ trợ ngày/tuần/tháng và cách tính hiện có, không nhận trung bình/ngày hoặc quý.")
        else:
            if request.metricCode == "error_rate":
                raise ValueError("Thống kê không hiển thị % báo sai; AI không tự tạo chỉ số này.")
            if request.rangeMode == "custom" and not (request.periodFrom or request.periodTo):
                raise ValueError("Hãy chọn khoảng kỳ thống kê.")
            if request.periodFrom and request.periodTo and request.periodFrom > request.periodTo:
                raise ValueError("Kỳ bắt đầu phải trước kỳ kết thúc.")
            periods, _, first, last = _statistics_period_window(
                project_data, request.groupBy, request.includeIncomplete,
                3660 if request.rangeMode == "all" else request.periodCount,
                request.periodFrom if request.rangeMode == "custom" else None,
                request.periodTo if request.rangeMode == "custom" else None,
            )
            # all means all: detect an unsupported history rather than clipping it.
            if request.rangeMode == "all" and len(aggregation_period_ranges(sorted(pd.to_datetime(project_data.date).dt.date.unique()), request.groupBy)) > 3660:
                raise ValueError("Lịch sử có hơn 3.660 kỳ, chưa hỗ trợ trong một lần phân tích; không cắt dữ liệu âm thầm.")
            context["periods"] = [{"start": p.start.isoformat(), "end": p.end.isoformat(), "label": p.label, "complete": p.is_complete} for p in periods]
            fallback_dates = pd.to_datetime(project_data.date)
            context["start"] = (first or fallback_dates.min().date()).isoformat()
            context["end"] = (last or fallback_dates.max().date()).isoformat()
            check_context_budget(context, members)
            prepared = {}
            modes = {"sum": ["SUM"], "average_per_day": ["AVG/ngày"], "both": ["SUM", "AVG/ngày"]}[request.calculation]
            period_keys = {pd.Timestamp(p.start) for p in periods}
            for member in members:
                rows = project_data[project_data.entity_id.eq(member)].copy()
                if rows.empty or not first or not last:
                    prepared[member] = (pd.DataFrame(), {})
                    continue
                frame = prepare_period_statistics(rows, first, last, request.groupBy, coverage_data=project_data)
                if not frame.empty:
                    frame = frame[frame.period_start.isin(period_keys) | frame.period_start.eq(pd.Timestamp(first))].copy()
                figure = build_period_statistics_chart(rows, first, last, request.groupBy, modes,
                    "AI statistics evidence", coverage_data=project_data, prepared_frame=frame)
                attach_aggregate_lineage(DB_PATH, SOURCE_KEY, project, figure, rows, entities,
                    kind="statistics", group_by=request.groupBy, start_date=first, end_date=last,
                    coverage_data=project_data, prepared_summary=frame)
                targets = {}
                for trace in figure.data:
                    name = str(trace.name or "")
                    if " · " not in name:
                        continue
                    aggregation, metric = name.split(" · ", 1)
                    calculation = "sum" if aggregation in {"SUM", "Tổng"} else "average_per_day"
                    refs = (trace.meta or {}).get("lineage", {}).get("aggregateRefs", [])
                    for label, ref in zip(trace.x, refs):
                        if ref:
                            targets[(calculation, metric, str(label))] = {"kind": "aggregate", "aggregateRef": ref}
                prepared[member] = (frame, targets)
        return context_summary(service, db_path=DB_PATH, source_key=SOURCE_KEY,
            project=project, data=project_data, entities=entities, context=context, members=members, prepared=prepared,
            generate_narrative=generate_narrative, retain_snapshots=retain_snapshots, persist_analysis=persist_analysis)
    except PermissionError as exc:
        raise HTTPException(409, {"code": "AI_FEATURE_DISABLED", "message": str(exc), "retryable": False}) from exc
    except ValueError as exc:
        raise HTTPException(422, {"code": "AI_CONTEXT_INVALID", "message": str(exc), "retryable": False}) from exc


def _report_operation(operation):
    try:
        return operation()
    except ReportConflict as exc:
        raise HTTPException(409, {'code': 'REPORT_CONFLICT', 'message': str(exc), 'retryable': False}) from exc
    except LookupError as exc:
        raise HTTPException(404, {'code': 'REPORT_NOT_FOUND', 'message': str(exc), 'retryable': False}) from exc
    except PermissionError as exc:
        raise HTTPException(409, {'code': 'AI_FEATURE_DISABLED', 'message': str(exc), 'retryable': False}) from exc
    except ValueError as exc:
        raise HTTPException(422, {'code': 'REPORT_INVALID', 'message': str(exc), 'retryable': False}) from exc


def _report_repository(project: str):
    return ReportRepository(DB_PATH, SOURCE_KEY, project)


def _report_public(repository, document):
    current = latest_committed_version(DB_PATH, SOURCE_KEY)
    value = public_document(document, repository.review(document['reportId'], document['revision']),
                            current_import=current.import_ref if current else None)
    value['versions'] = repository.versions(document['reportId'])
    return value


def _capture_report(project: str, request: ReportCreateRequest):
    if not request.title.strip():
        raise ValueError('Hãy nhập tên báo cáo.')
    # Version, data and entities come from one SQLite read transaction.
    version, data, entities = load_current_snapshot(DB_PATH, SOURCE_KEY)
    if version is None:
        raise ValueError('Chưa có dữ liệu đã nhập để tạo báo cáo.')
    project_data = data[data.project_label.eq(project)].copy()
    project_entities = entities[entities.project_label.eq(project)].copy()
    if project_data.empty:
        raise ValueError('Dự án không tồn tại hoặc chưa có dữ liệu.')
    if request.context.expectedImportRef and request.context.expectedImportRef != version.import_ref:
        raise ReportConflict('Dữ liệu đã thay đổi. Kiểm tra lại phạm vi trước khi tạo báo cáo.')
    context = request.context.model_copy(update={'expectedImportRef': version.import_ref})
    bundle = _build_context_bundle(project, context, project_data, project_entities, _ai_service(),
                                   generate_narrative=False, retain_snapshots=True, persist_analysis=False)
    current = latest_committed_version(DB_PATH, SOURCE_KEY)
    if bundle['dataAsOf']['stale'] or not current or current.run_id != version.run_id:
        raise ReportConflict('Dữ liệu thay đổi trong lúc chuẩn bị. Chưa lưu báo cáo; hãy thử lại.')
    if not bundle['context']['analyzedEntityRefs']:
        raise ValueError('Phạm vi chưa có số liệu hợp lệ. Hãy đổi vấn đề hoặc thời gian; chưa tạo nhận định.')
    bundle['dataAsOf']['sourceCommittedAt'] = version.committed_at
    return compose(bundle, request.title.strip())


@app.post('/api/projects/{project}/reports/preview')
def report_preview(project: str, request: ReportCreateRequest):
    def operation():
        document = _capture_report(project, request)
        return public_document(document, {'status': 'not_saved', 'authority': 'local_check_only', 'publicationStatus': 'draft'},
                               current_import=document['dataAsOf']['committedImportRef'])
    return _report_operation(operation)


@app.post('/api/projects/{project}/reports')
def create_report(project: str, request: ReportCreateRequest):
    def operation():
        repository = _report_repository(project)
        fingerprint = checksum(request.model_dump(mode='json', exclude={'requestId'}))
        with report_lock(DB_PATH, f'create:{SOURCE_KEY}:{project}:{request.requestId}'):
            document = repository.created(request.requestId, fingerprint)
            if document is None:
                document = repository.create(_capture_report(project, request), request.requestId, fingerprint)
        return _report_public(repository, document)
    return _report_operation(operation)


@app.get('/api/projects/{project}/reports')
def list_reports(project: str):
    return _report_operation(lambda: {'items': _report_repository(project).items()})


@app.get('/api/projects/{project}/reports/{report_id}')
def get_report(project: str, report_id: str):
    def operation():
        repository = _report_repository(project)
        return _report_public(repository, repository.get(report_id))
    return _report_operation(operation)


@app.delete('/api/projects/{project}/reports/{report_id}')
def delete_report(project: str, report_id: str, request: ReportDeleteRequest):
    def operation():
        with report_lock(DB_PATH, report_id):
            return _report_repository(project).delete(report_id, request.baseRevision)
    return _report_operation(operation)


@app.get('/api/projects/{project}/reports/{report_id}/revisions/{revision}')
def get_report_revision(project: str, report_id: str, revision: int):
    def operation():
        repository = _report_repository(project)
        return _report_public(repository, repository.get(report_id, revision))
    return _report_operation(operation)


@app.post('/api/projects/{project}/reports/{report_id}/revisions')
def save_report_revision(project: str, report_id: str, request: ReportRevisionRequest):
    def operation():
        repository = _report_repository(project)
        fingerprint = checksum(request.model_dump(exclude={'requestId'}))
        with report_lock(DB_PATH, report_id):
            document = repository.operation(report_id, request.requestId, fingerprint)
            if document is None:
                original = repository.require_latest(report_id, request.baseRevision)
                if request.title is not None and not request.title.strip():
                    raise ValueError('Tên báo cáo không được để trống.')
                if any(not text.strip() or len(text) > 5000 for text in request.narrativeEdits.values()):
                    raise ValueError('Mỗi diễn giải phải có nội dung và tối đa 5.000 ký tự.')
                updated = revise(original, title=request.title, notes=request.userNotes,
                                 selected=request.selectedFindingIds, edits=request.narrativeEdits, service=_ai_service())
                document = repository.append(updated, request.baseRevision, request.requestId, fingerprint)
        return _report_public(repository, document)
    return _report_operation(operation)


@app.post('/api/projects/{project}/reports/{report_id}/regenerate')
def regenerate_report(project: str, report_id: str, request: ReportRegenerateRequest):
    def operation():
        repository = _report_repository(project)
        fingerprint = checksum({'action': 'regenerate', 'baseRevision': request.baseRevision})
        with report_lock(DB_PATH, report_id):
            document = repository.operation(report_id, request.requestId, fingerprint)
            if document is None:
                original = repository.require_latest(report_id, request.baseRevision)
                bundle = narrate_context(_ai_service(), original['_bundle'])
                updated = compose(bundle, original['title'], prior=original)
                # User-edited, validated paragraphs are never silently replaced.
                manual = {b['blockId']: b for b in original['blocks'] if b['source'] == 'manual'}
                for block in updated['blocks']:
                    if block['blockId'] in manual:
                        block.update(text=manual[block['blockId']]['text'], source='manual', validation='accepted')
                for finding in updated['findings']:
                    if finding.get('blockId') in manual:
                        finding.update(text=manual[finding['blockId']]['text'], source='manual')
                updated['executiveSummary'] = summary_blocks(updated['blocks'], updated['findings'])
                document = repository.append(updated, request.baseRevision, request.requestId, fingerprint)
        return _report_public(repository, document)
    return _report_operation(operation)


@app.post('/api/projects/{project}/reports/{report_id}/revisions/{revision}/check')
def check_report(project: str, report_id: str, revision: int):
    def operation():
        repository = _report_repository(project)
        repository.check(report_id, revision)
        return _report_public(repository, repository.get(report_id, revision))
    return _report_operation(operation)


@app.post('/api/projects/{project}/reports/{report_id}/revisions/{revision}/exports')
def export_report(project: str, report_id: str, revision: int, request: ReportExportRequest):
    def operation():
        repository = _report_repository(project)
        with report_lock(DB_PATH, f'export:{report_id}:{revision}:{request.format}'):
            document = repository.get(report_id, revision)
            artifact = repository.exported(report_id, revision, request.format)
            if artifact is None:
                document['reviewAtExport'] = repository.review(report_id, revision)
                content = render_report(document, request.format)
                repository.store_export(document, request.format, content, RENDERER_VERSION)
                artifact = repository.exported(report_id, revision, request.format)
        content, receipt = artifact
        return Response(content, media_type=CONTENT_TYPES[request.format], headers={
            'Content-Disposition': f'attachment; filename="Automated-CX-Report-{report_id}-v{revision}.{request.format}"',
            'X-Report-Revision': str(revision), 'X-Content-SHA256': receipt['content_hash'], 'Cache-Control': 'no-store'})
    return _report_operation(operation)


@app.get("/api/ai/analyses/{analysis_id}")
def get_ai_analysis(analysis_id: str):
    analysis = _ai_service().get_analysis(
        analysis_id, db_path=DB_PATH, source_key=SOURCE_KEY
    )
    if analysis is None:
        raise HTTPException(
            404,
            {"code": "AI_ANALYSIS_NOT_FOUND", "message": "Bản phân tích đã lưu không tồn tại."},
        )
    return analysis


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
    response: Response,
    view: str = Query("all", pattern="^(all|overview|statistics|comparison|audit)$"),
    mode: str = Query("recent", pattern="^(recent|week|month|custom)$"),
    count: int = Query(8, ge=1, le=60),
    start: date | None = None,
    end: date | None = None,
    entity: str | None = None,
    scope: str = Query("node", pattern="^(node|children)$"),
    overview_source: str | None = None,
    statistics_group: str = Query("week", pattern="^(day|week|month|quarter)$"),
    statistics_mode: str = Query("both", pattern="^(both|sum|average)$"),
    include_incomplete: bool = True,
    statistics_count: int = Query(8, ge=1, le=3660),
    statistics_from: date | None = None,
    statistics_to: date | None = None,
    comparison_metric: str = "Báo sai/Lỗi",
    comparison_entities: str = "",
    comparison_anchor: str | None = None,
    comparison_lens: str = Query("metric", pattern="^(metric|statistics)$"),
    comparison_calculation: str = Query("sum", pattern="^(sum|average_per_day)$"),
    audit_offset: int = Query(0, ge=0),
    audit_limit: int = Query(100, ge=1, le=500),
):
    started = perf_counter()
    last_checkpoint = started
    timings: list[tuple[str, float]] = []

    def checkpoint(name: str) -> None:
        nonlocal last_checkpoint
        now = perf_counter()
        timings.append((name, (now - last_checkpoint) * 1000))
        last_checkpoint = now

    committed_version = latest_committed_version(DB_PATH, SOURCE_KEY)
    revision = committed_version.run_id if committed_version is not None else None
    overview_policy = json.loads((ROOT / "config/overview-sources.json").read_text(encoding="utf-8")) if view in {"all", "overview", "statistics"} else None
    overview_policy_key = json.dumps(overview_policy, ensure_ascii=False, sort_keys=True)
    comparison_entity_key = tuple(sorted(set(
        value for value in comparison_entities.split(",") if value
    )))
    cache_key = (
        str(DB_PATH.resolve()), SOURCE_KEY, revision, project, view, mode, count,
        start, end, entity, scope, statistics_group, statistics_mode,
        include_incomplete, statistics_count, statistics_from, statistics_to,
        comparison_metric, comparison_entity_key, comparison_anchor, comparison_lens,
        comparison_calculation,
        audit_offset, audit_limit, overview_source, overview_policy_key,
    )
    with _WORKSPACE_CACHE_LOCK:
        cached = _WORKSPACE_CACHE.get(cache_key)
        if cached is not None:
            _WORKSPACE_CACHE.move_to_end(cache_key)
            response.headers["Server-Timing"] = f"cache;desc=hit;dur={(perf_counter() - started) * 1000:.1f}"
            return cached

    committed_version, source_data, source_entities = _source_versioned()
    revision = committed_version.run_id if committed_version else None
    cache_key = cache_key[:2] + (revision,) + cache_key[3:]
    project_data = source_data[source_data["project_label"].eq(project)].copy()
    entities = source_entities[source_entities["project_label"].eq(project)].copy()
    if project_data.empty:
        raise HTTPException(404, "Dự án không tồn tại hoặc chưa có dữ liệu")
    checkpoint("source")
    entities = entities.sort_values(["source_row", "entity_depth"])
    entity_lookup = entities.set_index("entity_id")
    start_date, end_date, group_by = _window(project_data, mode, count, start, end)
    if entity is None:
        entity = initial_entity_with_data(entities, project_data, start_date, end_date, list(METRICS))
    if entity not in entity_lookup.index:
        raise HTTPException(422, "Nội dung theo dõi không thuộc dự án đã chọn")
    children = entities.loc[entities["parent_entity_id"] == entity, "entity_id"].tolist()
    scope_ids = children if scope == "children" and children else [entity]
    detail = project_data[project_data["entity_id"].isin(scope_ids)]
    metric_data = detail[detail["metric_normalized"].isin(METRICS)]
    metric_dates = pd.to_datetime(metric_data["date"]).dt.date
    range_data = metric_data[(metric_dates >= start_date) & (metric_dates <= end_date)]
    checkpoint("filter")

    overview = []
    if view in {"all", "overview"}:
        for entity_id in scope_ids:
            rows = range_data[range_data["entity_id"] == entity_id]
            if rows.empty:
                continue
            item = entity_lookup.loc[entity_id]
            title = f"{display_entity_label(item['entity_label'], item['entity_level'])} — {item['effective_unit']}"
            prepared_overview = (
                prepare_period_metric_summary(rows, start_date, end_date, group_by)
                if group_by else None
            )
            chart = (build_period_metric_combo_chart(
                rows, start_date, end_date, group_by, title, prepared_frame=prepared_overview
            ) if group_by else build_metric_combo_chart(rows, title))
            if group_by:
                attach_aggregate_lineage(
                    DB_PATH, SOURCE_KEY, project, chart, rows, entities,
                    kind="overview", group_by=group_by,
                    start_date=start_date, end_date=end_date,
                    prepared_summary=prepared_overview,
                )
            overview.append({"entityId": entity_id, "title": title, "figure": _figure(chart)})
    checkpoint("overview")

    statistic_rows = metric_data[metric_data["metric_normalized"].isin(METRICS[:2])]
    periods: list = []
    statistic_dates: list[date] = []
    period_start: date | None = None
    period_end: date | None = None
    statistics = []
    if view in {"all", "statistics"} or comparison_anchor is not None:
        periods, statistic_dates, period_start, period_end = _statistics_period_window(
            metric_data, statistics_group, include_incomplete, statistics_count,
            statistics_from, statistics_to,
        )
    if view in {"all", "statistics"}:
        modes = {"both": ["SUM", "AVG/ngày"], "sum": ["SUM"], "average": ["AVG/ngày"]}[statistics_mode]
        if periods and period_start is not None and period_end is not None:
            for entity_id in scope_ids:
                rows = statistic_rows[statistic_rows["entity_id"] == entity_id]
                if rows.empty:
                    continue
                item = entity_lookup.loc[entity_id]
                prepared_statistics = prepare_period_statistics(
                    rows, period_start, period_end, statistics_group,
                    coverage_data=project_data,
                    semantic_data=project_data,
                )
                chart = build_period_statistics_chart(
                    rows, period_start, period_end, statistics_group, modes,
                    f"{display_entity_label(item['entity_label'], item['entity_level'])} — {statistics_group}", coverage_data=project_data,
                    semantic_data=project_data,
                    prepared_frame=prepared_statistics,
                )
                attach_aggregate_lineage(
                    DB_PATH, SOURCE_KEY, project, chart, rows, entities,
                    kind="statistics", group_by=statistics_group,
                    start_date=period_start, end_date=period_end,
                    coverage_data=project_data,
                    prepared_summary=prepared_statistics,
                )
                statistics.append({
                    "entityId": entity_id,
                    "title": display_entity_label(item["entity_label"], item["entity_level"]),
                    "figure": _figure(chart),
                })
    checkpoint("statistics")

    if comparison_metric not in METRICS:
        raise HTTPException(422, "Chỉ số so sánh không hợp lệ")
    candidates: pd.DataFrame | list[dict] = entities.iloc[0:0]
    comparison = None
    comparison_context = None
    comparison_selection = None
    comparison_table = None
    if view in {"all", "comparison"}:
        project_dates = pd.to_datetime(project_data["date"]).dt.date
        if comparison_anchor is not None:
            comparison_group_by = None if statistics_group == "day" else statistics_group
            prepared_comparison_statistics = pd.DataFrame()
            if comparison_lens == "statistics":
                candidates, chosen, removed, comparison_context, prepared_comparison_statistics = _contextual_statistics_contract(
                    project_data=project_data,
                    entities=entities,
                    scope_ids=scope_ids,
                    anchor_id=comparison_anchor,
                    calculation=comparison_calculation,
                    requested_entities=comparison_entities,
                    group_by=statistics_group,
                    start_date=period_start,
                    end_date=period_end,
                )
            else:
                candidates, chosen, removed, comparison_context = _contextual_comparison_contract(
                    project_data=project_data,
                    entities=entities,
                    scope_ids=scope_ids,
                    anchor_id=comparison_anchor,
                    metric=comparison_metric,
                    requested_entities=comparison_entities,
                    group_by=comparison_group_by,
                    start_date=period_start,
                    end_date=period_end,
                )
            comparison_selection = {"accepted": chosen, "removed": removed, "limit": 3}
            if len(chosen) >= 2 and period_start is not None and period_end is not None:
                rows = project_data[
                    project_data["entity_id"].isin(chosen)
                    & project_data["metric_normalized"].isin(METRICS)
                    & (project_dates >= period_start) & (project_dates <= period_end)
                ]
                if comparison_lens == "statistics":
                    chosen_summary = prepared_comparison_statistics[
                        prepared_comparison_statistics["entity_id"].isin(chosen)
                    ].copy()
                    comparison_chart = build_multi_entity_statistics_chart(
                        chosen_summary,
                        comparison_calculation,
                        "So sánh thống kê",
                    )
                    attach_aggregate_lineage(
                        DB_PATH, SOURCE_KEY, project, comparison_chart, rows, entities,
                        kind="statistics_comparison", group_by=statistics_group,
                        start_date=period_start, end_date=period_end,
                        comparison_calculation=comparison_calculation,
                        coverage_data=project_data,
                        prepared_summary=chosen_summary,
                    )
                    aggregate_refs = {
                        (
                            str(trace.legendgroup),
                            str((trace.meta or {}).get("statisticsMetric")),
                            str(label),
                        ): ref
                        for trace in comparison_chart.data
                        for label, ref in zip(
                            list(trace.x) if trace.x is not None else [],
                            (trace.meta or {}).get("lineage", {}).get("aggregateRefs", []),
                        )
                        if ref
                    }
                    value_column = "period_sum" if comparison_calculation == "sum" else "average_per_day"
                    display_column = "display_sum" if comparison_calculation == "sum" else "display_average"
                    table_rows = chosen_summary[
                        chosen_summary[value_column].notna()
                    ].sort_values(["period_start", "entity_label", "metric_normalized"])
                    comparison_table = {
                        "columns": ["period", "entity", "metric", "value", "eligibleDays"],
                        "rows": [
                            {
                                "period": str(row.period_label),
                                "periodStart": pd.Timestamp(row.period_start).date().isoformat(),
                                "periodEnd": pd.Timestamp(row.period_end).date().isoformat(),
                                "entityId": str(row.entity_id),
                                "entity": display_entity_label(str(row.entity_label), str(row.entity_level)),
                                "metric": str(row.metric_normalized),
                                "value": float(getattr(row, value_column)),
                                "displayValue": str(getattr(row, display_column)),
                                "eligibleDays": int(row.eligible_day_count),
                                "calendarDays": int(row.calendar_day_count),
                                "coverageSourceEntityId": str(row.coverage_source_entity_id),
                                "inferredZero": bool(row.inferred_zero),
                                "aggregateRef": aggregate_refs.get(
                                    (
                                        str(row.entity_id),
                                        str(row.metric_normalized),
                                        str(row.period_label),
                                    )
                                ),
                            }
                            for row in table_rows.itertuples(index=False)
                        ],
                    }
                else:
                    comparison_chart = build_multi_entity_metric_chart(
                        rows, comparison_metric, f"So sánh {comparison_metric}",
                        group_by=comparison_group_by,
                        start_date=period_start, end_date=period_end,
                        coverage_data=project_data,
                    )
                    if comparison_group_by:
                        attach_aggregate_lineage(
                            DB_PATH, SOURCE_KEY, project, comparison_chart, rows, entities,
                            kind="comparison", group_by=comparison_group_by,
                            start_date=period_start, end_date=period_end,
                            comparison_metric=comparison_metric,
                            coverage_data=project_data,
                        )
                comparison = _figure(comparison_chart)
        else:
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
            if len(chosen) >= 2:
                units = candidates[candidates["entity_id"].isin(chosen)]["effective_unit"].unique()
                if len(units) != 1:
                    raise HTTPException(422, "Các nội dung so sánh phải cùng đơn vị đo")
                rows = project_data[
                    project_data["entity_id"].isin(chosen)
                    & project_data["metric_normalized"].isin(METRICS)
                    & (project_dates >= start_date) & (project_dates <= end_date)
                ]
                comparison_chart = build_multi_entity_metric_chart(
                    rows, comparison_metric, f"So sánh {comparison_metric}",
                    group_by=group_by, start_date=start_date, end_date=end_date,
                    coverage_data=project_data,
                )
                if group_by:
                    attach_aggregate_lineage(
                        DB_PATH, SOURCE_KEY, project, comparison_chart, rows, entities,
                        kind="comparison", group_by=group_by,
                        start_date=start_date, end_date=end_date,
                        comparison_metric=comparison_metric,
                        coverage_data=project_data,
                    )
                comparison = _figure(comparison_chart)
    checkpoint("comparison")

    audit = range_data.iloc[0:0].loc[:, AUDIT_COLUMNS].copy()
    if view in {"all", "audit"}:
        audit = range_data.loc[:, AUDIT_COLUMNS].sort_values(
            ["entity_path", "date", "metric_normalized"]
        ).copy()
        audit["raw_value"] = audit["raw_value"].astype("string")
    checkpoint("audit")
    response.headers["Server-Timing"] = ", ".join(
        f"{name};dur={duration:.1f}" for name, duration in timings
    )
    payload = {
        "dataVersion": {
            "committedImportRef": committed_version.import_ref,
            "committedAt": committed_version.committed_at,
        } if committed_version is not None else None,
        "window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "selectedEntity": entity,
        "scopeIds": scope_ids,
        "overview": overview,
        "overviewSummary": None,
        "statisticsSummary": None,
        "statistics": statistics,
        "statisticsPeriods": [{"start": p.start.isoformat(), "label": p.label,
                              "complete": p.is_complete} for p in periods],
        "comparisonCandidates": (
            candidates if isinstance(candidates, list)
            else _records(candidates[["entity_id", "entity_label", "effective_unit"]])
        ),
        "comparison": comparison,
        "comparisonTable": comparison_table,
        "comparisonContext": comparison_context,
        "comparisonSelection": comparison_selection,
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
    if view in {"all", "overview"}:
        try:
            payload["overviewSummary"] = build_overview_summary(
                project_data, entities, project, start_date, end_date, group_by or "day", overview_policy, overview_source,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    if view in {"all", "statistics"}:
        try:
            payload["statisticsSummary"] = build_statistics_summary(
                project_data, entities, project, period_start, period_end, statistics_group,
                periods, statistics_mode, overview_policy, overview_source,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    with _WORKSPACE_CACHE_LOCK:
        _WORKSPACE_CACHE[cache_key] = payload
        _WORKSPACE_CACHE.move_to_end(cache_key)
        while len(_WORKSPACE_CACHE) > _WORKSPACE_CACHE_LIMIT:
            _WORKSPACE_CACHE.popitem(last=False)
    return payload


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
        raise HTTPException(422, "Chỉ hỗ trợ tệp Excel định dạng .xlsx")
    payload = await file.read(50 * 1024 * 1024 + 1)
    if len(payload) > 50 * 1024 * 1024:
        raise HTTPException(413, "Tệp vượt giới hạn 50 MB")
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
        raise HTTPException(422, f"Không đọc được tệp Excel: {exc}") from exc
    return {"manifest": result.manifest, "valid": result.report.is_valid,
            "issues": [issue.as_dict() for issue in result.report.issues[:100]],
            "errorCount": len(result.report.errors), "warningCount": len(result.report.warnings)}


@app.post("/api/imports")
async def commit_import(file: UploadFile = File(...), mode: str = Form(...),
                        expected_hash: str = Form(...)):
    if mode not in {"full_snapshot", "incremental"}:
        raise HTTPException(422, "Cách nhập dữ liệu không hợp lệ")
    payload = await _workbook(file)
    try:
        result = _preview(payload, file.filename or "source.xlsx")
        if result.manifest["source_hash"] != expected_hash:
            raise HTTPException(409, "Tệp đã thay đổi sau khi xem trước; hãy kiểm tra lại")
        if not result.report.is_valid:
            raise HTTPException(422, "Dữ liệu không đạt kiểm tra chất lượng; chưa thể nhập tệp")
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
