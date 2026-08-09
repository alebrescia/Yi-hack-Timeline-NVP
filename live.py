import os
import subprocess
import threading
import time
from urllib.parse import urlsplit, urlunsplit, quote

import config as cfg

_processes = {}     # camera_id -> subprocess.Popen
_last_access = {}   # camera_id -> unix timestamp
_lock = threading.Lock()

IDLE_TIMEOUT_SECONDS = 30  # ferma ffmpeg se nessuno chiede segmenti da questo tempo


def _hls_dir(camera_id):
    d = os.path.join(cfg.HLS_DIR, str(camera_id))
    os.makedirs(d, exist_ok=True)
    return d


def _playlist_path(camera_id):
    return os.path.join(_hls_dir(camera_id), "stream.m3u8")


def _get_camera(camera_id):
    return next((c for c in cfg.CAMERAS if c["id"] == camera_id), None)


def _build_auth_url(cam):
    """Inserisce utente/password (quelli della diretta, non quelli FTP) nella
    URL RTSP, gestendo correttamente eventuali caratteri speciali."""
    live = cam.get("live") or {}
    url = live.get("rtsp_url")
    if not url:
        return None
    user = live.get("user")
    password = live.get("password", "")

    if not user:
        return url

    parts = urlsplit(url)
    host = parts.hostname or ""
    netloc = f"{host}:{parts.port}" if parts.port else host
    userinfo = quote(user, safe="")
    if password:
        userinfo += f":{quote(password, safe='')}"
    netloc = f"{userinfo}@{netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def is_running(camera_id):
    proc = _processes.get(camera_id)
    return proc is not None and proc.poll() is None


def touch(camera_id):
    _last_access[camera_id] = time.time()


def start(camera_id):
    cam = _get_camera(camera_id)
    if not cam:
        raise ValueError("camera sconosciuta")
    rtsp_url = _build_auth_url(cam)
    if not rtsp_url:
        raise ValueError(
            f"la camera '{cam['name']}' non ha una sezione 'live' configurata in config.json"
        )

    with _lock:
        if is_running(camera_id):
            touch(camera_id)
            return

        out_dir = _hls_dir(camera_id)
        for name in os.listdir(out_dir):
            try:
                os.remove(os.path.join(out_dir, name))
            except OSError:
                pass

        playlist = _playlist_path(camera_id)
        segment_pattern = os.path.join(out_dir, "seg_%05d.ts")

        cmd = [
            "ffmpeg", "-nostdin", "-loglevel", "warning",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "64k", "-ar", "44100", "-ac", "1",
            "-f", "hls",
            "-hls_time", str(cfg.LIVE_HLS_SEGMENT_SECONDS),
            "-hls_list_size", str(cfg.LIVE_HLS_LIST_SIZE),
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_filename", segment_pattern,
            playlist,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _processes[camera_id] = proc
        touch(camera_id)


def stop(camera_id):
    with _lock:
        proc = _processes.pop(camera_id, None)
    _last_access.pop(camera_id, None)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def wait_for_playlist(camera_id, timeout_seconds=10):
    playlist = _playlist_path(camera_id)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if os.path.exists(playlist) and os.path.getsize(playlist) > 0:
            return True
        if not is_running(camera_id):
            return False  # ffmpeg è morto subito, es. credenziali/URL sbagliati
        time.sleep(0.25)
    return os.path.exists(playlist)


def watchdog_loop():
    """Ferma le dirette che nessuno guarda più da IDLE_TIMEOUT_SECONDS,
    per non tenere ffmpeg (e il carico sulla camera) attivo inutilmente."""
    while True:
        now = time.time()
        for camera_id in list(_processes.keys()):
            last = _last_access.get(camera_id, 0)
            if now - last > IDLE_TIMEOUT_SECONDS:
                stop(camera_id)
        time.sleep(5)
