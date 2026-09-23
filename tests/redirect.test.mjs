import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import redirect, { migrationWorker } from "../deploy/la-redirect.mjs";

test("old LA links preserve paths, queries, and encoded characters", () => {
  for (const path of ["/", "/index.html", "/rules.html", "/station-reference.csv?download=1", "/?q=Union%20Station"]) {
    const response = redirect.fetch(new Request("https://la.jetlag.adalie.me" + path));
    assert.equal(response.status, 308);
    assert.equal(response.headers.get("Location"), "https://jetlag.adalie.me/la" + path);
  }
});

test("installed apps receive a service worker without a cross-origin redirect", async () => {
  const response = redirect.fetch(new Request("https://la.jetlag.adalie.me/sw.js?update=1"));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Content-Type"), "application/javascript");
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal(await response.text(), migrationWorker);
});

test("migration clears only LA caches and moves existing tabs with their full URL", async () => {
  const events = {}, deleted = [], navigated = [];
  let unregistered = false, skipped = false;
  vm.runInNewContext(migrationWorker, {
    URL,
    caches: {
      keys: async () => ["jetlag-la-v1", "jetlag-la-tiles-v1", "jetlag-state-college-v1"],
      delete: async key => deleted.push(key),
    },
    self: {
      addEventListener: (name, callback) => { events[name] = callback; },
      skipWaiting: () => { skipped = true; },
      registration: {unregister: async () => { unregistered = true; }},
      clients: {matchAll: async options => {
        assert.equal(options.includeUncontrolled, true);
        return [{url: "https://la.jetlag.adalie.me/rules.html?view=all#safety", navigate: async url => navigated.push(url)}];
      }},
    },
  });
  events.install();
  let activation;
  events.activate({waitUntil: promise => { activation = promise; }});
  await activation;
  assert.equal(skipped, true);
  assert.equal(unregistered, true);
  assert.deepEqual(deleted, ["jetlag-la-v1", "jetlag-la-tiles-v1"]);
  assert.deepEqual(navigated, ["https://jetlag.adalie.me/la/rules.html?view=all#safety"]);
});
