const CACHE_NAME = "jetlag-state-college-__CACHE_VERSION__";
const TILE_CACHE = "jetlag-state-college-tiles-v1";
const MAX_TILE_ENTRIES = 500;
const APP_SHELL = [
  "./",
  "./index.html",
  "./rules.html",
  "./RULES_STATE_COLLEGE.md",
  "./map-data.geojson.json",
  "./station-reference.csv",
  "./station-reference-saturday.csv",
  "./station-reference-sunday.csv",
  "./stop-exclusions.csv",
  "./manifest.webmanifest",
  "./favicon.svg",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
];

async function trimTileCache(cache) {
  const keys = await cache.keys();
  await Promise.all(keys.slice(0, Math.max(0, keys.length - MAX_TILE_ENTRIES)).map(key => cache.delete(key)));
}

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(key => key.startsWith("jetlag-state-college-") && key !== CACHE_NAME && key !== TILE_CACHE)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  const scope = new URL(self.registration.scope);
  // Let other locations handle their own navigation and offline fallback.
  if (url.origin === scope.origin && !url.pathname.startsWith(scope.pathname)) return;

  if (url.hostname === "tile.openstreetmap.org") {
    event.respondWith(
      caches.open(TILE_CACHE).then(cache =>
        cache.match(event.request).then(cached => cached || fetch(event.request).then(response => {
          cache.put(event.request, response.clone());
          trimTileCache(cache);
          return response;
        }))
      )
    );
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then(cached => cached || caches.match("./index.html")))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
      if (url.origin === self.location.origin || url.hostname === "unpkg.com") {
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, response.clone()));
      }
      return response;
    }))
  );
});
