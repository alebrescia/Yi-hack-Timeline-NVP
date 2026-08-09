// Service worker minimale: serve solo a rendere l'app installabile
// ("Aggiungi a schermata Home"). Non mette in cache nulla di proposito,
// perché qui i contenuti (timeline, video, diretta) sono sempre dinamici
// e protetti da autenticazione: la cache offline farebbe più danni che bene.

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
