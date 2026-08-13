# Cronologia delle versioni. La prima voce della lista è sempre quella
# corrente (mostrata nel footer della pagina Impostazioni). Ad ogni nuova
# modifica va aggiunta una voce in cima, non in fondo.

CHANGELOG = [
    {
        "version": "0.9.20",
        "date": "2026-08-13",
        "changes": [
            "Prima versione con numero di revisione tracciato: da qui in poi ogni modifica viene registrata in questa pagina.",
            "Nuova pagina Impostazioni (icona ingranaggio in sidebar), con switch Basic/Advanced e salvataggio diretto su config.json.",
            "Nuova sezione Manutenzione nelle impostazioni avanzate: riavvio di ogni camera via SSH con un click.",
            "Pulsante di ricarica per singola tile nel Livewall, per far ripartire una diretta bloccata senza toccare le altre.",
        ],
    },
]

APP_VERSION = CHANGELOG[0]["version"]
APP_VERSION_DATE = CHANGELOG[0]["date"]
