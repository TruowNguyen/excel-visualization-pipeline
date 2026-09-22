from __future__ import annotations

from html import escape
from io import BytesIO
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.config import ParserConfig  # noqa: E402
from excel_visualization_pipeline.pipeline import run_pipeline  # noqa: E402
from excel_visualization_pipeline.storage import (  # noqa: E402
    import_pipeline_result,
    initialize_database,
    load_current_data,
    load_current_entities,
    load_import_history,
)
from excel_visualization_pipeline.entity_selection import initial_entity_with_data  # noqa: E402
from excel_visualization_pipeline.date_ranges import (  # noqa: E402
    aggregation_period_ranges,
    recent_data_range,
)
from excel_visualization_pipeline.visualization import (  # noqa: E402
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
    build_period_metric_combo_chart,
    build_period_statistics_chart,
)


def hierarchy_label(row: pd.Series) -> str:
    indent = "　" * int(row["entity_depth"])
    unit = f" · {row['effective_unit']}" if pd.notna(row["effective_unit"]) else " · chưa có unit"
    return f"{indent}{row['entity_label']}{unit}"


def option_index(options, requested, default: int = 0) -> int:
    """Resolve a stored value against current workbook options without trusting stale state."""
    try:
        return list(options).index(requested)
    except (ValueError, TypeError):
        return default


def stored_date(state, name, default, minimum, maximum):
    """Read a bounded ISO date from browser state, falling back when stale or invalid."""
    raw_value = state.get(name)
    if not raw_value:
        return default
    try:
        value = pd.Timestamp(raw_value).date()
    except (TypeError, ValueError):
        return default
    return value if minimum <= value <= maximum else default


def widget_default(name: str, value, restoring: bool) -> dict:
    """Pass a widget default only when Session State is not restoring that widget."""
    return {} if restoring else {name: value}


def restore_browser_filters() -> None:
    component_state = st.session_state.get("browser_filter_state_reader", {})
    restored = component_state.get("restored") if hasattr(component_state, "get") else None
    st.session_state["_restored_filters"] = restored if isinstance(restored, dict) else {}
    widget_keys = {
        "project_filter",
        "range_mode",
        "overview_week_count",
        "overview_month_count",
        "custom_start_date",
        "custom_end_date",
        "entity_navigator",
        "entity_scope",
        "statistics_group",
        "statistics_range",
        "statistics_modes",
        "include_incomplete",
        "recent_period_count",
        "statistics_period_from",
        "statistics_period_to",
        "comparison_metric",
    }
    for key in widget_keys:
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if str(key).startswith("comparison_entities::"):
            del st.session_state[key]
    st.session_state["_apply_restored_state"] = True
    st.session_state["_browser_state_loaded"] = True


@st.cache_resource
def create_browser_state_component():
    """Register the versioned browser-state component once per server process."""
    return st.components.v2.component(
        "excel_visualization_pipeline.browser_state_v2",
        html="<span aria-hidden='true'></span>",
        js="""
        export default function ({ data, setStateValue }) {
          const storageKey = data.storageKey;

          if (data.mode === "read") {
            let restored = {};
            try {
              const serialized = window.sessionStorage.getItem(storageKey);
              restored = serialized ? JSON.parse(serialized) : {};
            } catch (_) {
              restored = {};
            }
            setStateValue("restored", restored);
            return;
          }

          if (data.mode === "write") {
            try {
              const serialized = JSON.stringify(data.state ?? {});
              if (window.sessionStorage.getItem(storageKey) !== serialized) {
                window.sessionStorage.setItem(storageKey, serialized);
              }
            } catch (_) {
              // Storage may be disabled by browser policy; the dashboard still works for this session.
            }
          }
        }
        """,
    )


browser_state_component = create_browser_state_component()


@st.cache_data(show_spinner="Đang đọc và kiểm tra workbook...")
def cached_preview(
    payload: bytes,
    source_name: str,
    config_path: str,
    config_mtime_ns: int,
):
    """Parse/validate for preview only; this function never writes SQLite."""
    _ = config_mtime_ns
    source = BytesIO(payload)
    source.name = source_name
    return run_pipeline(source, config_path)


st.set_page_config(page_title="Excel Quality Dashboard", layout="wide")
st.markdown(
    """
    <style>
    /* Plotly's native legend remains the toggle control; only its visual affordance changes. */
    div[data-testid="stPlotlyChart"] g.legend g.traces {
        cursor: pointer;
        transform-box: fill-box;
        transform-origin: center;
        transition: opacity 180ms ease;
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces rect.legendtoggle {
        fill: rgba(148, 163, 184, 0.06) !important;
        fill-opacity: 1 !important;
        stroke: rgba(148, 163, 184, 0.28);
        stroke-width: 0.75px;
        height: 26px;
        transform: translateY(-3px);
        rx: 7px;
        ry: 7px;
        transition: fill 180ms ease, stroke 180ms ease;
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces text.legendtext {
        font-size: 12px !important;
        text-rendering: geometricPrecision;
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces g.layers {
        transform: translateY(0);
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces:hover rect.legendtoggle {
        fill: rgba(148, 163, 184, 0.16) !important;
        stroke: rgba(100, 116, 139, 0.55);
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces[style*="opacity: 0.5"] {
        opacity: 0.4 !important;
    }
    div[data-testid="stPlotlyChart"] g.legend g.traces:focus rect.legendtoggle,
    div[data-testid="stPlotlyChart"] g.legend g.traces:focus-within rect.legendtoggle {
        fill: rgba(59, 130, 246, 0.10) !important;
        stroke: #3B82F6;
        stroke-width: 1px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Excel Visualization Pipeline")

if st.query_params.to_dict():
    st.query_params.clear()

if not st.session_state.get("_browser_state_loaded", False):
    browser_state_component(
        key="browser_filter_state_reader",
        data={
            "mode": "read",
            "storageKey": "excel_visualization_pipeline.filters.v1",
        },
        default={"restored": None},
        on_restored_change=restore_browser_filters,
        width="content",
        height=1,
    )


database_file = PROJECT_ROOT / "data" / "local" / "analytics.sqlite3"
source_key = "cx_report_master"
config_file = PROJECT_ROOT / "config" / "parser.yaml"
initialize_database(database_file)

st.sidebar.subheader("Import dữ liệu")
import_mode_label = st.sidebar.selectbox(
    "Chế độ cập nhật dữ liệu",
    ["Toàn bộ snapshot", "Chỉ dữ liệu bổ sung"],
    help=(
        "Toàn bộ snapshot dùng khi workbook đại diện đầy đủ cho phạm vi trong file. "
        "Chỉ dữ liệu bổ sung dùng khi file chỉ chứa ngày/record mới; record vắng mặt sẽ không bị xóa."
    ),
)
import_mode = "full_snapshot" if import_mode_label == "Toàn bộ snapshot" else "incremental"
uploaded = st.sidebar.file_uploader("Chọn file Excel", type=["xlsx"])
preview_result = None
source_payload = None
source_name = None

if uploaded is None:
    st.sidebar.caption("Chưa chọn file · dashboard chỉ đọc dữ liệu hiện có từ SQLite.")
else:
    source_payload = uploaded.getvalue()
    source_name = uploaded.name
    preview_result = cached_preview(
        source_payload,
        source_name,
        str(config_file),
        config_file.stat().st_mtime_ns,
    )
    preview_manifest = preview_result.manifest
    st.sidebar.caption(
        f"Preview: {preview_manifest['record_count']:,} record · "
        f"{preview_manifest['date_count']} ngày · "
        f"{len(preview_result.report.errors)} lỗi · "
        f"{len(preview_result.report.warnings)} cảnh báo"
    )
    if preview_result.report.errors:
        st.sidebar.error("Quality gate chưa đạt; không thể import file này.")
    confirm_import = st.sidebar.button(
        "Xác nhận import",
        type="primary",
        disabled=bool(preview_result.report.errors),
        use_container_width=True,
    )
    if confirm_import:
        outcome = import_pipeline_result(
            database_file,
            source_key,
            source_name,
            source_payload,
            preview_result,
            config=ParserConfig.from_yaml(config_file),
            mode=import_mode,
            display_name="CX Report Master",
        )
        st.session_state["_last_import_feedback"] = {
            "source_hash": preview_manifest["source_hash"],
            "status": outcome.status,
            "run_id": outcome.run_id,
            "duplicate_of_run_id": outcome.duplicate_of_run_id,
            "inserted_count": outcome.inserted_count,
            "updated_count": outcome.updated_count,
            "unchanged_count": outcome.unchanged_count,
            "message": outcome.message,
        }

    feedback = st.session_state.get("_last_import_feedback", {})
    if feedback.get("source_hash") == preview_manifest["source_hash"]:
        if feedback.get("status") == "committed":
            st.sidebar.success(
                f"Đã lưu run #{feedback['run_id']}: +{feedback['inserted_count']}, "
                f"sửa {feedback['updated_count']}, giữ nguyên {feedback['unchanged_count']}."
            )
        elif feedback.get("status") == "duplicate":
            st.sidebar.info(
                f"File đã được lưu ở run #{feedback['duplicate_of_run_id']}; không tạo dữ liệu trùng."
            )
        elif feedback.get("status") == "rejected":
            st.sidebar.error(feedback.get("message") or "Import bị từ chối; SQLite không thay đổi.")

data = load_current_data(database_file, source_key)
entities = load_current_entities(database_file, source_key)
if data.empty or entities.empty:
    if preview_result is not None and preview_result.report.errors:
        st.error(f"Quality gate thất bại: {len(preview_result.report.errors)} lỗi.")
        st.dataframe(
            pd.DataFrame(issue.as_dict() for issue in preview_result.report.issues),
            width="stretch",
        )
    else:
        st.info("SQLite chưa có dữ liệu. Hãy chọn workbook, kiểm tra preview và bấm Xác nhận import.")
    st.stop()

saved_state = st.session_state.get("_restored_filters", {})
apply_restored_state = st.session_state.pop("_apply_restored_state", False)
if saved_state.get("source_key") not in {None, source_key}:
    saved_state = {}
    apply_restored_state = False

projects = sorted(data["project_label"].dropna().unique())
if apply_restored_state:
    requested_project = saved_state.get("project")
    st.session_state["project_filter"] = (
        requested_project if requested_project in projects else projects[0]
    )
selected_project = st.sidebar.selectbox(
    "Project",
    projects,
    key="project_filter",
    **widget_default(
        "index", option_index(projects, saved_state.get("project")), apply_restored_state
    ),
)
project_entities = entities[entities["project_label"] == selected_project].copy()
project_entities = project_entities.sort_values(["source_row", "entity_depth"])
project_data = data[data["project_label"] == selected_project].copy()

project_units = project_entities["unit_normalized"].dropna().nunique()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Project", selected_project)
c2.metric("Entity nodes", len(project_entities))
c3.metric("Units", project_units)
c4.metric("Records", len(project_data))

chartable_project_data = project_data[project_data["chart_value"].notna()].copy()
available_dates = sorted(pd.to_datetime(chartable_project_data["date"]).dt.date.unique())
if not available_dates:
    st.warning("Project không có dữ liệu dạng số để hiển thị.")
    st.stop()

st.sidebar.subheader("Khoảng thời gian")
range_options = ["10 ngày gần nhất", "Theo tuần", "Theo tháng", "Tùy chỉnh"]
if apply_restored_state:
    requested_range = saved_state.get("range")
    st.session_state["range_mode"] = (
        requested_range if requested_range in range_options else range_options[0]
    )
range_mode = st.sidebar.selectbox(
    "Chọn theo",
    range_options,
    key="range_mode",
    **widget_default(
        "index", option_index(range_options, saved_state.get("range")), apply_restored_state
    ),
)
recent_range = recent_data_range(available_dates, count=10)
overview_group_by = None
overview_period_count = None

if range_mode == "10 ngày gần nhất":
    start_date, end_date = recent_range.start, recent_range.end
    st.sidebar.caption(
        f"{start_date:%d/%m/%Y} – {end_date:%d/%m/%Y} "
        f"({recent_range.data_date_count} ngày có dữ liệu)"
    )
elif range_mode == "Theo tuần":
    overview_group_by = "week"
    ranges = aggregation_period_ranges(available_dates, overview_group_by)
    default_count = min(8, len(ranges))
    try:
        requested_count = int(saved_state.get("overview_period_count", default_count))
    except (TypeError, ValueError):
        requested_count = default_count
    requested_count = min(max(requested_count, 1), len(ranges))
    if apply_restored_state:
        st.session_state["overview_week_count"] = requested_count
    overview_period_count = int(
        st.sidebar.number_input(
            "Số tuần so sánh",
            min_value=1,
            max_value=len(ranges),
            step=1,
            key="overview_week_count",
            **widget_default("value", requested_count, apply_restored_state),
        )
    )
    selected_ranges = ranges[-overview_period_count:]
    start_date = max(selected_ranges[0].start, available_dates[0])
    end_date = min(selected_ranges[-1].end, available_dates[-1])
    st.sidebar.caption(
        f"So sánh {overview_period_count} tuần lịch · "
        f"{start_date:%d/%m/%Y} – {end_date:%d/%m/%Y}"
    )
elif range_mode == "Theo tháng":
    overview_group_by = "month"
    ranges = aggregation_period_ranges(available_dates, overview_group_by)
    default_count = min(6, len(ranges))
    try:
        requested_count = int(saved_state.get("overview_period_count", default_count))
    except (TypeError, ValueError):
        requested_count = default_count
    requested_count = min(max(requested_count, 1), len(ranges))
    if apply_restored_state:
        st.session_state["overview_month_count"] = requested_count
    overview_period_count = int(
        st.sidebar.number_input(
            "Số tháng so sánh",
            min_value=1,
            max_value=len(ranges),
            step=1,
            key="overview_month_count",
            **widget_default("value", requested_count, apply_restored_state),
        )
    )
    selected_ranges = ranges[-overview_period_count:]
    start_date = max(selected_ranges[0].start, available_dates[0])
    end_date = min(selected_ranges[-1].end, available_dates[-1])
    st.sidebar.caption(
        f"So sánh {overview_period_count} tháng lịch · "
        f"{start_date:%d/%m/%Y} – {end_date:%d/%m/%Y}"
    )
else:
    restored_start_date = stored_date(
        saved_state, "start", recent_range.start, available_dates[0], available_dates[-1]
    )
    restored_end_date = stored_date(
        saved_state, "end", recent_range.end, available_dates[0], available_dates[-1]
    )
    if apply_restored_state:
        st.session_state["custom_start_date"] = restored_start_date
        st.session_state["custom_end_date"] = restored_end_date
    start_date = st.sidebar.date_input(
        "Từ ngày",
        min_value=available_dates[0],
        max_value=available_dates[-1],
        key="custom_start_date",
        **widget_default("value", restored_start_date, apply_restored_state),
    )
    end_date = st.sidebar.date_input(
        "Đến ngày",
        min_value=available_dates[0],
        max_value=available_dates[-1],
        key="custom_end_date",
        **widget_default("value", restored_end_date, apply_restored_state),
    )
if start_date > end_date:
    st.error("Từ ngày phải nhỏ hơn hoặc bằng Đến ngày.")
    st.stop()

st.subheader(f"Dashboard — {selected_project}")
st.caption(
    "Dashboard mở trực tiếp entity cấp cao nhất trong cây. Có thể chuyển sang node khác hoặc xem các node con trực tiếp."
)
st.subheader("Overview")
entity_lookup = project_entities.set_index("entity_id")
entity_ids = list(project_entities["entity_id"])
combo_metrics = ["Tổng số", "Báo sai/Lỗi", "% báo sai"]
initial_entity_id = initial_entity_with_data(
    project_entities,
    project_data,
    start_date,
    end_date,
    combo_metrics,
)
if apply_restored_state:
    requested_entity = saved_state.get("entity")
    st.session_state["entity_navigator"] = (
        requested_entity if requested_entity in entity_ids else initial_entity_id
    )
selected_entity_id = st.selectbox(
    "**Hierarchy Navigator**",
    entity_ids,
    format_func=lambda entity_id: hierarchy_label(entity_lookup.loc[entity_id]),
    key="entity_navigator",
    **widget_default(
        "index",
        option_index(
            entity_ids,
            saved_state.get("entity"),
            entity_ids.index(initial_entity_id),
        ),
        apply_restored_state,
    ),
)

child_ids = list(project_entities.loc[project_entities["parent_entity_id"] == selected_entity_id, "entity_id"])
scope_options = ["Node đã chọn"]
if child_ids:
    scope_options.append("Các node con trực tiếp")
if apply_restored_state:
    requested_scope = saved_state.get("scope")
    st.session_state["entity_scope"] = (
        requested_scope if requested_scope in scope_options else scope_options[0]
    )
selected_scope = st.radio(
    "**Phạm vi**",
    scope_options,
    horizontal=True,
    key="entity_scope",
    **widget_default(
        "index", option_index(scope_options, saved_state.get("scope")), apply_restored_state
    ),
)
scope_ids = child_ids if selected_scope == "Các node con trực tiếp" else [selected_entity_id]
detail_data = data[data["entity_id"].isin(scope_ids)].copy()

metric_data = detail_data[detail_data["metric_normalized"].isin(combo_metrics)].copy()
metric_dates = pd.to_datetime(metric_data["date"]).dt.date
range_data = metric_data[(metric_dates >= start_date) & (metric_dates <= end_date)]

if range_data.empty:
    st.info("Không có dữ liệu cho ba metric trong khoảng ngày đã chọn.")
else:
    chart_entity_ids = [
        entity_id
        for entity_id in scope_ids
        if not range_data[range_data["entity_id"] == entity_id].empty
    ]
    if len(chart_entity_ids) > 1:
        st.caption("Các biểu đồ entity được xếp theo lưới, tối đa 2 biểu đồ trên mỗi hàng.")
    for row_start in range(0, len(chart_entity_ids), 2):
        row_entity_ids = chart_entity_ids[row_start : row_start + 2]
        chart_columns = st.columns(len(row_entity_ids), gap="medium")
        for chart_column, entity_id in zip(chart_columns, row_entity_ids):
            with chart_column:
                entity_data = range_data[range_data["entity_id"] == entity_id]
                entity = entity_lookup.loc[entity_id]
                entity_units = list(entity_data["effective_unit"].dropna().unique())
                entity_unit = str(entity_units[0]) if entity_units else "Chưa xác định từ Excel"
                st.markdown(
                    '<div style="font-size:14px;font-weight:600;margin-bottom:0.5rem">'
                    f"Effective Unit: {escape(entity_unit)}"
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    (
                        build_period_metric_combo_chart(
                            entity_data,
                            start_date,
                            end_date,
                            overview_group_by,
                            f"{entity['entity_label']} — {entity_unit}",
                        )
                        if overview_group_by
                        else build_metric_combo_chart(
                            entity_data,
                            f"{entity['entity_label']} — {entity_unit}",
                        )
                    ),
                    width="stretch",
                )
                missing_metrics = [
                    metric
                    for metric in combo_metrics
                    if metric not in set(entity_data["metric_normalized"])
                ]
                if missing_metrics:
                    st.caption(f"Thiếu metric: {', '.join(missing_metrics)}")

st.subheader("Thống kê SUM / AVG theo kỳ")
st.caption(
    "Khu vực này dùng toàn bộ lịch sử của entity, độc lập với khoảng ngày của biểu đồ chi tiết ở sidebar. "
    "SUM của Tổng số/Cảnh báo và Báo sai/Lỗi được vẽ bằng cột; AVG/ngày = SUM / số ngày hợp lệ "
    "và được vẽ bằng đường. % báo sai không tham gia."
)
period_labels = {
    "Theo ngày": "day",
    "Theo tuần": "week",
    "Theo tháng": "month",
    "Theo quý": "quarter",
}
period_defaults = {"day": 10, "week": 8, "month": 6, "quarter": 4}
statistics_source = metric_data[
    metric_data["metric_normalized"].isin(["Tổng số", "Báo sai/Lỗi"])
].copy()

period_control, range_control, mode_control = st.columns(3)
with period_control:
    period_label_options = list(period_labels)
    if apply_restored_state:
        requested_statistics_group = saved_state.get("statistics_group")
        st.session_state["statistics_group"] = (
            requested_statistics_group
            if requested_statistics_group in period_label_options
            else period_label_options[1]
        )
    selected_period_label = st.selectbox(
        "Nhóm thống kê theo",
        period_label_options,
        key="statistics_group",
        **widget_default(
            "index",
            option_index(
                period_label_options,
                saved_state.get("statistics_group"),
                1,
            ),
            apply_restored_state,
        ),
    )
with range_control:
    statistics_range_options = ["Các kỳ gần nhất", "Toàn bộ dữ liệu", "Chọn khoảng kỳ"]
    if apply_restored_state:
        requested_statistics_range = saved_state.get("statistics_range")
        st.session_state["statistics_range"] = (
            requested_statistics_range
            if requested_statistics_range in statistics_range_options
            else statistics_range_options[0]
        )
    selected_statistics_range = st.selectbox(
        "Phạm vi thống kê",
        statistics_range_options,
        key="statistics_range",
        **widget_default(
            "index",
            option_index(
                statistics_range_options,
                saved_state.get("statistics_range"),
            ),
            apply_restored_state,
        ),
    )
with mode_control:
    stat_mode_options = ["SUM", "AVG/ngày"]
    requested_stat_modes = saved_state.get("stat_modes")
    if requested_stat_modes == "none":
        default_stat_modes = []
    elif requested_stat_modes:
        default_stat_modes = [
            mode for mode in requested_stat_modes.split(",") if mode in stat_mode_options
        ]
    else:
        default_stat_modes = stat_mode_options
    if apply_restored_state:
        st.session_state["statistics_modes"] = default_stat_modes
    selected_stat_modes = st.multiselect(
        "Chỉ số hiển thị",
        stat_mode_options,
        key="statistics_modes",
        **widget_default("default", default_stat_modes, apply_restored_state),
    )

statistics_group = period_labels[selected_period_label]
statistics_dates = sorted(
    pd.to_datetime(statistics_source["date"], errors="coerce").dropna().dt.date.unique()
)
all_statistics_periods = aggregation_period_ranges(statistics_dates, statistics_group)
if apply_restored_state:
    st.session_state["include_incomplete"] = (
        saved_state.get("include_incomplete", "1") != "0"
    )
include_incomplete = st.checkbox(
    "Bao gồm kỳ chưa đầy đủ",
    key="include_incomplete",
    help=(
        "Kỳ đầu hoặc cuối không phủ đủ ranh giới lịch vẫn được tính trên số ngày thực tế có trong nguồn. "
        "Tắt tùy chọn này để chỉ so sánh các kỳ lịch hoàn chỉnh."
    ),
    **widget_default(
        "value", saved_state.get("include_incomplete", "1") != "0", apply_restored_state
    ),
)
available_statistics_periods = [
    period for period in all_statistics_periods if include_incomplete or period.is_complete
]


def statistics_period_label(period):
    suffix = " · chưa đầy đủ" if not period.is_complete else ""
    return f"{period.label}{suffix}"


selected_statistics_periods = []
recent_period_count = None
statistics_period_from = None
statistics_period_to = None
if not available_statistics_periods:
    st.info("Không có kỳ hoàn chỉnh trong dữ liệu hiện tại. Hãy bật ‘Bao gồm kỳ chưa đầy đủ’.")
elif selected_statistics_range == "Các kỳ gần nhất":
    default_period_count = min(period_defaults[statistics_group], len(available_statistics_periods))
    try:
        requested_period_count = int(saved_state.get("period_count", default_period_count))
    except (TypeError, ValueError):
        requested_period_count = default_period_count
    requested_period_count = min(max(requested_period_count, 1), len(available_statistics_periods))
    if apply_restored_state:
        st.session_state["recent_period_count"] = requested_period_count
    recent_period_count = int(
        st.number_input(
            "Số kỳ gần nhất",
            min_value=1,
            max_value=len(available_statistics_periods),
            step=1,
            key="recent_period_count",
            **widget_default("value", requested_period_count, apply_restored_state),
        )
    )
    selected_statistics_periods = available_statistics_periods[-recent_period_count:]
elif selected_statistics_range == "Toàn bộ dữ liệu":
    selected_statistics_periods = available_statistics_periods
else:
    requested_period_from = saved_state.get("statistics_from")
    period_from_index = next(
        (
            index
            for index, value in enumerate(available_statistics_periods)
            if value.start.isoformat() == requested_period_from
        ),
        0,
    )
    if apply_restored_state:
        st.session_state["statistics_period_from"] = available_statistics_periods[
            period_from_index
        ]
    period_from_control, period_to_control = st.columns(2)
    with period_from_control:
        statistics_period_from = st.selectbox(
            "Từ kỳ",
            available_statistics_periods,
            format_func=statistics_period_label,
            key="statistics_period_from",
            **widget_default("index", period_from_index, apply_restored_state),
        )
    valid_period_ends = [
        period for period in available_statistics_periods if period.start >= statistics_period_from.start
    ]
    requested_period_to = saved_state.get("statistics_to")
    period_to_index = next(
        (
            index
            for index, value in enumerate(valid_period_ends)
            if value.start.isoformat() == requested_period_to
        ),
        len(valid_period_ends) - 1,
    )
    if apply_restored_state:
        st.session_state["statistics_period_to"] = valid_period_ends[period_to_index]
    with period_to_control:
        statistics_period_to = st.selectbox(
            "Đến kỳ",
            valid_period_ends,
            format_func=statistics_period_label,
            key="statistics_period_to",
            **widget_default("index", period_to_index, apply_restored_state),
        )
    selected_statistics_periods = [
        period
        for period in available_statistics_periods
        if statistics_period_from.start <= period.start <= statistics_period_to.start
    ]

if not selected_stat_modes:
    st.info("Chọn ít nhất một chế độ SUM hoặc AVG/ngày để hiển thị thống kê.")
elif selected_statistics_periods:
    data_window_start = statistics_dates[0]
    data_window_end = statistics_dates[-1]
    statistics_start_date = max(selected_statistics_periods[0].start, data_window_start)
    statistics_end_date = min(selected_statistics_periods[-1].end, data_window_end)
    selected_statistics_dates = pd.to_datetime(statistics_source["date"]).dt.date
    selected_statistics_data = statistics_source[
        (selected_statistics_dates >= statistics_start_date)
        & (selected_statistics_dates <= statistics_end_date)
    ]
    statistic_entity_ids = [
        entity_id
        for entity_id in scope_ids
        if not selected_statistics_data[selected_statistics_data["entity_id"] == entity_id].empty
    ]
    incomplete_count = sum(not period.is_complete for period in selected_statistics_periods)
    incomplete_note = f" · {incomplete_count} kỳ chưa đầy đủ" if incomplete_count else ""
    st.caption(
        f"Đang tính {len(selected_statistics_periods)} kỳ: "
        f"{statistics_start_date:%d/%m/%Y} – {statistics_end_date:%d/%m/%Y}{incomplete_note}."
    )
    for row_start in range(0, len(statistic_entity_ids), 2):
        row_entity_ids = statistic_entity_ids[row_start : row_start + 2]
        statistic_columns = st.columns(len(row_entity_ids), gap="medium")
        for statistic_column, entity_id in zip(statistic_columns, row_entity_ids):
            with statistic_column:
                entity_data = statistics_source[statistics_source["entity_id"] == entity_id]
                entity = entity_lookup.loc[entity_id]
                st.plotly_chart(
                    build_period_statistics_chart(
                        entity_data,
                        statistics_start_date,
                        statistics_end_date,
                        statistics_group,
                        selected_stat_modes,
                        f"{entity['entity_label']} — {selected_period_label}",
                        coverage_data=project_data,
                    ),
                    width="stretch",
                )


audit_columns = [
    "date",
    "project_label",
    "entity_path",
    "entity_level",
    "effective_unit",
    "metric_original",
    "metric_normalized",
    "raw_value",
    "display_value",
    "chart_value",
    "value_kind",
    "data_note",
    "sheet_name",
    "cell_address",
    "number_format",
    "parser_rule",
    "parser_confidence",
    "validation_status",
]
with st.expander("Audit Table — dữ liệu nguồn"):
    st.caption(
        "Tooltip phục vụ đọc nhanh; bảng này giữ thông tin đầy đủ để truy vết về workbook và ô nguồn. "
        "not_recorded là ô trống/không ghi nhận trong ngày; source_marker là ký hiệu '-' hoặc N/A "
        "được giữ nguyên để đánh dấu dữ liệu khác bản chất; default_zero_rate là % báo sai được "
        "mặc định 0% khi không ghi nhận Báo sai/Lỗi hoặc số lỗi bằng 0."
    )
    audit_data = range_data.loc[:, audit_columns].sort_values(
        ["entity_path", "date", "metric_normalized"]
    )
    # raw_value intentionally preserves mixed Excel types in the pipeline. Cast only the
    # displayed slice so PyArrow receives one stable type without duplicating the full dataset.
    audit_data["raw_value"] = audit_data["raw_value"].astype("string")
    st.dataframe(
        audit_data,
        width="stretch",
        hide_index=True,
    )


st.divider()
st.subheader("So sánh nhiều entity")
st.caption(
    "Chọn từ 2 đến 3 entity cùng Effective Unit. Có thể so sánh các cấp hierarchy khác nhau; "
    "chọn một metric cần xem và mỗi entity sẽ có một màu riêng."
)
if apply_restored_state:
    requested_comparison_metric = saved_state.get("comparison_metric")
    st.session_state["comparison_metric"] = (
        requested_comparison_metric
        if requested_comparison_metric in combo_metrics
        else "Báo sai/Lỗi"
    )
comparison_metric = st.selectbox(
    "Metric so sánh",
    combo_metrics,
    key="comparison_metric",
    **widget_default(
        "index",
        option_index(
            combo_metrics,
            saved_state.get("comparison_metric"),
            combo_metrics.index("Báo sai/Lỗi"),
        ),
        apply_restored_state,
    ),
)
comparison_dates = pd.to_datetime(project_data["date"]).dt.date
comparison_source = project_data[
    (project_data["metric_normalized"] == comparison_metric)
    & project_data["chart_value"].notna()
    & (comparison_dates >= start_date)
    & (comparison_dates <= end_date)
].copy()
comparison_candidate_ids = set(comparison_source["entity_id"])
comparison_entities = project_entities[
    project_entities["entity_id"].isin(comparison_candidate_ids)
    & project_entities["effective_unit"].notna()
].copy()
comparison_lookup = comparison_entities.set_index("entity_id")
comparison_ids = list(comparison_entities["entity_id"])
requested_comparison_ids = [
    entity_id
    for entity_id in saved_state.get("comparison_entities", "").split(",")
    if entity_id in comparison_ids
][:3]
comparison_entities_key = f"comparison_entities::{selected_project}::{comparison_metric}"
if apply_restored_state:
    st.session_state[comparison_entities_key] = requested_comparison_ids
selected_comparison_ids = st.multiselect(
    "Entities so sánh",
    comparison_ids,
    max_selections=3,
    format_func=lambda entity_id: hierarchy_label(comparison_lookup.loc[entity_id]),
    key=comparison_entities_key,
    **widget_default("default", requested_comparison_ids, apply_restored_state),
)

if len(selected_comparison_ids) < 2:
    st.info("Chọn ít nhất 2 và tối đa 3 entity để tạo biểu đồ so sánh.")
else:
    selected_entities = comparison_lookup.loc[selected_comparison_ids]
    selected_units = selected_entities["effective_unit"].dropna().unique()
    if len(selected_units) != 1:
        st.error("Các entity được chọn phải có cùng Effective Unit.")
    else:
        comparison_data = project_data[
            project_data["entity_id"].isin(selected_comparison_ids)
            & project_data["metric_normalized"].isin(combo_metrics)
            & (comparison_dates >= start_date)
            & (comparison_dates <= end_date)
        ].copy()
        st.plotly_chart(
            build_multi_entity_metric_chart(
                comparison_data,
                comparison_metric,
                f"So sánh {comparison_metric} của {len(selected_comparison_ids)} entity — {selected_units[0]}",
                group_by=overview_group_by,
                start_date=start_date,
                end_date=end_date,
            ),
            width="stretch",
        )

current_state = {
    "source_key": source_key,
    "project": selected_project,
    "range": range_mode,
    "start": start_date.isoformat(),
    "end": end_date.isoformat(),
    "entity": selected_entity_id,
    "scope": selected_scope,
    "statistics_group": selected_period_label,
    "statistics_range": selected_statistics_range,
    "stat_modes": ",".join(selected_stat_modes) if selected_stat_modes else "none",
    "include_incomplete": "1" if include_incomplete else "0",
    "comparison_metric": comparison_metric,
}
if selected_comparison_ids:
    current_state["comparison_entities"] = ",".join(selected_comparison_ids)
if overview_period_count is not None:
    current_state["overview_period_count"] = str(overview_period_count)
if recent_period_count is not None:
    current_state["period_count"] = str(recent_period_count)
if statistics_period_from is not None:
    current_state["statistics_from"] = statistics_period_from.start.isoformat()
if statistics_period_to is not None:
    current_state["statistics_to"] = statistics_period_to.start.isoformat()

if st.session_state.get("_browser_state_loaded", False):
    browser_state_component(
        key="browser_filter_state_writer",
        data={
            "mode": "write",
            "storageKey": "excel_visualization_pipeline.filters.v1",
            "state": current_state,
        },
        width="content",
        height=1,
    )

preview_warnings = preview_result.report.warnings if preview_result is not None else []
with st.expander(f"Cảnh báo chất lượng của file preview ({len(preview_warnings)})"):
    if preview_warnings:
        st.dataframe(pd.DataFrame(issue.as_dict() for issue in preview_warnings), width="stretch")
    else:
        st.caption("Chưa chọn file preview hoặc file không có warning.")

with st.expander("Lịch sử import SQLite"):
    import_history = load_import_history(database_file, source_key)
    history_columns = [
        "attempt_id",
        "run_id",
        "submitted_file_name",
        "requested_mode",
        "attempt_status",
        "started_at",
        "committed_at",
        "inserted_count",
        "updated_count",
        "unchanged_count",
        "restored_count",
        "deleted_count",
        "lineage_changed_count",
        "error_count",
        "warning_count",
    ]
    st.dataframe(import_history.loc[:, history_columns], width="stretch", hide_index=True)

st.download_button(
    "Tải toàn bộ normalized CSV",
    data.to_csv(index=False).encode("utf-8-sig"),
    file_name="normalized_data.csv",
    mime="text/csv",
)
