# State College design notes

Updated September 21, 2026.

## Player choices

- Town + campus footprint, using Small-game card values.
- One full day, budget 6–8 hours.
- 2–3 fixed pairs (4–6 players), with all non-hiding pairs seeking together.
- CATA fixed-route buses and walking, during a full-service weekend.
- September 26–27, October 3–4, or later; exact date undecided.

The hiding period is **45 minutes**, interpreting the requested extra five
minutes relative to the LA game's 40-minute period. Other Small-game timers
and card values remain as printed.

Final hiding spots follow the printed rules, with a local exception allowing
indoor common areas open to all students. Every player must be able to enter
legitimately with their own ordinary student access for the whole round.
Classrooms/lecture halls, labs, offices, bathrooms, private residential areas,
and restricted spaces are excluded. Publicly accessible outdoor spots remain
allowed. These choices are recorded in `game-plan.json`.

## Draft map

The expanded draft has **151 Saturday centers and 85 Sunday centers**. It covers
downtown, campus, the Waupelani corridor, North Atherton, and Martin/Vairo.
Following the September 21 user choice, each day includes every stop with
scheduled boarding in the reference window, no recorded closure, and a full
400 m circle inside the border. The former 47-stop handpicked selection and
requirement for service on both days have been removed. Nearby and opposite-
direction stops are distinct centers; no total-count or headway cap is imposed.

This adds 13 Saturday centers named on North Atherton Street, plus eligible
Park Forest, West Aaron Drive, and other previously omitted stops. The smaller
Sunday network produces a separate selection. Gray markers show available
boarding-only stops whose full circles cross the border: 28 on Saturday and
18 on Sunday. Search explains every exclusion, including stops without service
and stops closed by an alert. The selected day also controls the CSV download,
and is kept in the URL for sharing and reloading.

CATA alerts checked September 21 close stops **161, 471, 2004, 384, and 718**.
These overrides apply even when the timetable lists a departure. The Pike Street
construction alert also suspends CC service to Lemont; the reference feed already
has no weekend calls at the affected Pike/Elmwood stops.
[CATA rider alerts](https://catabus.com/rider-tools/riders/rider-alerts/)

The border follows a connected loop of street segments saved in
`data/boundary-streets.geojson`. The original OpenStreetMap way and node data
are saved in `data/boundary-osm.json` (retained sections downloaded September 16;
expanded sections September 19). The builder
assembles the exact coordinates, validates the closed polygon, and clips
routes and municipal polygons to it.

Clockwise from Blue Course Drive / West Whitehall Road: Blue Course Drive →
Circleville Road → Valley Vista Drive → Valley Vista interchange ramps →
I-99 / US 220 / US 322 → Waddle Road interchange ramp → Waddle Road → Toftrees
Avenue → Fox Hollow Road → Orchard Road → Puddintown Road → East College Avenue
→ Elmwood Street → East Branch Road → South Atherton Street → West Branch Road
→ Shingletown Road → Scott Road → West College Avenue → West Whitehall Road.
Interstate and ramp segments are map edges, not pedestrian routes.

The loop encloses about **37.9 km² / 14.6 square miles**, compared with the
previous **30.5 km² / 11.8 square miles**: **7.4 km² (24%) larger**. Both areas
use the same local metric projection; the prior rough estimate was 30.6 km².
The expansion retains every part of the previous area. Road connections require
a larger change than simply moving the old edge 100–200 m: south of Whitehall,
the loop goes around via Scott, Shingletown, and West Branch Roads.

The expansion restores all three previously removed centers:

| Center | Old circle area outside | Old radius shortfall | New center-to-border clearance |
| --- | --- | --- | --- |
| Southgate (411) | ~9% | ~108 m | ~683 m |
| Hearthside (409) | ~5% | ~98 m | ~987 m |
| Williamsburg Square (516) | ~8% | ~197 m | ~513 m |

Every selected center retains its full 400 m zone; the closest current
center-to-border clearance is about 416 m at stop 413. Only blue markers for the
selected day qualify. Small-game values, the 45-minute hiding period, and the
one-day budget remain the agreed settings. The larger number of possible centers
adds choices; the budget is not a guarantee of completing every hiding turn.

The previous road segments are preserved in `data/boundary-streets-44.geojson`.
The preview's comparison toggle shows that old edge in purple dashes, the added
area in green, and the three restored 400 m circles. The red edge is the expanded
draft to review with the group.

Municipal polygons are actual January 2026 Census geography, rechecked on
September 19. Harris township was added to cover approximately 0.61 km² of the
expanded southern area; the four existing municipality geometries match the
latest source. The builder now requires municipal coverage of the entire map.
Exact hiding
locations and pedestrian access still require player review; no in-person
access inspection is claimed.

## Timing and date advice

For two pairs, one 6–8-hour day is a reasonable starting budget. For three,
use close to eight hours and agree how to score an unfinished round. These
are estimates; the map does not impose a custom cap. Small-game values remain
appropriate even if the group later adds a second day for more turns.

October 3 is the preferred candidate Saturday: Penn State plays away on
October 2. September 26 is a home football/Homecoming game, and CATA's campus
loops use detours on home-game Saturdays. A different stop/route map would be
needed for that day. [Penn State schedule](https://gopsusports.com/sports/football/schedule)
[CATA game-day service](https://catabus.com/services-schedules/catabus/game-day-shuttle/)

Sunday has a smaller network: for example, AC has no Sunday service. Centers,
routes, and scheduled waits now change with the Saturday/Sunday selector.
[AC schedule](https://catabus.com/services-schedules/catabus/system-map/as-connector/)

## Research sources and limits

The downloaded CATA feed covers August 17–December 13, 2026, version 20260810.
The source, checksum, and September 14 download date are recorded in
`data/source.json`. A September 21 refresh attempt returned HTTP 403; the
existing feed remains the timetable source, supplemented by the refreshed
closure list. No successful timetable refresh is claimed.
[CATA developer tools](https://catabus.com/developer-tools/)

Reference dates are October 3–4, 10 a.m.–6 p.m. Eastern. Maximum scheduled
boarding gaps among the selected centers are 43 minutes Saturday and 35 minutes
Sunday. These include edge gaps between the analysis-window boundary and the
first/last scheduled departure; they are not real-time estimates or a guarantee
of bus frequency.

The earlier all-network counts in `data/weekend-service.json` are raw boarding
stop IDs before boundary and alert checks. They do not account for the recorded
construction closures. Use the generated daily center CSVs and exclusions CSV
for the game selections and the reasons behind them.
