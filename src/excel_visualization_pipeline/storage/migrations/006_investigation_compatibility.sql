-- Some internal databases applied an early 005 draft without a cursor secret.
-- Keep this migration idempotent for databases that already have the table.
CREATE TABLE IF NOT EXISTS aggregate_cursor_secret (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    secret BLOB NOT NULL
);

INSERT OR IGNORE INTO aggregate_cursor_secret(singleton, secret)
VALUES (1, randomblob(32));

CREATE TABLE IF NOT EXISTS validation_issue_public_refs (
    issue_id INTEGER PRIMARY KEY REFERENCES validation_issues(issue_id),
    issue_ref TEXT NOT NULL UNIQUE
);

INSERT INTO validation_issue_public_refs(issue_id, issue_ref)
SELECT issue_id, 'val_' || lower(hex(randomblob(16)))
FROM validation_issues
WHERE issue_id NOT IN (SELECT issue_id FROM validation_issue_public_refs);
