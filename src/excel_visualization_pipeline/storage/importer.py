from __future__ import annotations

import re
import sqlite3
import uuid
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from io import BytesIO
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, Iterable, Sequence

import pandas as pd

from ..config import ParserConfig
from ..models import ValidationIssue
from ..pipeline import PipelineResult, run_pipeline
from .canonical import canonical_json, content_hash, decimal_text, raw_value
from .connection import connect_database, utc_now
from .migrations import initialize_database


PARSER_VERSION = "0.1.0"


@dataclass(frozen=True)
class ImportScope:
    date_from: str
    date_to: str
    sheet_name: str | None = None
    project_key: str | None = None
    root_external_entity_key: str | None = None
    metric_code: str | None = None
    is_complete: bool = True
    missing_policy: str = "ignore"

    def normalized(self) -> "ImportScope":
        start = date.fromisoformat(str(self.date_from))
        end = date.fromisoformat(str(self.date_to))
        if start > end:
            raise ValueError("date_from phải nhỏ hơn hoặc bằng date_to.")
        if self.missing_policy not in {"ignore", "tombstone"}:
            raise ValueError("missing_policy phải là 'ignore' hoặc 'tombstone'.")
        return ImportScope(
            date_from=start.isoformat(),
            date_to=end.isoformat(),
            sheet_name=self.sheet_name or None,
            project_key=self.project_key or None,
            root_external_entity_key=self.root_external_entity_key or None,
            metric_code=self.metric_code or None,
            is_complete=bool(self.is_complete),
            missing_policy=self.missing_policy,
        )


@dataclass(frozen=True)
class ImportOutcome:
    attempt_id: int
    status: str
    run_id: int | None = None
    duplicate_of_run_id: int | None = None
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    restored_count: int = 0
    deleted_count: int = 0
    lineage_changed_count: int = 0
    message: str | None = None


@dataclass(frozen=True)
class ImportExecution:
    result: PipelineResult | None
    outcome: ImportOutcome


class StorageImportError(RuntimeError):
    pass


def _read_source(source: str | Path | bytes | BinaryIO) -> tuple[bytes, str]:
    if isinstance(source, bytes):
        return source, "uploaded.xlsx"
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path.read_bytes(), path.name
    payload = source.read()
    if hasattr(source, "seek"):
        source.seek(0)
    return payload, Path(getattr(source, "name", "uploaded.xlsx")).name


def _optional(value):
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _text(value) -> str | None:
    normalized = _optional(value)
    return None if normalized is None else str(normalized)


def _integer(value) -> int | None:
    normalized = _optional(value)
    return None if normalized is None else int(normalized)


def _float(value) -> float | None:
    normalized = _optional(value)
    return None if normalized is None else float(normalized)


def _metric_code(metric: str) -> str:
    known = {
        "Tổng số": "total",
        "Báo sai/Lỗi": "error",
        "% báo sai": "error_rate",
    }
    if metric in known:
        return known[metric]
    normalized = unicodedata.normalize("NFD", metric.casefold())
    ascii_text = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")
    return slug or f"metric_{content_hash(metric)[:12]}"


def _config_hash(config: ParserConfig) -> str:
    return content_hash(asdict(config))


def _contract(mode: str, scopes: Sequence[ImportScope] | None) -> tuple[str, str]:
    payload = {
        "mode": mode,
        "scopes": [asdict(scope.normalized()) for scope in scopes] if scopes is not None else "auto_from_input",
    }
    rendered = canonical_json(payload)
    return content_hash(payload), rendered


def _replay_contract(
    base_contract_hash: str,
    base_contract_json: str,
    attempt_id: int,
) -> tuple[str, str]:
    payload = {
        "base_contract_hash": base_contract_hash,
        "base_contract_json": base_contract_json,
        "explicit_replay_attempt_id": attempt_id,
    }
    return content_hash(payload), canonical_json(payload)


def _auto_scopes(result: PipelineResult, mode: str) -> list[ImportScope]:
    if mode == "incremental" or result.data.empty:
        return []
    scopes: list[ImportScope] = []
    for sheet_name, frame in result.data.groupby("sheet_name"):
        dates = pd.to_datetime(frame["date"])
        scopes.append(
            ImportScope(
                sheet_name=str(sheet_name),
                date_from=dates.min().date().isoformat(),
                date_to=dates.max().date().isoformat(),
                is_complete=True,
                missing_policy="ignore",
            )
        )
    return scopes


def _validate_mode_and_scopes(mode: str, scopes: Sequence[ImportScope]) -> list[ImportScope]:
    if mode not in {"full_snapshot", "incremental"}:
        raise ValueError("mode phải là 'full_snapshot' hoặc 'incremental'.")
    normalized = [scope.normalized() for scope in scopes]
    if mode == "full_snapshot" and not normalized:
        raise ValueError("full_snapshot phải có ít nhất một declared scope.")
    if mode == "incremental" and any(scope.missing_policy == "tombstone" for scope in normalized):
        raise ValueError("incremental không được sử dụng missing_policy='tombstone'.")
    return normalized


def _default_raw_dir(db_path: str | Path) -> Path:
    db_parent = Path(db_path).resolve().parent
    return db_parent.parent / "raw" if db_parent.name == "local" else db_parent / "raw"


def _prepare_attempt(
    db_path: str | Path,
    source_key: str,
    display_name: str,
    source_name: str,
    payload: bytes,
    parser_config_hash: str,
    mode: str,
    contract_hash: str,
    contract_json: str,
    minimum_data_date: str | None,
    raw_dir: str | Path | None,
) -> tuple[int, int, int, str]:
    initialize_database(db_path)
    source_hash = sha256(payload).hexdigest()
    archive_dir = Path(raw_dir) if raw_dir is not None else _default_raw_dir(db_path)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{source_hash}.xlsx"
    archive_is_valid = (
        archive_path.exists()
        and sha256(archive_path.read_bytes()).hexdigest() == source_hash
    )
    if not archive_is_valid:
        temporary = archive_path.with_suffix(".xlsx.tmp")
        temporary.write_bytes(payload)
        temporary.replace(archive_path)

    started_at = utc_now()
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute(
                """
                INSERT INTO data_sources(source_key, display_name, source_type, minimum_data_date, created_at)
                VALUES (?, ?, 'excel', ?, ?)
                ON CONFLICT(source_key) DO UPDATE SET
                    display_name = excluded.display_name,
                    minimum_data_date = COALESCE(excluded.minimum_data_date, data_sources.minimum_data_date)
                """,
                (source_key, display_name, minimum_data_date, started_at),
            )
            source_id = connection.execute(
                "SELECT source_id FROM data_sources WHERE source_key = ?", (source_key,)
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO source_artifacts(
                    source_id, source_file, archived_file_path, source_hash, file_size, received_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, source_hash) DO NOTHING
                """,
                (source_id, source_name, str(archive_path), source_hash, len(payload), started_at),
            )
            artifact_id = connection.execute(
                "SELECT artifact_id FROM source_artifacts WHERE source_id = ? AND source_hash = ?",
                (source_id, source_hash),
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO import_attempts(
                    source_id, artifact_id, submitted_file_name, requested_mode,
                    parser_config_hash, import_contract_hash, import_contract_json,
                    parser_version, status, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'received', ?)
                """,
                (
                    source_id,
                    artifact_id,
                    source_name,
                    mode,
                    parser_config_hash,
                    contract_hash,
                    contract_json,
                    PARSER_VERSION,
                    started_at,
                ),
            )
            attempt_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO import_attempt_public_refs(attempt_id, attempt_ref) VALUES (?, ?)",
                (attempt_id, f"att_{uuid.uuid4().hex}"),
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return attempt_id, int(source_id), int(artifact_id), source_hash


def _set_attempt(
    db_path: str | Path,
    attempt_id: int,
    status: str,
    *,
    duplicate_of_run_id: int | None = None,
    failure_code: str | None = None,
    failure_message: str | None = None,
    contract_hash: str | None = None,
    contract_json: str | None = None,
) -> None:
    finished_at = utc_now() if status in {"duplicate", "rejected", "failed", "committed"} else None
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE import_attempts
            SET status = ?, finished_at = ?, duplicate_of_run_id = ?,
                failure_code = ?, failure_message = ?,
                import_contract_hash = COALESCE(?, import_contract_hash),
                import_contract_json = COALESCE(?, import_contract_json)
            WHERE attempt_id = ?
            """,
            (
                status,
                finished_at,
                duplicate_of_run_id,
                failure_code,
                failure_message,
                contract_hash,
                contract_json,
                attempt_id,
            ),
        )
        connection.execute("COMMIT")


def _existing_run(
    connection: sqlite3.Connection,
    source_id: int,
    source_hash: str,
    parser_config_hash: str,
    contract_hash: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT run_id FROM import_runs
        WHERE source_id = ? AND source_hash = ? AND parser_config_hash = ?
          AND import_contract_hash = ? AND status = 'committed'
        """,
        (source_id, source_hash, parser_config_hash, contract_hash),
    ).fetchone()
    return int(row[0]) if row else None


def _store_issues(
    connection: sqlite3.Connection,
    attempt_id: int,
    issues: Iterable[ValidationIssue],
    run_id: int | None = None,
) -> None:
    created_at = utc_now()
    for issue in issues:
        cursor = connection.execute(
            """
            INSERT INTO validation_issues(
                attempt_id, run_id, severity, code, message, sheet_name, cell_address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id, run_id, issue.severity, issue.code, issue.message,
                issue.sheet_name, issue.cell_address, created_at,
            ),
        )
        connection.execute(
            "INSERT INTO validation_issue_public_refs(issue_id, issue_ref) VALUES (?, ?)",
            (int(cursor.lastrowid), f"val_{uuid.uuid4().hex}"),
        )
        if run_id is None or not issue.sheet_name or not issue.cell_address:
            continue
        candidates = connection.execute(
            """
            SELECT presence_id FROM import_observation_presence
            WHERE run_id = ? AND sheet_name = ? AND cell_address = ?
            """,
            (run_id, issue.sheet_name, issue.cell_address),
        ).fetchall()
        if len(candidates) == 1:
            connection.execute(
                "INSERT INTO validation_issue_lineage_links(issue_id, presence_id) VALUES (?, ?)",
                (int(cursor.lastrowid), int(candidates[0]["presence_id"])),
            )


def _reject_attempt(
    db_path: str | Path,
    attempt_id: int,
    issues: Sequence[ValidationIssue],
    message: str,
) -> ImportOutcome:
    with connect_database(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _store_issues(connection, attempt_id, issues)
        connection.execute(
            """
            UPDATE import_attempts
            SET status = 'rejected', finished_at = ?, failure_code = 'QUALITY_GATE', failure_message = ?
            WHERE attempt_id = ?
            """,
            (utc_now(), message, attempt_id),
        )
        connection.execute("COMMIT")
    return ImportOutcome(attempt_id=attempt_id, status="rejected", message=message)


def import_workbook(
    db_path: str | Path,
    source: str | Path | bytes | BinaryIO,
    *,
    source_key: str = "cx_report_master",
    display_name: str = "CX Report Master",
    config_path: str | Path | None = None,
    mode: str = "full_snapshot",
    scopes: Sequence[ImportScope] | None = None,
    raw_dir: str | Path | None = None,
    allow_replay: bool = False,
) -> ImportExecution:
    if mode not in {"full_snapshot", "incremental"}:
        raise ValueError("mode phải là 'full_snapshot' hoặc 'incremental'.")
    payload, source_name = _read_source(source)
    config = ParserConfig.from_yaml(config_path) if config_path else ParserConfig()
    parser_config_hash = _config_hash(config)
    initial_contract_hash, initial_contract_json = _contract(mode, scopes)
    attempt_id, source_id, artifact_id, source_hash = _prepare_attempt(
        db_path,
        source_key,
        display_name,
        source_name,
        payload,
        parser_config_hash,
        mode,
        initial_contract_hash,
        initial_contract_json,
        config.minimum_data_date,
        raw_dir,
    )
    _set_attempt(db_path, attempt_id, "processing")
    try:
        stream = BytesIO(payload)
        stream.name = source_name
        result = run_pipeline(stream, config_path)
    except Exception as exc:
        _set_attempt(
            db_path,
            attempt_id,
            "failed",
            failure_code="PARSE_FAILED",
            failure_message=str(exc),
        )
        raise StorageImportError(f"Không thể parse workbook {source_name}: {exc}") from exc

    effective_scopes = list(scopes) if scopes is not None else _auto_scopes(result, mode)
    if not result.report.is_valid:
        contract_hash, contract_json = _contract(mode, effective_scopes)
        _set_attempt(
            db_path,
            attempt_id,
            "processing",
            contract_hash=contract_hash,
            contract_json=contract_json,
        )
        outcome = _reject_attempt(
            db_path,
            attempt_id,
            result.report.issues,
            f"Quality gate có {len(result.report.errors)} error.",
        )
        return ImportExecution(result=result, outcome=outcome)
    try:
        normalized_scopes = _validate_mode_and_scopes(mode, effective_scopes)
    except Exception as exc:
        _set_attempt(
            db_path,
            attempt_id,
            "failed",
            failure_code="INVALID_IMPORT_CONTRACT",
            failure_message=str(exc),
        )
        raise
    contract_hash, contract_json = _contract(mode, normalized_scopes)
    if allow_replay:
        contract_hash, contract_json = _replay_contract(
            contract_hash, contract_json, attempt_id
        )
    _set_attempt(
        db_path,
        attempt_id,
        "processing",
        contract_hash=contract_hash,
        contract_json=contract_json,
    )
    outcome = _process_result(
        db_path,
        attempt_id,
        source_id,
        artifact_id,
        source_hash,
        source_name,
        parser_config_hash,
        contract_hash,
        mode,
        normalized_scopes,
        result,
        allow_replay=allow_replay,
    )
    return ImportExecution(result=result, outcome=outcome)


def import_pipeline_result(
    db_path: str | Path,
    source_key: str,
    source_name: str,
    source_payload: bytes,
    result: PipelineResult,
    *,
    config: ParserConfig | None = None,
    mode: str = "full_snapshot",
    scopes: Sequence[ImportScope] | None = None,
    display_name: str | None = None,
    raw_dir: str | Path | None = None,
    allow_replay: bool = False,
) -> ImportOutcome:
    if mode not in {"full_snapshot", "incremental"}:
        raise ValueError("mode phải là 'full_snapshot' hoặc 'incremental'.")
    parser_config = config or ParserConfig()
    parser_config_hash = _config_hash(parser_config)
    effective_scopes = list(scopes) if scopes is not None else _auto_scopes(result, mode)
    if result.report.is_valid:
        normalized_scopes = _validate_mode_and_scopes(mode, effective_scopes)
    else:
        normalized_scopes = [scope.normalized() for scope in effective_scopes]
    contract_hash, contract_json = _contract(mode, normalized_scopes)
    attempt_id, source_id, artifact_id, source_hash = _prepare_attempt(
        db_path,
        source_key,
        display_name or source_key,
        source_name,
        source_payload,
        parser_config_hash,
        mode,
        contract_hash,
        contract_json,
        parser_config.minimum_data_date,
        raw_dir,
    )
    if allow_replay:
        contract_hash, contract_json = _replay_contract(
            contract_hash, contract_json, attempt_id
        )
        _set_attempt(
            db_path,
            attempt_id,
            "received",
            contract_hash=contract_hash,
            contract_json=contract_json,
        )
    _set_attempt(db_path, attempt_id, "processing")
    if result.manifest.get("source_hash") not in {None, source_hash}:
        _set_attempt(
            db_path,
            attempt_id,
            "failed",
            failure_code="SOURCE_HASH_MISMATCH",
            failure_message="PipelineResult không thuộc source_payload đã cung cấp.",
        )
        raise ValueError("PipelineResult source hash không khớp source_payload.")
    return _process_result(
        db_path,
        attempt_id,
        source_id,
        artifact_id,
        source_hash,
        source_name,
        parser_config_hash,
        contract_hash,
        mode,
        normalized_scopes,
        result,
        allow_replay=allow_replay,
    )


def _process_result(
    db_path: str | Path,
    attempt_id: int,
    source_id: int,
    artifact_id: int,
    source_hash: str,
    source_name: str,
    parser_config_hash: str,
    contract_hash: str,
    mode: str,
    scopes: Sequence[ImportScope],
    result: PipelineResult,
    *,
    allow_replay: bool = False,
) -> ImportOutcome:
    with connect_database(db_path) as connection:
        duplicate_run_id = _existing_run(
            connection, source_id, source_hash, parser_config_hash, contract_hash
        )
    if duplicate_run_id is not None:
        _set_attempt(db_path, attempt_id, "duplicate", duplicate_of_run_id=duplicate_run_id)
        return ImportOutcome(
            attempt_id=attempt_id,
            status="duplicate",
            duplicate_of_run_id=duplicate_run_id,
            message="Workbook/config/import contract đã được commit trước đó.",
        )

    if not allow_replay:
        with connect_database(db_path) as connection:
            previous = connection.execute(
                """
                SELECT MAX(run_id) AS run_id
                FROM import_runs
                WHERE source_id = ? AND artifact_id = ? AND status = 'committed'
                """,
                (source_id, artifact_id),
            ).fetchone()
            previous_run_id = int(previous["run_id"]) if previous["run_id"] is not None else None
            newer_run_id = None
            if previous_run_id is not None:
                newer = connection.execute(
                    """
                    SELECT MAX(run_id) AS run_id
                    FROM import_runs
                    WHERE source_id = ? AND run_id > ? AND artifact_id <> ?
                      AND status = 'committed'
                    """,
                    (source_id, previous_run_id, artifact_id),
                ).fetchone()
                newer_run_id = int(newer["run_id"]) if newer["run_id"] is not None else None
        if previous_run_id is not None:
            if newer_run_id is not None:
                code = "STALE_ARTIFACT_REPLAY"
                message = (
                    f"Workbook này đã được áp dụng ở run #{previous_run_id}, nhưng đã có "
                    f"run mới hơn #{newer_run_id} từ workbook khác. Chặn replay để tránh "
                    "ghi đè current data bằng dữ liệu cũ."
                )
            else:
                code = "ARTIFACT_ALREADY_APPLIED"
                message = (
                    f"Workbook này đã được áp dụng ở run #{previous_run_id} với import contract khác. "
                    "Không tự áp dụng lại cùng nội dung; cần thao tác replay tường minh."
                )
            replay_issue = ValidationIssue("error", code, message)
            return _reject_attempt(
                db_path,
                attempt_id,
                [*result.report.issues, replay_issue],
                message,
            )

    if not result.report.is_valid:
        return _reject_attempt(
            db_path,
            attempt_id,
            result.report.issues,
            f"Quality gate có {len(result.report.errors)} error.",
        )

    data = result.data.copy()
    if not data.empty:
        key_frame = data.assign(
            _date=pd.to_datetime(data["date"]).dt.date.astype(str)
        )[["entity_id", "_date", "metric_normalized"]]
        duplicate_mask = key_frame.duplicated(keep=False)
        if duplicate_mask.any():
            issue = ValidationIssue(
                "error",
                "DUPLICATE_LOGICAL_KEY",
                f"Có {int(duplicate_mask.sum())} record trùng entity/date/metric; import bị từ chối.",
            )
            return _reject_attempt(
                db_path,
                attempt_id,
                [*result.report.issues, issue],
                issue.message,
            )

    return _commit_result(
        db_path,
        attempt_id,
        source_id,
        artifact_id,
        source_hash,
        source_name,
        parser_config_hash,
        contract_hash,
        mode,
        scopes,
        result,
    )


def _upsert_projects(
    connection: sqlite3.Connection,
    source_id: int,
    run_id: int,
    entities: pd.DataFrame,
) -> dict[str, int]:
    now = utc_now()
    project_map: dict[str, int] = {}
    projects = entities.sort_values(["entity_depth", "source_row"]).drop_duplicates("project_id")
    for row in projects.itertuples(index=False):
        project_key = str(row.project_id)
        existing = connection.execute(
            "SELECT project_id, current_revision_id FROM projects WHERE source_id = ? AND project_key = ?",
            (source_id, project_key),
        ).fetchone()
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO projects(
                    source_id, project_key, current_revision_id,
                    first_seen_run_id, last_seen_run_id, is_active
                ) VALUES (?, ?, NULL, ?, ?, 1)
                """,
                (source_id, project_key, run_id, run_id),
            )
            project_id = int(cursor.lastrowid)
            current_revision_id = None
        else:
            project_id = int(existing["project_id"])
            current_revision_id = existing["current_revision_id"]
        revision_hash = content_hash(
            {"project_label": str(row.project_label), "sheet_name": str(row.sheet_name)}
        )
        previous_hash = None
        if current_revision_id is not None:
            previous_hash = connection.execute(
                "SELECT semantic_hash FROM project_revisions WHERE project_revision_id = ?",
                (current_revision_id,),
            ).fetchone()[0]
        if revision_hash != previous_hash:
            cursor = connection.execute(
                """
                INSERT INTO project_revisions(
                    project_id, run_id, semantic_hash, project_label, sheet_name, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, run_id, revision_hash, str(row.project_label), str(row.sheet_name), now),
            )
            current_revision_id = int(cursor.lastrowid)
        connection.execute(
            """
            UPDATE projects
            SET current_revision_id = ?, last_seen_run_id = ?, is_active = 1
            WHERE project_id = ?
            """,
            (current_revision_id, run_id, project_id),
        )
        project_map[project_key] = project_id
    return project_map


def _upsert_entities(
    connection: sqlite3.Connection,
    source_id: int,
    run_id: int,
    entities: pd.DataFrame,
    project_map: dict[str, int],
) -> dict[str, int]:
    now = utc_now()
    entity_map = {
        row["external_entity_key"]: int(row["entity_id"])
        for row in connection.execute(
            """
            SELECT external_entity_key, entity_id FROM entity_aliases
            WHERE source_id = ? AND valid_to_run_id IS NULL
            """,
            (source_id,),
        )
    }
    ordered = entities.sort_values(["entity_depth", "source_row", "entity_id"])
    for row in ordered.itertuples(index=False):
        external_key = str(row.entity_id)
        project_id = project_map[str(row.project_id)]
        parent_id = entity_map.get(_text(row.parent_entity_id))
        entity_id = entity_map.get(external_key)
        if entity_id is None:
            cursor = connection.execute(
                """
                INSERT INTO entities(
                    source_id, project_id, parent_entity_id, current_revision_id,
                    first_seen_run_id, last_seen_run_id, is_active
                ) VALUES (?, ?, ?, NULL, ?, ?, 1)
                """,
                (source_id, project_id, parent_id, run_id, run_id),
            )
            entity_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO entity_aliases(
                    source_id, external_entity_key, entity_id,
                    valid_from_run_id, valid_to_run_id, alias_reason
                ) VALUES (?, ?, ?, ?, NULL, 'initial')
                """,
                (source_id, external_key, entity_id, run_id),
            )
            entity_map[external_key] = entity_id
        unit_source_id = entity_map.get(_text(row.unit_source_entity_id))
        payload = {
            "external_entity_key": external_key,
            "sheet_name": str(row.sheet_name),
            "source_row": int(row.source_row),
            "parent_entity_id": parent_id,
            "entity_level": str(row.entity_level),
            "entity_depth": int(row.entity_depth),
            "entity_label": str(row.entity_label),
            "entity_path": str(row.entity_path),
            "unit_raw": _text(row.unit_raw),
            "unit_original": _text(row.unit_original),
            "unit_normalized": _text(row.unit_normalized),
            "effective_unit": _text(row.effective_unit),
            "unit_source_level": _text(row.unit_source_level),
            "unit_source_entity_id": unit_source_id,
            "parser_rule": _text(row.parser_rule),
            "parser_confidence": _text(row.parser_confidence),
        }
        revision_hash = content_hash(payload)
        current = connection.execute(
            """
            SELECT e.current_revision_id, er.semantic_hash
            FROM entities e
            LEFT JOIN entity_revisions er ON er.entity_revision_id = e.current_revision_id
            WHERE e.entity_id = ?
            """,
            (entity_id,),
        ).fetchone()
        current_revision_id = current["current_revision_id"]
        if current["semantic_hash"] != revision_hash:
            cursor = connection.execute(
                """
                INSERT INTO entity_revisions(
                    entity_id, run_id, semantic_hash, external_entity_key, sheet_name, source_row,
                    parent_entity_id, entity_level, entity_depth, entity_label, entity_path,
                    unit_raw, unit_original, unit_normalized, effective_unit,
                    unit_source_level, unit_source_entity_id, parser_rule, parser_confidence, recorded_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    entity_id,
                    run_id,
                    revision_hash,
                    payload["external_entity_key"],
                    payload["sheet_name"],
                    payload["source_row"],
                    payload["parent_entity_id"],
                    payload["entity_level"],
                    payload["entity_depth"],
                    payload["entity_label"],
                    payload["entity_path"],
                    payload["unit_raw"],
                    payload["unit_original"],
                    payload["unit_normalized"],
                    payload["effective_unit"],
                    payload["unit_source_level"],
                    payload["unit_source_entity_id"],
                    payload["parser_rule"],
                    payload["parser_confidence"],
                    now,
                ),
            )
            current_revision_id = int(cursor.lastrowid)
        connection.execute(
            """
            UPDATE entities
            SET project_id = ?, parent_entity_id = ?, current_revision_id = ?,
                last_seen_run_id = ?, is_active = 1
            WHERE entity_id = ?
            """,
            (project_id, parent_id, current_revision_id, run_id, entity_id),
        )
    return entity_map


def _ensure_metric(connection: sqlite3.Connection, metric: str) -> str:
    code = _metric_code(metric)
    value_type = "percentage" if "%" in metric else "count"
    connection.execute(
        """
        INSERT INTO metrics(metric_code, display_name, value_type, is_active)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(metric_code) DO UPDATE SET display_name = excluded.display_name, is_active = 1
        """,
        (code, metric, value_type),
    )
    return code


REVISION_COLUMNS = (
    "metric_original, metric_normalized, unit_normalized, effective_unit, raw_value_text, "
    "raw_value_type, value_numeric, value_numeric_text, chart_value, chart_value_text, "
    "display_value, number_format, value_kind, data_note, validation_status"
)


def _revision_values(row) -> tuple[dict[str, object], str]:
    raw_text, raw_type = raw_value(row.raw_value)
    value_numeric_text = decimal_text(_optional(row.value_numeric))
    chart_value_text = decimal_text(_optional(row.chart_value))
    values: dict[str, object] = {
        "metric_original": str(row.metric_original),
        "metric_normalized": str(row.metric_normalized),
        "unit_normalized": _text(row.unit_normalized),
        "effective_unit": _text(row.effective_unit),
        "raw_value_text": raw_text,
        "raw_value_type": raw_type,
        "value_numeric": _float(row.value_numeric),
        "value_numeric_text": value_numeric_text,
        "chart_value": _float(row.chart_value),
        "chart_value_text": chart_value_text,
        "display_value": _text(row.display_value) or "",
        "number_format": _text(row.number_format),
        "value_kind": str(row.value_kind),
        "data_note": _text(row.data_note),
        "validation_status": str(row.validation_status),
    }
    semantic_payload = {
        key: values[key]
        for key in (
            "raw_value_type",
            "raw_value_text",
            "value_numeric_text",
            "chart_value_text",
            "display_value",
            "number_format",
            "value_kind",
            "data_note",
            "unit_normalized",
            "effective_unit",
            "validation_status",
        )
    }
    return values, content_hash(semantic_payload)


def _insert_revision(
    connection: sqlite3.Connection,
    observation_id: int,
    run_id: int,
    change_type: str,
    semantic_hash: str,
    values: dict[str, object],
    *,
    is_deleted: int = 0,
) -> int:
    columns = [column.strip() for column in REVISION_COLUMNS.split(",")]
    placeholders = ", ".join("?" for _ in columns)
    cursor = connection.execute(
        f"""
        INSERT INTO observation_revisions(
            observation_id, run_id, change_type, semantic_hash, {REVISION_COLUMNS},
            is_deleted, recorded_at
        ) VALUES (?, ?, ?, ?, {placeholders}, ?, ?)
        """,
        (
            observation_id,
            run_id,
            change_type,
            semantic_hash,
            *(values[column] for column in columns),
            is_deleted,
            utc_now(),
        ),
    )
    revision_id = int(cursor.lastrowid)
    connection.execute(
        "INSERT INTO observation_revision_public_refs(revision_id, revision_ref) VALUES (?, ?)",
        (revision_id, f"rev_{uuid.uuid4().hex}"),
    )
    return revision_id


def _upsert_observations(
    connection: sqlite3.Connection,
    source_id: int,
    run_id: int,
    source_hash: str,
    source_name: str,
    data: pd.DataFrame,
    entity_map: dict[str, int],
) -> tuple[dict[str, int], set[int]]:
    counters = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "restored": 0,
        "lineage_changed": 0,
    }
    seen: set[int] = set()
    for row in data.itertuples(index=False):
        internal_entity_id = entity_map[str(row.entity_id)]
        observed_date = pd.Timestamp(row.date).date().isoformat()
        date.fromisoformat(observed_date)
        metric_code = _ensure_metric(connection, str(row.metric_normalized))
        values, semantic_hash = _revision_values(row)
        existing = connection.execute(
            """
            SELECT o.observation_id, o.current_revision_id, o.latest_presence_id, o.is_deleted,
                   r.semantic_hash, p.lineage_hash
            FROM observations o
            LEFT JOIN observation_revisions r ON r.revision_id = o.current_revision_id
            LEFT JOIN import_observation_presence p ON p.presence_id = o.latest_presence_id
            WHERE o.source_id = ? AND o.entity_id = ? AND o.observed_date = ? AND o.metric_code = ?
            """,
            (source_id, internal_entity_id, observed_date, metric_code),
        ).fetchone()
        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO observations(
                    source_id, entity_id, metric_code, observed_date,
                    current_revision_id, latest_presence_id,
                    first_seen_run_id, last_seen_run_id, is_deleted
                ) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, 0)
                """,
                (source_id, internal_entity_id, metric_code, observed_date, run_id, run_id),
            )
            observation_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO observation_public_refs(observation_id, observation_ref, created_at)
                VALUES (?, ?, ?)
                """,
                (observation_id, f"obs_{uuid.uuid4().hex}", utc_now()),
            )
            status = "inserted"
            revision_id = _insert_revision(
                connection, observation_id, run_id, "insert", semantic_hash, values
            )
            counters["inserted"] += 1
            previous_lineage_hash = None
        else:
            observation_id = int(existing["observation_id"])
            previous_lineage_hash = existing["lineage_hash"]
            if int(existing["is_deleted"]) == 1:
                status = "restored"
                revision_id = _insert_revision(
                    connection, observation_id, run_id, "restore", semantic_hash, values
                )
                counters["restored"] += 1
            elif existing["semantic_hash"] != semantic_hash:
                status = "updated"
                revision_id = _insert_revision(
                    connection, observation_id, run_id, "update", semantic_hash, values
                )
                counters["updated"] += 1
            else:
                status = "unchanged"
                revision_id = int(existing["current_revision_id"])
                counters["unchanged"] += 1

        lineage_payload = {
            "source_hash": source_hash,
            "sheet_name": str(row.sheet_name),
            "cell_address": str(row.cell_address),
            "source_row": int(row.source_row),
            "parser_version": PARSER_VERSION,
            "parser_rule": _text(row.parser_rule),
            "parser_confidence": _text(row.parser_confidence),
            "external_entity_key": str(row.entity_id),
        }
        lineage_hash = content_hash(lineage_payload)
        if status == "unchanged" and previous_lineage_hash not in {None, lineage_hash}:
            counters["lineage_changed"] += 1
        cursor = connection.execute(
            """
            INSERT INTO import_observation_presence(
                run_id, observation_id, sheet_name, cell_address, source_row,
                source_file, source_hash, lineage_hash, parser_rule,
                parser_confidence, presence_status, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                observation_id,
                str(row.sheet_name),
                str(row.cell_address),
                int(row.source_row),
                source_name,
                source_hash,
                lineage_hash,
                _text(row.parser_rule),
                _text(row.parser_confidence),
                status,
                utc_now(),
            ),
        )
        presence_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO observation_lineage_snapshots(
                presence_id, lineage_ref, observation_id, revision_id, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (presence_id, f"lin_{uuid.uuid4().hex}", observation_id, revision_id, utc_now()),
        )
        connection.execute(
            """
            UPDATE observations
            SET current_revision_id = ?, latest_presence_id = ?,
                last_seen_run_id = ?, is_deleted = 0
            WHERE observation_id = ?
            """,
            (revision_id, presence_id, run_id, observation_id),
        )
        seen.add(observation_id)
    return counters, seen


def _resolve_and_store_scopes(
    connection: sqlite3.Connection,
    run_id: int,
    source_id: int,
    mode: str,
    scopes: Sequence[ImportScope],
    project_map: dict[str, int],
    entity_map: dict[str, int],
) -> list[tuple[ImportScope, int | None, int | None, str | None]]:
    resolved = []
    for scope in scopes:
        project_id = None
        if scope.project_key is not None:
            project_id = project_map.get(scope.project_key)
            if project_id is None:
                row = connection.execute(
                    "SELECT project_id FROM projects WHERE source_id = ? AND project_key = ?",
                    (source_id, scope.project_key),
                ).fetchone()
                project_id = int(row[0]) if row else None
            if project_id is None:
                raise ValueError(f"Không resolve được project scope: {scope.project_key}")
        root_entity_id = None
        if scope.root_external_entity_key is not None:
            root_entity_id = entity_map.get(scope.root_external_entity_key)
            if root_entity_id is None:
                raise ValueError(
                    f"Không resolve được entity scope: {scope.root_external_entity_key}"
                )
        metric_code = _metric_code(scope.metric_code) if scope.metric_code else None
        if metric_code is not None:
            exists = connection.execute(
                "SELECT 1 FROM metrics WHERE metric_code = ?", (metric_code,)
            ).fetchone()
            if exists is None:
                raise ValueError(f"Không resolve được metric scope: {scope.metric_code}")
        if mode == "incremental" and scope.missing_policy == "tombstone":
            raise ValueError("Incremental scope không được tombstone.")
        selector = asdict(scope)
        scope_hash = content_hash(selector)
        connection.execute(
            """
            INSERT INTO import_scopes(
                run_id, sheet_name, project_key, project_id,
                root_external_entity_key, root_entity_id, metric_code,
                date_from, date_to, is_complete, missing_policy, scope_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                scope.sheet_name,
                scope.project_key,
                project_id,
                scope.root_external_entity_key,
                root_entity_id,
                metric_code,
                scope.date_from,
                scope.date_to,
                int(scope.is_complete),
                scope.missing_policy,
                scope_hash,
            ),
        )
        resolved.append((scope, project_id, root_entity_id, metric_code))
    return resolved


def _descendant_ids(connection: sqlite3.Connection, source_id: int, root_id: int) -> set[int]:
    rows = connection.execute(
        "SELECT entity_id, parent_entity_id FROM entities WHERE source_id = ?",
        (source_id,),
    )
    children: dict[int | None, list[int]] = {}
    for row in rows:
        children.setdefault(row["parent_entity_id"], []).append(int(row["entity_id"]))
    result: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(children.get(current, []))
    return result


def _apply_tombstones(
    connection: sqlite3.Connection,
    source_id: int,
    run_id: int,
    scopes: Sequence[tuple[ImportScope, int | None, int | None, str | None]],
    seen: set[int],
) -> int:
    deleted = 0
    already_deleted: set[int] = set()
    candidates = list(
        connection.execute(
            """
            SELECT o.observation_id, o.entity_id, o.metric_code, o.observed_date,
                   e.project_id, ep.sheet_name, r.*
            FROM observations o
            JOIN entities e ON e.entity_id = o.entity_id
            JOIN entity_revisions ep ON ep.entity_revision_id = e.current_revision_id
            JOIN observation_revisions r ON r.revision_id = o.current_revision_id
            WHERE o.source_id = ? AND o.is_deleted = 0
            """,
            (source_id,),
        )
    )
    revision_columns = [column.strip() for column in REVISION_COLUMNS.split(",")]
    for scope, project_id, root_entity_id, metric_code in scopes:
        if not scope.is_complete or scope.missing_policy != "tombstone":
            continue
        allowed_entities = (
            _descendant_ids(connection, source_id, root_entity_id)
            if root_entity_id is not None
            else None
        )
        for row in candidates:
            observation_id = int(row["observation_id"])
            if observation_id in seen or observation_id in already_deleted:
                continue
            if not (scope.date_from <= row["observed_date"] <= scope.date_to):
                continue
            if scope.sheet_name is not None and row["sheet_name"] != scope.sheet_name:
                continue
            if project_id is not None and int(row["project_id"]) != project_id:
                continue
            if allowed_entities is not None and int(row["entity_id"]) not in allowed_entities:
                continue
            if metric_code is not None and row["metric_code"] != metric_code:
                continue
            values = {column: row[column] for column in revision_columns}
            revision_id = _insert_revision(
                connection,
                observation_id,
                run_id,
                "delete",
                str(row["semantic_hash"]),
                values,
                is_deleted=1,
            )
            connection.execute(
                """
                UPDATE observations
                SET current_revision_id = ?, is_deleted = 1
                WHERE observation_id = ?
                """,
                (revision_id, observation_id),
            )
            already_deleted.add(observation_id)
            deleted += 1
    return deleted


def _commit_result(
    db_path: str | Path,
    attempt_id: int,
    source_id: int,
    artifact_id: int,
    source_hash: str,
    source_name: str,
    parser_config_hash: str,
    contract_hash: str,
    mode: str,
    scopes: Sequence[ImportScope],
    result: PipelineResult,
) -> ImportOutcome:
    connection = connect_database(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        duplicate_run_id = _existing_run(
            connection, source_id, source_hash, parser_config_hash, contract_hash
        )
        if duplicate_run_id is not None:
            connection.execute("ROLLBACK")
            _set_attempt(db_path, attempt_id, "duplicate", duplicate_of_run_id=duplicate_run_id)
            return ImportOutcome(
                attempt_id=attempt_id,
                status="duplicate",
                duplicate_of_run_id=duplicate_run_id,
                message="Duplicate được phát hiện lại tại commit boundary.",
            )

        dates = pd.to_datetime(result.data["date"]) if not result.data.empty else pd.Series(dtype="datetime64[ns]")
        now = utc_now()
        cursor = connection.execute(
            """
            INSERT INTO import_runs(
                attempt_id, source_id, artifact_id, source_hash,
                parser_config_hash, import_contract_hash, parser_version,
                import_mode, status, started_at, minimum_data_date, maximum_data_date,
                input_record_count, accepted_key_count, error_count, warning_count, manifest_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                source_id,
                artifact_id,
                source_hash,
                parser_config_hash,
                contract_hash,
                PARSER_VERSION,
                mode,
                now,
                dates.min().date().isoformat() if len(dates) else None,
                dates.max().date().isoformat() if len(dates) else None,
                len(result.data),
                len(result.data),
                len(result.report.errors),
                len(result.report.warnings),
                canonical_json(result.manifest),
            ),
        )
        run_id = int(cursor.lastrowid)
        connection.execute(
            "INSERT INTO import_run_public_refs(run_id, import_ref) VALUES (?, ?)",
            (run_id, f"imp_{uuid.uuid4().hex}"),
        )
        project_map = _upsert_projects(connection, source_id, run_id, result.entities)
        entity_map = _upsert_entities(
            connection, source_id, run_id, result.entities, project_map
        )
        resolved_scopes = _resolve_and_store_scopes(
            connection, run_id, source_id, mode, scopes, project_map, entity_map
        )
        counters, seen = _upsert_observations(
            connection,
            source_id,
            run_id,
            source_hash,
            source_name,
            result.data,
            entity_map,
        )
        deleted_count = _apply_tombstones(
            connection, source_id, run_id, resolved_scopes, seen
        )
        _store_issues(connection, attempt_id, result.report.issues, run_id)
        accepted_count = sum(
            counters[name] for name in ("inserted", "updated", "unchanged", "restored")
        )
        if accepted_count != len(result.data):
            raise RuntimeError(
                f"Counter invariant sai: accepted={accepted_count}, input={len(result.data)}"
            )
        connection.execute(
            """
            UPDATE import_runs
            SET status = 'committed', committed_at = ?, accepted_key_count = ?,
                inserted_count = ?, updated_count = ?, unchanged_count = ?,
                restored_count = ?, deleted_count = ?, lineage_changed_count = ?
            WHERE run_id = ?
            """,
            (
                utc_now(),
                accepted_count,
                counters["inserted"],
                counters["updated"],
                counters["unchanged"],
                counters["restored"],
                deleted_count,
                counters["lineage_changed"],
                run_id,
            ),
        )
        connection.execute(
            """
            UPDATE import_attempts
            SET status = 'committed', finished_at = ?
            WHERE attempt_id = ?
            """,
            (utc_now(), attempt_id),
        )
        connection.execute("COMMIT")
    except Exception as exc:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        _set_attempt(
            db_path,
            attempt_id,
            "failed",
            failure_code="COMMIT_FAILED",
            failure_message=str(exc),
        )
        raise StorageImportError(f"Không thể commit import attempt {attempt_id}: {exc}") from exc
    finally:
        connection.close()

    return ImportOutcome(
        attempt_id=attempt_id,
        status="committed",
        run_id=run_id,
        inserted_count=counters["inserted"],
        updated_count=counters["updated"],
        unchanged_count=counters["unchanged"],
        restored_count=counters["restored"],
        deleted_count=deleted_count,
        lineage_changed_count=counters["lineage_changed"],
    )
