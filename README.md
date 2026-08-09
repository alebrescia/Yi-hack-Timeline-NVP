<img width="75%" height="75%" alt="live_garden" src="https://github.com/user-attachments/assets/76d32c68-b182-4077-b92e-b8532b3acf97" />

# Yi-hack-Timeline-NVP ( Network Video Player )

A lightweight self-hosted web server that connects over FTP to your Yi
cameras running [yi-hack](https://github.com/roleoroleo) custom firmware,
indexes the recordings it finds, and presents them as a scrollable daily
timeline with an integrated video player — think of it as a self-hosted,
open-source alternative to the stock Yi Home app, plus a live view and a
multi-camera wall.

Built around the folder/file structure yi-hack writes to the SD card:

```
/tmp/sd/record/
  2026Y07M26D07H/
    21M22S38.mp4
    22M00S60.mp4
    ...
```

## Table of contents

- [Purpose](#purpose)
- [Hardware & software requirements](#hardware--software-requirements)
- [Features](#features)
- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [Where to run it](#where-to-run-it)
- [Configuration reference](#configuration-reference)
- [Authentication](#authentication)
- [HTTPS (self-signed certificate)](#https-self-signed-certificate)
- [Encrypted camera credentials](#encrypted-camera-credentials)
- [Running as a service](#running-as-a-service)
- [No-wait playback between clips](#no-wait-playback-between-clips)
- [Recording timezone](#recording-timezone)
- [Automatic video cache cleanup](#automatic-video-cache-cleanup)
- [Automatic stale-clip removal](#automatic-stale-clip-removal)
- [Clip locking & download](#clip-locking--download)
- [Live view (RTSP)](#live-view-rtsp)
- [Live wall (multi-camera view)](#live-wall-multi-camera-view)
- [Mobile use & installing as an app](#mobile-use--installing-as-an-app)
- [Camera icons](#camera-icons)
- [Easy customizations](#easy-customizations)
- [Credits](#credits)
- [License](#license)
- [Disclaimer](#disclaimer)

## Purpose

Yi cameras running the stock firmware are tied to the Yi Home app and
Yi's own cloud — fine for casual use, but limiting if you want local-only
storage, a browsable timeline that doesn't feel like an afterthought, or
just to keep full control of your own footage. The
[yi-hack](https://github.com/roleoroleo) custom firmware projects solve the
cloud dependency by exposing the camera's local storage over FTP and its
stream over RTSP — but on their own, that's just raw files and a stream
URL, not something you'd want to browse day-to-day.

This project fills that gap: point it at your yi-hack cameras' FTP and
RTSP, and it gives you back the "browsable timeline + live view" experience
of a normal camera app, self-hosted, with no cloud account, no
subscription, and no vendor lock-in — running on whatever always-on device
you already have at home.

## Hardware & software requirements

**Hardware**
- One or more Yi cameras (1080p Home/Outdoor or similar) flashed with
  [yi-hack-MStar](https://github.com/roleoroleo/yi-hack-MStar) or
  [yi-hack-Allwinner](https://github.com/roleoroleo/yi-hack-Allwinner-v2)
  custom firmware — this project relies on the FTP server and folder/file
  naming conventions that firmware provides (stock Yi firmware won't work).
- An always-on device on the same LAN to run the server: a Raspberry Pi 4
  or newer (a Pi 3 is too weak for more than one camera), a small x86 mini
  PC, or a NAS capable of running Python 3 directly (Docker not required,
  just a working Python 3 environment).

**Software**
- Python 3.9+ (3.11 recommended; tested on Raspberry Pi OS Bookworm)
- Python packages, installed via `pip` (see `requirements.txt`):
  [Flask](https://flask.palletsprojects.com/) 3.x, `tzdata`, `cryptography`
- [`ffmpeg`](https://ffmpeg.org/) — system package, required only for the
  live view (`sudo apt install ffmpeg` on Debian/Raspberry Pi OS)
- `openssl` — system package, only needed if you use the included
  self-signed HTTPS certificate script (present by default on virtually
  every Linux distribution)
- A modern browser (Chrome, Firefox, Safari, Edge) — no plugins required

## Features

- **Recordings timeline** — day-by-day, hour-by-hour browsable timeline
  with a fixed minute ruler, continuous auto-play across clips, and
  next-clip prefetching so there's no loading gap between clips.
- **Incremental indexing** — only the most recent (still-being-written)
  hour folder gets re-scanned on every sync; older, closed folders are
  scanned once and cached. Stays fast even with thousands of indexed clips.
- **Automatic cache management** — downloaded clips are cached locally for
  instant replay, with configurable cleanup by size and/or age.
- **Automatic stale-clip cleanup** — cameras record in a rolling window
  (SD card capacity dependent); the index mirrors that automatically, so
  you never see "ghost" clips that no longer exist on the camera.
- **Clip locking & download** — right-click (desktop) or long-press
  (mobile) a clip to permanently protect it from cache/expiry cleanup, or
  download it with a readable filename.
- **Live view (RTSP → HLS)** — watch any camera's live feed (video + audio)
  directly in the browser via `ffmpeg` remuxing, no plugins required.
- **Live wall** — two configurable grid pages showing several cameras'
  live feeds at once, with tap-to-fullscreen on any tile.
- **Authentication** — proper session-based login (not a browser-native
  popup), with configurable session length.
- **HTTPS** — self-signed certificate generation with proper SAN support
  (works correctly with Chrome/PWA installability).
- **Encrypted camera credentials** — FTP/RTSP passwords in `config.json`
  can be encrypted at rest with a separate key file.
- **Installable PWA** — add it to your phone's home screen for an
  app-like experience, fully responsive on mobile.
- **Multi-camera** — just add more entries to `config.json`.
- **Automatic timezone handling** — DST-aware conversion from the
  camera's clock (usually UTC) to your local time.
- **systemd service** unit included for running unattended on boot.

## Screenshots

<img width="40%" height="40%" alt="bzNjk4F3Ho" src="https://github.com/user-attachments/assets/e5d024b3-1941-498a-80ad-6eb17b21b906" /> <img width="40%" height="40%" alt="live_wall" src="https://github.com/user-attachments/assets/9f6ec07b-7263-449b-af86-908fc6c4823e" />

## Quick start

```bash
git clone https://github.com/alebrescia/Yi-hack-Timeline-NVP.git
cd Yi-hack-Timeline-NVP
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp config.example.json config.json
# edit config.json with each camera's IP and FTP credentials
```

FTP credentials are set in the camera's own yi-hack web UI (FTP server on
port 21 by default — enable it there if you haven't already).

```bash
python3 app.py
```

Open `http://<server-ip>:5050` in your browser. On first load the day list
will be empty until the first sync runs — click "Update index" and wait
(the very first scan can take a few minutes with a lot of pre-existing
footage; subsequent syncs are much faster).

For always-on unattended use, see [Running as a service](#running-as-a-service) below.

## Where to run it

Any always-on Linux/Windows/macOS device on your LAN works: a Raspberry Pi
4 (not a Pi 3 — too weak for multiple cameras), a mini PC, or your NAS if it
supports Docker with a recent Python image. The server itself is
lightweight (no continuous video decoding — just FTP listing and on-demand
clip downloads), so modest hardware is fine. `ffmpeg` (for live view) adds
some CPU load only while a live stream is actually being watched.

## Configuration reference

All configuration lives in `config.json` (copy `config.example.json` to
start). Below is a summary — see the sections further down for details on
each feature.

```jsonc
{
  "cameras": [
    {
      "id": 1,
      "name": "Front door",
      "icon": "porta",                 // optional, see "Camera icons"
      "host": "192.168.1.101",
      "port": 21,
      "user": "root",
      "password": "",
      "ftp_root": "/tmp/sd/record",    // optional, per-camera override
      "live": {                        // optional, enables live view
        "rtsp_url": "rtsp://192.168.1.101:8554/unicast",
        "user": "liveuser",
        "password": "livepass"
      }
    }
  ],
  "sync_interval_seconds": 60,
  "cache_dir": "cache",
  "db_path": "index.db",
  "ftp_root": "/tmp/sd/record",
  "hls_dir": "hls_cache",
  "camera_timezone": "UTC",
  "timezone": "Europe/Rome",
  "cache_max_mb": 2048,
  "cache_max_age_hours": 0,
  "live_hls_segment_seconds": 2,
  "live_hls_list_size": 6,
  "live_walls": { "1": [1, 2, 3, 4], "2": [5, 6, 7, 8] },
  "auth": {
    "enabled": false,
    "username": "admin",
    "password_hash": "",
    "session_days": 30
  },
  "https": { "enabled": false, "cert": "cert.pem", "key": "key.pem" }
}
```

## Authentication

Access is protected by a real login page (username/password → session
cookie), not a browser-native popup — more reliable on tabs left inactive
for hours (some browsers, Firefox especially, don't correctly re-trigger
the native HTTP-auth popup after discarding an inactive tab to save
memory; a real login page doesn't have this problem).

```bash
source venv/bin/activate
python3 set_password.py
```

The script asks for a username and password and writes them **directly**
into `config.json` (no manual hash copy-pasting). Then restart the server.

Sessions stay valid for **30 days** by default (even across browser
restarts, not just tab restarts). Change this with `"session_days"` under
`"auth"` in `config.json`. A **"Logout"** button at the bottom of the
sidebar ends the session manually at any time.

## HTTPS (self-signed certificate)

Optional, but **required** if you also want to install the app as a PWA
(see below), and recommended in general if you access it from outside your
LAN, so credentials don't travel in plaintext.

```bash
./generate_cert.sh 192.168.1.10
```

Pass the IP (or hostname) you normally use to reach the server. You can
list more than one, space-separated, if you connect from multiple
addresses (e.g. a LAN IP and a DDNS hostname for remote access):

```bash
./generate_cert.sh 192.168.1.10 nas.local
```

This creates `cert.pem` and `key.pem` in the project folder. Then in
`config.json`:

```json
"https": { "enabled": true, "cert": "cert.pem", "key": "key.pem" }
```

After restarting, the app is reachable at `https://<ip>:5050`. Being
self-signed, browsers will show a security warning on first connection —
that's expected; accept the exception (or better, import `cert.pem` as a
trusted CA on the device you use — required anyway for PWA installation).

If you later change IP or add access from a different address, re-run the
script with the updated list: it generates a new certificate that replaces
the old one, which then needs to be re-imported as a CA on every device.

## Encrypted camera credentials

FTP and RTSP passwords in `config.json` can be encrypted instead of stored
in plaintext. The encryption key is kept separately in `secret.key`
(restricted permissions, auto-generated on first use) — so even if
`config.json` were accidentally shared, the passwords stay unreadable
without that file.

```bash
source venv/bin/activate
pip install -r requirements.txt   # adds 'cryptography' if not already installed
python3 encrypt_config.py
```

The script reads the plaintext passwords already in `config.json` (FTP and
live) and replaces them in-place with the encrypted form (`enc:` prefix) —
no need to retype them. It's idempotent: running it again on already
encrypted passwords does nothing. Restart the server for the change to
take effect; the rest of the app works unchanged, since decryption happens
automatically and only in memory at startup.

**Important:**
- Keep a separate backup of `secret.key` (e.g. on a USB drive or in a
  password manager). If you lose it, the encrypted passwords become
  unreadable and need to be re-entered in plaintext and re-encrypted.
- **Never share `secret.key` alongside `config.json`** in the same place
  (same backup, same cloud folder): anyone with both files can decrypt the
  passwords, so encryption only protects you if they stay separate.
- To add a new camera, just write its password in plaintext in
  `config.json` as usual, then re-run `python3 encrypt_config.py`.

## Running as a service

A ready-made **systemd** unit file, `yicam-timeline.service`, is included
for running unattended on boot.

Update the paths in the file to match where you put the project (it
assumes `/home/pi/yicam-timeline` with the venv inside `venv/`):

```ini
WorkingDirectory=/home/pi/yicam-timeline
ExecStart=/home/pi/yicam-timeline/venv/bin/python3 /home/pi/yicam-timeline/app.py
```

Then install it (these commands are run **without** the venv active —
they're system commands, not Python):

```bash
sudo cp yicam-timeline.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yicam-timeline
sudo systemctl start yicam-timeline
```

Useful commands once it's running as a service:

```bash
sudo systemctl status yicam-timeline    # current status
sudo journalctl -u yicam-timeline -f    # live logs
sudo systemctl restart yicam-timeline   # after editing config.json or any .py file
sudo systemctl stop yicam-timeline      # stop it
```

**When a restart is actually needed:** after editing `config.json` or any
`.py` file. Files under `static/` (`.css`, `.js`, icons) never need a
restart — just refresh the browser (hard refresh to bypass cache). `.html`
files under `templates/` also apply without a restart — template caching
is intentionally disabled for convenience during day-to-day use.

## No-wait playback between clips

When a clip starts playing, the server automatically downloads the next
one in that day's list in the background, so it's already cached when
needed — whether you clicked another clip manually or continuous playback
advanced to it automatically. The only case where a brief load can still
happen is the very first clip of the following day (prefetching stays
within the currently selected day).

## Recording timezone

yi-hack writes filenames using the camera's internal clock, which is
usually **UTC** regardless of where you are — this is why clips can appear
"behind" the real time on the timeline.

In `config.json`:

```json
"camera_timezone": "UTC",
"timezone": "Europe/Rome"
```

- `camera_timezone`: the timezone the camera writes filenames in (usually
  leave as `UTC`).
- `timezone`: your actual timezone. With an IANA name like `Europe/Rome`,
  the conversion **automatically** accounts for daylight saving time — no
  manual updates needed twice a year.

If you change these after clips are already indexed, existing entries keep
the timestamps computed under the old settings. To recompute everything:

```bash
rm index.db
```

then restart the server (or click "Update index"): the index rebuilds
from scratch with correct timestamps. This doesn't touch already-cached
video files, only the metadata index.

## Automatic video cache cleanup

`index.db` (the metadata index) always stays small — a few hundred KB even
with thousands of indexed clips, since it only stores filenames and
timestamps, not video. What *can* grow is the `cache/` folder, where
actually-downloaded videos end up (when you watch them, and now also
ahead of time thanks to prefetching).

To keep it from filling up your storage, in `config.json`:

```json
"cache_max_mb": 2048,
"cache_max_age_hours": 0
```

- `cache_max_mb`: maximum total cache size, in MB. When exceeded, the
  least-recently-downloaded clips are removed first until back under the
  limit. `0` disables this check.
- `cache_max_age_hours`: removes any clip downloaded more than N hours ago,
  regardless of total size. `0` disables this check.

Use either, both, or neither (at your own risk). Cleanup runs
automatically on every background sync cycle (`sync_interval_seconds`). It
never touches footage still on the camera's SD card — only the locally
cached copy, which gets re-downloaded on demand if you open that clip
again.

## Automatic stale-clip removal

Cameras record in a loop over a fixed retention window (typically 2-3
days, depending on SD card capacity): once space runs out, the oldest
hours are automatically deleted by the camera itself to make room.

On every sync, the server compares the hour-folders still present on the
camera against what's already indexed: any folder no longer on the camera
gets removed from both the database and any locally cached video. This
keeps the timeline showing exactly the footage that's actually available,
with no "ghost" clips that would error out if you tried to open them. No
configuration needed — this mirrors 1:1 how the camera itself manages SD
space (it deletes whole hours, not individual scattered files).

## Clip locking & download
<img width="424" height="298" alt="lock_clip" src="https://github.com/user-attachments/assets/229ad434-f037-4504-afcf-117c7c8f884e" />
On any clip in the timeline:
- **Right-click** (desktop) or **long-press ~0.5s** (mobile, with a
  confirmation vibration if supported) opens a context menu with two
  options.
- **🔒 Lock / 🔓 Unlock clip**: a locked clip is downloaded immediately (if
  not already cached) and permanently protected — excluded from both
  automatic cache cleanup (size/age) and removal when its folder expires
  on the camera. Locked clips show a purple outline, plus a small lock
  icon on desktop (hidden on mobile to avoid cluttering already-small
  blocks).
- **⬇ Download clip**: downloads the mp4 with a readable filename (e.g.
  `FrontDoor_2026-07-26_07-00-00.mp4`) instead of the camera's cryptic
  original name.

Important clarification: the video physically lives on the camera's SD
card, which manages its own rotation independently — the server can't stop
it from deleting the original. "Locking" therefore concretely means
**permanently keeping the already-downloaded copy on the server**,
regardless of what later happens on the camera.

## Live view (RTSP)

Besides recordings, you can watch any camera's live feed (video **and
audio**) directly in the browser. Since browsers can't play RTSP natively,
the server uses `ffmpeg` to remux the video (no re-encoding — zero extra
CPU cost) and transcode only the audio to AAC (lightweight, needed because
many cameras send audio in a format HLS doesn't support directly),
producing an HLS stream any browser can play.

### Requirement: ffmpeg

```bash
sudo apt install ffmpeg
```

If missing, you'll see a warning in the console on startup, and the "live"
button will error out when pressed.

### Configuration

For each camera in `config.json`, add a `live` section with the RTSP URL
and live credentials (which can differ from the FTP credentials used for
recordings):

```json
{
  "id": 1,
  "name": "Front door",
  "host": "192.168.1.101",
  "port": 21,
  "user": "root",
  "password": "",
  "live": {
    "rtsp_url": "rtsp://192.168.1.101:8554/unicast",
    "user": "liveuser",
    "password": "livepass"
  }
}
```

Use the RTSP URL exactly as you'd use it for any live stream you've
already verified works (without embedding user/password in the URL itself
— the server composes them correctly, handling special characters in the
password too). A camera without a `live` section simply won't show the
"live" button.

### How it behaves

- The "● live" button only appears for cameras with `live` configured.
- On press, the server starts `ffmpeg` for that camera (takes 1-2 seconds
  to attach to the stream) and playback starts in HLS.
- If the live view isn't watched for more than 30 seconds (page change,
  switching to a recorded clip, closing the tab), the `ffmpeg` process is
  automatically stopped in the background, so it doesn't keep the camera's
  CPU/network needlessly busy.
- Clicking a recorded clip while watching live automatically exits live
  mode and resumes normal playback.
- Switching camera while watching live automatically follows the newly
  selected camera.
- If on first start the video stays paused instead of autoplaying, tap the
  native ▶ button once: some browsers block autoplay with audio until
  there's a direct tap on the video element.

### Buffer margin (useful for remote access)

In `config.json`:
```json
"live_hls_segment_seconds": 2,
"live_hls_list_size": 6
```
Together these determine how many seconds of margin the player has before
a segment gets deleted server-side (default: 2×6 = 12 seconds). Higher
values = more tolerance for latency/unstable networks (useful when
accessing from outside your home network), at the cost of a slightly
higher delay versus the true live instant — irrelevant for surveillance
use.

## Live wall (multi-camera view)

Two dedicated pages show a grid of several cameras' live feeds at once:
**Livewall 1** and **Livewall 2**, reachable from the two sidebar buttons
above "Update index", or directly at `/wall/1` and `/wall/2`.

Which camera ids appear in each is set in `config.json`:
```json
"live_walls": {
  "1": [1, 2, 3, 4],
  "2": [5, 6, 7, 8]
}
```
They don't need to be consecutive or ordered — `[1, 3, 7, 8]` works fine if
you want to mix cameras from different logical groups into one view. If
`live_walls` is absent, these two defaults apply. An id without a
configured camera (or later removed) just shows a placeholder instead of
erroring.

- **Tap/click a tile** to expand it to fill the screen (the other three
  disappear); tap the same tile again — or press **Esc** on desktop — to
  return to the grid. This is a CSS-based "fake" fullscreen, not the
  browser's real Fullscreen API: instant, no permission prompts.
- On **desktop** the grid fills the available screen space exactly,
  maximizing each tile. On **mobile** the tiles stack in a column and
  scroll normally with the page.
- Audio is **always disabled** in this view (four simultaneous audio
  streams wouldn't be practical) — for audio, use a single camera's live
  view from the main timeline.
- Leaving the page explicitly stops all active live streams server-side
  (in addition to the automatic watchdog that would stop them anyway after
  30s of inactivity).

Note: mind the load with 4 simultaneous 1080p live streams — bandwidth and
CPU (for `ffmpeg`) scale proportionally versus a single live view. If you
notice slowdowns, try raising `live_hls_segment_seconds`/
`live_hls_list_size` as above, or consider a lower resolution on the
cameras if your hardware struggles with all 4 at once.

## Mobile use & installing as an app

The UI is responsive: below a certain width (phones, tablets in portrait)
the sidebar (cameras, days, sync) becomes a slide-out panel reachable via
the ☰ icon top-left, and the player bar's buttons spread across the full
width.

The timeline table has a fixed minute ruler at the top (00, 10, 20...50),
useful on both desktop and mobile to see at a glance which minute a block
corresponds to. On mobile, each hour's minute lane is wider than the
screen and **scrolls horizontally** (the rest of the UI, including the
hour label, stays put) — clips become much wider and easier to tap versus
a view compressed to fit the screen width.

The app is also an installable **PWA (Progressive Web App)**: add it to
your phone's home screen and it behaves like a real app (own icon, opens
full-screen without the browser's address bar).

**On Android (Chrome):**
1. Open `https://<server-ip>:5050` in Chrome.
2. Tap the menu (⋮) top-right.
3. Choose **"Add to Home screen"** (or **"Install app"** if it appears
   directly).

**On iPhone (Safari):** Share → "Add to Home Screen".

Note: since it's a self-signed HTTPS certificate, Chrome will show a
security warning on the very first visit — that's expected, accept the
exception once. After that the home-screen icon works normally.

**For a "real" install** (standalone icon, not just a shortcut), Chrome
requires the certificate to be generated with the correct IP/hostname as
Subject Alternative Name (see the HTTPS section above: use
`./generate_cert.sh <your-ip>`) **and** imported as a trusted CA on the
phone — otherwise Chrome only offers "Create shortcut" instead of a true
PWA install.

## Camera icons

Each camera in the sidebar shows a small hand-drawn icon (no external
icon library). There are two ways to choose it, in priority order:

**1. Explicit** — add an `"icon"` field to the camera in `config.json`:
```json
{
  "id": 5,
  "name": "Garage",
  "icon": "garage",
  ...
}
```
Available values: `porta` (door), `giardino` (garden), `camera` (bedroom),
`cameretta` (kid's room), `garage`, `cancello` (gate), `soggiorno` (living
room), `scale` (stairs), `cortile` (yard). An unrecognized value (or no
field at all) falls through to the next step.

**2. Automatic from the name** — if `"icon"` isn't set, the system tries
to guess it from the `name` field (case-insensitive, Italian keywords):
"giardino" → plant, "ingresso" → door, "cameretta" → crib, "camera" (but
not "cameretta") → bed, "garage"/"cancello"/"soggiorno"/"scale" → their
respective icons, "cortile" or "esterno" → sun/yard.

If neither applies, a **generic camera icon** is used as a fallback —
never an error, just a less specific icon.

## Easy customizations

- **Sync interval**: `sync_interval_seconds` in `config.json`.
- **Different FTP path** (if it varies per camera): add
  `"ftp_root": "/different/path"` to that camera's entry in `config.json`.
- **Cache cleanup**: the `cache/` folder can be safely emptied at any time;
  files get re-downloaded from the camera on next use.

## Credits

This project was built through an extended, iterative conversation with
**Claude** ([Anthropic](https://www.anthropic.com)) — every line of code,
from the initial FTP indexer to the live view, the PWA, and every bug fix
along the way, was written by Claude. **[alebrescia](https://github.com/alebrescia)**
defined the requirements, tested every change on real hardware, reported
back what worked and what didn't, and steered the project's direction from
a basic clip browser into what it is now.

## License

Licensed under the [MIT License](LICENSE) — free to use, modify, and
redistribute.

## Disclaimer

This is a personal hobby project, shared as-is. It's tailored to
yi-hack-MStar/yi-hack-Allwinner filename conventions but should be
adaptable to other cameras with a similar recording folder structure.
Pull requests and issues are welcome, but there's no guarantee of active
maintenance.
The implemented security is not suitable for production use. 
You should not expose this service publicly (or do at your own risk). 
My advice is to use a VPN!
