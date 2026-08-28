-- Web Crawler SQLite schema
-- Tables: jobs, pages, links

CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    start_url   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending|running|done|cancelled|error
    options     TEXT NOT NULL DEFAULT '{}',         -- JSON blob of CrawlOptions
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_failed  INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    created_at  REAL NOT NULL,
    finished_at REAL
);

CREATE TABLE IF NOT EXISTS pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    url         TEXT NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 0,
    title       TEXT NOT NULL DEFAULT '',
    text_snippet TEXT NOT NULL DEFAULT '',
    content_type TEXT NOT NULL DEFAULT '',
    depth       INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    elapsed_ms  INTEGER NOT NULL DEFAULT 0,
    crawled_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id     INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    source_url  TEXT NOT NULL,
    target_url  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pages_job_id ON pages(job_id);
CREATE INDEX IF NOT EXISTS idx_links_page_id ON links(page_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
