"""
Storage for every prediction the bot makes, plus the outcome once the match
finishes. This log is the entire basis for honest evaluation -- without it
you're just trusting a script's word for it.

Backend is auto-selected:
  - If a DATABASE_URL env var is set (Render provides this automatically
    when you attach a Postgres database), it uses Postgres. This survives
    redeploys and free-instance restarts -- unlike local disk on Render.
  - Otherwise it falls back to the local SQLite file at config.DB_PATH,
    same as running it on your own PC.

Every function below behaves the same regardless of backend -- the rest of
the app (main.py, grade.py, metrics.py, calibrate.py, webapp.py) doesn't
need to know or care which one is active.
"""

import os
import sqlite3
from contextlib import contextmanager

from config import DB_PATH

DATABASE_URL = os.environ.get("DATABASE_URL")
USING_POSTGRES = bool(DATABASE_URL)

if USING_POSTGRES:
    import psycopg2
    import psycopg2.extras

    # Render's DATABASE_URL sometimes starts with "postgres://"; psycopg2
    # wants "postgresql://". Normalize it.
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    _db_dir = os.path.dirname(DB_PATH)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id INTEGER NOT NULL,
    league TEXT,
    home_team TEXT,
    away_team TEXT,
    kickoff TEXT,
    market TEXT NOT NULL,
    model_prob REAL NOT NULL,
    calibrated_prob REAL,
    market_prob REAL NOT NULL,
    best_odds REAL NOT NULL,
    bookmaker TEXT,
    edge REAL NOT NULL,
    kelly_stake_fraction REAL,
    kelly_stake_amount REAL,
    predicted_at TEXT DEFAULT (datetime('now')),
    result TEXT,
    graded_at TEXT
);

CREATE TABLE IF NOT EXISTS bankroll_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    bankroll REAL NOT NULL,
    note TEXT
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    fixture_id INTEGER NOT NULL,
    league TEXT,
    home_team TEXT,
    away_team TEXT,
    kickoff TEXT,
    market TEXT NOT NULL,
    model_prob REAL NOT NULL,
    calibrated_prob REAL,
    market_prob REAL NOT NULL,
    best_odds REAL NOT NULL,
    bookmaker TEXT,
    edge REAL NOT NULL,
    kelly_stake_fraction REAL,
    kelly_stake_amount REAL,
    predicted_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
    result TEXT,
    graded_at TEXT
);

CREATE TABLE IF NOT EXISTS bankroll_log (
    id SERIAL PRIMARY KEY,
    timestamp TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
    bankroll REAL NOT NULL,
    note TEXT
);
"""


def _ph(n: int) -> str:
    """Placeholder string for n values, in the active backend's style."""
    mark = "%s" if USING_POSTGRES else "?"
    return ", ".join([mark] * n)


@contextmanager
def get_conn():
    if USING_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        if USING_POSTGRES:
            conn.cursor().execute(SCHEMA_POSTGRES)
        else:
            conn.executescript(SCHEMA_SQLITE)


def insert_prediction(row: dict) -> int:
    cols = (
        "fixture_id, league, home_team, away_team, kickoff, market, "
        "model_prob, calibrated_prob, market_prob, best_odds, bookmaker, "
        "edge, kelly_stake_fraction, kelly_stake_amount"
    )
    values = (
        row["fixture_id"], row["league"], row["home_team"], row["away_team"],
        row["kickoff"], row["market"], row["model_prob"], row.get("calibrated_prob"),
        row["market_prob"], row["best_odds"], row.get("bookmaker"),
        row["edge"], row["kelly_stake_fraction"], row["kelly_stake_amount"],
    )
    with get_conn() as conn:
        cur = conn.cursor()
        if USING_POSTGRES:
            cur.execute(
                f"INSERT INTO predictions ({cols}) VALUES ({_ph(14)}) RETURNING id", values
            )
            return cur.fetchone()["id"]
        else:
            cur.execute(f"INSERT INTO predictions ({cols}) VALUES ({_ph(14)})", values)
            return cur.lastrowid


def get_ungraded_predictions():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM predictions WHERE result IS NULL")
        return [dict(r) for r in cur.fetchall()]


def get_graded_predictions():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM predictions WHERE result IS NOT NULL")
        return [dict(r) for r in cur.fetchall()]


def get_all_predictions(limit: int | None = None):
    with get_conn() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM predictions ORDER BY id DESC"
        if limit:
            query += f" LIMIT {int(limit)}"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def set_result(prediction_id: int, result: str):
    with get_conn() as conn:
        cur = conn.cursor()
        if USING_POSTGRES:
            cur.execute(
                "UPDATE predictions SET result = %s, graded_at = to_char(now(), 'YYYY-MM-DD HH24:MI:SS') WHERE id = %s",
                (result, prediction_id),
            )
        else:
            cur.execute(
                "UPDATE predictions SET result = ?, graded_at = datetime('now') WHERE id = ?",
                (result, prediction_id),
            )


def log_bankroll(bankroll: float, note: str = ""):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO bankroll_log (bankroll, note) VALUES ({_ph(2)})", (bankroll, note)
        )


def latest_bankroll(default: float) -> float:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT bankroll FROM bankroll_log ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row["bankroll"] if row else default


def get_bankroll_history(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT timestamp, bankroll, note FROM bankroll_log ORDER BY id ASC LIMIT {_ph(1)}",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
