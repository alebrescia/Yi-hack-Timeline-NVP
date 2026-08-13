/* global initialConfig */

function initSettings(initialConfig) {

  // ---- Switch Basic / Advanced ----
  const advToggle = document.getElementById('advanced-toggle');
  const advSections = document.querySelectorAll('[data-advanced]');

  function applyMode(advanced) {
    advSections.forEach(s => { s.style.display = advanced ? '' : 'none'; });
    advToggle.checked = advanced;
    try { localStorage.setItem('settings_advanced', advanced ? '1' : '0'); } catch (_) {}
  }

  // ripristina l'ultima modalità usata, default: basic (false)
  const savedMode = (() => { try { return localStorage.getItem('settings_advanced') === '1'; } catch (_) { return false; } })();
  applyMode(savedMode);

  advToggle.addEventListener('change', () => applyMode(advToggle.checked));

  const ICON_KEYS = [
    '', 'porta', 'giardino', 'camera', 'cameretta',
    'garage', 'cancello', 'soggiorno', 'scale', 'cortile',
  ];

  // ---- Rendering delle card camera ----

  const list = document.getElementById('cameras-list');
  let cameras = JSON.parse(JSON.stringify(initialConfig.cameras || []));

  function renderCameras() {
    list.innerHTML = '';
    cameras.forEach((cam, idx) => renderCamera(cam, idx));
  }

  function renderCamera(cam, idx) {
    const card = document.createElement('div');
    card.className = 'cam-card';
    card.dataset.idx = idx;

    card.innerHTML = `
      <div class="cam-card-header">
        <span class="cam-card-title">Telecamera #${cam.id || '?'} — ${cam.name || '(senza nome)'}</span>
        <button class="cam-card-remove" data-idx="${idx}" title="Rimuovi telecamera">✕</button>
      </div>
      <div class="settings-grid">
        <label class="settings-label">ID (intero univoco)
          <input class="settings-input" type="number" name="id" min="1" value="${cam.id ?? ''}">
        </label>
        <label class="settings-label">Nome
          <input class="settings-input" type="text" name="name" value="${esc(cam.name)}">
        </label>
        <label class="settings-label">Icona
          <select class="settings-input" name="icon">
            ${ICON_KEYS.map(k => `<option value="${k}" ${cam.icon === k ? 'selected' : ''}>${k || '(automatica dal nome)'}</option>`).join('')}
          </select>
        </label>
        <label class="settings-label">Host / IP
          <input class="settings-input" type="text" name="host" value="${esc(cam.host)}">
        </label>
        <label class="settings-label">Porta FTP
          <input class="settings-input" type="number" name="port" min="1" max="65535" value="${cam.port ?? 21}">
        </label>
        <label class="settings-label">Utente FTP
          <input class="settings-input" type="text" name="user" value="${esc(cam.user)}">
        </label>
        <label class="settings-label">Password FTP (lascia vuoto per non cambiare)
          <input class="settings-input" type="password" name="password" placeholder="••••••">
        </label>
        <label class="settings-label">Percorso FTP (lascia vuoto per usare quello globale)
          <input class="settings-input" type="text" name="ftp_root" value="${esc(cam.ftp_root || '')}">
        </label>
      </div>

      <details class="cam-live-details">
        <summary class="cam-live-summary">Impostazioni diretta (RTSP)</summary>
        <div class="settings-grid" style="padding-top:12px">
          <label class="settings-label">URL RTSP
            <input class="settings-input" type="text" name="live_rtsp_url" value="${esc((cam.live || {}).rtsp_url || '')}">
          </label>
          <label class="settings-label">Utente RTSP
            <input class="settings-input" type="text" name="live_user" value="${esc((cam.live || {}).user || '')}">
          </label>
          <label class="settings-label">Password RTSP (lascia vuoto per non cambiare)
            <input class="settings-input" type="password" name="live_password" placeholder="••••••">
          </label>
        </div>
      </details>
    `;

    // aggiorna il titolo della card in tempo reale
    card.querySelector('[name="id"]').addEventListener('input', () => {
      card.querySelector('.cam-card-title').textContent =
        `Telecamera #${card.querySelector('[name="id"]').value || '?'} — ${card.querySelector('[name="name"]').value || '(senza nome)'}`;
    });
    card.querySelector('[name="name"]').addEventListener('input', () => {
      card.querySelector('.cam-card-title').textContent =
        `Telecamera #${card.querySelector('[name="id"]').value || '?'} — ${card.querySelector('[name="name"]').value || '(senza nome)'}`;
    });

    card.querySelector('.cam-card-remove').addEventListener('click', () => {
      cameras.splice(idx, 1);
      renderCameras();
    });

    list.appendChild(card);
  }

  document.getElementById('add-camera-btn').addEventListener('click', () => {
    const maxId = cameras.reduce((m, c) => Math.max(m, c.id || 0), 0);
    cameras.push({ id: maxId + 1, name: '', host: '', port: 21, user: 'root', password: '' });
    renderCameras();
    list.lastElementChild.scrollIntoView({ behavior: 'smooth' });
  });

  renderCameras();

  // ---- Manutenzione: riavvio camere via SSH ----

  const maintList = document.getElementById('maintenance-list');

  function renderMaintenance() {
    maintList.innerHTML = '';
    (initialConfig.cameras || []).forEach((cam) => {
      const row = document.createElement('div');
      row.className = 'maint-row';
      row.innerHTML = `
        <span class="maint-name">${esc(cam.name)} <span class="maint-host">(${esc(cam.host)})</span></span>
        <button class="maint-reboot-btn" data-id="${cam.id}">Riavvia</button>
        <span class="maint-status"></span>
      `;
      const btn = row.querySelector('.maint-reboot-btn');
      const status = row.querySelector('.maint-status');

      btn.addEventListener('click', async () => {
        if (!confirm(`Riavviare davvero la camera "${cam.name}"? La diretta e la sincronizzazione si interromperanno per qualche decina di secondi.`)) {
          return;
        }
        btn.disabled = true;
        status.textContent = 'invio comando...';
        status.className = 'maint-status';
        try {
          const res = await fetch(`/api/camera/${cam.id}/reboot`, { method: 'POST' });
          const body = await res.json();
          if (!res.ok || body.status !== 'ok') {
            throw new Error(body.message || 'errore sconosciuto');
          }
          status.textContent = '✓ comando inviato';
          status.className = 'maint-status maint-status--ok';
        } catch (e) {
          status.textContent = '✕ ' + e.message;
          status.className = 'maint-status maint-status--err';
        } finally {
          btn.disabled = false;
        }
      });

      maintList.appendChild(row);
    });
  }

  renderMaintenance();

  // ---- Raccolta valori dal form ----

  function collectCameras() {
    const cards = list.querySelectorAll('.cam-card');
    return Array.from(cards).map(card => {
      const g = name => card.querySelector(`[name="${name}"]`);
      const cam = {
        id: parseInt(g('id').value) || 0,
        name: g('name').value.trim(),
        host: g('host').value.trim(),
        port: parseInt(g('port').value) || 21,
        user: g('user').value.trim(),
      };
      const iconVal = g('icon').value;
      if (iconVal) cam.icon = iconVal;
      const pw = g('password').value;
      cam.password = pw || null;
      const ftpRoot = g('ftp_root').value.trim();
      if (ftpRoot) cam.ftp_root = ftpRoot;

      const rtsp = g('live_rtsp_url').value.trim();
      if (rtsp) {
        cam.live = {
          rtsp_url: rtsp,
          user: g('live_user').value.trim(),
          password: g('live_password').value || null,
        };
      }
      return cam;
    });
  }

  function v(id) { return document.getElementById(id).value.trim(); }
  function vn(id) { return parseFloat(document.getElementById(id).value) || 0; }
  function vb(id) { return document.getElementById(id).checked; }

  function parseIdList(str) {
    return str.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n) && n > 0);
  }

  function collectConfig() {
    return {
      cameras: collectCameras(),
      sync_interval_seconds: Math.max(5, parseInt(vn('sync_interval_seconds'))),
      cache_max_mb: parseInt(vn('cache_max_mb')),
      cache_max_age_hours: parseInt(vn('cache_max_age_hours')),
      cache_dir: v('cache_dir') || 'cache',
      db_path: v('db_path') || 'index.db',
      ftp_root: v('ftp_root') || '/tmp/sd/record',
      camera_timezone: v('camera_timezone') || 'UTC',
      timezone: v('timezone') || 'Europe/Rome',
      live_hls_segment_seconds: Math.max(1, parseInt(vn('live_hls_segment_seconds'))),
      live_hls_list_size: Math.max(2, parseInt(vn('live_hls_list_size'))),
      hls_dir: v('hls_dir') || 'hls_cache',
      live_walls: {
        '1': parseIdList(v('livewall_1')),
        '2': parseIdList(v('livewall_2')),
      },
      https: {
        enabled: vb('https_enabled'),
        cert: v('https_cert') || 'cert.pem',
        key: v('https_key') || 'key.pem',
      },
    };
  }

  // ---- Salvataggio ----

  const banner = document.getElementById('save-banner');
  const saveBtn = document.getElementById('save-btn');

  function showBanner(msg, ok) {
    banner.textContent = msg;
    banner.className = 'save-banner ' + (ok ? 'save-banner--ok' : 'save-banner--err');
    banner.hidden = false;
    banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  saveBtn.addEventListener('click', async () => {
    saveBtn.disabled = true;
    saveBtn.textContent = 'Salvataggio...';

    try {
      const cfg = collectConfig();
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      });
      const body = await res.json();

      if (!res.ok || body.status !== 'ok') {
        showBanner('Errore: ' + (body.message || 'errore sconosciuto'), false);
        saveBtn.disabled = false;
        saveBtn.textContent = 'Salva e riavvia';
        return;
      }

      showBanner(body.message, true);
      // ricarica dopo che il server ha avuto il tempo di riavviarsi
      setTimeout(() => window.location.reload(), 4000);

    } catch (e) {
      showBanner('Errore di rete: ' + e.message, false);
      saveBtn.disabled = false;
      saveBtn.textContent = 'Salva e riavvia';
    }
  });
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
