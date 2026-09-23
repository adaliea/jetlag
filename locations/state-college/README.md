# Jet Lag: Hide + Seek — State College, Pennsylvania

A town-and-campus Small-game companion for **2–3 teams of two**, playing
**one 6–8-hour day** using CATA buses and walking. Use your official cards
and printed rulebooks for the core game.

## Open the map

**Live:** [jetlag.adalie.me/state-college/](https://jetlag.adalie.me/state-college/)
([Saturday](https://jetlag.adalie.me/state-college/?day=saturday) ·
[Sunday](https://jetlag.adalie.me/state-college/?day=sunday)).

The LA map is at [jetlag.adalie.me/la/](https://jetlag.adalie.me/la/).
Both locations share one repository and deployment, with links between maps.

The generated map is at [map/index.html](map/index.html). From the repository
root, run `npm run preview` and open **http://localhost:5174/state-college/**.
The site includes stop search, 400 m circles, municipal boundaries, separate
Saturday/Sunday center and route layers, local rules, daily CSV stop references, opt-in device
location, and Home Screen/offline caching support after an initial online load.
Offline tiles are limited to previously viewed areas.

## Preview over Tailscale

The existing local preview service serves the combined site's `dist/` folder
at **http://100.78.183.107:5174/state-college/**. Run `npm run build` from the
repository root to update it. The host must be on and connected to Tailscale.
The public HTTPS site works independently and supports location and offline
caching without Tailscale.

## Current status and decisions

The map is a **draft for review**, with **151 Saturday centers and 85 Sunday
centers**. Every stop with scheduled boarding during that day's reference window,
no recorded closure, and a full 400 m circle inside the border is included.
Nearby and opposite-direction stops remain separate centers; there is no curated
subset, center-count cap, or automatic exclusion for long headways. Its red
border follows real road geometry around downtown, University Park, the
Waupelani corridor, and Martin Street/Vairo. Tap a red section for its street
name, or expand “Streets around the border” in the sidebar. Each full hiding circle fits within the border.
The expanded road loop includes Southgate (411), Hearthside (409), and
Williamsburg Square (516). It encloses about **37.9 km² / 14.6 square miles**,
compared with 30.5 km² / 11.8 square miles previously: **7.4 km² / 24% larger**.
Open “Expanded border comparison” and enable its overlay to see the previous
border, added area, and restored circles. That old outline is a historical
comparison; the current center selection is generated separately for each day.

Blue markers are that day's hiding centers. Smaller gray markers are available
boarding stops whose full circles cross the border: **28 Saturday / 18 Sunday**.
Closed stops and stops without service are not shown as boarding markers, but
searching any stop shows its status and exclusion reasons. Switching the day
updates the layers, count, search, selected stop, circle, and download link.
The day is stored in the URL, so a shared `?day=sunday` link opens Sunday.
Use the same day on every phone before starting play.

The downloads include daily eligible-center lists, a combined
`station-reference.csv`, and `stop-exclusions.csv` with a reason for every
excluded stop on each day, including stops outside the game area.

The southern edge reaches Scott, Shingletown, and West Branch Roads. The
northwest edge follows I-99 / US 322 and its interchange ramps; those are map
edges, not walking routes. No perimeter walk is required. The full circles at
the restored centers now have approximately 683 m, 987 m, and 513 m of clearance
from their centers to the border, respectively (at least 400 m is required).

Confirmed choices are in [game-plan.json](game-plan.json): **45 minutes to
hide**, with **outdoor spots and indoor common areas open to all students**.
Every player must have legitimate access throughout the round. Classrooms,
lecture halls, labs, offices, bathrooms, private residential areas, and
restricted spaces are excluded. Other Small-game settings follow your printed
rulebooks. Outside Schlow Library is a proposed meeting point.
The precise date, start time, end time, and unfinished-round handling remain
pre-game decisions. A 6–8-hour budget does not guarantee three completed runs.

Local rules are generated from [RULES_STATE_COLLEGE.md](RULES_STATE_COLLEGE.md)
and the configuration, so the map dialog and standalone page remain in sync.
Read the fully rendered [local rules](map/RULES_STATE_COLLEGE.md).

## Weekend service and geography

- Reference dates: **October 3 and 4, 2026**, full-service Saturday and Sunday,
  using a 10 a.m.–6 p.m. Eastern analysis window. These are not chosen play dates.
- Centers need service on the selected day only. Saturday includes 13 centers
  named on North Atherton Street that have no Sunday service in the feed.
  Stops around Park Forest and West Aaron Drive are also included when eligible.
- CATA feed validity: August 17–December 13, 2026. Downloaded September 14.
- Closures checked September 21 exclude **161, 471, 2004, 384, and 718**.
  The builder enforces recorded exclusions even if the feed lists departures.
  A feed refresh on September 21 returned HTTP 403, so the map still uses the
  September 14 feed with its recorded validity period and the updated alerts.
- Full service does not remove football detours. **This map is not a home-game
  Saturday map.** Recheck CATA alerts and the actual date before playing.
- Municipal divisions use Census January 2026 boundaries for State College
  borough and College, Ferguson, Harris, and Patton townships. Harris covers
  part of the expanded southern area.
- Timetable/geometry checks are automated; pedestrian access and specific hiding
  locations have not been inspected in person. The group should review them.

## Build and validation

Run the commands below from the repository root. Python 3.10+ and Shapely build the map. Shapely clips the route and municipal
polygons to the actual street boundary, including its concave sections.
The reviewed CATA ZIP, generated map assets, and municipality inputs are
checked in so builds and tests work from a fresh clone.

```bash
npm run setup:python
npm run build:state-college
npm test
```

`setup:python` creates `.venv` and installs the pinned requirements using the
system Python/pip. The build and test scripts use that virtual environment.

Edit `game-plan.json` for agreed settings, `data/game-area.json` for the selection policy,
`data/boundary-streets.geojson` for the ordered boundary street segments, and
`data/service-overrides.json` for dated closures. The boundary is assembled
from those connected segments; it is never generated from a bounding box.
The previous 44-center outline is preserved in `data/boundary-streets-44.geojson`
for comparison. The builder calculates both areas using the same local metric
projection and verifies that the expansion retains the whole previous area.
The source OpenStreetMap ways and nodes are saved in `data/boundary-osm.json`. Updating a feed
outside the reference dates' validity fails rather than silently showing an
empty or wrong network. Update and review the reference dates as needed.

The builder checks the feed checksum, calendar exceptions, selected boarding
service, municipal membership and coverage, and full-circle containment. It
reports first/last departures and maximum gaps without filtering slow stops.
It clips route/municipal geometry to the border. Tests cover calendar changes,
GTFS times, concave boundaries, preserved polygon holes, exact alignment with
OSM street edges, full inclusion of the previous area, restoration of all three
centers, completeness against every eligible GTFS stop, day-specific exclusions,
boarding restrictions, CSV coverage, and reproducible output.

For an independent comparison of candidate weekends:

```bash
python3 locations/state-college/scripts/inspect_cata.py 2026-09-26 2026-09-27 2026-10-03 2026-10-04
```

The inventory counts raw boarding stops, not approved hiding centers.

## Deployment

The repository-root `npm run deploy` packages and deploys both maps to the
`jetlag` Cloudflare Worker. State College is at `/state-college/`. The former
State College deployment is retired; LA's former address redirects to `/la/`.
See the [combined project guide](../../README.md) for setup and deployment.

## Sources

- [CATA data and provenance](data/source.json)
- [CATA rider alerts and recorded exclusions](data/service-overrides.json)
- [Census municipal data provenance](data/municipalities-source.json)
- [Boundary street geometry](data/boundary-streets.geojson), sourced from
  [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) on September 16 and 19, 2026
- [Design and date notes](STATE_COLLEGE_PLAN.md)
