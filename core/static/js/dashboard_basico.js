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

    const totalMin  = parseInt(panel.dataset.interval);  // minutos
    const durMin    = parseInt(panel.dataset.duracion);   // minutos de descanso
    const mensaje   = panel.dataset.mensaje || '¡Hora de descansar!';
    const pid       = panel.dataset.pid || '';
    const totalSec  = totalMin * 60;
    let   remaining = totalSec;

    const clock = document.getElementById(clockId);
    const bar   = document.getElementById(barId);
    const next  = document.getElementById(nextId);

    function tick() {
      remaining--;
      if (clock) clock.textContent = formatTime(remaining);
      if (bar)   bar.style.width   = ((remaining / totalSec) * 100) + '%';
      if (next)  next.textContent  = 'Próxima alerta en ' + formatTime(remaining);

      if (remaining <= 0) {
        clearInterval(handle);
        // Registrar en BD vía fetch (sin recargar la página)
        registrarAlerta(formId, pid);
        // Mostrar modal de descanso
        showModal(mensaje, durMin * 60, () => {
          // Al cerrar el modal, reiniciar el countdown
          remaining = totalSec;
          handle = setInterval(tick, 1000);
        });
      }
    }

    let handle = setInterval(tick, 1000);
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
    // Asignar pid al input oculto si existe
    const hiddenPid = document.getElementById('hiddenPid');
    if (hiddenPid && pid) hiddenPid.value = pid;

    const data = new FormData(form);
    fetch(form.action, { method: 'POST', body: data, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .catch(() => {}); // fallo silencioso, no interrumpe la UX
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

  function closeModal() {
    clearInterval(modalHandle);
    const modal = document.getElementById('alertModal');
    if (modal) modal.classList.add('hidden');
    if (typeof modalCallback === 'function') {
      modalCallback();
      modalCallback = null;
    }
  }

  window.dismissAlert = closeModal;

  /* ──────────────────────────────────────────
     SLIDERS — actualizar valores y preview
  ────────────────────────────────────────── */
  window.updateRange = (type) => {
    if (type === 'work') {
      const val = document.getElementById('workRange')?.value;
      const el  = document.getElementById('workVal');
      const pv  = document.getElementById('prev-work');
      if (el) el.textContent = val + ' min';
      if (pv) pv.textContent = val + ' min';
    } else {
      const val = document.getElementById('breakRange')?.value;
      const el  = document.getElementById('breakVal');
      const pv  = document.getElementById('prev-break');
      if (el) el.textContent = val + ' min';
      if (pv) pv.textContent = val + ' min';
    }
    updateCycleBar();
  };

  document.getElementById('mensaje_custom')?.addEventListener('input', (e) => {
    const pv = document.getElementById('prev-msg');
    if (pv) pv.textContent = e.target.value.trim() || 'Sin mensaje personalizado';
  });

  function updateCycleBar() {
    const work  = parseInt(document.getElementById('workRange')?.value  || 30);
    const brk   = parseInt(document.getElementById('breakRange')?.value || 5);
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