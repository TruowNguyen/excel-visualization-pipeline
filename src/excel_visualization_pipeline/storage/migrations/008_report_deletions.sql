CREATE TABLE report_deletions (
    report_id TEXT PRIMARY KEY REFERENCES reports(report_id),
    deleted_at TEXT NOT NULL,
    base_revision INTEGER NOT NULL
);
