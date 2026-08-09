#!/usr/bin/env python3
"""
Imposta utente e password per l'accesso web, scrivendo direttamente
in config.json (niente copia-incolla manuale, quindi niente rischio di
hash troncati o spezzati su piu' righe).

Uso:
    python3 set_password.py
"""
import getpass
import json
import os

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

if not os.path.exists(CONFIG_PATH):
    print(f"Non trovo {CONFIG_PATH}. Copia prima config.example.json in config.json.")
    raise SystemExit(1)

username = input("Nome utente per l'accesso web: ").strip()
if not username:
    print("Nome utente vuoto, operazione annullata.")
    raise SystemExit(1)

pw = getpass.getpass("Password da usare per l'accesso web: ")
pw2 = getpass.getpass("Ripeti la password: ")

if not pw:
    print("Password vuota, operazione annullata.")
    raise SystemExit(1)
if pw != pw2:
    print("Le due password non coincidono, riprova.")
    raise SystemExit(1)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg["auth"] = {
    "enabled": True,
    "username": username,
    "password_hash": generate_password_hash(pw),
}

with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\nFatto. config.json aggiornato: accesso protetto per l'utente '{username}'.")
print("Riavvia il server (python3 app.py) perche' la modifica abbia effetto.")
