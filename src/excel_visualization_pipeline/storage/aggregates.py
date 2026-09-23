"""Immutable aggregate evidence captured from rendered chart inputs."""

from __future__ import annotations

import base64
import hmac
import json
import uuid
from hashlib import sha256
from pathlib import Path
from typing import Any

from .canonical import content_hash
from .connection import connect_database, utc_now
from .migrations import initialize_database
from .repository import LineageNotFoundError


def register_aggregate_snapshots(
    db_path: str | Path,
    source_key: str,
    project_label: str,
    specifications: list[dict[str, Any]],
) -> list[str]:
    """Persist all evidence before returning any aggregate reference to a chart."""
    if not specifications:
        return []
    initialize_database(db_path)
    fingerprints = [
        content_hash({
            "sourceKey": source_key,
            "project": project_label,
            "context": spec["context"],
            "result": spec["result"],
            "aggregation": spec["aggregation"],
            "sourceRunId": spec.get("sourceRunId"),
            "members": spec["members"],
            "calculatorVersion": 1,
        })
        for spec in specifications
    ]
    refs: list[str] = []
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        source = connection.execute(
            "SELECT source_id FROM data_sources WHERE source_key = ?", (source_key,)
        ).fetchone()
        if source is None:
            raise LineageNotFoundError("Nguồn dữ liệu không tồn tại.")
        source_id = int(source["source_id"])
        try:
            existing_by_fingerprint: dict[str, str] = {}
            unique_fingerprints = list(dict.fromkeys(fingerprints))
            for offset in range(0, len(unique_fingerprints), 500):
                batch = unique_fingerprints[offset:offset + 500]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT fingerprint, aggregate_ref FROM aggregate_snapshots WHERE fingerprint IN ({placeholders})",
                    batch,
                ).fetchall()
                existing_by_fingerprint.update(
                    {str(row["fingerprint"]): str(row["aggregate_ref"]) for row in rows}
                )

            missing_pairs = [
                (spec, fingerprint)
                for spec, fingerprint in zip(specifications, fingerprints)
                if fingerprint not in existing_by_fingerprint
            ]
            lineage_refs = list(dict.fromkeys(
                str(member["lineageRef"])
                for spec, _ in missing_pairs
                for member in spec["members"]
            ))
            valid_refs: set[str] = set()
            for offset in range(0, len(lineage_refs), 500):
                batch = lineage_refs[offset:offset + 500]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"""
                    SELECT ols.lineage_ref FROM observation_lineage_snapshots ols
                    JOIN observations o ON o.observation_id = ols.observation_id
                    WHERE o.source_id = ? AND ols.lineage_ref IN ({placeholders})
                    """,
                    [source_id, *batch],
                ).fetchall()
                valid_refs.update(str(row["lineage_ref"]) for row in rows)
            if len(valid_refs) != len(lineage_refs):
                raise LineageNotFoundError("Aggregate chứa lineage không hợp lệ.")

            for spec, fingerprint in zip(specifications, fingerprints):
                existing_ref = existing_by_fingerprint.get(fingerprint)
                if existing_ref is not None:
                    refs.append(existing_ref)
                    continue
                members = spec["members"]
                aggregate_ref = f"agg_{uuid.uuid4().hex}"
                cursor = connection.execute(
                    """
                    INSERT INTO aggregate_snapshots(
                        aggregate_ref, fingerprint, source_id, project_label,
                        context_json, result_json, aggregation_json, source_run_id,
                        calculator_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        aggregate_ref, fingerprint, source_id, project_label,
                        json.dumps(spec["context"], ensure_ascii=False, allow_nan=False),
                        json.dumps(spec["result"], ensure_ascii=False, allow_nan=False),
                        json.dumps(spec["aggregation"], ensure_ascii=False, allow_nan=False),
                        spec.get("sourceRunId"), utc_now(),
                    ),
                )
                aggregate_id = int(cursor.lastrowid)
                for ordinal, member in enumerate(members):
                    connection.execute(
                        """
                        INSERT INTO aggregate_snapshot_members(
                            aggregate_id, ordinal, lineage_ref, role, included,
                            contribution_value, note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            aggregate_id, ordinal, member["lineageRef"], member["role"],
                            int(bool(member["included"])), member.get("contributionValue"),
                            member.get("note"),
                        ),
                    )
                existing_by_fingerprint[fingerprint] = aggregate_ref
                refs.append(aggregate_ref)
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    return refs


def _aggregate_row(connection, project_label: str, aggregate_ref: str, source_key: str):
    row = connection.execute(
        """
        SELECT a.* FROM aggregate_snapshots a
        JOIN data_sources ds ON ds.source_id = a.source_id
        WHERE a.aggregate_ref = ? AND a.project_label = ? AND ds.source_key = ?
        """,
        (aggregate_ref, project_label, source_key),
    ).fetchone()
    if row is None:
        raise LineageNotFoundError("Aggregate reference không tồn tại trong project.")
    return row


def resolve_aggregate_provenance(
    db_path: str | Path,
    source_key: str,
    project_label: str,
    aggregate_ref: str,
) -> dict[str, Any]:
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        row = _aggregate_row(connection, project_label, aggregate_ref, source_key)
        member_count = connection.execute(
            "SELECT COUNT(*) FROM aggregate_snapshot_members WHERE aggregate_id = ?",
            (row["aggregate_id"],),
        ).fetchone()[0]
        latest_run = connection.execute(
            "SELECT MAX(run_id) FROM import_runs WHERE source_id = ? AND status = 'committed'",
            (row["source_id"],),
        ).fetchone()[0]
    return {
        "contractVersion": 2,
        "kind": "aggregate",
        "aggregateRef": aggregate_ref,
        "context": json.loads(row["context_json"]),
        "result": json.loads(row["result_json"]),
        "aggregation": json.loads(row["aggregation_json"]),
        "contributors": {"total": member_count, "pageSize": 50},
        "freshness": {
            "snapshotCreatedAt": row["created_at"],
            "observedThrough": json.loads(row["context_json"]).get("observedThrough"),
            "newerDataAvailable": latest_run is not None
            and (row["source_run_id"] is None or latest_run > row["source_run_id"]),
        },
    }


def _encode_cursor(secret: bytes, aggregate_ref: str, ordinal: int) -> str:
    payload = json.dumps([aggregate_ref, ordinal], separators=(",", ":")).encode()
    signature = hmac.new(secret, payload, sha256).digest()
    return base64.urlsafe_b64encode(payload + signature).decode().rstrip("=")


def _decode_cursor(secret: bytes, aggregate_ref: str, cursor: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        payload, signature = raw[:-32], raw[-32:]
        if not hmac.compare_digest(hmac.new(secret, payload, sha256).digest(), signature):
            raise ValueError("Invalid cursor signature")
        cursor_ref, ordinal = json.loads(payload)
        if cursor_ref != aggregate_ref or not isinstance(ordinal, int) or ordinal < 0:
            raise ValueError("Cursor belongs to another aggregate")
        return ordinal
    except (ValueError, UnicodeError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Contributor cursor không hợp lệ.") from exc


def list_aggregate_contributors(
    db_path: str | Path,
    source_key: str,
    project_label: str,
    aggregate_ref: str,
    *,
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    if not 1 <= limit <= 100:
        raise ValueError("Giới hạn contributor phải từ 1 đến 100.")
    initialize_database(db_path)
    with connect_database(db_path) as connection:
        aggregate = _aggregate_row(connection, project_label, aggregate_ref, source_key)
        secret = connection.execute(
            "SELECT secret FROM aggregate_cursor_secret WHERE singleton = 1"
        ).fetchone()[0]
        after = _decode_cursor(secret, aggregate_ref, cursor) if cursor else -1
        rows = connection.execute(
            """
            SELECT member.ordinal, member.role, member.included,
                   member.contribution_value, member.note,
                   opr.observation_ref, member.lineage_ref,
                   o.observed_date, r.metric_normalized, r.display_value,
                   r.chart_value, r.validation_status,
                   er.entity_label
            FROM aggregate_snapshot_members member
            JOIN observation_lineage_snapshots ols ON ols.lineage_ref = member.lineage_ref
            JOIN observation_public_refs opr ON opr.observation_id = ols.observation_id
            JOIN observations o ON o.observation_id = ols.observation_id
            JOIN observation_revisions r ON r.revision_id = ols.revision_id
            JOIN entities e ON e.entity_id = o.entity_id
            JOIN entity_revisions er ON er.entity_revision_id = (
                SELECT er2.entity_revision_id FROM entity_revisions er2
                JOIN import_observation_presence p ON p.presence_id = ols.presence_id
                WHERE er2.entity_id = e.entity_id AND er2.run_id <= p.run_id
                ORDER BY er2.run_id DESC, er2.entity_revision_id DESC LIMIT 1
            )
            WHERE member.aggregate_id = ? AND member.ordinal > ?
            ORDER BY member.ordinal LIMIT ?
            """,
            (aggregate["aggregate_id"], after, limit + 1),
        ).fetchall()
        total = connection.execute(
            "SELECT COUNT(*) FROM aggregate_snapshot_members WHERE aggregate_id = ?",
            (aggregate["aggregate_id"],),
        ).fetchone()[0]
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _encode_cursor(secret, aggregate_ref, page[-1]["ordinal"]) if has_more else None
    return {
        "contractVersion": 2,
        "aggregateRef": aggregate_ref,
        "total": total,
        "items": [
            {
                "observationRef": row["observation_ref"],
                "lineageRef": row["lineage_ref"],
                "role": row["role"],
                "included": bool(row["included"]),
                "contributionValue": row["contribution_value"],
                "note": row["note"],
                "date": row["observed_date"],
                "entityLabel": row["entity_label"],
                "metric": row["metric_normalized"],
                "displayValue": row["display_value"],
                "chartValue": row["chart_value"],
                "validationStatus": row["validation_status"],
            }
            for row in page
        ],
        "nextCursor": next_cursor,
    }
