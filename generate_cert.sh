#!/bin/bash
# Genera un certificato self-signed per l'accesso HTTPS in rete locale,
# includendo uno o più IP/hostname come Subject Alternative Name (SAN).
#
# Uso (uno o più indirizzi, separati da spazio):
#   ./generate_cert.sh 192.168.1.10
#   ./generate_cert.sh 192.168.1.10 192.168.1.50
#   ./generate_cert.sh 192.168.1.10 nas.local mionas.duckdns.org
#
# Il SAN e' necessario: senza, Chrome carica comunque la pagina ma non la
# considera un "contesto pienamente sicuro", e blocca silenziosamente
# l'installazione del Service Worker (necessario per la PWA installabile).
# Ogni indirizzo/hostname da cui vuoi accedere al server deve comparire
# nel certificato, altrimenti per quello specifico indirizzo tornerebbe
# lo stesso problema.

set -e

if [ "$#" -eq 0 ]; then
  echo "Uso: ./generate_cert.sh <ip-o-hostname-1> [ip-o-hostname-2] [...]"
  echo "Esempio: ./generate_cert.sh 192.168.1.10 nas.local"
  exit 1
fi

DAYS=825
FIRST="$1"

# Costruisce la lista SAN riconoscendo IP vs hostname per ciascun argomento
SAN=""
for TARGET in "$@"; do
  if [[ "$TARGET" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    ENTRY="IP:$TARGET"
  else
    ENTRY="DNS:$TARGET"
  fi
  if [ -z "$SAN" ]; then
    SAN="$ENTRY"
  else
    SAN="$SAN,$ENTRY"
  fi
done

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days "$DAYS" \
  -subj "/CN=$FIRST" \
  -addext "subjectAltName=$SAN"

echo ""
echo "Creati cert.pem e key.pem, validi per: $SAN"
echo "Imposta \"https\": {\"enabled\": true} in config.json per attivarli."
echo ""
echo "IMPORTANTE: se avevi già importato un vecchio cert.pem come CA sul"
echo "telefono/dispositivo, rimuovilo (Impostazioni > Sicurezza > Credenziali"
echo "attendibili > Utente) e importa questo nuovo cert.pem al suo posto —"
echo "su OGNI dispositivo da cui accedi al server."
