(() => {
  const state = {
    cameras: [],
    activeCameraId: null,
    days: [],
    activeDay: null,
    clips: [],
    selectedClipId: null,
    autoplay: true,
    mode: 'recorded', // 'recorded' | 'live'
    hls: null,
  };

  const el = {
    cameraList: document.getElementById('camera-list'),
    dayList: document.getElementById('day-list'),
    timelineDate: document.getElementById('timeline-date'),
    timelineCoverage: document.getElementById('timeline-coverage'),
    track: document.getElementById('timeline-track'),
    player: document.getElementById('player'),
    nowLabel: document.getElementById('now-label'),
    nowTime: document.getElementById('now-time'),
    syncBtn: document.getElementById('sync-btn'),
    syncStatus: document.getElementById('sync-status'),
    autoplayToggle: document.getElementById('autoplay-toggle'),
    liveToggle: document.getElementById('live-toggle'),
    menuToggle: document.getElementById('menu-toggle'),
    sidebar: document.getElementById('sidebar'),
    sidebarClose: document.getElementById('sidebar-close'),
    sidebarOverlay: document.getElementById('sidebar-overlay'),
  };

  const pad2 = (n) => String(n).padStart(2, '0');

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    if (res.status === 401) {
      // sessione scaduta mentre la pagina era aperta: torna al login
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
      throw new Error('sessione scaduta');
    }
    if (!res.ok) throw new Error(`${url} -> ${res.status}`);
    return res.json();
  }

  // ---------- Cameras ----------

  async function loadCameras() {
    state.cameras = await fetchJSON('/api/cameras');
    if (!state.activeCameraId && state.cameras.length) {
      state.activeCameraId = state.cameras[0].id;
    }
    renderCameraList();
    updateLiveButtonVisibility();
  }

  // Set di icone disponibili, disegnate a mano (nessuna libreria esterna).
  // La chiave è il valore da usare nel campo "icon" di config.json.
  const CAMERA_ICONS = {
    porta: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="1"/><circle cx="14.5" cy="12" r="1"/></svg>',
    giardino: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21V10"/><path d="M12 10C12 6 9 3 5 3c0 4 3 7 7 7Z"/><path d="M12 13c0-3.5 2.5-6 6-6 0 3.5-2.5 6-6 6Z"/></svg>',
    camera: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v5"/><path d="M3 18v2"/><path d="M21 18v2"/><path d="M3 13V8a2 2 0 0 1 2-2h4v5"/></svg>',
    cameretta: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v5"/><path d="M3 18v2"/><path d="M21 18v2"/><path d="M3 13V8a2 2 0 0 1 2-2h3v5"/><path d="M17.5 3.2l.6 1.3 1.4.2-1 1 .2 1.4-1.2-.7-1.2.7.2-1.4-1-1 1.4-.2z"/></svg>',
    garage: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 9L12 3l10 6"/><rect x="4" y="9" width="16" height="11" rx="1"/><path d="M4 13h16M4 16.5h16"/></svg>',
    cancello: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21V4M9 21V4M15 21V4M20 21V4M2 9h20M2 15h20"/></svg>',
    soggiorno: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18v-4a2 2 0 0 1 2-2h1V9a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v3h1a2 2 0 0 1 2 2v4"/><path d="M4 18v2M20 18v2M3 14h18"/></svg>',
    scale: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4v-4h4v-4h4v-4h4"/></svg>',
    cortile: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></svg>',
    generico: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="14" height="12" rx="2"/><path d="M16 10l6-3v10l-6-3"/></svg>',
  };

  // Sceglie l'icona per una camera: prima il campo esplicito "icon" in
  // config.json (se valido), altrimenti riconoscimento automatico dal nome
  // (per compatibilità con le configurazioni già esistenti), infine il
  // ripiego generico. 'cameretta' va controllato prima di 'camera' perché
  // la contiene come sottostringa.
  function cameraIcon(cam) {
    if (cam.icon && CAMERA_ICONS[cam.icon]) {
      return CAMERA_ICONS[cam.icon];
    }
    const n = (cam.name || '').toLowerCase();
    if (n.includes('cameretta')) return CAMERA_ICONS.cameretta;
    if (n.includes('giardino')) return CAMERA_ICONS.giardino;
    if (n.includes('ingresso')) return CAMERA_ICONS.porta;
    if (n.includes('garage')) return CAMERA_ICONS.garage;
    if (n.includes('cancello')) return CAMERA_ICONS.cancello;
    if (n.includes('soggiorno')) return CAMERA_ICONS.soggiorno;
    if (n.includes('scale')) return CAMERA_ICONS.scale;
    if (n.includes('cortile') || n.includes('esterno')) return CAMERA_ICONS.cortile;
    if (n.includes('camera')) return CAMERA_ICONS.camera;
    return CAMERA_ICONS.generico;
  }

  function renderCameraList() {
    el.cameraList.innerHTML = '';
    state.cameras.forEach((cam) => {
      const li = document.createElement('li');
      li.className = 'camera-item' + (cam.id === state.activeCameraId ? ' active' : '');
      li.innerHTML = `<span class="cam-label"><span class="cam-icon">${cameraIcon(cam)}</span><span>${cam.name}</span></span>`;
      if (cam.sync_error) {
        const dot = document.createElement('span');
        dot.className = 'err-dot';
        dot.title = cam.sync_error;
        li.appendChild(dot);
      }
      li.addEventListener('click', () => selectCamera(cam.id));
      el.cameraList.appendChild(li);
    });
  }

  async function selectCamera(id) {
    const wasLive = state.mode === 'live';
    const previousCameraId = state.activeCameraId;
    state.activeCameraId = id;
    renderCameraList();
    updateLiveButtonVisibility();

    if (wasLive && previousCameraId !== id) {
      // stay in live mode, but follow the newly selected camera
      await stopLive(previousCameraId);
      await startLive(id);
    }
    await loadDays();
    if (isMobile()) closeSidebar();
  }

  function updateLiveButtonVisibility() {
    const cam = state.cameras.find((c) => c.id === state.activeCameraId);
    el.liveToggle.hidden = !cam || !cam.has_live;
  }

  // ---------- Days ----------

  async function loadDays() {
    state.days = await fetchJSON(`/api/days?camera_id=${state.activeCameraId}`);
    if (!state.days.find((d) => d.day === state.activeDay)) {
      state.activeDay = state.days.length ? state.days[state.days.length - 1].day : null;
    }
    renderDayList();
    if (state.activeDay) {
      await loadTimeline();
    } else {
      renderEmptyTimeline();
    }
  }

  function renderDayList() {
    el.dayList.innerHTML = '';
    if (!state.days.length) {
      el.dayList.innerHTML = '<p class="empty-state" style="padding:12px 0;">nessuna registrazione trovata</p>';
      return;
    }
    const maxSeconds = Math.max(...state.days.map((d) => d.total_seconds || 1));
    [...state.days].reverse().forEach((d) => {
      const row = document.createElement('div');
      row.className = 'day-row' + (d.day === state.activeDay ? ' active' : '');
      const hours = ((d.total_seconds || 0) / 3600).toFixed(1);
      row.innerHTML = `
        <span>${formatDayShort(d.day)}</span>
        <span class="day-bar"><span class="day-bar-fill" style="width:${(100 * (d.total_seconds || 0) / maxSeconds).toFixed(0)}%"></span></span>
        <span class="day-count">${hours}h</span>
      `;
      row.addEventListener('click', () => selectDay(d.day));
      el.dayList.appendChild(row);
    });
  }

  function formatDayShort(isoDay) {
    const [y, m, d] = isoDay.split('-');
    return `${d}/${m}`;
  }

  async function selectDay(day) {
    state.activeDay = day;
    renderDayList();
    await loadTimeline();
    if (isMobile()) closeSidebar();
  }

  // ---------- Timeline ----------

  async function loadTimeline() {
    state.clips = await fetchJSON(
      `/api/timeline?camera_id=${state.activeCameraId}&date=${state.activeDay}`
    );
    renderTimeline();
  }

  function renderEmptyTimeline() {
    el.timelineDate.textContent = '—';
    el.timelineCoverage.textContent = '';
    el.track.innerHTML = '<p class="empty-state">Nessuna camera con registrazioni indicizzate.<br>Premi "Aggiorna indice" per avviare la prima sincronizzazione.</p>';
  }

  function renderTimeline() {
    el.timelineDate.textContent = formatDayLong(state.activeDay);
    const totalSeconds = state.clips.reduce((s, c) => s + c.duration, 0);
    el.timelineCoverage.textContent = `${(totalSeconds / 3600).toFixed(1)}h registrate · ${state.clips.length} clip`;

    el.track.innerHTML = '';
    const now = new Date();
    const isToday = state.activeDay === now.toISOString().slice(0, 10);
    const currentHour = now.getHours();

    // Intestazione con i minuti (0-50), fissa in alto e allineata alle
    // stesse colonne delle righe orarie sottostanti.
    const header = document.createElement('div');
    header.className = 'hour-row minute-header-row';
    const headerLabel = document.createElement('div');
    headerLabel.className = 'hour-label minute-header-label';
    const headerLane = document.createElement('div');
    headerLane.className = 'hour-lane minute-header-lane';
    [0, 10, 20, 30, 40, 50].forEach((m) => {
      const tick = document.createElement('span');
      tick.className = 'minute-tick';
      tick.style.left = (m / 60) * 100 + '%';
      tick.textContent = pad2(m);
      headerLane.appendChild(tick);
    });
    header.appendChild(headerLabel);
    header.appendChild(headerLane);
    el.track.appendChild(header);

    // group clips by hour
    const byHour = Array.from({ length: 24 }, () => []);
    state.clips.forEach((c) => {
      const hour = parseInt(c.start_ts.slice(11, 13), 10);
      byHour[hour].push(c);
    });

    for (let h = 0; h < 24; h++) {
      const row = document.createElement('div');
      row.className = 'hour-row';

      const label = document.createElement('div');
      label.className = 'hour-label';
      label.textContent = pad2(h) + ':00';

      const lane = document.createElement('div');
      lane.className = 'hour-lane';

      byHour[h].forEach((clip) => {
        const minute = parseInt(clip.start_ts.slice(14, 16), 10);
        const second = parseInt(clip.start_ts.slice(17, 19), 10);
        const startPct = ((minute * 60 + second) / 3600) * 100;
        const widthPct = Math.max((clip.duration / 3600) * 100, 0.6);

        const block = document.createElement('div');
        block.className = 'clip-block'
          + (clip.id === state.selectedClipId ? ' selected' : '')
          + (clip.locked ? ' locked' : '');
        block.style.left = startPct + '%';
        block.style.width = widthPct + '%';
        block.title = `${clip.start_ts} (${clip.duration}s)` + (clip.locked ? ' — bloccata' : '');
        if (isToday && h === currentHour && clip === byHour[h][byHour[h].length - 1]) {
          block.classList.add('live');
        }
        if (clip.locked) {
          const badge = document.createElement('span');
          badge.className = 'lock-badge';
          badge.innerHTML = '<svg viewBox="0 0 24 24" width="9" height="9" fill="currentColor"><path d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5zm-3 5a3 3 0 0 1 6 0v3H9V7z"/></svg>';
          block.appendChild(badge);
        }
        block.addEventListener('click', () => playClip(clip));
        block.addEventListener('contextmenu', (e) => {
          e.preventDefault();
          openContextMenu(e.pageX, e.pageY, clip);
        });

        // Tocco prolungato (mobile): stesso menu del tasto destro. Si
        // annulla se il dito si sposta (probabile scroll) prima della soglia.
        let touchTimer = null;
        let longPressTriggered = false;

        block.addEventListener('touchstart', (e) => {
          longPressTriggered = false;
          const touch = e.touches[0];
          const x = touch.clientX;
          const y = touch.clientY;
          touchTimer = setTimeout(() => {
            longPressTriggered = true;
            if (navigator.vibrate) navigator.vibrate(15);
            openContextMenu(x, y, clip);
          }, 500);
        }, { passive: true });

        block.addEventListener('touchmove', () => {
          clearTimeout(touchTimer);
        }, { passive: true });

        block.addEventListener('touchend', (e) => {
          clearTimeout(touchTimer);
          if (longPressTriggered) {
            // evita che, subito dopo aver aperto il menu, scatti anche il
            // click sintetico che avvierebbe la riproduzione della clip
            e.preventDefault();
          }
        }, { passive: false });

        block.addEventListener('touchcancel', () => {
          clearTimeout(touchTimer);
        }, { passive: true });

        lane.appendChild(block);
      });

      row.appendChild(label);
      row.appendChild(lane);
      el.track.appendChild(row);
    }
  }

  function formatDayLong(isoDay) {
    const d = new Date(isoDay + 'T00:00:00');
    return d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }

  // ---------- Menu contestuale (tasto destro su una clip) ----------

  let contextMenuEl = null;

  function closeContextMenu() {
    if (!contextMenuEl) return;
    contextMenuEl.remove();
    contextMenuEl = null;
    document.removeEventListener('click', closeContextMenu);
    document.removeEventListener('keydown', onContextMenuKey);
  }

  function onContextMenuKey(e) {
    if (e.key === 'Escape') closeContextMenu();
  }

  function openContextMenu(x, y, clip) {
    closeContextMenu();

    const menu = document.createElement('div');
    menu.className = 'context-menu';

    const lockItem = document.createElement('button');
    lockItem.className = 'context-menu-item';
    lockItem.textContent = clip.locked ? '🔓 Sblocca clip' : '🔒 Blocca clip';
    lockItem.addEventListener('click', () => {
      closeContextMenu();
      toggleClipLock(clip);
    });

    const downloadItem = document.createElement('button');
    downloadItem.className = 'context-menu-item';
    downloadItem.textContent = '⬇ Scarica clip';
    downloadItem.addEventListener('click', () => {
      closeContextMenu();
      downloadClip(clip);
    });

    menu.appendChild(lockItem);
    menu.appendChild(downloadItem);
    document.body.appendChild(menu);
    contextMenuEl = menu;

    // Posiziona il menu senza farlo uscire dallo schermo
    const rect = menu.getBoundingClientRect();
    const maxX = window.innerWidth - rect.width - 8;
    const maxY = window.innerHeight - rect.height - 8;
    menu.style.left = Math.min(x, maxX) + 'px';
    menu.style.top = Math.min(y, maxY) + 'px';

    // Chiude al click fuori o con Esc (registrato al giro successivo per
    // non intercettare subito il click destro che ha aperto il menu)
    setTimeout(() => {
      document.addEventListener('click', closeContextMenu);
      document.addEventListener('keydown', onContextMenuKey);
    }, 0);
  }

  async function toggleClipLock(clip) {
    const method = clip.locked ? 'DELETE' : 'POST';
    try {
      const res = await fetch(`/api/clip/${state.activeCameraId}/${clip.id}/lock`, { method });
      const body = await res.json();
      if (!res.ok || body.status !== 'ok') {
        throw new Error(body.message || 'errore sconosciuto');
      }
      clip.locked = body.locked ? 1 : 0;
      renderTimeline();
    } catch (e) {
      alert(`Impossibile aggiornare il blocco della clip: ${e.message}`);
    }
  }

  function downloadClip(clip) {
    const a = document.createElement('a');
    a.href = `/api/clip/${state.activeCameraId}/${clip.id}/download`;
    a.download = ''; // il nome file lo suggerisce già il server
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // ---------- Player ----------

  function playClip(clip) {
    if (state.mode === 'live') {
      state.mode = 'recorded';
      el.liveToggle.classList.remove('live-active');
      el.liveToggle.textContent = '● diretta';
      stopLive(state.activeCameraId);
    }

    state.selectedClipId = clip.id;
    renderTimeline();
    el.player.src = `/api/clip/${state.activeCameraId}/${clip.id}`;
    el.player.play().catch(() => {});
    const cam = state.cameras.find((c) => c.id === state.activeCameraId);
    el.nowLabel.textContent = cam ? cam.name : 'Camera';
    el.nowTime.textContent = `${clip.start_ts} → ${clip.end_ts.slice(11)}`;

    prefetchNext(clip);
  }

  // Warms the cache for the clip that will play next, so when the current
  // one ends (or the user skips ahead) there's no download delay.
  function prefetchNext(clip) {
    const idx = state.clips.findIndex((c) => c.id === clip.id);
    if (idx === -1) return;
    const next = state.clips[idx + 1];
    if (!next) return;
    fetch(`/api/prefetch/${state.activeCameraId}/${next.id}`, { method: 'POST' }).catch(() => {});
  }

  el.player.addEventListener('ended', () => {
    if (!state.autoplay) return;
    const idx = state.clips.findIndex((c) => c.id === state.selectedClipId);
    if (idx === -1) return;
    const current = state.clips[idx];
    const next = state.clips[idx + 1];
    // Only auto-continue if the next clip starts right where this one ends
    // (keeps playback coherent instead of jumping across real gaps silently).
    if (next && next.start_ts === current.end_ts) {
      playClip(next);
    } else if (next) {
      // small gap: still advance, but the timestamp jump makes the gap visible
      playClip(next);
    }
  });

  el.autoplayToggle.addEventListener('click', () => {
    state.autoplay = !state.autoplay;
    el.autoplayToggle.classList.toggle('active', state.autoplay);
    el.autoplayToggle.textContent = state.autoplay ? '▶ continuo' : '⏸ singolo';
  });

  // ---------- Live ----------

  el.player.addEventListener('error', () => {
    if (el.player.error) {
      console.error('[video] errore elemento <video>', el.player.error.code, el.player.error.message);
    }
  });

  async function startLive(cameraId) {
    el.liveToggle.textContent = '⏳ connessione…';
    try {
      const res = await fetch(`/api/live/${cameraId}/start`, { method: 'POST' });
      const body = await res.json();
      if (!res.ok || body.status !== 'ok') {
        throw new Error(body.message || 'errore sconosciuto');
      }
    } catch (e) {
      alert(`Impossibile avviare la diretta: ${e.message}`);
      state.mode = 'recorded';
      el.liveToggle.classList.remove('live-active');
      el.liveToggle.textContent = '● diretta';
      return;
    }

    state.mode = 'live';
    el.liveToggle.classList.add('live-active');
    el.liveToggle.textContent = '● in diretta';

    const cam = state.cameras.find((c) => c.id === cameraId);
    el.nowLabel.textContent = cam ? `${cam.name} — diretta` : 'Diretta';
    el.nowTime.textContent = '';

    const src = `/api/live/${cameraId}/stream.m3u8`;
    attachHls(src);
  }

  function attachHls(src) {
    detachHls();

    // L'autoplay muto è sempre permesso dai browser; quello con audio no,
    // specialmente se tra il tocco dell'utente e l'avvio effettivo passano
    // un paio di secondi (fetch, attesa ffmpeg, parsing del manifest) — il
    // browser può considerare "scaduto" il permesso concesso dal tocco
    // iniziale e mettere in pausa lo stream in silenzio, senza errori.
    // Si parte quindi muti, e si riattiva l'audio non appena la riproduzione
    // è davvero partita (i browser sono molto più permissivi nel permettere
    // di togliere il muto a qualcosa che sta già suonando).
    el.player.muted = true;
    const unmuteOnceStarted = () => {
      el.player.muted = false;
      el.player.removeEventListener('playing', unmuteOnceStarted);
    };
    el.player.addEventListener('playing', unmuteOnceStarted);

    if (window.Hls && Hls.isSupported()) {
      const hls = new Hls({ liveSyncDurationCount: 4 });

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        el.player.play().catch((err) => console.error('[live] play() rifiutata:', err));
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        // Log solo gli errori reali, non l'intero ciclo di vita dello
        // stream: type/details identificano esattamente cosa si è rotto
        // (rete, parsing del manifest, decodifica media, ecc.)
        console.error('[hls.js] ERRORE:', data.type, '|', data.details, '| fatal:', data.fatal, data);
        if (!data.fatal) return;
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            console.warn('[hls.js] errore di rete fatale, riprovo il caricamento');
            hls.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            console.warn('[hls.js] errore media fatale, provo a recuperare');
            hls.recoverMediaError();
            break;
          default:
            console.warn('[hls.js] errore non recuperabile, chiudo lo stream');
            hls.destroy();
            break;
        }
      });

      hls.loadSource(src);
      hls.attachMedia(el.player);
      state.hls = hls;
    } else if (el.player.canPlayType('application/vnd.apple.mpegurl')) {
      // Fallback solo per i rari casi senza hls.js utilizzabile (es. hls.js
      // non caricato dal CDN). Su Safari/iOS funziona comunque bene nativamente.
      el.player.src = src;
      el.player.play().catch((err) => console.error('[live] play() nativo rifiutata:', err));
    } else {
      alert('Questo browser non supporta la riproduzione HLS.');
    }
  }

  function detachHls() {
    if (state.hls) {
      state.hls.destroy();
      state.hls = null;
    }
  }

  async function stopLive(cameraId) {
    detachHls();
    el.player.removeAttribute('src');
    el.player.load();
    try {
      await fetch(`/api/live/${cameraId}/stop`, { method: 'POST' });
    } catch (e) {
      // best effort: il watchdog lato server la fermerà comunque dopo un po'
    }
  }

  el.liveToggle.addEventListener('click', async () => {
    if (state.mode === 'live') {
      const cameraId = state.activeCameraId;
      state.mode = 'recorded';
      el.liveToggle.classList.remove('live-active');
      el.liveToggle.textContent = '● diretta';
      el.nowLabel.textContent = 'Seleziona un momento sulla timeline';
      await stopLive(cameraId);
    } else {
      await startLive(state.activeCameraId);
    }
  });

  // ---------- Sync ----------

  el.syncBtn.addEventListener('click', async () => {
    el.syncBtn.classList.add('spinning');
    el.syncStatus.textContent = 'sincronizzazione in corso…';
    try {
      await fetchJSON('/api/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      await loadCameras();
      await loadDays();
      el.syncStatus.textContent = `ultimo aggiornamento: ${new Date().toLocaleTimeString('it-IT')}`;
    } catch (e) {
      el.syncStatus.textContent = 'errore di sincronizzazione';
    } finally {
      el.syncBtn.classList.remove('spinning');
    }
  });

  window.addEventListener('beforeunload', () => {
    if (state.mode === 'live' && state.activeCameraId) {
      navigator.sendBeacon(`/api/live/${state.activeCameraId}/stop`);
    }
  });

  // ---------- Menu mobile ----------

  function openSidebar() {
    el.sidebar.classList.add('open');
    el.sidebarOverlay.hidden = false;
    el.sidebarOverlay.classList.add('open');
  }

  function closeSidebar() {
    el.sidebar.classList.remove('open');
    el.sidebarOverlay.hidden = true;
    el.sidebarOverlay.classList.remove('open');
  }

  const isMobile = () => window.matchMedia('(max-width: 860px)').matches;

  el.menuToggle.addEventListener('click', openSidebar);
  el.sidebarClose.addEventListener('click', closeSidebar);
  el.sidebarOverlay.addEventListener('click', closeSidebar);

  // ---------- Init ----------

  (async function init() {
    await loadCameras();
    if (state.activeCameraId) {
      await loadDays();
    } else {
      renderEmptyTimeline();
    }
  })();
})();
