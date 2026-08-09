import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("YICAM_CONFIG", os.path.join(BASE_DIR, "config.json"))

if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(
        f"File di configurazione non trovato: {CONFIG_PATH}\n"
        f"Copia config.example.json in config.json e inserisci le tue camere."
    )

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _cfg = json.load(f)

import crypto_util

CAMERAS = _cfg["cameras"]
for _cam in CAMERAS:
    if _cam.get("password"):
        _cam["password"] = crypto_util.decrypt(_cam["password"])
    _live = _cam.get("live")
    if _live and _live.get("password"):
        _live["password"] = crypto_util.decrypt(_live["password"])
SYNC_INTERVAL_SECONDS = _cfg.get("sync_interval_seconds", 60)
CACHE_DIR = os.path.join(BASE_DIR, _cfg.get("cache_dir", "cache"))
DB_PATH = os.path.join(BASE_DIR, _cfg.get("db_path", "index.db"))
FTP_ROOT = _cfg.get("ftp_root", "/tmp/sd/record")
HLS_DIR = os.path.join(BASE_DIR, _cfg.get("hls_dir", "hls_cache"))
os.makedirs(HLS_DIR, exist_ok=True)

FLASK_SECRET_PATH = os.path.join(BASE_DIR, "flask_secret.key")

# Quali id-camera mostrare in ciascun "Livewall" (/wall/1, /wall/2). Se
# assente in config.json, restano i default storici (1-4 e 5-8).
LIVE_WALLS = _cfg.get("live_walls", {"1": [1, 2, 3, 4], "2": [5, 6, 7, 8]})

# Margine di buffer per la diretta (HLS). Valori più alti = più ritardo
# rispetto al "vero" istante live, ma molta più tolleranza a latenza/jitter
# di rete (utile soprattutto accedendo da fuori casa). Con i default (2s x 6
# segmenti) il margine è di circa 12 secondi prima che un segmento venga
# cancellato dal server.
LIVE_HLS_SEGMENT_SECONDS = _cfg.get("live_hls_segment_seconds", 2)
LIVE_HLS_LIST_SIZE = _cfg.get("live_hls_list_size", 6)

# Fuso orario in cui la camera scrive i nomi dei file (yi-hack di solito usa
# UTC indipendentemente da dove ti trovi). Di norma non va toccato.
CAMERA_TIMEZONE = _cfg.get("camera_timezone", "UTC")

# Il tuo fuso orario reale: la conversione da CAMERA_TIMEZONE a questo tiene
# conto automaticamente di ora legale/solare (nessun numero fisso da
# aggiornare due volte l'anno).
TIMEZONE = _cfg.get("timezone", "Europe/Rome")

# Limiti automatici sulla cartella cache/ (i video scaricati dalle camere).
# cache_max_mb: dimensione massima totale della cache, in MB (0 = nessun limite).
# cache_max_age_hours: elimina comunque i file più vecchi di N ore (0 = nessun limite).
# Quando la cache supera cache_max_mb, i file più vecchi vengono eliminati per
# primi finché non si rientra nel limite.
CACHE_MAX_MB = _cfg.get("cache_max_mb", 2048)
CACHE_MAX_AGE_HOURS = _cfg.get("cache_max_age_hours", 0)

AUTH = _cfg.get("auth", {"enabled": False})

_https_cfg = _cfg.get("https", {"enabled": False, "cert": "cert.pem", "key": "key.pem"})
HTTPS = {
    "enabled": _https_cfg.get("enabled", False),
    "cert": os.path.join(BASE_DIR, _https_cfg.get("cert", "cert.pem")),
    "key": os.path.join(BASE_DIR, _https_cfg.get("key", "key.pem")),
}

os.makedirs(CACHE_DIR, exist_ok=True)
