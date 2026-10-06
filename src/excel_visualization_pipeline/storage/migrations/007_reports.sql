-- Report snapshots are durable and independent of the transient AI cache.
CREATE TABLE reports (
    report_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    source_key TEXT NOT NULL,
    latest_revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    request_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    UNIQUE(project, source_key, request_id)
);
CREATE TABLE report_revisions (
    report_id TEXT NOT NULL REFERENCES reports(report_id),
    revision INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    document_json TEXT NOT NULL,
    PRIMARY KEY(report_id, revision)
);
CREATE TABLE report_operations (
    report_id TEXT NOT NULL REFERENCES reports(report_id),
    request_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    PRIMARY KEY(report_id, request_id)
);
CREATE TABLE report_checks (
    report_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    checked_at TEXT NOT NULL,
    FOREIGN KEY(report_id, revision) REFERENCES report_revisions(report_id, revision),
    PRIMARY KEY(report_id, revision)
);
CREATE TABLE report_exports (
    report_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('pdf', 'docx')),
    renderer_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    document_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    artifact BLOB NOT NULL,
    FOREIGN KEY(report_id, revision) REFERENCES report_revisions(report_id, revision),
    PRIMARY KEY(report_id, revision, format)
);
CREATE INDEX reports_project ON reports(source_key, project, created_at);
