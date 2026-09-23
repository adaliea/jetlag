# Jet Lag: Hide + Seek Los Angeles

An LA-specific small game for the official Jet Lag: The Game Hide + Seek
home game.

## Start here

1. Read [RULES_LA.md](RULES_LA.md).
2. Open [the LA map](https://jetlag.adalie.me/la/).
3. At Union Station, randomly choose the first hiding pair and begin a 40-minute
   hiding period.

The standard game uses Metro Rail stations inside the map as eligible hiding
zone centers. The interactive map shows the agreed game border, current rail
lines, neighborhood divisions, and a 400 m hiding-zone preview for every
eligible station. It also includes opt-in device location, an official-rules
link, an in-map LA special-rules panel, and a rendered full-rules page with
the safety exclusion list. The site is installable as a Home Screen web app
and caches the app plus previously viewed map tiles for offline use.

For an offline lookup table, use
[map/station-reference.csv](map/station-reference.csv).

## Why this differs from the older LA map

The useful core of
[kavigupta/jet-lag-small-game-la](https://github.com/kavigupta/jet-lag-small-game-la)
is retained: a central-LA border, neighborhood/CDP divisions, and a
transit-centered game.

The older map used July 2023 rail data and included 530 multi-line bus stops,
for 581 total hiding centers. This edition uses current Metro Rail data and
keeps the standard game within the official small-game recommendation of
30-100 stations. In particular, it includes the three D Line Extension
Section 1 stations now present in Metro's current feed.

## Rebuild the map

The checked-in map is ready to deploy from the repository root with
`npm run deploy`. No Metro download is needed for a normal website build.

To refresh the LA map, put Metro's extracted rail feed in this location's
`current-gtfs-rail/` directory, and clone the reference geometry into
`reference-old-la-map/`. Run these commands from `locations/la/`:

```bash
curl -fL https://gitlab.com/LACMTA/gtfs_rail/-/raw/master/gtfs_rail.zip -o gtfs_rail.zip
python3 -m zipfile -e gtfs_rail.zip current-gtfs-rail
git clone https://github.com/kavigupta/jet-lag-small-game-la reference-old-la-map
```

Then run `npm run build:la` from the repository root. Review any service and
station changes before deploying. The builder uses the reference project's
hand-drawn central-LA border and neighborhood divisions.

## Preview and deployment

Use `npm run dev` or `npm run preview` from the repository root and open `/la/`.
`npm run deploy` publishes both LA and State College to `jetlag.adalie.me`.
The old `la.jetlag.adalie.me` address redirects here, preserving deep links.
See the [combined project guide](../../README.md) for details.

## Sources

- [Official home-game rules](https://jetlag.denull.ru/en/rules/)
- [LA Metro current rail GTFS](https://gitlab.com/LACMTA/gtfs_rail)
- [Older LA map and source data](https://github.com/kavigupta/jet-lag-small-game-la)
