(() => {
  const tiles = Array.from(document.querySelectorAll('.wall-tile[data-camera-id]'));
  const hlsInstances = {};

  async function startTile(tile) {
    const cameraId = tile.dataset.cameraId;
    const video = tile.querySelector('video');
    const status = tile.querySelector('.wall-status');
    if (!video) return;

    try {
      const res = await fetch(`/api/live/${cameraId}/start`, { method: 'POST' });
      const body = await res.json();
      if (!res.ok || body.status !== 'ok') {
        throw new Error(body.message || 'errore sconosciuto');
      }
    } catch (e) {
      setError(status, e.message);
      return;
    }

    const src = `/api/live/${cameraId}/stream.m3u8`;

    if (window.Hls && Hls.isSupported()) {
      const hls = new Hls({ liveSyncDurationCount: 4 });

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
        if (status) status.remove();
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        console.error(`[wall] camera ${cameraId} hls.js`, data.type, data.details, 'fatal:', data.fatal);
        if (data.fatal) {
          setError(status, data.details);
        }
      });

      hls.loadSource(src);
      hls.attachMedia(video);
      hlsInstances[cameraId] = hls;
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src;
      video.play().catch(() => {});
      if (status) status.remove();
    } else {
      setError(status, 'HLS non supportato da questo browser');
    }
  }

  function setError(status, message) {
    if (!status) return;
    status.textContent = '● errore';
    status.dataset.status = 'error';
    if (message) status.title = message;
  }

  tiles.forEach(startTile);

  // Tocco/click su una tile: la espande a schermo intero (nasconde le
  // altre). Ripremendo la stessa tile si torna alla griglia a 4.
  const grid = document.querySelector('.wall-grid');
  tiles.forEach((tile) => {
    tile.addEventListener('click', () => {
      const alreadyExpanded = tile.classList.contains('expanded');
      tiles.forEach((t) => t.classList.remove('expanded'));
      if (alreadyExpanded) {
        grid.classList.remove('expanded-mode');
      } else {
        tile.classList.add('expanded');
        grid.classList.add('expanded-mode');
      }
    });
  });

  // Esc riporta sempre alla griglia (comodo da tastiera su desktop)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && grid.classList.contains('expanded-mode')) {
      tiles.forEach((t) => t.classList.remove('expanded'));
      grid.classList.remove('expanded-mode');
    }
  });

  // Ferma tutte le dirette avviate quando si lascia la pagina, cosi' ffmpeg
  // non resta impegnato inutilmente sul server (il watchdog lato server le
  // fermerebbe comunque dopo un po' di inattivita', questo lo rende immediato).
  window.addEventListener('beforeunload', () => {
    tiles.forEach((tile) => {
      const cameraId = tile.dataset.cameraId;
      if (cameraId) navigator.sendBeacon(`/api/live/${cameraId}/stop`);
    });
  });
})();
