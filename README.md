# Jet Lag: Hide + Seek maps

One repository and website for the Los Angeles and State College home games.
Use your official cards and rulebooks alongside each location's local rules.

**[Choose a location](https://jetlag.adalie.me/)**

| Location | Map | Source and local rules |
| --- | --- | --- |
| State College, PA | [jetlag.adalie.me/state-college/](https://jetlag.adalie.me/state-college/) | [locations/state-college](locations/state-college) |
| Los Angeles, CA | [jetlag.adalie.me/la/](https://jetlag.adalie.me/la/) | [locations/la](locations/la) |

State College has separate Saturday and Sunday center sets. LA retains its
original rail game. Each location has its own rules, map data, downloads,
installable app, and offline cache.

## Repository layout

```text
locations/
  la/              # LA builder, rules, and generated map/
  state-college/   # State College builder, reviewed data, rules, tests, and map/
site/              # Location picker and shared static hosting files
scripts/           # Combined-site packaging
deploy/            # Redirect for the old LA address
dist/              # Generated website; ignored by Git
wrangler.toml      # The jetlag Worker at jetlag.adalie.me
```

The repository preserves the original LA Git history. State College was
imported from the local copy based on commit `d880795`. The GitHub repository
is [adaliea/jetlag](https://github.com/adaliea/jetlag).

## Preview and deploy

Requires Node.js 22+ and Python 3.10+.

```bash
npm ci
npm run build
npm run dev
```

`build` packages the checked-in maps into `dist/la/` and `dist/state-college/`
without downloading or changing transit data. `dev` serves the combined site
with Cloudflare's routing behavior. `npm run preview` provides a simpler
Python HTTP server at http://localhost:5174/.

To publish both maps together:

```bash
npm run deploy
```

Wrangler authentication is required (`npx wrangler login` on a new machine).
The only published files are in `dist/`; raw data and source stay in Git.
Deployment is manual; pushing a commit does not deploy automatically.

## Rebuild map data and run checks

```bash
npm run setup:python
npm run build:state-college
npm test
```

The reviewed CATA feed snapshot is checked in so the State College map and
tests are reproducible from a fresh clone. `npm run refresh:state-college`
downloads a new feed and records its checksum. Review reference dates and
service changes before rebuilding from new data.

`npm run build:la` rebuilds LA when its Metro GTFS and reference geometry
inputs are present. See [the LA guide](locations/la/README.md) for those inputs.
Ordinary site builds and deployments use its checked-in map and need no
transit download. Each map build also repackages the combined site.

`npm test` checks the LA redirect and installed-app migration, plus the State
College schedule, boundary, stop-selection, CSV, and reproducibility checks.

## Previous addresses

- `la.jetlag.adalie.me` and `jetlag-la.dacubeking.workers.dev` permanently
  redirect to `/la/`, preserving paths and query strings. The small legacy
  Worker also updates old installed apps so their service worker does not
  trap them on a cached copy. Its source lives in this repository; deploy it
  with `npm run deploy:la-redirect` after the main site is live.
- The previous `statecollege.jetlag.adalie.me` deployment is retired. Use
  `/state-college/` for State College.
- The main Worker's fallback URL is `https://jetlag.dacubeking.workers.dev/`.

Location navigation uses paths relative to the site root. Preview the combined
site when editing either map. Both public maps use HTTPS; Tailscale is optional.
