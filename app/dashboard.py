from __future__ import annotations

from html import escape
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from excel_visualization_pipeline.pipeline import run_pipeline  # noqa: E402
from excel_visualization_pipeline.entity_selection import initial_entity_with_data  # noqa: E402
from excel_visualization_pipeline.date_ranges import (  # noqa: E402
    month_ranges,
    recent_data_range,
    week_ranges,
)
from excel_visualization_pipeline.visualization import (  # noqa: E402
    build_metric_average_chart,
    build_metric_combo_chart,
    build_multi_entity_metric_chart,
    prepare_metric_averages,
)


def hierarchy_label(row: pd.Series) -> str:
    indent = "　" * int(row["entity_depth"])
    unit = f" · {row['effective_unit']}" if pd.notna(row["effective_unit"]) else " · chưa có unit"
    return f"{indent}{row['entity_label']}{unit}"


st.set_page_config(page_title="Excel Quality Dashboard", layout="wide")
st.title("Excel Visualization Pipeline")


default_file = PROJECT_ROOT.parent / "test data for CX report dashboard.xlsx"
uploaded = st.sidebar.file_uploader("Chọn file Excel", type=["xlsx"])
source = uploaded if uploaded is not None else default_file

if not source or (isinstance(source, Path) and not source.exists()):
    st.info("Hãy tải lên một file .xlsx để bắt đầu.")
    st.stop()

result = run_pipeline(source, PROJECT_ROOT / "config" / "parser.yaml")
data = result.data.copy()
manifest = result.manifest

if result.report.errors:
    st.error(f"Quality gate thất bại: {len(result.report.errors)} lỗi. Biểu đồ không được render.")
    st.dataframe(pd.DataFrame(issue.as_dict() for issue in result.report.issues), use_container_width=True)
    st.stop()

projects = sorted(data["project_label"].dropna().unique())
selected_project = st.sidebar.selectbox("Project", projects)
project_entities = result.entities[result.entities["project_label"] == selected_project].copy()
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
range_mode = st.sidebar.selectbox(
    "Chọn theo",
    ["10 ngày gần nhất", "Theo tuần", "Theo tháng", "Tùy chỉnh"],
)
recent_range = recent_data_range(available_dates, count=10)

if range_mode == "10 ngày gần nhất":
    start_date, end_date = recent_range.start, recent_range.end
    st.sidebar.caption(
        f"{start_date:%d/%m/%Y} – {end_date:%d/%m/%Y} "
        f"({recent_range.data_date_count} ngày có dữ liệu)"
    )
elif range_mode == "Theo tuần":
    ranges = week_ranges(available_dates)
    selected_range = st.sidebar.selectbox(
        "Chọn tuần",
        ranges,
        format_func=lambda value: f"{value.label} · {value.data_date_count} ngày dữ liệu",
    )
    start_date, end_date = selected_range.start, selected_range.end
elif range_mode == "Theo tháng":
    ranges = month_ranges(available_dates)
    selected_range = st.sidebar.selectbox(
        "Chọn tháng",
        ranges,
        format_func=lambda value: f"{value.label} · {value.data_date_count} ngày dữ liệu",
    )
    start_date, end_date = selected_range.start, selected_range.end
else:
    start_date = st.sidebar.date_input(
        "Từ ngày",
        value=recent_range.start,
        min_value=available_dates[0],
        max_value=available_dates[-1],
    )
    end_date = st.sidebar.date_input(
        "Đến ngày",
        value=recent_range.end,
        min_value=available_dates[0],
        max_value=available_dates[-1],
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
selected_entity_id = st.selectbox(
    "**Hierarchy Navigator**",
    entity_ids,
    index=entity_ids.index(initial_entity_id),
    format_func=lambda entity_id: hierarchy_label(entity_lookup.loc[entity_id]),
)

child_ids = list(project_entities.loc[project_entities["parent_entity_id"] == selected_entity_id, "entity_id"])
scope_options = ["Node đã chọn"]
if child_ids:
    scope_options.append("Các node con trực tiếp")
selected_scope = st.radio("**Phạm vi**", scope_options, horizontal=True)
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
                    build_metric_combo_chart(
                        entity_data,
                        f"{entity['entity_label']} — {entity_unit}",
                    ),
                    use_container_width=True,
                )
                missing_metrics = [
                    metric
                    for metric in combo_metrics
                    if metric not in set(entity_data["metric_normalized"])
                ]
                if missing_metrics:
                    st.caption(f"Thiếu metric: {', '.join(missing_metrics)}")

average_data = prepare_metric_averages(range_data)
if not average_data.empty:
    st.subheader("Trung bình trong khoảng đã chọn")
    st.caption(
        "Chỉ tính Tổng số và Báo sai/Lỗi trên các ngày thực sự có dữ liệu; "
        "giá trị 0 được giữ lại, dữ liệu thiếu và % báo sai không tham gia."
    )
    st.plotly_chart(
        build_metric_average_chart(range_data, start_date, end_date),
        use_container_width=True,
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
    "sheet_name",
    "cell_address",
    "number_format",
    "parser_rule",
    "parser_confidence",
    "validation_status",
]
with st.expander("Audit Table — dữ liệu nguồn"):
    st.caption(
        "Tooltip phục vụ đọc nhanh; bảng này giữ thông tin đầy đủ để truy vết về workbook và ô nguồn."
    )
    st.dataframe(
        range_data[audit_columns].sort_values(["entity_path", "date", "metric_normalized"]),
        use_container_width=True,
        hide_index=True,
    )


st.divider()
st.subheader("So sánh nhiều entity")
st.caption(
    "Chọn từ 2 đến 3 entity cùng Effective Unit. Có thể so sánh các cấp hierarchy khác nhau; "
    "chọn một metric cần xem và mỗi entity sẽ có một màu riêng."
)
comparison_metric = st.selectbox(
    "Metric so sánh",
    combo_metrics,
    index=combo_metrics.index("Báo sai/Lỗi"),
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
selected_comparison_ids = st.multiselect(
    "Entities so sánh",
    comparison_ids,
    max_selections=3,
    format_func=lambda entity_id: hierarchy_label(comparison_lookup.loc[entity_id]),
    key=f"comparison_entities::{selected_project}::{comparison_metric}",
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
            ),
            use_container_width=True,
        )

with st.expander(f"Cảnh báo chất lượng ({len(result.report.warnings)})"):
    st.dataframe(pd.DataFrame(issue.as_dict() for issue in result.report.warnings), use_container_width=True)

st.download_button(
    "Tải toàn bộ normalized CSV",
    result.data.to_csv(index=False).encode("utf-8-sig"),
    file_name="normalized_data.csv",
    mime="text/csv",
)
