/* ============================================================
   EyeGuard — service_worker.js
   Maneja notificaciones push en segundo plano
   ============================================================ */

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

// Escuchar mensajes desde el JS principal
self.addEventListener('message', (event) => {
  if (event.data?.type === 'MOSTRAR_NOTIFICACION') {
    const { titulo, cuerpo, icono, tag } = event.data;

    event.waitUntil(
      self.registration.showNotification(titulo, {
        body:               cuerpo,
        icon:               icono || '/static/img/icon.png',
        badge:              icono || '/static/img/icon.png',
        tag:                tag || 'eyeguard-alerta',
        requireInteraction: true,   // no desaparece sola hasta que el usuario la toque
        vibrate:            [200, 100, 200],
        actions: [
          { action: 'descansar', title: '✓ Voy a descansar' },
          { action: 'ignorar',   title: 'Ignorar' },
        ],
      })
    );
  }
});

// Click en la notificación → enfocar la ventana del navegador
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'ignorar') return;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Si la app ya está abierta, enfocarla
      for (const client of clientList) {
        if (client.url.includes('dashboard') && 'focus' in client) {
          return client.focus();
        }
      }
      // Si no está abierta, abrirla
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});