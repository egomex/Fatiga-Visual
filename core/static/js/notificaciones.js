/* ============================================================
   EyeGuard — notificaciones.js
   Notificaciones nativas del SO para modo básico y avanzado.
   Funciona en localhost sin necesidad de HTTPS ni Service Worker.
   ============================================================ */

const EyeGuardNotif = (() => {

  let permisoOk = false;
  let swRegistration = null;

  /* ─────────────────────────────────────
     INICIALIZAR — pedir permiso al usuario
  ───────────────────────────────────── */
  async function init() {
    if (!('Notification' in window)) {
      console.warn('[EyeGuard] Notificaciones no soportadas.');
      return false;
    }

    if (Notification.permission === 'default') {
      await Notification.requestPermission();
    }

    if (Notification.permission !== 'granted') {
      console.warn('[EyeGuard] Notificaciones bloqueadas.');
      return false;
    }

    permisoOk = true;

    // Si hay Service Worker disponible (requiere HTTPS), registrarlo
    // para que las notificaciones sobresalgan sobre otras apps
    if ('serviceWorker' in navigator) {
      try {
        swRegistration = await navigator.serviceWorker.register(
          '/static/js/service_worker.js'
        );
        console.log('[EyeGuard] Service Worker activo — notificaciones mejoradas.');
      } catch (e) {
        console.log('[EyeGuard] Sin Service Worker (HTTP) — notificaciones básicas.');
      }
    }

    return true;
  }

  /* ─────────────────────────────────────
     MOSTRAR NOTIFICACIÓN NATIVA
  ───────────────────────────────────── */
  async function mostrar({ titulo, cuerpo, tag }) {
    if (!permisoOk) {
      console.warn('[EyeGuard] Sin permiso para notificaciones.');
      return;
    }

    // Con Service Worker (HTTPS): notificación que sobresale sobre otras apps
    if (swRegistration) {
      try {
        const sw = await navigator.serviceWorker.ready;
        sw.active.postMessage({
          type: 'MOSTRAR_NOTIFICACION',
          titulo, cuerpo, tag: tag || 'eyeguard',
        });
        return;
      } catch (e) {}
    }

    // Sin SW (HTTP/localhost): notificación básica del navegador
    const notif = new Notification(titulo, {
      body:               cuerpo,
      tag:                tag || 'eyeguard',
      requireInteraction: true,
    });
    notif.onclick = () => { window.focus(); notif.close(); };
  }

  /* ─────────────────────────────────────
     MÉTODOS ESPECÍFICOS
  ───────────────────────────────────── */
  function alertaFatiga(recomendacion, ear) {
    mostrar({
      titulo: '👁️ EyeGuard — Fatiga visual detectada',
      cuerpo: `EAR: ${ear} · ${recomendacion.slice(0, 120)}`,
      tag:    'fatiga',
    });
  }

  function alertaDescanso(protocolo, mensaje) {
    mostrar({
      titulo: `⏱️ EyeGuard — ${protocolo}`,
      cuerpo: mensaje,
      tag:    'descanso',
    });
  }

  function alertaPersonalizada(mensaje) {
    mostrar({
      titulo: '⏱️ EyeGuard — ¡Hora de descansar!',
      cuerpo: mensaje,
      tag:    'custom',
    });
  }

  return { init, alertaFatiga, alertaDescanso, alertaPersonalizada };

})();

// Inicializar al cargar
document.addEventListener('DOMContentLoaded', () => {
  EyeGuardNotif.init().then(ok => {
    if (ok) console.log('[EyeGuard] Notificaciones activadas.');
  });
});