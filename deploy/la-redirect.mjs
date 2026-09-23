const DESTINATION = "https://jetlag.adalie.me/la";

// Existing installed maps must receive a real service worker, not a redirect
// (browsers reject redirects while updating a service-worker script).
export const migrationWorker = `
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith("jetlag-la-")).map(key => caches.delete(key)));
    await self.registration.unregister();
    const windows = await self.clients.matchAll({type: "window", includeUncontrolled: true});
    await Promise.all(windows.map(client => {
      const url = new URL(client.url);
      return client.navigate(${JSON.stringify(DESTINATION)} + url.pathname + url.search + url.hash);
    }));
  })());
});
`;

export default {
  fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/sw.js") {
      return new Response(migrationWorker, {
        headers: {"Content-Type": "application/javascript", "Cache-Control": "no-store"},
      });
    }
    return Response.redirect(DESTINATION + url.pathname + url.search, 308);
  },
};
