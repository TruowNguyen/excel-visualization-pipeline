from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ..storage.aggregates import register_aggregate_snapshots
from ..storage.connection import connect_database
from ..storage.migrations import initialize_database
from .analytics import TrendComputation, TrendPoint


class EvidenceBuilder:
    def __init__(self, db_path: str | Path, source_key: str):
        self.db_path = Path(db_path)
        self.source_key = source_key

    def committed_version(self) -> tuple[int, str]:
        initialize_database(self.db_path)
        with connect_database(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT ir.run_id, irpr.import_ref
                FROM import_runs ir
                JOIN data_sources ds ON ds.source_id = ir.source_id
                JOIN import_run_public_refs irpr ON irpr.run_id = ir.run_id
                WHERE ds.source_key = ? AND ir.status = 'committed'
                ORDER BY ir.run_id DESC LIMIT 1
                """,
                (self.source_key,),
            ).fetchone()
        if row is None:
            raise ValueError("Chưa có lần nhập dữ liệu thành công để phân tích.")
        return int(row["run_id"]), str(row["import_ref"])

    def build(
        self,
        computation: TrendComputation,
        *,
        project: str,
        entity: dict[str, Any],
        source_run_id: int,
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        point_groups = (
            ("series", computation.points),
            ("history", computation.historical_points),
        )
        for period_kind, points in point_groups:
            for index, point in enumerate(points):
                target = self._target(
                    computation, point, project=project, entity=entity,
                    source_run_id=source_run_id,
                )
                evidence.append({
                    "evidenceId": point.evidence_id,
                    "period": period_kind,
                    "periodIndex": index,
                    "periodStart": point.period_start.isoformat(),
                    "periodEnd": point.period_end.isoformat(),
                    "periodLabel": point.period_label,
                    "observedDate": point.period_end.isoformat(),
                    "target": target,
                })
        return evidence

    def _target(
        self,
        computation: TrendComputation,
        point: TrendPoint,
        *,
        project: str,
        entity: dict[str, Any],
        source_run_id: int,
    ) -> dict[str, Any]:
        numeric = point.rows[point.rows["chart_value"].notna()]
        if (
            computation.group_by == "day"
            and computation.metric_code in {"total", "error"}
            and len(numeric) == 1
            and not point.inferred_zero
        ):
            row = numeric.iloc[0]
            observation_ref, lineage_ref = row.get("observation_ref"), row.get("lineage_ref")
            if not isinstance(observation_ref, str) or not observation_ref.startswith("obs_"):
                raise ValueError("Điểm dữ liệu chưa có thông tin nguồn hợp lệ.")
            if not isinstance(lineage_ref, str) or not lineage_ref.startswith("lin_"):
                raise ValueError("Điểm dữ liệu chưa có thông tin nguồn hợp lệ.")
            return {
                "kind": "exact", "observationRef": observation_ref,
                "lineageRef": lineage_ref,
            }

        members: list[dict[str, Any]] = []
        for row in point.rows.sort_values(["date", "metric_code"]).itertuples(index=False):
            lineage_ref = getattr(row, "lineage_ref", None)
            if not isinstance(lineage_ref, str) or not lineage_ref.startswith("lin_"):
                raise ValueError("Không thể lưu bằng chứng tổng hợp vì thiếu thông tin nguồn.")
            label = str(getattr(row, "metric_normalized"))
            value = getattr(row, "chart_value", None)
            paired_eligible = bool(getattr(row, "ai_included", True))
            included = value is not None and pd.notna(value) and paired_eligible
            role = "value"
            if computation.metric_code == "error_rate":
                role = "numerator" if label == "Báo sai/Lỗi" else "denominator"
            elif point.inferred_zero and label == "Tổng số":
                role = "coverage"
            members.append({
                "lineageRef": lineage_ref,
                "role": role if included else ("excluded" if value is not None and pd.notna(value) else "missing"),
                "included": included,
                "contributionValue": float(value) if included else None,
                "note": (
                    "Giá trị nguồn dùng trong phép tính."
                    if included else
                    "Giá trị bị loại vì ngày không có đủ cặp tử số/mẫu số hợp lệ."
                    if value is not None and pd.notna(value) else
                    "Giá trị thiếu không được tính như 0."
                ),
            })
        if not members:
            raise ValueError("Không có dữ liệu nguồn cho điểm phân tích.")
        hierarchy = [part.strip() for part in str(entity["entity_path"]).replace(" > ", "/").split("/") if part.strip()]
        spec = {
            "context": {
                "project": project,
                "entity": {
                    "ref": entity["entity_id"], "label": entity["entity_label"],
                    "hierarchyPath": hierarchy, "effectiveUnit": (
                        None if pd.isna(entity.get("effective_unit")) else entity.get("effective_unit")
                    ),
                },
                "metric": computation.metric_display_name,
                "series": "Tóm tắt xu hướng tự động",
                "period": {"start": point.period_start.isoformat(), "end": point.period_end.isoformat()},
                "observedThrough": computation.window_end.isoformat(),
            },
            "result": {"chartValue": point.value, "displayValue": self._point_display(computation, point.value)},
            "aggregation": {
                "ruleCode": computation.aggregation_rule,
                "explanation": (
                    "Tổng Báo sai/Lỗi chia Tổng số rồi nhân 100; không lấy trung bình tỷ lệ ngày."
                    if computation.metric_code == "error_rate" else
                    "Cộng các giá trị trong kỳ; giá trị 0 chỉ được suy ra khi Tổng số đã ghi nhận và ô lỗi để trống, không phải source marker."
                ),
                "valueObservationCount": sum(1 for item in members if item["included"] and item["role"] != "coverage"),
                "coverageObservationCount": sum(1 for item in members if item["included"] and item["role"] == "coverage"),
                "eligibleDayCount": point.observed_day_count,
                "calendarDayCount": point.expected_day_count,
                "inferredZero": point.inferred_zero,
            },
            "members": members,
            "sourceRunId": source_run_id,
        }
        aggregate_ref = register_aggregate_snapshots(
            self.db_path, self.source_key, project, [spec]
        )[0]
        return {"kind": "aggregate", "aggregateRef": aggregate_ref}

    @staticmethod
    def _point_display(computation: TrendComputation, value: float) -> str:
        if computation.metric_code == "error_rate":
            return f"{value:.2f}%"
        return f"{value:,.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def checksum(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(encoded.encode("utf-8")).hexdigest()
