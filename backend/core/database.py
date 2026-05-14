import sqlite3
import os

DB_PATH = None

def get_db_path():
    global DB_PATH
    if DB_PATH is None:
        from backend.core.config import settings
        DB_PATH = settings.database_path
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            genre           TEXT,
            story_cards     TEXT,
            style_sig       TEXT,
            omniscient      TEXT,
            settings        TEXT,
            experience_flags TEXT,
            chapter_count   INTEGER DEFAULT 30,
            last_snapshot_at TEXT,
            import_source   TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS blocks (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            type         TEXT NOT NULL,
            canvas_x     REAL DEFAULT 0,
            canvas_y     REAL DEFAULT 0,
            canvas_w     REAL DEFAULT 280,
            collapsed    INTEGER DEFAULT 0,
            color        TEXT,
            timeline_id  TEXT,
            chapter_pos  TEXT,
            completeness REAL DEFAULT 0.0,
            tags         TEXT DEFAULT '[]',
            notes        TEXT DEFAULT '',
            content      TEXT NOT NULL DEFAULT '{}',
            is_draft     INTEGER DEFAULT 0,
            save_status  TEXT DEFAULT 'saved',
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS connections (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            from_block   TEXT NOT NULL,
            to_block     TEXT NOT NULL,
            conn_type    TEXT NOT NULL,
            label        TEXT,
            chapter_hint TEXT,
            created_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (from_block) REFERENCES blocks(id),
            FOREIGN KEY (to_block) REFERENCES blocks(id)
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL,
            chapter_num  INTEGER NOT NULL,
            title        TEXT,
            timeline_id  TEXT,
            outline      TEXT,
            content      TEXT,
            audit_result TEXT,
            status       TEXT DEFAULT 'planned',
            word_count   INTEGER DEFAULT 0,
            block_refs   TEXT DEFAULT '[]',
            special_links TEXT DEFAULT '[]',
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS canvas_layout (
            project_id   TEXT PRIMARY KEY,
            viewport_x   REAL DEFAULT 0,
            viewport_y   REAL DEFAULT 0,
            zoom         REAL DEFAULT 1.0,
            timeline_y   TEXT DEFAULT '{}',
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id               TEXT PRIMARY KEY,
            project_id       TEXT NOT NULL,
            snapshot_type    TEXT NOT NULL,
            label            TEXT,
            blocks_json      TEXT NOT NULL,
            connections_json TEXT NOT NULL,
            canvas_layout_json TEXT,
            chapters_json    TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            word_count       INTEGER DEFAULT 0,
            block_count      INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE INDEX IF NOT EXISTS idx_blocks_project ON blocks(project_id);
        CREATE INDEX IF NOT EXISTS idx_connections_project ON connections(project_id);
        CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);
        CREATE INDEX IF NOT EXISTS idx_snapshots_project ON snapshots(project_id);
    """)

    # Migration: add new columns if they don't exist
    _migrate_add_column(conn, "projects", "last_snapshot_at", "TEXT")
    _migrate_add_column(conn, "projects", "import_source", "TEXT")
    _migrate_add_column(conn, "blocks", "save_status", "TEXT DEFAULT 'saved'")
    _migrate_add_column(conn, "blocks", "on_canvas", "INTEGER DEFAULT 1")
    # 修复已有数据：NULL → 1
    conn.execute("UPDATE blocks SET on_canvas = 1 WHERE on_canvas IS NULL")
    _migrate_add_column(conn, "chapters", "special_links", "TEXT DEFAULT '[]'")

    conn.commit()
    conn.close()


def _migrate_add_column(conn: sqlite3.Connection, table: str, column: str, col_type: str):
    """安全地添加列（如果不存在）"""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {row["name"] for row in cursor.fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

