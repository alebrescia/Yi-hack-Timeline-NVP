import os
import re
import time
import shutil
import ftplib
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config as cfg
import db

_download_locks = {}
_download_locks_guard = threading.Lock()

_CAMERA_TZ = ZoneInfo(cfg.CAMERA_TIMEZONE)
_LOCAL_TZ = ZoneInfo(cfg.TIMEZONE)


def _lock_for(path):
    with _download_locks_guard:
        lock = _download_locks.get(path)
        if lock is None:
            lock = threading.Lock()
            _download_locks[path] = lock
        return lock

# 2026Y07M26D07H
FOLDER_RE = re.compile(r"^(\d{4})Y(\d{2})M(\d{2})D(\d{2})H$")
# 21M22S38.mp4  ->  minute 21, second 22, duration 38s
# alcune camere aggiungono un prefisso (es. "E2") prima del nome standard:
# E221M22S38.mp4 viene comunque riconosciuto e trattato come 21M22S38.mp4
FILE_RE = re.compile(r"^(?:[A-Za-z]\d*)?(\d{2})M(\d{2})S(\d+)\.mp4$", re.IGNORECASE)


def connect(cam):
    ftp = ftplib.FTP()
    ftp.connect(cam["host"], cam.get("port", 21), timeout=15)
    ftp.login(cam.get("user", "anonymous"), cam.get("password", ""))
    ftp.set_pasv(True)
    return ftp


def _basename_list(ftp):
    """nlst() sometimes returns full paths, sometimes just names depending on server."""
    return [n.rsplit("/", 1)[-1] for n in ftp.nlst()]


def list_folders(ftp, root):
    ftp.cwd(root)
    names = _basename_list(ftp)
    folders = [n for n in names if FOLDER_RE.match(n)]
    return sorted(folders)


def list_files(ftp, root, folder):
    ftp.cwd(f"{root}/{folder}")
    names = _basename_list(ftp)
    files = [n for n in names if FILE_RE.match(n)]
    return sorted(files)


def parse_folder(folder):
    m = FOLDER_RE.match(folder)
    y, mo, d, h = (int(x) for x in m.groups())
    return y, mo, d, h


def parse_file(folder, filename):
    y, mo, d, h = parse_folder(folder)
    m = FILE_RE.match(filename)
    minute, second, duration = int(m.group(1)), int(m.group(2)), int(m.group(3))
    start_camera = datetime(y, mo, d, h, minute, second, tzinfo=_CAMERA_TZ)
    start_local = start_camera.astimezone(_LOCAL_TZ)
    end_local = start_local + timedelta(seconds=duration)
    return start_local, end_local, duration


def sync_camera(cam):
    """Scan the camera's FTP folder. Folders other than the most recent one
    are assumed immutable once indexed, so they're skipped on later runs."""
    root = cam.get("ftp_root", cfg.FTP_ROOT)
    ftp = connect(cam)
    try:
        folders = list_folders(ftp, root)
        folder_set = set(folders)

        # La camera registra in loop su uno storico fisso (es. ~3 giorni):
        # le cartelle più vecchie di quelle ancora presenti sulla SD vanno
        # rimosse dall'indice (e dalla eventuale cache video locale),
        # altrimenti resterebbero in timeline puntando a file non più
        # scaricabili.
        known_folders = db.get_distinct_folders(cam["id"])
        for stale_folder in known_folders - folder_set:
            locked_files = db.get_locked_filenames(cam["id"], stale_folder)
            remaining = db.delete_folder(cam["id"], stale_folder)
            _remove_cached_folder(cam["id"], stale_folder, keep_filenames=locked_files)
            if remaining:
                print(
                    f"[sync] camera {cam['name']}: cartella {stale_folder} scaduta, "
                    f"{remaining} clip bloccate conservate"
                )
            else:
                print(f"[sync] camera {cam['name']}: rimossa cartella scaduta {stale_folder}")

        for i, folder in enumerate(folders):
            is_last = i == len(folders) - 1
            if not is_last and db.is_folder_complete(cam["id"], folder):
                continue
            try:
                files = list_files(ftp, root, folder)
            except ftplib.error_perm:
                continue
            for filename in files:
                try:
                    start, end, duration = parse_file(folder, filename)
                except Exception:
                    continue
                db.upsert_clip(
                    cam["id"],
                    folder,
                    filename,
                    start.strftime("%Y-%m-%d %H:%M:%S"),
                    end.strftime("%Y-%m-%d %H:%M:%S"),
                    duration,
                )
            if not is_last:
                db.mark_folder_complete(cam["id"], folder)
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def ensure_local(camera_id, clip):
    """Download a clip to the local cache the first time it's requested,
    then serve subsequent requests straight from disk."""
    cam = next(c for c in cfg.CAMERAS if c["id"] == camera_id)
    root = cam.get("ftp_root", cfg.FTP_ROOT)
    local_dir = os.path.join(cfg.CACHE_DIR, str(camera_id), clip["folder"])
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, clip["filename"])

    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    # Avoids downloading the same clip twice if a normal "play" request and a
    # background prefetch for it race each other.
    lock = _lock_for(local_path)
    with lock:
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return local_path

        ftp = connect(cam)
        tmp_path = local_path + ".part"
        try:
            ftp.cwd(f"{root}/{clip['folder']}")
            with open(tmp_path, "wb") as f:
                ftp.retrbinary(f"RETR {clip['filename']}", f.write)
            os.replace(tmp_path, local_path)
        finally:
            try:
                ftp.quit()
            except Exception:
                pass
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    return local_path


def _remove_cached_folder(camera_id, folder, keep_filenames=None):
    """Elimina la cache locale (se presente) di una cartella che non esiste
    più sulla camera, cosi' non resta spazio occupato per clip ormai
    irraggiungibili. I file in keep_filenames (clip bloccate) non vengono
    toccati."""
    keep_filenames = keep_filenames or set()
    path = os.path.join(cfg.CACHE_DIR, str(camera_id), folder)
    if not os.path.isdir(path):
        return
    if not keep_filenames:
        shutil.rmtree(path, ignore_errors=True)
        return
    for name in os.listdir(path):
        if name in keep_filenames:
            continue
        try:
            os.remove(os.path.join(path, name))
        except OSError:
            pass


def prune_cache():
    """Keeps the local video cache (cache/) under control by deleting the
    oldest downloaded clips first, based on cache_max_mb and/or
    cache_max_age_hours from config.json. Runs once per background sync
    cycle. A file's age is its download time (mtime), which for this cache
    is a reliable proxy for "oldest/least relevant" since files are never
    modified after being written."""
    max_mb = cfg.CACHE_MAX_MB
    max_age_hours = cfg.CACHE_MAX_AGE_HOURS
    if not max_mb and not max_age_hours:
        return

    locked = db.get_all_locked()

    entries = []
    total_size = 0
    for root, _dirs, files in os.walk(cfg.CACHE_DIR):
        for name in files:
            if name.endswith(".part"):
                continue  # in-progress download, leave it alone
            path = os.path.join(root, name)

            # Le clip bloccate sono escluse del tutto dalla pulizia
            # automatica (né per età né per spazio occupato).
            rel_parts = os.path.relpath(path, cfg.CACHE_DIR).split(os.sep)
            if len(rel_parts) == 3:
                try:
                    rel_camera_id = int(rel_parts[0])
                except ValueError:
                    rel_camera_id = None
                if rel_camera_id is not None and (rel_camera_id, rel_parts[1], rel_parts[2]) in locked:
                    continue

            try:
                stat = os.stat(path)
            except OSError:
                continue
            entries.append([path, stat.st_size, stat.st_mtime])
            total_size += stat.st_size

    removed = 0

    if max_age_hours:
        cutoff = time.time() - max_age_hours * 3600
        remaining = []
        for entry in entries:
            path, size, mtime = entry
            if mtime < cutoff:
                if _try_remove(path):
                    total_size -= size
                    removed += 1
            else:
                remaining.append(entry)
        entries = remaining

    if max_mb:
        budget = max_mb * 1024 * 1024
        if total_size > budget:
            entries.sort(key=lambda e: e[2])  # oldest download first
            for path, size, _mtime in entries:
                if total_size <= budget:
                    break
                if _try_remove(path):
                    total_size -= size
                    removed += 1

    if removed:
        print(f"[cache] rimossi {removed} clip dalla cache (limiti configurati)")
        _remove_empty_dirs(cfg.CACHE_DIR)


def _try_remove(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def _remove_empty_dirs(root):
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if dirpath == root:
            continue
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
            except OSError:
                pass
