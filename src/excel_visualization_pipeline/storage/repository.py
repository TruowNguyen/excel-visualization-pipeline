from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from .connection import connect_database
from .migrations import initialize_database


class LineageNotFoundError(LookupError):
    pass


class LineageMismatchError(ValueError):
    pass


def _source_clause(source_key: str | None) -> tuple[str, list[Any]]:
    if source_key is None:
        return "", []
    return " AND ds.source_key = ?", [source_key]


def load_current_entities(
    db_path: str | Path,
    source_key: str | None = None,
    project_id: str | None = None,
) -> pd.DataFrame:
    initialize_database(db_path)
    query = """
        SELECT e.*
        FROM v_current_entities e
        JOIN data_sources ds ON ds.source_id = e.source_id
        WHERE 1 = 1
    """
    source_sql, parameters = _source_clause(source_key)
    query += source_sql
    if project_id is not None:
        query += " AND e.project_id = ?"
        parameters.append(project_id)
    query += " ORDER BY e.project_id, e.source_row, e.entity_depth, e.db_entity_id"
    with connect_database(db_path) as connection:
        return pd.read_sql_query(query, connection, params=parameters)


def _restore_raw_value(value: Any, value_type: str) -> Any:
    if value_type == "null":
        return None
    if value_type == "boolean":
        return value == "true"
    if value_type == "integer":
        return int(value)
    if value_type == "number":
        return float(value)
    return value


def _add_compatibility_columns(data: pd.DataFrame, entities: pd.DataFrame) -> pd.DataFrame:
    if data.empty:
        for column in ("entity_key", "project", "section", "item", "unit"):
            data[column] = pd.Series(dtype="object")
        return data
    lookup = entities.set_index("entity_id", drop=False).to_dict("index")

    def section_label(entity_id: str) -> str | None:
        current = lookup.get(entity_id)
        visited: set[str] = set()
        while current is not None and current["entity_id"] not in visited:
            visited.add(current["entity_id"])
            if current["entity_level"] == "section":
                return current["entity_label"]
            parent = current.get("parent_entity_id")
            current = lookup.get(parent) if parent else None
        return None

    data["entity_key"] = data["entity_id"]
    data["project"] = data["project_label"]
    data["section"] = data["entity_id"].map(section_label)
    data["item"] = data.apply(
        lambda row: row["entity_label"]
        if row["entity_level"] not in {"project", "section"}
        else None,
        axis=1,
    )
    data["unit"] = data["effective_unit"]
    return data


def load_current_data(
    db_path: str | Path,
    source_key: str | None = None,
    project_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    initialize_database(db_path)
    query = """
        SELECT o.*
        FROM v_current_observations o
        JOIN data_sources ds ON ds.source_id = o.source_id
        WHERE 1 = 1
    """
    source_sql, parameters = _source_clause(source_key)
    query += source_sql
    if project_id is not None:
        query += " AND o.project_id = ?"
        parameters.append(project_id)
    if start_date is not None:
        query += " AND o.date >= ?"
        parameters.append(str(start_date))
    if end_date is not None:
        query += " AND o.date <= ?"
        parameters.append(str(end_date))
    query += " ORDER BY o.project_id, o.entity_depth, o.entity_id, o.date, o.metric_code"
    with connect_database(db_path) as connection:
        data = pd.read_sql_query(query, connection, params=parameters)
    if not data.empty:
        data["date"] = pd.to_datetime(data["date"])
        data["raw_value"] = [
            _restore_raw_value(value, value_type)
            for value, value_type in zip(data["raw_value"], data["raw_value_type"])
        ]
    entities = load_current_entities(db_path, source_key, project_id)
    return _add_compatibility_columns(data, entities)


def load_import_history(
    db_path: str | Path,
    source_key: str | None = None,
) -> pd.DataFrame:
    initialize_database(db_path)
    query = """
        SELECT h.*
        FROM v_import_history h
        JOIN data_sources ds ON ds.source_id = h.source_id
        WHERE 1 = 1
    """
    source_sql, parameters = _source_clause(source_key)
    query += source_sql + " ORDER BY h.attempt_id DESC"
    with connect_database(db_path) as connection:
        return pd.read_sql_query(query, connection, params=parameters)


def load_observation_history(
    db_path: str | Path,
    observation_id: int,
) -> pd.DataFrame:
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        return pd.read_sql_query(
            """
            SELECT * FROM observation_revisions
            WHERE observation_id = ?
            ORDER BY revision_id
            """,
            connection,
            params=[observation_id],
        )


def resolve_observation_lineage(
    db_path: str | Path,
    project_label: str,
    observation_ref: str,
    lineage_ref: str,
) -> dict[str, Any]:
    """Resolve one immutable chart snapshot without consulting current chart values."""
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        observation = connection.execute(
            """
            SELECT o.observation_id
            FROM observation_public_refs opr
            JOIN observations o ON o.observation_id = opr.observation_id
            WHERE opr.observation_ref = ?
            """,
            (observation_ref,),
        ).fetchone()
        if observation is None:
            raise LineageNotFoundError("Observation reference không tồn tại.")

        snapshot = connection.execute(
            """
            SELECT observation_id FROM observation_lineage_snapshots
            WHERE lineage_ref = ?
            """,
            (lineage_ref,),
        ).fetchone()
        if snapshot is None:
            raise LineageNotFoundError("Lineage reference không tồn tại.")
        if int(snapshot["observation_id"]) != int(observation["observation_id"]):
            raise LineageMismatchError("Observation và lineage reference không cùng dữ liệu.")

        row = connection.execute(
            """
            SELECT
                opr.observation_ref,
                ols.lineage_ref,
                o.observation_id,
                o.source_id,
                o.observed_date,
                o.current_revision_id,
                o.latest_presence_id,
                o.is_deleted,
                r.revision_id,
                rpr.revision_ref,
                r.metric_original,
                r.metric_normalized,
                o.metric_code,
                r.effective_unit,
                r.raw_value_text,
                r.raw_value_type,
                r.chart_value,
                r.display_value,
                r.number_format,
                r.value_kind,
                r.data_note,
                r.validation_status,
                r.change_type,
                r.recorded_at AS revision_recorded_at,
                p.presence_id,
                p.run_id,
                p.sheet_name,
                p.cell_address,
                p.source_file,
                p.source_hash,
                p.parser_rule,
                p.parser_confidence,
                ir.import_mode,
                ir.committed_at,
                irpr.import_ref,
                iapr.attempt_ref,
                er.external_entity_key AS entity_ref,
                er.entity_label,
                er.entity_level,
                er.entity_path,
                pr.project_label
            FROM observation_lineage_snapshots ols
            JOIN observation_public_refs opr ON opr.observation_id = ols.observation_id
            JOIN observations o ON o.observation_id = ols.observation_id
            JOIN observation_revisions r ON r.revision_id = ols.revision_id
            LEFT JOIN observation_revision_public_refs rpr ON rpr.revision_id = r.revision_id
            JOIN import_observation_presence p ON p.presence_id = ols.presence_id
            JOIN import_runs ir ON ir.run_id = p.run_id
            LEFT JOIN import_run_public_refs irpr ON irpr.run_id = ir.run_id
            LEFT JOIN import_attempt_public_refs iapr ON iapr.attempt_id = ir.attempt_id
            JOIN entities e ON e.entity_id = o.entity_id
            JOIN entity_revisions er ON er.entity_revision_id = (
                SELECT er2.entity_revision_id
                FROM entity_revisions er2
                WHERE er2.entity_id = e.entity_id AND er2.run_id <= p.run_id
                ORDER BY er2.run_id DESC, er2.entity_revision_id DESC
                LIMIT 1
            )
            JOIN projects project ON project.project_id = e.project_id
            JOIN project_revisions pr ON pr.project_revision_id = (
                SELECT pr2.project_revision_id
                FROM project_revisions pr2
                WHERE pr2.project_id = project.project_id AND pr2.run_id <= p.run_id
                ORDER BY pr2.run_id DESC, pr2.project_revision_id DESC
                LIMIT 1
            )
            WHERE opr.observation_ref = ? AND ols.lineage_ref = ?
            """,
            (observation_ref, lineage_ref),
        ).fetchone()
        if row is None or row["project_label"] != project_label:
            raise LineageNotFoundError("Lineage không thuộc project được yêu cầu.")

        issues = [
            dict(issue)
            for issue in connection.execute(
                """
                    SELECT vipr.issue_ref, vi.severity, vi.code, vi.message
                    FROM validation_issues vi
                    JOIN validation_issue_lineage_links link ON link.issue_id = vi.issue_id
                    JOIN validation_issue_public_refs vipr ON vipr.issue_id = vi.issue_id
                WHERE link.presence_id = ?
                    ORDER BY vi.issue_id
                """,
                (row["presence_id"],),
            )
        ]
        latest_date = connection.execute(
            """
            SELECT MAX(o2.observed_date)
            FROM observations o2
            JOIN entities e2 ON e2.entity_id = o2.entity_id
            JOIN projects p2 ON p2.project_id = e2.project_id
            JOIN project_revisions pr2 ON pr2.project_revision_id = p2.current_revision_id
            WHERE o2.source_id = ? AND pr2.project_label = ? AND o2.is_deleted = 0
            """,
            (row["source_id"], project_label),
        ).fetchone()[0]
        latest_run = connection.execute(
            "SELECT MAX(run_id) FROM import_runs WHERE source_id = ? AND status = 'committed'",
            (row["source_id"],),
        ).fetchone()[0]

    revision_current = int(row["current_revision_id"] or 0) == int(row["revision_id"]) and int(row["is_deleted"]) == 0
    presence_current = int(row["latest_presence_id"] or 0) == int(row["presence_id"]) and int(row["is_deleted"]) == 0
    is_current = revision_current and presence_current
    return {
        "contractVersion": 1,
        "status": "available",
        "observationRef": row["observation_ref"],
        "lineageRef": row["lineage_ref"],
        "context": {
            "project": {"label": row["project_label"]},
            "entity": {
                "ref": row["entity_ref"],
                "label": row["entity_label"],
                "level": row["entity_level"],
                "hierarchyPath": [
                    part.strip()
                    for part in str(row["entity_path"]).replace(" > ", "/").split("/")
                    if part.strip()
                ],
                "effectiveUnit": row["effective_unit"],
            },
            "metric": {"key": row["metric_code"], "label": row["metric_normalized"]},
            "observedDate": row["observed_date"],
        },
        "source": {
            "workbookName": row["source_file"],
            "workbookHash": {"algorithm": "sha256", "value": row["source_hash"]},
            "sheet": row["sheet_name"],
            "cell": row["cell_address"],
            "cellReference": f'{row["sheet_name"]}!{row["cell_address"]}',
        },
        "values": {
            "raw": {"text": row["raw_value_text"], "type": row["raw_value_type"]},
            "display": row["display_value"],
            "chart": row["chart_value"],
            "valueKind": row["value_kind"],
            "numberFormat": row["number_format"],
        },
        "transformation": {
            "parserRule": row["parser_rule"],
            "parserConfidence": row["parser_confidence"],
            "note": row["data_note"],
        },
        "validation": {
            "status": row["validation_status"],
            "issues": [
                {"issueRef": issue["issue_ref"], "severity": issue["severity"],
                 "code": issue["code"], "message": issue["message"]}
                for issue in issues
            ],
            "issueLinkage": "exact" if issues else "none",
        },
        "revision": {
            "revisionRef": row["revision_ref"],
            "changeType": row["change_type"],
            "recordedAt": row["revision_recorded_at"],
            "state": "current" if is_current else "superseded",
            "revisionCurrent": revision_current,
            "sourcePresenceCurrent": presence_current,
        },
        "import": {
            "mode": row["import_mode"],
            "committedAt": row["committed_at"],
            "importRef": row["import_ref"],
            "attemptRef": row["attempt_ref"],
        },
        "freshness": {
            "observedThrough": latest_date,
            "isCurrent": is_current,
            "newerSnapshotAvailable": not is_current,
            "newerSourceDataAvailable": latest_run is not None and int(latest_run) > int(row["run_id"]),
            "sourceCommittedAt": row["committed_at"],
        },
    }


def lookup_audit_lineage(
    db_path: str | Path,
    project_label: str,
    observation_ref: str,
    lineage_ref: str,
) -> dict[str, Any]:
    resolved = resolve_observation_lineage(
        db_path, project_label, observation_ref, lineage_ref
    )
    context = resolved["context"]
    source = resolved["source"]
    values = resolved["values"]
    return {
        "contractVersion": 1,
        "observationRef": observation_ref,
        "lineageRef": lineage_ref,
        "row": {
            "date": context["observedDate"],
            "project_label": context["project"]["label"],
            "entity_path": " / ".join(context["entity"]["hierarchyPath"]),
            "effective_unit": context["entity"]["effectiveUnit"],
            "metric_normalized": context["metric"]["label"],
            "raw_value": values["raw"]["text"],
            "display_value": values["display"],
            "chart_value": values["chart"],
            "value_kind": values["valueKind"],
            "sheet_name": source["sheet"],
            "cell_address": source["cell"],
            "validation_status": resolved["validation"]["status"],
            "revision_state": resolved["revision"]["state"],
        },
        "recommendedContext": {
            "entityRef": context["entity"]["ref"],
            "start": context["observedDate"],
            "end": context["observedDate"],
            "metric": context["metric"]["key"],
        },
    }


def list_observation_revisions(
    db_path: str | Path,
    project_label: str,
    observation_ref: str,
    source_key: str | None = None,
) -> dict[str, Any]:
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        observation = connection.execute(
            """
            SELECT o.observation_id, o.current_revision_id, o.is_deleted
            FROM observation_public_refs opr
            JOIN observations o ON o.observation_id = opr.observation_id
            JOIN entities e ON e.entity_id = o.entity_id
            JOIN projects p ON p.project_id = e.project_id
            JOIN project_revisions pr ON pr.project_revision_id = p.current_revision_id
            JOIN data_sources ds ON ds.source_id = o.source_id
            WHERE opr.observation_ref = ? AND pr.project_label = ?
              AND (? IS NULL OR ds.source_key = ?)
            """,
            (observation_ref, project_label, source_key, source_key),
        ).fetchone()
        if observation is None:
            raise LineageNotFoundError("Observation không thuộc project được yêu cầu.")
        rows = connection.execute(
            """
            SELECT r.revision_id, rpr.revision_ref, r.change_type, r.recorded_at,
                   r.display_value, r.chart_value, r.validation_status, r.is_deleted,
                   irpr.import_ref, iapr.attempt_ref,
                   (
                       SELECT ols.lineage_ref
                       FROM observation_lineage_snapshots ols
                       JOIN import_observation_presence p ON p.presence_id = ols.presence_id
                       WHERE ols.revision_id = r.revision_id
                       ORDER BY p.run_id DESC, p.presence_id DESC LIMIT 1
                   ) AS lineage_ref
            FROM observation_revisions r
            LEFT JOIN observation_revision_public_refs rpr ON rpr.revision_id = r.revision_id
            JOIN import_runs ir ON ir.run_id = r.run_id
            LEFT JOIN import_run_public_refs irpr ON irpr.run_id = ir.run_id
            LEFT JOIN import_attempt_public_refs iapr ON iapr.attempt_id = ir.attempt_id
            WHERE r.observation_id = ?
            ORDER BY r.revision_id DESC
            """,
            (observation["observation_id"],),
        ).fetchall()
    return {
        "contractVersion": 2,
        "observationRef": observation_ref,
        "items": [
            {
                "revisionRef": row["revision_ref"],
                "lineageRef": row["lineage_ref"],
                "changeType": row["change_type"],
                "recordedAt": row["recorded_at"],
                "displayValue": row["display_value"],
                "chartValue": row["chart_value"],
                "validationStatus": row["validation_status"],
                "state": "deleted" if row["is_deleted"] else (
                    "current" if row["revision_id"] == observation["current_revision_id"]
                    and not observation["is_deleted"] else "superseded"
                ),
                "importRef": row["import_ref"],
                "attemptRef": row["attempt_ref"],
            }
            for row in rows
        ],
    }


def resolve_import_run(
    db_path: str | Path,
    project_label: str,
    import_ref: str,
    source_key: str | None = None,
) -> dict[str, Any]:
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        row = connection.execute(
            """
            SELECT ir.run_id, irpr.import_ref, iapr.attempt_ref,
                   ia.submitted_file_name, ia.status AS attempt_status,
                   ir.import_mode, ir.source_hash, ir.committed_at,
                   ir.minimum_data_date, ir.maximum_data_date,
                   ir.inserted_count, ir.updated_count, ir.unchanged_count,
                   ir.restored_count, ir.deleted_count,
                   ds.source_key
            FROM import_run_public_refs irpr
            JOIN import_runs ir ON ir.run_id = irpr.run_id
            JOIN import_attempts ia ON ia.attempt_id = ir.attempt_id
            JOIN import_attempt_public_refs iapr ON iapr.attempt_id = ia.attempt_id
            JOIN data_sources ds ON ds.source_id = ir.source_id
            WHERE irpr.import_ref = ? AND ir.status = 'committed'
              AND (? IS NULL OR ds.source_key = ?)
            """,
            (import_ref, source_key, source_key),
        ).fetchone()
        if row is None:
            raise LineageNotFoundError("Lần nhập dữ liệu không tồn tại.")
        project_member = connection.execute(
            """
            SELECT 1
            FROM observations o
            JOIN entities e ON e.entity_id = o.entity_id
            JOIN projects p ON p.project_id = e.project_id
            JOIN project_revisions pr ON pr.project_revision_id = p.current_revision_id
            JOIN import_observation_presence presence ON presence.observation_id = o.observation_id
            WHERE presence.run_id = ? AND pr.project_label = ?
            LIMIT 1
            """,
            (row["run_id"], project_label),
        ).fetchone()
        if project_member is None:
            raise LineageNotFoundError("Lần nhập không thuộc project được yêu cầu.")
    return {
        "contractVersion": 2,
        "importRef": row["import_ref"],
        "attemptRef": row["attempt_ref"],
        "status": row["attempt_status"],
        "workbookName": row["submitted_file_name"],
        "workbookHash": row["source_hash"],
        "mode": row["import_mode"],
        "committedAt": row["committed_at"],
        "dataRange": {"start": row["minimum_data_date"], "end": row["maximum_data_date"]},
        "outcome": {
            "inserted": row["inserted_count"],
            "updated": row["updated_count"],
            "unchanged": row["unchanged_count"],
            "restored": row["restored_count"],
            "deleted": row["deleted_count"],
        },
    }


def latest_committed_run_id(db_path: str | Path, source_key: str | None = None) -> int | None:
    initialize_database(db_path)
    query = """
        SELECT MAX(r.run_id)
        FROM import_runs r
        JOIN data_sources ds ON ds.source_id = r.source_id
        WHERE r.status = 'committed'
    """
    parameters: list[Any] = []
    if source_key is not None:
        query += " AND ds.source_key = ?"
        parameters.append(source_key)
    with connect_database(db_path) as connection:
        value = connection.execute(query, parameters).fetchone()[0]
    return int(value) if value is not None else None
