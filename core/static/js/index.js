/* ============================================================
   EyeGuard — index.js
   Lógica interactiva de la pantalla principal
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  const form      = document.getElementById('startForm');
  const btnStart  = document.getElementById('btnStart');
  const nameInput = document.getElementById('username');
  const nameHint  = document.getElementById('nameHint');
  const modeRadios = document.querySelectorAll('input[name="mode"]');

  /* ── Ocultar hint al escribir ── */
  nameInput.addEventListener('input', () => {
    nameHint.classList.remove('visible');
  });

  /* ── Cambiar estilo del botón según modo ── */
  function updateButton() {
    const mode = document.querySelector('input[name="mode"]:checked').value;

    if (mode === 'advanced') {
      btnStart.classList.add('advanced-mode');
      btnStart.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
        Activar cámara e iniciar`;
    } else {
      btnStart.classList.remove('advanced-mode');
      btnStart.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/>
        </svg>
        Iniciar monitoreo`;
    }
  }

  modeRadios.forEach(radio => radio.addEventListener('change', updateButton));

  /* ── Validación antes de enviar ── */
  form.addEventListener('submit', (e) => {
    const name = nameInput.value.trim();

    if (!name) {
      e.preventDefault();
      nameHint.classList.add('visible');
      nameInput.focus();
    }
  });

});