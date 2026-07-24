import sqlite3
from datetime import datetime, timezone

DB_PATH = "finsight.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticker TEXT NOT NULL,
            company_name TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            current_step TEXT,
            price_data TEXT,
            fundamentals TEXT,
            news_json TEXT,
            analysis_json TEXT,
            dcf_json TEXT,
            report_html TEXT,
            report_json TEXT,
            error_message TEXT
        )
    """)

    try:
        cur.execute("ALTER TABLE reports ADD COLUMN dcf_json TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            step_name TEXT,
            input_data TEXT,
            output_data TEXT,
            duration_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            current_step TEXT,
            input_type TEXT,
            holdings_json TEXT,
            enrichment_json TEXT,
            analysis_json TEXT,
            error_message TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_report(ticker, user_id):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO reports (ticker, user_id, status, current_step)
        VALUES (?, ?, 'pending', 'queued')
    """, (ticker, user_id))
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def update_report(report_id, **fields):
    if not fields:
        return
    columns = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [report_id]
    conn = get_connection()
    conn.execute(f"UPDATE reports SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_report(report_id, user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_reports(user_id, limit=5):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM reports WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_report(report_id, user_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM agent_logs WHERE report_id = ? AND report_id IN (SELECT id FROM reports WHERE user_id = ?)",
        (report_id, user_id),
    )
    conn.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    conn.commit()
    conn.close()


def log_agent_step(report_id, step_name, input_data, output_data, duration_ms):
    conn = get_connection()
    conn.execute("""
        INSERT INTO agent_logs (report_id, step_name, input_data, output_data, duration_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (report_id, step_name, input_data, output_data, duration_ms, _now()))
    conn.commit()
    conn.close()


def create_user(email, password_hash):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO users (email, password_hash, created_at)
        VALUES (?, ?, ?)
    """, (email, password_hash, _now()))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_portfolio_analysis(user_id, input_type):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO portfolio_analyses (user_id, status, current_step, input_type)
        VALUES (?, 'pending', 'queued', ?)
    """, (user_id, input_type))
    conn.commit()
    analysis_id = cur.lastrowid
    conn.close()
    return analysis_id


def update_portfolio_analysis(analysis_id, **fields):
    if not fields:
        return
    columns = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [analysis_id]
    conn = get_connection()
    conn.execute(f"UPDATE portfolio_analyses SET {columns} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_portfolio_analysis(analysis_id, user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM portfolio_analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_portfolio_analyses(user_id, limit=5):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM portfolio_analyses WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(row) for row in rows]
