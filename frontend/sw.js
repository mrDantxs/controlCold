const CACHE_NAME = 'controlcold-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/auth.html',
  '/css/style.css',
  '/css/auth.css',
  '/js/app.js',
  '/js/auth.js',
  '/js/chart-manager.js',
  '/manifest.json'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

// Ativação e limpeza de caches antigos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Interceptação de requisições
self.addEventListener('fetch', (event) => {
  // Ignora requisições de API, queremos dados frescos sempre
  if (event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        // Retorna do cache se encontrar, senão busca na rede
        return cachedResponse || fetch(event.request).then(
          (response) => {
            // Clona a resposta e guarda no cache dinamicamente (opcional)
            // if(!response || response.status !== 200 || response.type !== 'basic') return response;
            return response;
          }
        );
      })
  );
});

// Escuta de Notificações Push
self.addEventListener('push', (event) => {
  let data = {};
  if (event.data) {
    data = event.data.json();
  }

  const title = data.title || "Alerta ControlCold";
  const options = {
    body: data.body || "Nova notificação do sistema térmico.",
    icon: '/assets/icon-192.png',
    badge: '/assets/icon-192.png',
    vibrate: [200, 100, 200, 100, 200, 100, 200],
    data: {
      url: data.url || '/'
    },
    requireInteraction: true // Mantém a notificação na tela até o usuário clicar
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Clique na Notificação Push
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Se já tiver uma aba aberta, foca nela
      for (let client of windowClients) {
        if (client.url === event.notification.data.url && 'focus' in client) {
          return client.focus();
        }
      }
      // Se não, abre uma nova janela
      if (clients.openWindow) {
        return clients.openWindow(event.notification.data.url);
      }
    })
  );
});
