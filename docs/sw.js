const CACHE_NAME = 'mille-sabords-v1';

const ASSETS = [
  './',
  './index.html',
  './app.js',
  './style.css',
  './vue.esm-browser.prod.js',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './data/default.json',
  './data/coin.json',
  './data/diamond.json',
  './data/animals.json',
  './data/guardian.json',
  './data/pirate.json',
  './data/pirate-ship-2.json',
  './data/pirate-ship-3.json',
  './data/pirate-ship-4.json',
  './data/skull-1.json',
  './data/skull-2.json',
  './data/treasure-island.json',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cached => cached ?? fetch(event.request))
  );
});
