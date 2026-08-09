# Yi-hack-Timeline-NVP

Piccolo server web che si collega via FTP alle tue Yi camera (firmware yi-hack-MStar),
indicizza le registrazioni presenti in `/tmp/sd/record` e le mostra come una timeline
giornaliera navigabile, con player video integrato.

Il design è basato sulla struttura di cartelle/file che genera yi-hack:

```
/tmp/sd/record/
  2026Y07M26D07H/
    21M22S38.mp4
    22M00S60.mp4
    ...
```

## Indice

- [Obiettivo](#obiettivo)
- [Hardware e software necessari](#hardware-e-software-necessari)
- [Funzionalità](#funzionalità)
- [Screenshot](#screenshot)
- [Installazione](#installazione)
- [Avvio](#avvio)
- [Note su dove farlo girare](#note-su-dove-farlo-girare)
- [Riferimento configurazione](#riferimento-configurazione)
- [Sicurezza: utente e password](#sicurezza-utente-e-password)
- [Sicurezza: HTTPS con certificato self-signed](#sicurezza-https-con-certificato-self-signed)
- [Sicurezza: cifratura delle password delle camere](#sicurezza-cifratura-delle-password-delle-camere)
- [Eseguire come servizio (avvio automatico)](#eseguire-come-servizio-avvio-automatico)
- [Riproduzione senza attese tra una clip e l'altra](#riproduzione-senza-attese-tra-una-clip-e-laltra)
- [Fuso orario delle registrazioni](#fuso-orario-delle-registrazioni)
- [Pulizia automatica della cache video](#pulizia-automatica-della-cache-video)
- [Rimozione automatica delle clip scadute](#rimozione-automatica-delle-clip-scadute)
- [Blocco e download delle clip](#blocco-e-download-delle-clip)
- [Diretta (live RTSP)](#diretta-live-rtsp)
- [Diretta multipla (Livewall)](#diretta-multipla-livewall)
- [Uso da smartphone (Android/iOS) e installazione come app](#uso-da-smartphone-androidios-e-installazione-come-app)
- [Icone delle camere nel menu](#icone-delle-camere-nel-menu)
- [Personalizzazioni facili](#personalizzazioni-facili)
- [Crediti](#crediti)
- [Licenza](#licenza)
- [Disclaimer](#disclaimer)

## Obiettivo

Le Yi camera col firmware originale sono legate all'app Yi Home e al cloud
di Yi — comodo per un uso occasionale, ma limitante se vuoi conservare le
registrazioni solo in locale, avere una timeline navigabile che non sembri
un ripiego, o semplicemente mantenere il pieno controllo delle tue
registrazioni. I firmware modificati [yi-hack](https://github.com/roleoroleo)
risolvono la dipendenza dal cloud esponendo lo storage locale della camera
via FTP e lo stream via RTSP — ma da soli restano solo file grezzi e un
indirizzo di streaming, non qualcosa che vorresti sfogliare ogni giorno.

Questo progetto colma quel divario: puntalo alle tue camere yi-hack (FTP e
RTSP) e ottieni indietro l'esperienza "timeline navigabile + diretta" di
una normale app per videocamere, ma self-hosted, senza account cloud, senza
abbonamenti e senza vincoli col produttore — in esecuzione su qualunque
dispositivo sempre acceso tu abbia già in casa.

## Hardware e software necessari

**Hardware**
- Una o più Yi camera (1080p Home/Outdoor o simili) con firmware
  [yi-hack-MStar](https://github.com/roleoroleo/yi-hack-MStar) o
  [yi-hack-Allwinner](https://github.com/roleoroleo/yi-hack-Allwinner-v2)
  — il progetto si basa sul server FTP e sulla convenzione di nomi di
  cartelle/file che quel firmware fornisce (il firmware originale Yi non
  funziona).
- Un dispositivo sempre acceso sulla stessa rete locale per far girare il
  server: un Raspberry Pi 4 o successivo (un Pi 3 è troppo debole con più
  di una camera), un piccolo mini PC x86, o un NAS in grado di eseguire
  direttamente Python 3 (Docker non necessario, basta un ambiente Python 3
  funzionante).

**Software**
- Python 3.9+ (consigliato 3.11; testato su Raspberry Pi OS Bookworm)
- Pacchetti Python, installati via `pip` (vedi `requirements.txt`):
  [Flask](https://flask.palletsprojects.com/) 3.x, `tzdata`, `cryptography`
- [`ffmpeg`](https://ffmpeg.org/) — pacchetto di sistema, necessario solo
  per la diretta (`sudo apt install ffmpeg` su Debian/Raspberry Pi OS)
- `openssl` — pacchetto di sistema, serve solo se usi lo script incluso
  per il certificato HTTPS self-signed (presente di default praticamente
  su ogni distribuzione Linux)
- Un browser moderno (Chrome, Firefox, Safari, Edge) — nessun plugin
  richiesto

## Funzionalità

- **Timeline delle registrazioni** — timeline navigabile giorno per giorno
  e ora per ora, con righello dei minuti fisso, riproduzione continua tra
  le clip, e pre-caricamento della clip successiva così non c'è mai un
  vuoto di caricamento tra un clip e l'altro.
- **Indicizzazione incrementale**: alla prima sincronizzazione scansiona tutte le
  cartelle/ore trovate sulla camera. Alle esecuzioni successive, le ore già "chiuse"
  (non l'ultima) non vengono più ri-scansionate: solo l'ultima cartella (quella
  potenzialmente ancora in scrittura) viene ricontrollata ogni volta. Questo tiene
  le sincronizzazioni successive veloci anche con migliaia di clip accumulate.
- **Cache dei video**: un clip viene scaricato dalla camera solo la prima volta che
  lo apri; dopo resta in cache locale (`cache/`) e viene servito da lì, quindi il
  riavvolgimento/riascolto è istantaneo, con pulizia automatica configurabile per
  dimensione e/o età.
- **Rimozione automatica delle clip scadute** — le camere registrano in
  loop su uno storico fisso (in base alla capienza della SD); l'indice si
  allinea automaticamente, così non vedrai mai clip "fantasma" non più
  presenti sulla camera.
- **Blocco e download delle clip** — tasto destro (desktop) o tocco
  prolungato (mobile) su una clip per proteggerla permanentemente dalla
  pulizia automatica, o scaricarla con un nome file leggibile.
- **Diretta (RTSP → HLS)** — guarda la diretta (video e audio) di ogni
  camera direttamente nel browser tramite `ffmpeg`, senza plugin.
- **Diretta multipla (Livewall)** — due pagine griglia configurabili che
  mostrano più camere insieme in diretta, con tocco per schermo intero su
  ogni tile.
- **Autenticazione** — vero login con sessione (non il popup nativo del
  browser), durata sessione configurabile.
- **HTTPS** — generazione di certificato self-signed con supporto SAN
  corretto (funziona bene con Chrome/installabilità PWA).
- **Credenziali camere cifrate** — le password FTP/RTSP in `config.json`
  possono essere cifrate a riposo con un file chiave separato.
- **PWA installabile** — aggiungila alla schermata Home del telefono per
  un'esperienza da app vera, completamente responsive su mobile.
- **Multi-camera** — basta aggiungere più voci in `config.json`.
- **Gestione automatica del fuso orario** — conversione dall'orologio
  della camera (di solito UTC) al tuo fuso locale, con cambio automatico
  ora legale/solare.
- **Servizio systemd** incluso per l'esecuzione automatica all'avvio.

## Screenshot

*(Aggiungi qui i tuoi screenshot — timeline desktop, vista mobile, livewall.)*

## Installazione

```bash
cd yicam-timeline
python3 -m venv venv
source venv/bin/activate          # su Windows: venv\Scripts\activate
pip install -r requirements.txt

cp config.example.json config.json
# modifica config.json con IP, utente e password FTP di ciascuna camera
```

Le credenziali FTP (utente/password) si configurano nella web UI della camera
(yi-hack-MStar espone un server FTP locale sulla porta 21 di default; se non l'hai
ancora attivato, controlla le impostazioni FTP nella pagina web della camera).

## Avvio

Con il venv attivo (`source venv/bin/activate` dalla cartella del progetto,
se non lo è già):

```bash
python3 app.py
```

Poi apri `http://<ip-del-server>:5050` da browser (anche da smartphone, se il
server gira su un dispositivo sempre acceso in rete locale: NAS, Raspberry Pi,
mini PC...).

Alla prima apertura la lista "Giorni disponibili" sarà vuota finché non parte la
prima sincronizzazione: premi "Aggiorna indice" e attendi (con molte ore di
registrazioni pregresse la primissima scansione può richiedere qualche minuto,
le successive saranno molto più rapide).

Per farlo partire da solo all'avvio del sistema e restare su in background
(senza tenere un terminale aperto), vedi la sezione **"Eseguire come
servizio"** più sotto — è il modo consigliato per un uso quotidiano.

## Note su dove farlo girare

Va bene qualunque dispositivo Linux/Windows/macOS sempre acceso in rete locale:
un Raspberry Pi 4 (non un 3B, troppo debole viste le camere multiple), un mini PC,
o anche direttamente il NAS se supporta Docker con un'immagine Python recente.
Il carico di questo servizio è leggero (non fa decodifica video continua, solo
listing FTP + download on-demand dei clip aperti), quindi anche hardware modesto
va benissimo.

## Riferimento configurazione

Tutta la configurazione vive in `config.json` (copia `config.example.json`
per iniziare). Qui sotto un riepilogo — le sezioni più avanti spiegano nel
dettaglio ogni funzionalità.

```jsonc
{
  "cameras": [
    {
      "id": 1,
      "name": "Ingresso",
      "icon": "porta",                 // facoltativo, vedi "Icone delle camere"
      "host": "192.168.1.101",
      "port": 21,
      "user": "root",
      "password": "",
      "ftp_root": "/tmp/sd/record",    // facoltativo, override per singola camera
      "live": {                        // facoltativo, abilita la diretta
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

## Sicurezza: utente e password

L'accesso è protetto da una vera pagina di login (utente/password → cookie
di sessione), non dal popup nativo del browser: più affidabile su schede
rimaste inattive per ore (alcuni browser, specialmente Firefox, non
ripropongono correttamente il popup di autenticazione HTTP dopo aver
"scartato" una scheda per risparmiare memoria — con una pagina di login vera
questo problema non si presenta).

Con il venv attivo:
```bash
source venv/bin/activate   # se non è già attivo
python3 set_password.py
```
Lo script chiede nome utente e password e li scrive **direttamente** in
`config.json` (niente copia-incolla manuale di hash). Poi riavvia il server.

Una volta effettuato il login, la sessione resta valida **30 giorni** di
default (anche chiudendo e riaprendo il browser, non solo la scheda). Per
cambiare questa durata, aggiungi in `config.json` dentro `"auth"`:
```json
"auth": {
  "enabled": true,
  "username": "admin",
  "password_hash": "...",
  "session_days": 30
}
```

Un pulsante **"Esci"** in fondo al menu laterale permette di terminare la
sessione manualmente in qualsiasi momento.

## Sicurezza: HTTPS con certificato self-signed

Facoltativo, ma **necessario** se vuoi anche installare l'app come PWA (vedi
più sotto) e comunque consigliato se accedi da fuori la LAN, per non far
viaggiare utente/password in chiaro sulla rete.

```bash
./generate_cert.sh 192.168.1.10
```

Passa l'IP (o l'hostname) con cui accedi normalmente al server. Puoi
indicarne più di uno, separati da spazio, se ti colleghi da indirizzi diversi
(es. un IP in LAN e un hostname DDNS per l'accesso da fuori):

```bash
./generate_cert.sh 192.168.1.10 nas.local
```

Questo crea `cert.pem` e `key.pem` nella cartella del progetto. Poi in
`config.json`:

```json
"https": { "enabled": true, "cert": "cert.pem", "key": "key.pem" }
```

Riavviando il server, l'interfaccia sarà raggiungibile su
`https://<ip>:5050`. Essendo un certificato autofirmato, il browser mostrerà
un avviso di sicurezza alla prima connessione: è normale, basta confermare
l'eccezione (o meglio ancora importare `cert.pem` come certificato CA
attendibile sul dispositivo che usi per guardare le registrazioni — necessario
comunque se vuoi installare l'app come PWA, vedi sotto).

Se in futuro cambi IP o aggiungi un accesso da un indirizzo diverso, rilancia
lo script con la lista aggiornata: genera un certificato nuovo che sostituisce
il precedente, da reimportare come CA su ogni dispositivo.

## Sicurezza: cifratura delle password delle camere

Le password FTP e RTSP delle camere in `config.json` possono essere cifrate
invece di restare in chiaro nel file. La chiave di cifratura viene salvata
separatamente in `secret.key` (permessi ristretti, generato automaticamente
al primo utilizzo) — così anche se `config.json` finisse condiviso per
sbaglio, le password restano illeggibili senza quel file.

Con il venv attivo:
```bash
source venv/bin/activate   # se non è già attivo
pip install -r requirements.txt   # la prima volta, aggiunge 'cryptography'
python3 encrypt_config.py
```

Lo script legge le password già scritte in `config.json` (FTP e diretta) e
le sostituisce in-place con la versione cifrata (prefisso `enc:`) — non serve
reinserirle a mano. È idempotente: rilanciarlo su password già cifrate non fa
nulla. Riavvia il server perché le modifiche abbiano effetto; il resto
dell'app (sync FTP, diretta) continua a funzionare invariato, perché la
decifratura avviene automaticamente e solo in memoria all'avvio.

**Importante:**
- Fai un backup separato di `secret.key` (es. su una chiavetta USB o in un
  gestore password). Se lo perdi, le password cifrate diventano illeggibili
  e vanno reinserite in chiaro e ricifrate da capo.
- **Non condividere mai `secret.key` insieme a `config.json`** nello stesso
  posto (stesso backup, stessa chat, stesso cloud): chi ha entrambi i file
  può decifrare le password, quindi la cifratura protegge solo se restano
  separati.
- Per aggiungere una nuova camera in chiaro e poi cifrarla, scrivi la
  password in chiaro nel campo `password`/`live.password` di `config.json`
  come al solito, poi rilancia `python3 encrypt_config.py`.

## Eseguire come servizio (avvio automatico)

Per farlo partire da solo al boot e restare attivo in background, senza
tenere un terminale aperto, c'è un file di unit per **systemd** già pronto:
`yicam-timeline.service`.

Aggiorna prima i percorsi nel file in base a dove hai messo il progetto
(assume `/home/pi/yicam-timeline` con il venv dentro `venv/`):

```ini
WorkingDirectory=/home/pi/yicam-timeline
ExecStart=/home/pi/yicam-timeline/venv/bin/python3 /home/pi/yicam-timeline/app.py
```

Poi installalo (questi comandi vanno lanciati **senza** il venv attivo, sono
comandi di sistema, non Python):

```bash
sudo cp yicam-timeline.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable yicam-timeline
sudo systemctl start yicam-timeline
```

Comandi utili una volta attivo come servizio:

```bash
sudo systemctl status yicam-timeline    # stato attuale
sudo journalctl -u yicam-timeline -f    # log in tempo reale
sudo systemctl restart yicam-timeline   # dopo aver modificato config.json o i file del progetto
sudo systemctl stop yicam-timeline      # fermarlo
```

Da quando gira come servizio, non serve più aprire un terminale e attivare
il venv per l'uso quotidiano — solo se devi rilanciare `set_password.py`,
`encrypt_config.py` o `generate_cert.sh` manualmente.

**Quando serve davvero un riavvio:** dopo aver modificato `config.json` o
un qualunque file `.py`. I file dentro `static/` (`.css`, `.js`, icone) non
richiedono riavvio: basta un refresh del browser (Ctrl+Shift+R per essere
sicuri di non prendere una versione in cache). Anche i file `.html` dentro
`templates/` si aggiornano senza riavviare — l'app disattiva volutamente la
cache dei template, per comodità durante l'uso quotidiano.

## Riproduzione senza attese tra una clip e l'altra

Quando parte la riproduzione di una clip, il server scarica automaticamente
in background anche quella successiva nell'elenco del giorno selezionato,
così è già in cache locale quando serve. Questo vale sia quando clicchi
manualmente un'altra clip sulla timeline, sia durante la riproduzione
continua automatica: ad ogni clip che parte, viene subito richiesta la
successiva, creando una catena di download anticipati senza intervento
dell'utente. L'unico caso in cui può ricomparire una breve attesa è il primo
clip del giorno seguente (il prefetch resta all'interno del giorno
selezionato).

## Fuso orario delle registrazioni

yi-hack scrive i nomi dei file usando l'orologio interno della camera, che
di norma è in **UTC** indipendentemente da dove ti trovi — per questo le
clip possono apparire "indietro" sulla timeline rispetto all'ora reale.

In `config.json` puoi indicare:

```json
"camera_timezone": "UTC",
"timezone": "Europe/Rome"
```

- `camera_timezone`: il fuso in cui la camera scrive i nomi file (di solito
  non va toccato, resta `UTC`).
- `timezone`: il tuo fuso reale. Con `Europe/Rome` la conversione tiene
  conto **automaticamente** del passaggio ora legale/ora solare — non serve
  aggiornare nulla a fine ottobre o fine marzo.

Se cambi questi valori dopo aver già indicizzato delle registrazioni, le
clip già in indice mantengono l'orario calcolato con le impostazioni
precedenti. Per far ricalcolare tutto da capo:

```bash
rm index.db
```

e poi riavvia il server (o premi "Aggiorna indice"): l'indice verrà
ricostruito da zero con gli orari corretti. Non tocca la cache dei video già
scaricati, solo l'indice dei metadati.

## Pulizia automatica della cache video

`index.db` (l'indice dei metadati) resta sempre piccolo — poche centinaia di
KB anche con migliaia di clip indicizzate, perché contiene solo nomi file e
orari, non i video. Quello che invece può crescere è la cartella `cache/`,
dove finiscono i video effettivamente scaricati (quando li guardi, e ora
anche in anticipo grazie al prefetch).

Per evitare che riempia lo storage, in `config.json`:

```json
"cache_max_mb": 2048,
"cache_max_age_hours": 0
```

- `cache_max_mb`: dimensione massima totale della cache, in MB. Quando viene
  superata, i clip scaricati meno di recente vengono eliminati per primi
  finché non si rientra nel limite. `0` disattiva questo controllo.
- `cache_max_age_hours`: elimina comunque, indipendentemente dallo spazio
  occupato, qualunque clip scaricato da più di N ore. `0` disattiva questo
  controllo.

Puoi usare uno dei due, entrambi, o nessuno (a tuo rischio). La pulizia
viene eseguita automaticamente ad ogni ciclo di sincronizzazione in
background (quindi ogni `sync_interval_seconds`). Non tocca mai i video
ancora sulla SD della camera: elimina solo la copia locale già scaricata,
che verrà ri-scaricata al bisogno se richiedi di nuovo quel clip.

## Rimozione automatica delle clip scadute

Le camere registrano in loop su uno storico fisso (tipicamente 2-3 giorni,
in base alla capienza della SD): quando lo spazio finisce, le ore più
vecchie vengono eliminate automaticamente dalla camera stessa per fare
posto alle nuove registrazioni.

Ad ogni sincronizzazione, il server confronta le cartelle-ora ancora
presenti sulla camera con quelle già indicizzate: qualunque cartella non
più presente sulla camera viene rimossa sia dal database sia dall'eventuale
cache video locale. Così la timeline mostra sempre e solo lo storico
realmente disponibile, senza clip "fantasma" che darebbero errore se
provassi ad aprirle. Non serve alcuna configurazione: è un comportamento
automatico, allineato 1:1 a come la camera stessa gestisce lo spazio sulla
SD (elimina ore intere, non singoli file sparsi).

## Blocco e download delle clip

Su ogni clip della timeline:
- **Tasto destro** (desktop) o **tocco prolungato ~0.5s** (mobile, con
  vibrazione di conferma se il telefono la supporta) apre un menu con due
  opzioni.
- **🔒 Blocca clip / 🔓 Sblocca clip**: una clip bloccata viene scaricata
  subito (se non è già in cache) e protetta permanentemente — esclusa sia
  dalla pulizia automatica della cache (dimensione/età) sia dalla rimozione
  quando la cartella scade sulla camera. Le clip bloccate mostrano un
  contorno viola, con una piccola icona a forma di lucchetto in più su
  desktop (nascosta su mobile per non appesantire blocchi già piccoli).
- **⬇ Scarica clip**: avvia il download del file mp4 con un nome leggibile
  (es. `Ingresso_2026-07-26_07-00-00.mp4`) invece del nome originale
  criptico della camera.

Un chiarimento importante: il video vive fisicamente sulla SD della camera,
che gestisce la propria rotazione in autonomia — il server non può
impedirle di cancellare l'originale. "Bloccare" quindi significa
concretamente **conservare per sempre la copia già scaricata sul server**,
indipendentemente da cosa succede poi sulla camera.

## Diretta (live RTSP)

Oltre alle registrazioni, puoi guardare la diretta (video **e audio**) di
ogni camera direttamente dal browser. Siccome i browser non sanno riprodurre
RTSP nativamente, il server usa `ffmpeg` per "rimpacchettare" il video (senza
ricodifica — quindi nessun carico aggiuntivo sulla CPU) e ricodificare solo
l'audio in AAC (leggero, necessario perché molte camere trasmettono l'audio
in un formato non supportato direttamente da HLS), producendo uno stream HLS
leggibile da qualsiasi browser.

### Requisito: ffmpeg

```bash
sudo apt install ffmpeg
```

Se manca, all'avvio del server vedrai un avviso in console e il pulsante
"diretta" darà errore quando lo premi.

### Configurazione

Per ogni camera in `config.json`, aggiungi una sezione `live` con l'URL RTSP
e le credenziali della diretta (che possono essere diverse da quelle FTP
usate per le registrazioni):

```json
{
  "id": 1,
  "name": "Ingresso",
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

Usa l'URL RTSP così come lo usi già per lo streaming live che hai verificato
funzionare (senza inserire utente/password dentro l'URL stesso: ci pensa il
server a comporli correttamente, gestendo anche eventuali caratteri speciali
nella password). Se una camera non ha la sezione `live`, semplicemente non
mostrerà il pulsante "diretta" nell'interfaccia.

### Come funziona in pratica

- Il pulsante "● diretta" compare solo per le camere che hanno `live`
  configurato.
- Alla pressione, il server avvia `ffmpeg` per quella camera (impiega
  1-2 secondi per agganciare lo stream) e il video parte in HLS nel player.
- Se non guardi la diretta per più di 30 secondi (cambi pagina, passi a una
  clip registrata, chiudi la scheda), il processo `ffmpeg` viene fermato
  automaticamente in background, per non tenere impegnate CPU e rete della
  camera inutilmente.
- Cliccando una clip registrata mentre sei in diretta, si esce
  automaticamente dalla diretta e riparte la normale riproduzione.
- Cambiando camera mentre sei in diretta, la diretta segue automaticamente
  la nuova camera selezionata.
- Se al primo avvio della diretta il video resta in pausa senza partire da
  solo, tocca una volta il pulsante ▶ nativo del player: alcuni browser
  bloccano l'avvio automatico con audio finché non c'è un tocco diretto
  sull'elemento video.

### Margine di buffer (utile per l'accesso da fuori casa)

In `config.json`:
```json
"live_hls_segment_seconds": 2,
"live_hls_list_size": 6
```
Insieme determinano quanti secondi di margine ha il player prima che un
segmento venga cancellato dal server (default: 2×6 = 12 secondi). Valori più
alti = più tolleranza a latenza/rete instabile (utile in accesso da fuori
casa), a scapito di un ritardo leggermente maggiore rispetto all'istante
live reale — irrilevante per uso di videosorveglianza.

## Diretta multipla (Livewall)

Due pagine dedicate mostrano in griglia le dirette di un gruppo di camere a
tua scelta: **Livewall 1** e **Livewall 2**. Si raggiungono dai due bottoni
nella sidebar sopra "Aggiorna indice", o direttamente da `/wall/1` e
`/wall/2`.

Quali id-camera mostrare in ciascuno si sceglie in `config.json`:
```json
"live_walls": {
  "1": [1, 2, 3, 4],
  "2": [5, 6, 7, 8]
}
```
Non serve che siano consecutivi né in ordine — puoi scrivere `[1, 3, 7, 8]`
se vuoi mescolare camere di gruppi diversi in una sola vista. Se il campo
`live_walls` non è presente, restano questi due default (1-4 e 5-8). Un id
senza camera configurata (o rimosso in futuro) mostra semplicemente un
placeholder invece di dare errore.

- Slot senza una camera configurata per quell'id, o camere senza sezione
  `live`, mostrano un placeholder invece di tentare la connessione.
- **Tocca/clicca una tile** per espanderla a schermo intero (le altre tre
  spariscono); ritocca la stessa tile — o premi **Esc** da desktop — per
  tornare alla griglia. È un "finto" schermo intero via CSS, non la vera
  Fullscreen API del browser: istantaneo, senza richieste di permessi.
- Su **desktop** la griglia riempie esattamente lo spazio disponibile,
  massimizzando ogni tile. Su **smartphone** le 4 tile sono impilate in
  colonna e scorrono normalmente con la pagina.
- L'audio è **sempre disattivato** in questa vista (con 4 flussi audio
  insieme sarebbe poco pratico) — per l'audio, usa la diretta della singola
  camera dalla timeline principale.
- Lasciando la pagina, tutte le dirette attive vengono fermate
  esplicitamente sul server (oltre al watchdog automatico che le
  fermerebbe comunque dopo 30s di inattività).

Nota: attenzione al carico con 4 dirette 1080p simultanee — banda e CPU
(per `ffmpeg`) aumentano in proporzione rispetto a una singola diretta. Se
noti rallentamenti, prova ad alzare `live_hls_segment_seconds`/
`live_hls_list_size` come sopra, oppure valuta una risoluzione minore sulle
camere se il tuo hardware fatica con tutte e 4 insieme.

## Uso da smartphone (Android/iOS) e installazione come app

L'interfaccia è responsive: sotto una certa larghezza (telefoni, tablet in
verticale) il menu laterale (camere, giorni, sync) si trasforma in un
pannello a scomparsa richiamabile con l'icona ☰ in alto a sinistra, e i
pulsanti della barra del player si distribuiscono su tutta la larghezza.

La tabella della timeline ha una riga di intestazione fissa in alto con i
minuti (00, 10, 20...30...50), utile sia su desktop che su mobile per capire
subito a che minuto corrisponde ogni blocco. Su smartphone, la corsia dei
minuti di ogni ora è più larga dello schermo e **scorre orizzontalmente**
(il resto dell'interfaccia, etichetta dell'ora inclusa, resta fermo) — le
clip diventano così molto più larghe e facili da toccare rispetto a una
vista compressa nella larghezza dello schermo.

In più, l'app è una **PWA (Progressive Web App)**: puoi installarla sulla
schermata Home del telefono e si comporta come un'app vera (icona propria,
si apre a schermo intero senza barra degli indirizzi del browser).

**Su Android (Chrome):**
1. Apri l'indirizzo `https://<ip-del-pi>:5050` da Chrome.
2. Tocca il menu (⋮) in alto a destra.
3. Scegli **"Aggiungi a schermata Home"** (o **"Installa app"** se compare
   direttamente).

**Su iPhone (Safari):** Condividi → "Aggiungi a Home".

Nota: essendo un certificato HTTPS autofirmato, alla primissima visita
Chrome mostrerà l'avviso di sicurezza — è normale, conferma l'eccezione una
volta sola. Da lì in poi l'icona sulla home funzionerà normalmente.

**Per l'installazione "vera"** (icona standalone, non solo una scorciatoia),
Chrome richiede che il certificato sia generato con l'IP/hostname corretto
come Subject Alternative Name (vedi sezione HTTPS più sopra: usa
`./generate_cert.sh <tuo-ip>`) **e** che tu l'abbia importato come CA
attendibile sul telefono — altrimenti Chrome offre solo "Crea scorciatoia"
invece della vera installazione PWA.

## Icone delle camere nel menu

Ogni camera nel menu laterale mostra una piccola icona (disegnata a mano,
nessuna libreria esterna). Ci sono due modi per sceglierla, in ordine di
priorità:

**1. Esplicita** — aggiungi il campo `"icon"` alla camera in `config.json`:
```json
{
  "id": 5,
  "name": "Box auto",
  "icon": "garage",
  ...
}
```
Valori disponibili: `porta`, `giardino`, `camera`, `cameretta`, `garage`,
`cancello`, `soggiorno`, `scale`, `cortile`. Un valore non riconosciuto (o
il campo assente) fa passare al punto successivo.

**2. Automatica dal nome** — se non specifichi `"icon"`, il sistema prova a
indovinarla dal campo `name` (case-insensitive): "giardino" → pianta,
"ingresso" → porta, "cameretta" → lettino con stellina, "camera" (ma non
"cameretta") → letto, "garage"/"cancello"/"soggiorno"/"scale" → le
rispettive icone, "cortile" o "esterno" → sole/cortile.

Se nessuna delle due si applica, resta l'**icona generica di
videocamera** come ripiego — mai un errore, solo un'icona meno specifica.
Utile quando aggiungi nuove camere: se il nome non è già una di queste
parole, basta il campo `"icon"` esplicito per scegliere quella giusta senza
dover rinominare nulla.

## Personalizzazioni facili

- **Intervallo di sync**: `sync_interval_seconds` in `config.json`.
- **Percorso FTP diverso** (se differisce da camera a camera): aggiungi
  `"ftp_root": "/percorso/diverso"` alla singola camera in `config.json`.
- **Pulizia cache**: la cartella `cache/` può essere svuotata in sicurezza in
  qualsiasi momento; i file verranno ri-scaricati dalla camera al prossimo utilizzo.

## Crediti

Questo progetto è nato da una lunga conversazione, portata avanti passo
dopo passo, con **Claude** ([Anthropic](https://www.anthropic.com)) — ogni
riga di codice, dall'indicizzatore FTP iniziale fino alla diretta, alla
PWA, e ad ogni correzione lungo il percorso, è stata scritta da Claude.
**[alebrescia](https://github.com/alebrescia)** ha definito i requisiti,
testato ogni modifica su hardware reale, segnalato cosa funzionava e cosa
no, e guidato la direzione del progetto trasformandolo da un semplice
visualizzatore di clip in quello che è oggi.

## Licenza

Distribuito con [licenza MIT](LICENSE) — libero uso, modifica e
redistribuzione.

## Disclaimer

Questo è un progetto hobbistico personale, condiviso così com'è. È
pensato per le convenzioni di nomi file di yi-hack-MStar/yi-hack-Allwinner,
ma dovrebbe essere adattabile ad altre camere con una struttura di
cartelle di registrazione simile. Pull request e segnalazioni sono
benvenute, ma non c'è garanzia di manutenzione attiva.
