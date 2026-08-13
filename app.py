import os
import json
import stat
import secrets
import subprocess
import threading
import time
from datetime import timedelta

from flask import (
    Flask, jsonify, request, render_template, send_file, send_from_directory,
    abort, redirect, url_for, session,
)
from werkzeug.security import check_password_hash

import config as cfg
import db
import indexer
import live
import ssh_util
from changelog import CHANGELOG, APP_VERSION, APP_VERSION_DATE

_MESI_IT = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]


def _format_date_it(iso_date):
    from datetime import datetime
    d = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{d.day} {_MESI_IT[d.month - 1]} {d.year}"

app = Flask(__name__)
# I template (.html) di default restano in cache in memoria finché il
# processo non si riavvia. Disattivandolo, si aggiornano subito come i file
# statici — comodo mentre si continua a modificare l'interfaccia.
app.config["TEMPLATES_AUTO_RELOAD"] = True


def _load_or_create_secret_key():
    """Chiave persistente per firmare i cookie di sessione: se non esiste
    viene generata al primo avvio, cosi' le sessioni sopravvivono ai riavvii
    del server invece di disconnettere tutti ad ogni restart."""
    path = cfg.FLASK_SECRET_PATH
    if not os.path.exists(path):
        key = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as f:
            f.write(key)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 600: solo il proprietario
        return key
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


app.secret_key = _load_or_create_secret_key()
app.permanent_session_lifetime = timedelta(days=cfg.AUTH.get("session_days", 30))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Il cookie va marcato "Secure" solo se il sito e' davvero servito in HTTPS,
# altrimenti il browser lo scarterebbe e nessuno riuscirebbe piu' a fare login.
app.config["SESSION_COOKIE_SECURE"] = bool(cfg.HTTPS.get("enabled"))


@app.before_request
def _require_auth():
    if not cfg.AUTH.get("enabled"):
        return None
    if request.path.startswith("/static/") or request.path in ("/sw.js", "/login"):
        return None
    if session.get("authenticated"):
        return None

    # Le chiamate API/risorse (fetch, <video>, ecc.) non possono essere
    # reindirizzate a una pagina HTML di login: rispondono con un 401 JSON,
    # che il frontend intercetta per rimandare l'utente al login. Le vere
    # navigazioni di pagina vengono invece reindirizzate direttamente.
    if request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "sessione scaduta, effettua di nuovo l'accesso"}), 401
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid = False
        if username == cfg.AUTH.get("username") and cfg.AUTH.get("password_hash"):
            try:
                valid = check_password_hash(cfg.AUTH["password_hash"], password)
            except ValueError:
                valid = False

        if valid:
            session.permanent = True
            session["authenticated"] = True
            next_url = request.form.get("next") or url_for("index")
            if not next_url.startswith("/"):  # niente redirect verso siti esterni
                next_url = url_for("index")
            return redirect(next_url)

        error = "Utente o password non validi."

    return render_template("login.html", error=error, next=request.args.get("next", ""))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


_sync_lock = threading.Lock()
_last_sync_error = {}


def background_sync_loop():
    while True:
        for cam in cfg.CAMERAS:
            try:
                with _sync_lock:
                    indexer.sync_camera(cam)
                _last_sync_error[cam["id"]] = None
            except Exception as e:
                _last_sync_error[cam["id"]] = str(e)
                print(f"[sync] camera {cam['name']} error: {e}")
        try:
            indexer.prune_cache()
        except Exception as e:
            print(f"[cache] errore pulizia cache: {e}")
        time.sleep(cfg.SYNC_INTERVAL_SECONDS)


@app.route("/")
def index():
    return render_template("index.html", cameras=cfg.CAMERAS, auth_enabled=cfg.AUTH.get("enabled", False))


@app.route("/settings", methods=["GET"])
def settings():
    with open(cfg.CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return render_template(
        "settings.html",
        config=raw,
        auth_enabled=cfg.AUTH.get("enabled", False),
        app_version=APP_VERSION,
        app_version_date=_format_date_it(APP_VERSION_DATE),
    )


@app.route("/changelog")
def changelog():
    entries = []
    for e in CHANGELOG:
        entries.append({**e, "date_formatted": _format_date_it(e["date"])})
    return render_template(
        "changelog.html",
        entries=entries,
        auth_enabled=cfg.AUTH.get("enabled", False),
    )


@app.route("/api/settings", methods=["POST"])
def api_settings_save():
    """Valida e salva il config.json, poi riavvia il servizio in background
    (se in esecuzione sotto systemd) perché le modifiche abbiano effetto."""
    try:
        new_cfg = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "JSON non valido"}), 400

    errors = _validate_config(new_cfg)
    if errors:
        return jsonify({"status": "error", "message": "\n".join(errors)}), 400

    # Non permettiamo mai di modificare la password di accesso da qui —
    # quella si cambia solo con set_password.py da terminale.
    try:
        with open(cfg.CONFIG_PATH, "r", encoding="utf-8") as f:
            original = json.load(f)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Impossibile leggere config.json: {e}"}), 500

    if "auth" in original:
        # Preserva l'intero blocco auth dal config originale
        new_cfg["auth"] = original["auth"]

    # Preserva i valori cifrati delle password camera: se l'utente non le
    # ha modificate (il frontend manda None per i campi password intatti),
    # rimettiamo il valore originale (potenzialmente già cifrato).
    orig_by_id = {c["id"]: c for c in original.get("cameras", [])}
    for cam in new_cfg.get("cameras", []):
        orig = orig_by_id.get(cam.get("id")) or {}
        if not cam.get("password"):
            cam["password"] = orig.get("password", "")
        live = cam.get("live")
        if live and not live.get("password"):
            orig_live = orig.get("live") or {}
            live["password"] = orig_live.get("password", "")

    tmp_path = cfg.CONFIG_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, cfg.CONFIG_PATH)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Impossibile salvare config.json: {e}"}), 500

    _restart_service_async()
    return jsonify({"status": "ok", "message": "Configurazione salvata. Il server si sta riavviando..."})


def _validate_config(c):
    errors = []
    if not isinstance(c.get("cameras"), list):
        errors.append("'cameras' deve essere una lista.")
    else:
        ids = []
        for i, cam in enumerate(c["cameras"]):
            if not isinstance(cam.get("id"), int):
                errors.append(f"Camera #{i+1}: 'id' deve essere un numero intero.")
            elif cam["id"] in ids:
                errors.append(f"Camera #{i+1}: id {cam['id']} duplicato.")
            else:
                ids.append(cam["id"])
            if not cam.get("name"):
                errors.append(f"Camera #{i+1}: 'name' non può essere vuoto.")
            if not cam.get("host"):
                errors.append(f"Camera #{i+1}: 'host' non può essere vuoto.")
    if not isinstance(c.get("sync_interval_seconds"), int) or c["sync_interval_seconds"] < 5:
        errors.append("'sync_interval_seconds' deve essere un intero >= 5.")
    return errors


def _restart_service_async():
    """Tenta di riavviare l'unità systemd in background, senza bloccare la
    risposta HTTP. Se il server non gira sotto systemd (es. avvio manuale
    con python3 app.py), lo skip è silenzioso: l'utente dovrà riavviarlo
    manualmente in quel caso."""
    def _do():
        time.sleep(1.5)  # lascia il tempo alla risposta di arrivare al browser
        try:
            subprocess.run(
                ["sudo", "systemctl", "restart", "yicam-timeline"],
                timeout=10, check=False, capture_output=True,
            )
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


@app.route("/wall/<int:group>")
def wall(group):
    """Pagina con le dirette configurate per questo gruppo (vedi
    'live_walls' in config.json). Gli slot senza una camera configurata (o
    senza sezione 'live') mostrano un placeholder invece di tentare la diretta."""
    ids = cfg.LIVE_WALLS.get(str(group))
    if ids is None:
        abort(404)
    by_id = {c["id"]: c for c in cfg.CAMERAS}
    slots = [by_id.get(i) for i in ids]
    return render_template("wall.html", group=group, slots=slots)


@app.route("/sw.js")
def service_worker():
    # Servito dalla radice (non da /static/) cosi' il suo scope copre tutta
    # l'app, non solo /static/ — condizione necessaria perche' Chrome offra
    # la vera installazione della PWA e non la semplice "crea scorciatoia".
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/api/cameras")
def api_cameras():
    return jsonify(
        [
            {
                "id": c["id"],
                "name": c["name"],
                "sync_error": _last_sync_error.get(c["id"]),
                "has_live": bool((c.get("live") or {}).get("rtsp_url")),
                "icon": c.get("icon"),
            }
            for c in cfg.CAMERAS
        ]
    )


@app.route("/api/days")
def api_days():
    camera_id = int(request.args.get("camera_id"))
    return jsonify(db.get_days_with_counts(camera_id))


@app.route("/api/timeline")
def api_timeline():
    camera_id = int(request.args.get("camera_id"))
    day = request.args.get("date")
    if not day:
        abort(400, "parametro 'date' mancante (YYYY-MM-DD)")
    return jsonify(db.get_clips_for_day(camera_id, day))


@app.route("/api/latest")
def api_latest():
    camera_id = int(request.args.get("camera_id"))
    clip = db.get_latest_clip(camera_id)
    return jsonify(clip)


@app.route("/api/clip/<int:camera_id>/<int:clip_id>")
def api_clip(camera_id, clip_id):
    clip = db.get_clip(camera_id, clip_id)
    if not clip:
        abort(404)
    try:
        local_path = indexer.ensure_local(camera_id, clip)
    except Exception as e:
        abort(502, f"impossibile scaricare il file dalla camera: {e}")
    return send_file(local_path, mimetype="video/mp4", conditional=True)


@app.route("/api/clip/<int:camera_id>/<int:clip_id>/download")
def api_clip_download(camera_id, clip_id):
    clip = db.get_clip(camera_id, clip_id)
    if not clip:
        abort(404)
    try:
        local_path = indexer.ensure_local(camera_id, clip)
    except Exception as e:
        abort(502, f"impossibile scaricare il file dalla camera: {e}")

    cam = next((c for c in cfg.CAMERAS if c["id"] == camera_id), None)
    cam_name = (cam["name"] if cam else f"camera{camera_id}").replace(" ", "_")
    safe_ts = clip["start_ts"].replace(":", "-").replace(" ", "_")
    download_name = f"{cam_name}_{safe_ts}.mp4"

    return send_file(
        local_path,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/api/clip/<int:camera_id>/<int:clip_id>/lock", methods=["POST", "DELETE"])
def api_clip_lock(camera_id, clip_id):
    clip = db.get_clip(camera_id, clip_id)
    if not clip:
        abort(404)

    locked = request.method == "POST"
    if locked:
        # Bloccare una clip la scarica subito (se non già in cache) e la
        # rende permanente: la camera non gestisce il "blocco" lato suo,
        # quindi possiamo solo garantire che la NOSTRA copia locale resti
        # protetta anche quando la camera elimina l'originale dalla SD.
        try:
            indexer.ensure_local(camera_id, clip)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"impossibile scaricare la clip per bloccarla: {e}",
            }), 502

    db.set_locked(camera_id, clip_id, locked)
    return jsonify({"status": "ok", "locked": locked})


@app.route("/api/prefetch/<int:camera_id>/<int:clip_id>", methods=["POST"])
def api_prefetch(camera_id, clip_id):
    """Kicks off a background download of a clip into the local cache without
    blocking the request or sending the video bytes back. Used to warm the
    cache for the clip that will play next, so playback is instant."""
    clip = db.get_clip(camera_id, clip_id)
    if not clip:
        return jsonify({"status": "not_found"}), 404

    def _bg():
        try:
            indexer.ensure_local(camera_id, clip)
        except Exception as e:
            print(f"[prefetch] camera {camera_id} clip {clip_id} error: {e}")

    threading.Thread(target=_bg, daemon=True).start()
    return jsonify({"status": "started"}), 202


@app.route("/api/live/<int:camera_id>/start", methods=["POST"])
def api_live_start(camera_id):
    try:
        live.start(camera_id)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    ready = live.wait_for_playlist(camera_id)
    if not ready:
        return jsonify({
            "status": "error",
            "message": "ffmpeg non è riuscito ad agganciare lo stream RTSP (controlla URL/utente/password della diretta)",
        }), 502
    return jsonify({"status": "ok"})


@app.route("/api/live/<int:camera_id>/stop", methods=["POST"])
def api_live_stop(camera_id):
    live.stop(camera_id)
    return jsonify({"status": "ok"})


@app.route("/api/live/<int:camera_id>/<path:filename>")
def api_live_file(camera_id, filename):
    live.touch(camera_id)
    directory = os.path.join(cfg.HLS_DIR, str(camera_id))
    if not os.path.exists(os.path.join(directory, filename)):
        abort(404)
    resp = send_from_directory(directory, filename)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/api/camera/<int:camera_id>/reboot", methods=["POST"])
def api_camera_reboot(camera_id):
    cam = next((c for c in cfg.CAMERAS if c["id"] == camera_id), None)
    if not cam:
        abort(404)
    try:
        ssh_util.reboot_camera(cam)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Impossibile contattare la camera via SSH: {e}",
        }), 502
    return jsonify({"status": "ok", "message": f"Comando di riavvio inviato a '{cam['name']}'."})


@app.route("/api/sync", methods=["POST"])
def api_sync():
    body = request.get_json(silent=True) or {}
    camera_id = body.get("camera_id")
    cams = cfg.CAMERAS if camera_id is None else [c for c in cfg.CAMERAS if c["id"] == camera_id]
    for cam in cams:
        with _sync_lock:
            indexer.sync_camera(cam)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import shutil
    if shutil.which("ffmpeg") is None:
        print("[live] ATTENZIONE: 'ffmpeg' non è installato o non è nel PATH. "
              "La diretta non funzionerà finché non lo installi (es. 'sudo apt install ffmpeg').")

    db.init_db()
    t = threading.Thread(target=background_sync_loop, daemon=True)
    t.start()
    t2 = threading.Thread(target=live.watchdog_loop, daemon=True)
    t2.start()

    ssl_context = None
    if cfg.HTTPS.get("enabled"):
        cert, key = cfg.HTTPS["cert"], cfg.HTTPS["key"]
        if os.path.exists(cert) and os.path.exists(key):
            ssl_context = (cert, key)
            print(f"[https] attivo con {cert}")
        else:
            print(f"[https] cert/key non trovati ({cert}, {key}) — avvio HTTP semplice."
                  f" Esegui ./generate_cert.sh per crearli.")

    if cfg.AUTH.get("enabled"):
        print(f"[auth] richiesto login per l'utente '{cfg.AUTH.get('username')}'")

    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True, ssl_context=ssl_context)
