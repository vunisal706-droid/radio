// VicRadio · service worker v2
// - El HTML se pide SIEMPRE primero a la red (así las actualizaciones llegan al móvil).
// - Los iconos y el manifest se sirven desde caché.
// - El audio nunca se cachea (es streaming en directo).
const CACHE = 'vicradio-v5-b2610102004';
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png',
  './favicon.svg'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.allSettled(ASSETS.map((a) => c.add(a))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Nunca tocar los streams de audio ni nada de otro dominio.
  if (req.destination === 'audio') return;
  if (/\.(mp3|aac|m3u8|m3u|ts)(\?|$)/i.test(url.pathname)) return;
  if (url.origin !== self.location.origin) return;

  const isHTML = req.mode === 'navigate' || req.destination === 'document';

  if (isHTML) {
    // Red primero, caché como respaldo sin conexión.
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('./index.html', copy));
          return res;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  // Resto de recursos: caché primero.
  e.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).catch(() => cached))
  );
});
