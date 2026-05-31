/* ============================================================
   EyeGuard — dashboard_basico.js
   Lógica: timers predeterminados, configurables, historial y modal
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ─────────────────────────────────────────
     ESTADO GLOBAL
  ───────────────────────────────────────── */
  const state = {
    // Timer activo (predeterminado)
    presetTimer:      null,
    presetInterval:   0,       // minutos de trabajo
    presetDuration:   0,       // segundos de descanso en modal
    presetName:       '',
    presetSecondsLeft: 0,
    presetTotal:      0,

    // Timer activo (configurable)
    customTimer:      null,
    customInterval:   0,
    customDuration:   0,
    customMessage:    '',
    customSecondsLeft: 0,
    customTotal:      0,

    // Modal de descanso
    modalTimer:       null,
    modalSecondsLeft: 0,
    modalTotal:       0,

    // Historial
    history:          JSON.parse(localStorage.getItem('eyeguard_history') || '[]'),
    sessionStart:     Date.now(),
    totalAlerts:      0,
    completedAlerts:  0,
    activeProtocol:   '—',
  };

  /* ─────────────────────────────────────────
     NAVEGACIÓN DE SECCIONES
  ───────────────────────────────────────── */
  window.showSection = (id) => {
    // Ocultar tarjetas de nav
    document.querySelector('.nav-grid').classList.add('hidden');
    document.querySelector('.page-header').classList.add('hidden');

    // Activar sección correcta
    ['predeterminadas', 'configurables', 'historial'].forEach(s => {
      document.getElementById('sec' + capitalize(s)).classList.add('hidden');
    });

    const sec = document.getElementById('sec' + capitalize(id));
    sec.classList.remove('hidden');

    if (id === 'historial') renderHistory();
  };

  window.hideSection = () => {
    document.querySelector('.nav-grid').classList.remove('hidden');
    document.querySelector('.page-header').classList.remove('hidden');
    ['secPredeterminadas', 'secConfigurables', 'secHistorial'].forEach(id => {
      document.getElementById(id).classList.add('hidden');
    });
  };

  function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  /* ─────────────────────────────────────────
     SECCIÓN 1 — ALERTAS PREDETERMINADAS
  ───────────────────────────────────────── */

  window.activatePreset = (btn) => {
    const intervalMin  = parseInt(btn.dataset.interval);   // minutos
    const durationSec  = parseInt(btn.dataset.duration);   // segundos de descanso
    const name         = btn.dataset.name;

    // Detener si ya había uno corriendo
    stopTimer(false);

    state.presetInterval    = intervalMin * 60;  // convertir a segundos
    state.presetDuration    = durationSec;
    state.presetName        = name;
    state.presetSecondsLeft = intervalMin * 60;
    state.presetTotal       = intervalMin * 60;
    state.activeProtocol    = name;

    showTimerPanel(true);
    startPresetCountdown();

    // Registrar en historial
    addHistoryItem(name, `Protocolo iniciado — cada ${intervalMin} min`, 'preset');
  };

  function startPresetCountdown() {
    clearInterval(state.presetTimer);
    updatePresetDisplay();

    state.presetTimer = setInterval(() => {
      state.presetSecondsLeft--;
      updatePresetDisplay();

      if (state.presetSecondsLeft <= 0) {
        clearInterval(state.presetTimer);
        triggerAlert(
          state.presetName,
          getAlertMessage(state.presetName),
          state.presetDuration,
          () => {
            // Reiniciar countdown
            state.presetSecondsLeft = state.presetTotal;
            startPresetCountdown();
          }
        );
      }
    }, 1000);
  }

  function updatePresetDisplay() {
    const clock   = document.getElementById('timerClock');
    const bar     = document.getElementById('timerBar');
    const next    = document.getElementById('timerNext');
    const label   = document.getElementById('timerLabel');
    if (!clock) return;

    label.textContent = state.presetName + ' activa';
    clock.textContent = formatTime(state.presetSecondsLeft);
    const pct = (state.presetSecondsLeft / state.presetTotal) * 100;
    bar.style.width = pct + '%';
    next.textContent = 'Próxima alerta en ' + formatTime(state.presetSecondsLeft);
  }

  function showTimerPanel(show) {
    const panel = document.getElementById('timerPanel');
    if (show) panel.classList.remove('hidden');
    else panel.classList.add('hidden');
  }

  window.stopTimer = (showFeedback = true) => {
    clearInterval(state.presetTimer);
    state.presetTimer = null;
    showTimerPanel(false);
    if (showFeedback && state.presetName) {
      addHistoryItem(state.presetName, 'Protocolo detenido por el usuario', 'preset');
    }
  };

  /* ─────────────────────────────────────────
     SECCIÓN 2 — ALERTAS CONFIGURABLES
  ───────────────────────────────────────── */

  // Actualizar sliders en tiempo real
  window.updateRange = (type) => {
    if (type === 'work') {
      const val = document.getElementById('workRange').value;
      document.getElementById('workVal').textContent  = val + ' min';
      document.getElementById('prev-work').textContent = val + ' min';
      updateCycleBar();
    } else {
      const val = document.getElementById('breakRange').value;
      document.getElementById('breakVal').textContent  = val + ' min';
      document.getElementById('prev-break').textContent = val + ' min';
      updateCycleBar();
    }

    const msg = document.getElementById('customMessage').value.trim();
    document.getElementById('prev-msg').textContent = msg || 'Sin mensaje personalizado';
  };

  // Actualizar barra de ciclo visual
  function updateCycleBar() {
    const work  = parseInt(document.getElementById('workRange').value);
    const brk   = parseInt(document.getElementById('breakRange').value);
    const total = work + brk;
    const wPct  = Math.round((work  / total) * 100);
    const bPct  = Math.round((brk   / total) * 100);
    document.getElementById('cycleWork').style.width  = wPct + '%';
    document.getElementById('cycleBreak').style.width = bPct + '%';
  }

  // Actualizar preview de mensaje al escribir
  document.getElementById('customMessage')?.addEventListener('input', () => {
    const msg = document.getElementById('customMessage').value.trim();
    document.getElementById('prev-msg').textContent = msg || 'Sin mensaje personalizado';
  });

  window.activateCustom = () => {
    const intervalMin = parseInt(document.getElementById('workRange').value);
    const durationMin = parseInt(document.getElementById('breakRange').value);
    const message     = document.getElementById('customMessage').value.trim();

    stopTimerCustom(false);

    state.customInterval    = intervalMin * 60;
    state.customDuration    = durationMin * 60;
    state.customMessage     = message || `Descansa ${durationMin} minuto${durationMin > 1 ? 's' : ''}.`;
    state.customSecondsLeft = intervalMin * 60;
    state.customTotal       = intervalMin * 60;
    state.activeProtocol    = `Personalizado (${intervalMin}/${durationMin} min)`;

    showTimerPanelCustom(true);
    startCustomCountdown();

    addHistoryItem(
      `Alerta personalizada`,
      `Cada ${intervalMin} min — Descanso de ${durationMin} min`,
      'custom'
    );
  };

  function startCustomCountdown() {
    clearInterval(state.customTimer);
    updateCustomDisplay();

    state.customTimer = setInterval(() => {
      state.customSecondsLeft--;
      updateCustomDisplay();

      if (state.customSecondsLeft <= 0) {
        clearInterval(state.customTimer);
        triggerAlert(
          'Tu descanso personalizado',
          state.customMessage,
          state.customDuration,
          () => {
            state.customSecondsLeft = state.customTotal;
            startCustomCountdown();
          }
        );
      }
    }, 1000);
  }

  function updateCustomDisplay() {
    const clock = document.getElementById('timerClockCustom');
    const bar   = document.getElementById('timerBarCustom');
    const next  = document.getElementById('timerNextCustom');
    if (!clock) return;

    clock.textContent = formatTime(state.customSecondsLeft);
    const pct = (state.customSecondsLeft / state.customTotal) * 100;
    bar.style.width = pct + '%';
    next.textContent = 'Próxima alerta en ' + formatTime(state.customSecondsLeft);
  }

  function showTimerPanelCustom(show) {
    const panel = document.getElementById('timerPanelCustom');
    if (show) panel.classList.remove('hidden');
    else panel.classList.add('hidden');
  }

  window.stopTimerCustom = (showFeedback = true) => {
    clearInterval(state.customTimer);
    state.customTimer = null;
    showTimerPanelCustom(false);
    if (showFeedback) {
      addHistoryItem('Alerta personalizada', 'Configuración detenida por el usuario', 'custom');
    }
  };

  /* ─────────────────────────────────────────
     MODAL DE ALERTA / DESCANSO
  ───────────────────────────────────────── */

  function triggerAlert(title, message, durationSec, onComplete) {
    state.totalAlerts++;
    addHistoryItem(title, message, title.includes('personal') ? 'custom' : 'preset');

    // Sonido (Web Audio API)
    playAlertSound();

    // Mostrar modal
    document.getElementById('modalTitle').textContent     = title;
    document.getElementById('modalMsg').textContent       = message;
    document.getElementById('alertModal').classList.remove('hidden');

    state.modalTotal       = durationSec;
    state.modalSecondsLeft = durationSec;
    updateModalDisplay();

    state.modalTimer = setInterval(() => {
      state.modalSecondsLeft--;
      updateModalDisplay();
      if (state.modalSecondsLeft <= 0) {
        clearInterval(state.modalTimer);
        dismissAlert(onComplete);
      }
    }, 1000);

    // guardar callback
    state._onAlertComplete = onComplete;
  }

  function updateModalDisplay() {
    const countdown = document.getElementById('modalCountdown');
    const bar       = document.getElementById('modalBar');
    countdown.textContent = state.modalSecondsLeft;
    const pct = (state.modalSecondsLeft / state.modalTotal) * 100;
    bar.style.width = pct + '%';
  }

  window.dismissAlert = (callback) => {
    clearInterval(state.modalTimer);
    document.getElementById('alertModal').classList.add('hidden');
    state.completedAlerts++;

    const fn = callback || state._onAlertComplete;
    if (typeof fn === 'function') fn();
    state._onAlertComplete = null;
  };

  /* ─────────────────────────────────────────
     SECCIÓN 3 — HISTORIAL
  ───────────────────────────────────────── */

  function addHistoryItem(name, message, type) {
    const item = {
      id:      Date.now(),
      name,
      message,
      type,    // 'preset' | 'custom'
      time:    new Date().toLocaleTimeString('es-EC', { hour:'2-digit', minute:'2-digit' }),
    };
    state.history.unshift(item);

    // Persistir en localStorage (máx. 100 items)
    if (state.history.length > 100) state.history.pop();
    try { localStorage.setItem('eyeguard_history', JSON.stringify(state.history)); } catch(e) {}
  }

  let currentFilter = 'all';

  window.filterHistory = (filter, btn) => {
    currentFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderHistory();
  };

  window.clearHistory = () => {
    state.history = [];
    try { localStorage.removeItem('eyeguard_history'); } catch(e) {}
    renderHistory();
  };

  function renderHistory() {
    const list = document.getElementById('histList');
    const empty = document.getElementById('histEmpty');

    // Actualizar estadísticas
    document.getElementById('statTotal').textContent       = state.history.length;
    document.getElementById('statCompletadas').textContent = state.completedAlerts;
    document.getElementById('statProtocolo').textContent   = state.activeProtocol;
    const mins = Math.floor((Date.now() - state.sessionStart) / 60000);
    document.getElementById('statTiempo').textContent      = mins + ' min';

    // Filtrar
    const filtered = currentFilter === 'all'
      ? state.history
      : state.history.filter(i => i.type === currentFilter);

    // Limpiar items anteriores (mantener el empty)
    list.querySelectorAll('.hist-item').forEach(el => el.remove());

    if (filtered.length === 0) {
      empty.classList.remove('hidden');
      return;
    }

    empty.classList.add('hidden');

    filtered.forEach(item => {
      const div = document.createElement('div');
      div.className = 'hist-item';
      div.innerHTML = `
        <span class="hist-item-dot dot-${item.type}"></span>
        <div class="hist-item-body">
          <div class="hist-item-name">${escapeHtml(item.name)}</div>
          <div class="hist-item-msg">${escapeHtml(item.message)}</div>
        </div>
        <span class="hist-item-time">${item.time}</span>
        <span class="hist-item-badge badge-${item.type}">${item.type === 'preset' ? 'Predeterminada' : 'Personalizada'}</span>
      `;
      list.appendChild(div);
    });
  }

  /* ─────────────────────────────────────────
     UTILIDADES
  ───────────────────────────────────────── */

  function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  function getAlertMessage(presetName) {
    const messages = {
      'Regla 20-20-20':   'Mira a 6 metros de distancia durante 20 segundos.',
      'Pausa 5min/hora':  'Tómate 5 minutos de descanso completo.',
      'Pomodoro Ocular':  'Descansa los ojos 5 minutos, parpadea despacio.',
      'Pausa 15min/2h':   'Descansa 15 minutos, levántate y camina.',
      'Protocolo OMS':    'Realiza una pausa activa de 10 minutos.',
    };
    return messages[presetName] || '¡Es hora de descansar la vista!';
  }

  function playAlertSound() {
    try {
      const ctx  = new (window.AudioContext || window.webkitAudioContext)();
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type      = 'sine';
      osc.frequency.setValueAtTime(520, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.6);
    } catch (e) { /* silencioso si el navegador no soporta */ }
  }

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Inicializar preview del configurable
  updateCycleBar();

});