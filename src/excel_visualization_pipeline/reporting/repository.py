from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from threading import RLock

from ..storage.connection import connect_database, utc_now
from ..storage.migrations import initialize_database


class ReportConflict(ValueError):
    pass


def serialize(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def checksum(value) -> str:
    return sha256(serialize(value).encode('utf-8')).hexdigest()


# Mutations on the same report serialize, but other reports/dashboard remain free.
# SQLite compare-and-swap also protects against a second application process.
_locks_guard = RLock()
_locks: dict[tuple[str, str], RLock] = {}


def report_lock(db_path, key: str) -> RLock:
    with _locks_guard:
        return _locks.setdefault((str(Path(db_path).resolve()), key), RLock())


class ReportRepository:
    def __init__(self, db_path, source_key: str, project: str):
        self.db_path, self.source_key, self.project = db_path, source_key, project
        initialize_database(db_path)

    def _owner(self, connection, report_id):
        row = connection.execute('SELECT * FROM reports WHERE report_id=? AND project=? AND source_key=? '
                                 'AND NOT EXISTS (SELECT 1 FROM report_deletions d WHERE d.report_id=reports.report_id)',
                                 (report_id, self.project, self.source_key)).fetchone()
        if row is None:
            raise LookupError('Không tìm thấy báo cáo trong dự án này.')
        return row

    def created(self, request_id: str, request_hash: str) -> dict | None:
        with connect_database(self.db_path) as connection:
            row = connection.execute('SELECT report_id, request_hash FROM reports WHERE project=? AND source_key=? AND request_id=?',
                                     (self.project, self.source_key, request_id)).fetchone()
        if row:
            if row['request_hash'] != request_hash:
                raise ReportConflict('Mã thao tác đã được dùng cho cấu hình khác. Hãy tạo thao tác mới.')
            with connect_database(self.db_path) as connection:
                if connection.execute('SELECT 1 FROM report_deletions WHERE report_id=?', (row['report_id'],)).fetchone():
                    raise ReportConflict('Bản nháp đã được xóa. Hãy tạo báo cáo mới bằng thao tác mới.')
            return self.get(row['report_id'], 1)
        return None

    def create(self, document: dict, request_id: str, request_hash: str) -> dict:
        with connect_database(self.db_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                connection.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)',
                    (document['reportId'], self.project, self.source_key, 1, document['createdAt'], request_id, request_hash))
                connection.execute('INSERT INTO report_revisions VALUES (?,?,?,?)',
                    (document['reportId'], 1, document['updatedAt'], serialize(document)))
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise
        return document

    def get(self, report_id: str, revision: int | None = None) -> dict:
        with connect_database(self.db_path) as connection:
            owner = self._owner(connection, report_id)
            row = connection.execute('SELECT document_json FROM report_revisions WHERE report_id=? AND revision=?',
                                     (report_id, revision or owner['latest_revision'])).fetchone()
        if row is None:
            raise LookupError('Không tìm thấy phiên bản báo cáo này.')
        return json.loads(row['document_json'])

    def items(self) -> list[dict]:
        with connect_database(self.db_path) as connection:
            rows = connection.execute('SELECT r.report_id, r.latest_revision, v.document_json FROM reports r JOIN report_revisions v '
                'ON v.report_id=r.report_id AND v.revision=r.latest_revision WHERE r.project=? AND r.source_key=? '
                'AND NOT EXISTS (SELECT 1 FROM report_deletions d WHERE d.report_id=r.report_id) ORDER BY r.created_at DESC LIMIT 100',
                (self.project, self.source_key)).fetchall()
        return [{'reportId': row['report_id'], 'revision': row['latest_revision'],
                 **{key: json.loads(row['document_json'])[key] for key in ('title', 'createdAt', 'updatedAt', 'window')}} for row in rows]

    def delete(self, report_id: str, base_revision: int) -> dict:
        deleted_at = utc_now()
        with connect_database(self.db_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                owner = self._owner(connection, report_id)
                if owner['latest_revision'] != base_revision:
                    raise ReportConflict('Bản nháp đã có phiên bản mới. Mở lại bản mới nhất trước khi xóa.')
                connection.execute('INSERT INTO report_deletions VALUES (?,?,?)', (report_id, deleted_at, base_revision))
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise
        return {'reportId': report_id, 'status': 'deleted', 'deletedAt': deleted_at}

    def versions(self, report_id: str) -> list[dict]:
        with connect_database(self.db_path) as connection:
            self._owner(connection, report_id)
            rows = connection.execute('SELECT v.revision, v.created_at, c.checked_at FROM report_revisions v LEFT JOIN report_checks c '
                'ON c.report_id=v.report_id AND c.revision=v.revision WHERE v.report_id=? ORDER BY v.revision DESC', (report_id,)).fetchall()
        return [{'revision': row['revision'], 'createdAt': row['created_at'], 'checkedAt': row['checked_at']} for row in rows]

    def operation(self, report_id: str, request_id: str, request_hash: str) -> dict | None:
        with connect_database(self.db_path) as connection:
            self._owner(connection, report_id)
            row = connection.execute('SELECT * FROM report_operations WHERE report_id=? AND request_id=?', (report_id, request_id)).fetchone()
        if row:
            if row['request_hash'] != request_hash:
                raise ReportConflict('Mã thao tác đã được dùng cho nội dung khác.')
            return self.get(report_id, row['revision'])
        return None

    def require_latest(self, report_id: str, base_revision: int) -> dict:
        document = self.get(report_id)
        if document['revision'] != base_revision:
            raise ReportConflict('Báo cáo đã có phiên bản mới. Mở lại bản mới nhất trước khi thay đổi.')
        return document

    def append(self, document: dict, base_revision: int, request_id: str, request_hash: str) -> dict:
        payload = serialize(document)
        if len(payload.encode('utf-8')) > 25_000_000:
            raise ValueError('Báo cáo quá lớn để lưu. Hãy thu hẹp phạm vi.')
        with connect_database(self.db_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                self._owner(connection, document['reportId'])
                changed = connection.execute('UPDATE reports SET latest_revision=? WHERE report_id=? AND latest_revision=?',
                    (document['revision'], document['reportId'], base_revision)).rowcount
                if changed != 1:
                    raise ReportConflict('Một thao tác khác đã lưu phiên bản mới. Nội dung cũ không bị ghi đè.')
                connection.execute('INSERT INTO report_revisions VALUES (?,?,?,?)',
                    (document['reportId'], document['revision'], document['updatedAt'], payload))
                connection.execute('INSERT INTO report_operations VALUES (?,?,?,?)',
                    (document['reportId'], request_id, request_hash, document['revision']))
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise
        return document

    def check(self, report_id: str, revision: int) -> dict:
        with connect_database(self.db_path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            try:
                owner = self._owner(connection, report_id)
                if owner['latest_revision'] != revision:
                    raise ReportConflict('Chỉ đánh dấu bản mới nhất đã kiểm tra; hãy mở lại báo cáo.')
                connection.execute('INSERT OR IGNORE INTO report_checks VALUES (?,?,?)', (report_id, revision, utc_now()))
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise
        return self.review(report_id, revision)

    def review(self, report_id: str, revision: int) -> dict:
        with connect_database(self.db_path) as connection:
            self._owner(connection, report_id)
            row = connection.execute('SELECT checked_at FROM report_checks WHERE report_id=? AND revision=?', (report_id, revision)).fetchone()
        return {'status': 'checked' if row else 'needs_review', 'checkedAt': row['checked_at'] if row else None,
                'authority': 'local_check_only', 'publicationStatus': 'draft'}

    def exported(self, report_id: str, revision: int, format: str) -> tuple[bytes, dict] | None:
        with connect_database(self.db_path) as connection:
            self._owner(connection, report_id)
            row = connection.execute('SELECT * FROM report_exports WHERE report_id=? AND revision=? AND format=?', (report_id, revision, format)).fetchone()
        if not row:
            return None
        return bytes(row['artifact']), {key: row[key] for key in ('format', 'renderer_version', 'created_at', 'document_hash', 'content_hash')}

    def store_export(self, document: dict, format: str, artifact: bytes, renderer_version: str) -> dict:
        if len(artifact) > 30_000_000:
            raise ValueError('Tệp xuất quá lớn. Bản nháp đã lưu vẫn được giữ nguyên.')
        receipt = (document['reportId'], document['revision'], format, renderer_version, utc_now(), checksum(document), sha256(artifact).hexdigest(), artifact)
        with connect_database(self.db_path) as connection:
            self._owner(connection, document['reportId'])
            connection.execute('INSERT OR IGNORE INTO report_exports VALUES (?,?,?,?,?,?,?,?)', receipt)
        return self.exported(document['reportId'], document['revision'], format)[1]
