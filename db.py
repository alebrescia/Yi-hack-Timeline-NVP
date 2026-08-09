import sqlite3
import threading

import config as cfg

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(cfg.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id INTEGER NOT NULL,
            folder TEXT NOT NULL,
            filename TEXT NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,
            duration INTEGER NOT NULL,
            locked INTEGER NOT NULL DEFAULT 0,
            UNIQUE(camera_id, folder, filename)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            camera_id INTEGER NOT NULL,
            folder TEXT NOT NULL,
            complete INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (camera_id, folder)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_clips_cam_start ON clips(camera_id, start_ts)")

    # Migrazione per database creati con versioni precedenti, senza la
    # colonna 'locked' (le CREATE TABLE IF NOT EXISTS sopra non la
    # aggiungono a una tabella già esistente).
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(clips)").fetchall()]
    if "locked" not in cols:
        conn.execute("ALTER TABLE clips ADD COLUMN locked INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()


def upsert_clip(camera_id, folder, filename, start_ts, end_ts, duration):
    conn = get_conn()
    with _lock:
        conn.execute(
            """
            INSERT OR IGNORE INTO clips (camera_id, folder, filename, start_ts, end_ts, duration)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (camera_id, folder, filename, start_ts, end_ts, duration),
        )
        conn.commit()
    conn.close()


def mark_folder_complete(camera_id, folder):
    conn = get_conn()
    with _lock:
        conn.execute(
            """
            INSERT INTO sync_state (camera_id, folder, complete) VALUES (?, ?, 1)
            ON CONFLICT(camera_id, folder) DO UPDATE SET complete=1
            """,
            (camera_id, folder),
        )
        conn.commit()
    conn.close()


def is_folder_complete(camera_id, folder):
    conn = get_conn()
    row = conn.execute(
        "SELECT complete FROM sync_state WHERE camera_id=? AND folder=?",
        (camera_id, folder),
    ).fetchone()
    conn.close()
    return bool(row and row["complete"])


def get_days_with_counts(camera_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT date(start_ts) as day, COUNT(*) as cnt, SUM(duration) as total_seconds
        FROM clips
        WHERE camera_id=?
        GROUP BY day
        ORDER BY day
        """,
        (camera_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_clips_for_day(camera_id, day):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, folder, filename, start_ts, end_ts, duration, locked
        FROM clips
        WHERE camera_id=? AND date(start_ts) = ?
        ORDER BY start_ts
        """,
        (camera_id, day),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_clip(camera_id, clip_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM clips WHERE camera_id=? AND id=?", (camera_id, clip_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_locked(camera_id, clip_id, locked):
    conn = get_conn()
    with _lock:
        conn.execute(
            "UPDATE clips SET locked=? WHERE camera_id=? AND id=?",
            (1 if locked else 0, camera_id, clip_id),
        )
        conn.commit()
    conn.close()


def get_all_locked():
    """Tutte le clip bloccate, su tutte le camere: (camera_id, folder, filename).
    Usato dalla pulizia della cache per non toccarle mai."""
    conn = get_conn()
    rows = conn.execute("SELECT camera_id, folder, filename FROM clips WHERE locked=1").fetchall()
    conn.close()
    return {(r["camera_id"], r["folder"], r["filename"]) for r in rows}


def get_locked_filenames(camera_id, folder):
    conn = get_conn()
    rows = conn.execute(
        "SELECT filename FROM clips WHERE camera_id=? AND folder=? AND locked=1",
        (camera_id, folder),
    ).fetchall()
    conn.close()
    return {r["filename"] for r in rows}


def get_distinct_folders(camera_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT folder FROM clips WHERE camera_id=?", (camera_id,)
    ).fetchall()
    conn.close()
    return {r["folder"] for r in rows}


def delete_folder(camera_id, folder):
    """Rimuove dall'indice le clip di una cartella (ora) che la camera ha
    eliminato dalla SD — tranne quelle bloccate, che restano in indice (e in
    cache) anche se sulla camera non esistono più. Ritorna il numero di
    clip bloccate rimaste per quella cartella."""
    conn = get_conn()
    with _lock:
        conn.execute(
            "DELETE FROM clips WHERE camera_id=? AND folder=? AND locked=0",
            (camera_id, folder),
        )
        remaining = conn.execute(
            "SELECT COUNT(*) as c FROM clips WHERE camera_id=? AND folder=?",
            (camera_id, folder),
        ).fetchone()["c"]
        if remaining == 0:
            conn.execute(
                "DELETE FROM sync_state WHERE camera_id=? AND folder=?", (camera_id, folder)
            )
        conn.commit()
    conn.close()
    return remaining


def get_latest_clip(camera_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM clips WHERE camera_id=? ORDER BY start_ts DESC LIMIT 1",
        (camera_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
