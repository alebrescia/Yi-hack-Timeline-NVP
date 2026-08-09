#!/usr/bin/env python3
"""
Cifra le password delle camere (FTP e diretta RTSP) già presenti in
config.json, sostituendole con una versione cifrata. Legge le password
così come sono già scritte nel file: non serve reinserirle a mano.

La chiave di cifratura viene creata automaticamente (o riutilizzata se già
presente) in secret.key, nella stessa cartella. Quel file è indispensabile
per decifrare le password: fanne un backup separato, e non condividerlo mai
insieme a config.json (altrimenti la cifratura non protegge nulla).

Uso:
    python3 encrypt_config.py
"""
import json
import os

import crypto_util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

if not os.path.exists(CONFIG_PATH):
    print(f"Non trovo {CONFIG_PATH}. Copia prima config.example.json in config.json.")
    raise SystemExit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

changed = 0
for cam in cfg.get("cameras", []):
    label = cam.get("name", cam.get("id"))

    pw = cam.get("password")
    if pw and not crypto_util.is_encrypted(pw):
        cam["password"] = crypto_util.encrypt(pw)
        changed += 1
        print(f"  [{label}] password FTP cifrata")

    live = cam.get("live")
    if live:
        lpw = live.get("password")
        if lpw and not crypto_util.is_encrypted(lpw):
            live["password"] = crypto_util.encrypt(lpw)
            changed += 1
            print(f"  [{label}] password diretta (RTSP) cifrata")

if changed == 0:
    print("Nessuna password in chiaro trovata: config.json è già a posto.")
else:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\nFatto: {changed} password cifrate e salvate in config.json.")
    print("Riavvia il server (o 'sudo systemctl restart yicam-timeline')")
    print("perché le modifiche abbiano effetto.")
