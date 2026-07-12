/* ============================================================
   EyeGuard — dashboard_basico.js
   Solo UI: countdown visual, modal de descanso, sliders, sonido.
   Toda la lógica de negocio (activar/detener/guardar) está en views.py
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ──────────────────────────────────────────
     COUNTDOWN VISUAL (lee datos del servidor)
  ────────────────────────────────────────── */
  const timerPreset  = document.getElementById('timerPanel');
  const timerCustom  = document.getElementById('timerPanelCustom');

  function startCountdown(panel, clockId, barId, nextId, formId) {
    if (!panel) return;

    const totalMin = parseInt(panel.dataset.interval);
    const durMin   = parseInt(panel.dataset.duracion);
    const mensaje  = panel.dataset.mensaje || '¡Hora de descansar!';
    const pid      = panel.dataset.pid || '';
    const totalSec = totalMin * 60;

    const clock = document.getElementById(clockId);
    const bar   = document.getElementById(barId);
    const next  = document.getElementById(nextId);

    // Usar timestamp para que funcione aunque la pestaña esté oculta
    let inicioMs  = Date.now();
    let handle    = null;
    let disparado = false;

    function tick() {
      const transcurrido = Math.floor((Date.now() - inicioMs) / 1000);
      const remaining    = Math.max(totalSec - transcurrido, 0);

      if (clock) clock.textContent = formatTime(remaining);
      if (bar)   bar.style.width   = ((remaining / totalSec) * 100) + '%';
      if (next)  next.textContent  = 'Próxima alerta en ' + formatTime(remaining);

      if (remaining <= 0 && !disparado) {
        disparado = true;
        clearInterval(handle);
        registrarAlerta(formId, pid);
        // Notificación nativa del SO
        EyeGuardNotif.alertaDescanso(
          panel.dataset.nombre || 'Alerta de descanso',
          mensaje
        );
        showModal(mensaje, durMin * 60, () => {
          // Reiniciar con nuevo timestamp
          inicioMs  = Date.now();
          disparado = false;
          handle    = setInterval(tick, 500);
        });
      }
    }

    // Cada 500ms para más precisión
    handle = setInterval(tick, 500);

    // Al volver a la pestaña, forzar actualización inmediata
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        tick();
      }
    });
  }

  // Iniciar countdown del timer activo si existe
  if (timerPreset) {
    startCountdown(timerPreset, 'timerClock', 'timerBar', 'timerNext', 'formAlertaDisparada');
  }
  if (timerCustom) {
    startCountdown(timerCustom, 'timerClockCustom', 'timerBarCustom', 'timerNextCustom', 'formAlertaDisparada');
  }

  /* ──────────────────────────────────────────
     REGISTRAR ALERTA EN BD (fetch silencioso)
  ────────────────────────────────────────── */
  function registrarAlerta(formId, pid) {
    const form = document.getElementById(formId);
    if (!form) return;

    const hiddenPid = document.getElementById('hiddenPid');
    if (hiddenPid && pid) hiddenPid.value = pid;

    const url  = form.getAttribute('action');
    const data = new FormData(form);

    fetch(url, {
      method:  'POST',
      body:    data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(r => r.json())
    .then(data => {
      // Guardar el ID para marcarlo como completado al cerrar el modal
      if (data.alerta_id) ultimaAlertaId = data.alerta_id;
    })
    .catch(() => {});
  }

  /* ──────────────────────────────────────────
     MODAL DE DESCANSO
  ────────────────────────────────────────── */
  let modalHandle     = null;
  let modalCallback   = null;

  function showModal(mensaje, durationSec, onComplete) {
    const modal     = document.getElementById('alertModal');
    const msgEl     = document.getElementById('modalMsg');
    const countdown = document.getElementById('modalCountdown');
    const bar       = document.getElementById('modalBar');
    if (!modal) return;

    playAlertSound();
    msgEl.textContent     = mensaje;
    modal.classList.remove('hidden');

    let remaining = durationSec;
    if (countdown) countdown.textContent = remaining;
    if (bar)       bar.style.width       = '100%';

    modalCallback = onComplete;
    modalHandle   = setInterval(() => {
      remaining--;
      if (countdown) countdown.textContent = remaining;
      if (bar)       bar.style.width       = ((remaining / durationSec) * 100) + '%';
      if (remaining <= 0) {
        clearInterval(modalHandle);
        closeModal();
      }
    }, 1000);
  }

  // ID de la última alerta registrada (se actualiza al registrar)
  let ultimaAlertaId = null;

  function closeModal() {
    clearInterval(modalHandle);
    const modal = document.getElementById('alertModal');
    if (modal) modal.classList.add('hidden');

    // Marcar como completada en la BD
    marcarCompletada();

    if (typeof modalCallback === 'function') {
      modalCallback();
      modalCallback = null;
    }
  }

  function marcarCompletada() {
    if (!ultimaAlertaId) return;

    // Obtener CSRF del form existente
    const form = document.getElementById('formAlertaDisparada');
    if (!form) return;
    const csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
    if (!csrfInput) return;

    const url  = form.getAttribute('action');
    const data = new FormData();
    data.append('csrfmiddlewaretoken', csrfInput.value);
    data.append('action', 'completar');         // ← action correcto
    data.append('alerta_id', ultimaAlertaId);

    fetch(url, {
      method:  'POST',
      body:    data,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(() => { ultimaAlertaId = null; })
    .catch(() => {});
  }

  window.dismissAlert = closeModal;

  /* ──────────────────────────────────────────
     SLIDERS — actualizar valores y preview
  ────────────────────────────────────────── */
  window.updateRange = (type) => {
    updateCycleBar();
  };

  window.updateNumberInput = (type) => {
    if (type === 'work') {
      const input = document.getElementById('workRange');
      const hint  = document.getElementById('workHint');
      const pv    = document.getElementById('prev-work');
      const val   = parseInt(input?.value);

      if (isNaN(val) || val < 5) {
        if (hint) hint.textContent = 'Mínimo 5 minutos.';
        if (input) input.classList.add('input-error');
      } else if (val > 120) {
        if (hint) hint.textContent = 'Máximo 120 minutos.';
        if (input) input.classList.add('input-error');
      } else {
        if (hint) hint.textContent = '';
        if (input) input.classList.remove('input-error');
        if (pv) pv.textContent = val + ' min';
      }
    } else {
      const input = document.getElementById('breakRange');
      const hint  = document.getElementById('breakHint');
      const pv    = document.getElementById('prev-break');
      const val   = parseInt(input?.value);

      if (isNaN(val) || val < 1) {
        if (hint) hint.textContent = 'Mínimo 1 minuto.';
        if (input) input.classList.add('input-error');
      } else if (val > 30) {
        if (hint) hint.textContent = 'Máximo 30 minutos.';
        if (input) input.classList.add('input-error');
      } else {
        if (hint) hint.textContent = '';
        if (input) input.classList.remove('input-error');
        if (pv) pv.textContent = val + ' min';
      }
    }
    updateCycleBar();
  };

  document.getElementById('mensaje_custom')?.addEventListener('input', (e) => {
    const pv = document.getElementById('prev-msg');
    if (pv) pv.textContent = e.target.value.trim() || 'Sin mensaje personalizado';
  });

  function updateCycleBar() {
    const workInput = document.getElementById('workRange');
    const breakInput = document.getElementById('breakRange');
    const work  = parseInt(workInput?.value  || 30);
    const brk   = parseInt(breakInput?.value || 5);
    const total = work + brk;
    const wPct  = Math.round((work / total) * 100);
    const bPct  = 100 - wPct;
    const cw = document.getElementById('cycleWork');
    const cb = document.getElementById('cycleBreak');
    if (cw) cw.style.width = wPct + '%';
    if (cb) cb.style.width = bPct + '%';
  }

  // Inicializar barra al cargar
  updateCycleBar();

  /* ──────────────────────────────────────────
     MODO AVANZADO — cambiar color del botón
  ────────────────────────────────────────── */
  document.querySelectorAll('input[name="mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const btn = document.getElementById('btnStart');
      if (!btn) return;
      const isAdvanced = radio.value === 'advanced' && radio.checked;
      btn.classList.toggle('advanced-mode', isAdvanced);
    });
  });

  /* ──────────────────────────────────────────
     SONIDO DE ALERTA (Web Audio API)
  ────────────────────────────────────────── */
  function playAlertSound() {
    try {
      const ctx  = new (window.AudioContext || window.webkitAudioContext)();
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(520, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.18, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.6);
    } catch (e) {}
  }

  /* ──────────────────────────────────────────
     UTILIDADES
  ────────────────────────────────────────── */
  function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

});