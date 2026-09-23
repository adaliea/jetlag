"""Build the State College weekend game map from reviewed inputs and CATA GTFS."""
from collections import defaultdict
from datetime import date
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union

from inspect_cata import active_services, read_rows, seconds
from map_support import (distance_to_boundary_km, geojson_feature, geometry_contains, local_xy,
                         render_markdown, render_rules_page)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'map'


def collection(features):
    return {'type': 'FeatureCollection', 'features': features}


def geometry_parts(geometry, kind):
    """Keep only nonempty parts of the requested dimension after clipping."""
    if geometry.is_empty:
        return []
    if geometry.geom_type == kind:
        return [geometry]
    if hasattr(geometry, 'geoms'):
        return [part for child in geometry.geoms for part in geometry_parts(child, kind)]
    return []


def clip_line(points, boundary):
    clipped = LineString(points).intersection(boundary)
    return [[list(p) for p in part.coords] for part in geometry_parts(clipped, 'LineString')]


def clip_polygons(geometry, boundary):
    clipped = shape(geometry).intersection(boundary)
    return [mapping(part)['coordinates'] for part in geometry_parts(clipped, 'Polygon')]


def load_boundary(area):
    streets = json.loads((ROOT / area['boundary_file']).read_text())
    border = []
    for feature in streets['features']:
        if feature['geometry']['type'] != 'LineString':
            raise ValueError('Boundary streets must be line strings')
        coordinates = feature['geometry']['coordinates']
        if len(coordinates) < 2:
            raise ValueError('Boundary street needs at least two coordinates')
        if border and border[-1] != coordinates[0]:
            raise ValueError(f"Disconnected boundary street: {feature['properties']['name']}")
        border.extend(coordinates if not border else coordinates[1:])
    if not border or border[0] != border[-1]:
        raise ValueError('Boundary streets must form a closed loop')
    polygon = Polygon(border)
    if not polygon.is_valid or polygon.area == 0:
        raise ValueError('Boundary streets must form a simple polygon without crossings')
    return streets, border, polygon


def boundary_comparison(area, boundary_polygon):
    comparison = area['comparison']
    _, previous_ring, previous_polygon = load_boundary(comparison)
    if not boundary_polygon.covers(previous_polygon):
        raise ValueError('Expanded boundary must retain the entire previous game area')
    # Use the same local metric projection for both outlines and their difference.
    def area_km2(polygon):
        return transform(lambda x, y: local_xy((x, y), 40.8), polygon).area
    current_area, previous_area = area_km2(boundary_polygon), area_km2(previous_polygon)
    added = boundary_polygon.difference(previous_polygon)
    return {
        'previous_boundary': geojson_feature('Polygon', [previous_ring], {'name': 'Previous 44-center border'}),
        'added_area': {'type': 'Feature', 'properties': {'name': 'Added area'}, 'geometry': mapping(added)},
        'previous_station_count': comparison['station_count'],
        'restored_stop_ids': comparison['restored_stop_ids'],
        'area_km2': round(current_area, 1), 'previous_area_km2': round(previous_area, 1),
        'added_area_km2': round(current_area - previous_area, 1),
        'increase_percent': round(100 * (current_area / previous_area - 1), 1),
    }


def schedule_for_day(active, times, routes, start, end):
    """Collect every boardable call in the play window, before choosing centers."""
    calls = defaultdict(set)
    served_routes = defaultdict(set)
    used_trips = set()
    for row in times:
        trip = active.get(row['trip_id'])
        if not trip or row.get('pickup_type', '0') == '1':
            continue
        departure = row['departure_time'] or row['arrival_time']
        if not departure:
            raise ValueError(f"Untimed boarding call at stop {row['stop_id']}; resolve it before selecting centers")
        clock = seconds(departure)
        if start <= clock < end:
            calls[row['stop_id']].add(clock)
            served_routes[row['stop_id']].add(trip['route_id'])
            used_trips.add(row['trip_id'])
    schedules = {}
    for stop_id, calls_at_stop in calls.items():
        departures = sorted(calls_at_stop)
        gap = max(b - a for a, b in zip([start] + departures, departures + [end])) / 60
        clock_label = lambda t: f'{t // 3600:02d}:{t % 3600 // 60:02d}'
        schedules[stop_id] = {
            'lines': sorted(routes[r]['route_short_name'] for r in served_routes[stop_id]),
            'departures': len(departures), 'max_gap_minutes': round(gap),
            'first_departure': clock_label(departures[0]),
            'last_departure': clock_label(departures[-1]),
        }
    return schedules, used_trips


def stop_eligibility(inside, clearance_m, service, closure, radius_m):
    reasons = []
    if closure:
        reasons.append(closure)
    if not inside:
        reasons.append('Stop is outside the game border.')
    elif clearance_m < radius_m:
        reasons.append(f'The full {radius_m} m circle crosses the game border.')
    if not service['departures']:
        reasons.append("No scheduled boarding in this day's reference window.")
    return {
        'center': not reasons,
        'boarding': inside and bool(service['departures']) and not bool(closure),
        'reasons': reasons,
    }


def build_data():
    config = json.loads((ROOT / 'game-plan.json').read_text())
    area = json.loads((ROOT / 'data/game-area.json').read_text())
    source = json.loads((ROOT / 'data/source.json').read_text())
    municipalities = json.loads((ROOT / 'data/municipalities.geojson').read_text())
    overrides = json.loads((ROOT / 'data/service-overrides.json').read_text())
    if area['selection'] != 'all-eligible-stops-by-day':
        raise ValueError('Expected automatic selection of all eligible stops by day')
    boundary_streets, border, boundary_polygon = load_boundary(area)
    feed_path = ROOT / 'data/cata-gtfs.zip'
    if hashlib.sha256(feed_path.read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('Feed checksum differs from recorded provenance; refresh the feed.')
    with zipfile.ZipFile(feed_path) as archive:
        info = read_rows(archive, 'feed_info.txt')[0]
        stops = {r['stop_id']: r for r in read_rows(archive, 'stops.txt')}
        routes = {r['route_id']: r for r in read_rows(archive, 'routes.txt')}
        trips = read_rows(archive, 'trips.txt')
        times = read_rows(archive, 'stop_times.txt')
        calendar = read_rows(archive, 'calendar.txt')
        exceptions = read_rows(archive, 'calendar_dates.txt')
        shapes = defaultdict(list)
        for row in read_rows(archive, 'shapes.txt'):
            shapes[row['shape_id']].append((int(row['shape_pt_sequence']),
                [float(row['shape_pt_lon']), float(row['shape_pt_lat'])]))
        if read_rows(archive, 'frequencies.txt'):
            raise ValueError('Expand frequency-based trips before building this feed.')
    shapes = {key: [p for _, p in sorted(points)] for key, points in shapes.items()}
    start, end = (seconds(config['service_window'][key]) for key in ('start', 'end'))
    if start >= end:
        raise ValueError('Service window must end after it starts')
    schedules, line_modes = {}, {}
    for mode, value in config['reference_dates'].items():
        day = date.fromisoformat(value)
        if day.strftime('%A').lower() != mode:
            raise ValueError(f'{value} is not a {mode}')
        if not info['feed_start_date'] <= day.strftime('%Y%m%d') <= info['feed_end_date']:
            raise ValueError(f'{value} is outside feed validity')
        services = active_services(calendar, exceptions, day)
        active = {t['trip_id']: t for t in trips if t['service_id'] in services}
        schedules[mode], used_trips = schedule_for_day(active, times, routes, start, end)
        line_features = []
        seen = set()
        # Show all scheduled route shapes crossing the map, including routes whose
        # only in-area boarding stops cannot fit a full hiding circle.
        for trip_id in sorted(used_trips):
            trip = active[trip_id]
            key = (trip['route_id'], trip['shape_id'])
            if key in seen:
                continue
            seen.add(key)
            route = routes[trip['route_id']]
            for points in clip_line(shapes[trip['shape_id']], boundary_polygon):
                line_features.append(geojson_feature('LineString', points, {
                    'line': route['route_short_name'], 'name': route['route_long_name'],
                    'color': '#' + (route['route_color'] or '567080'),
                }))
        line_modes[mode] = collection(line_features)
    features = []
    for stop_id, stop in sorted(stops.items(), key=lambda item: (item[1]['stop_name'], item[0])):
        if stop.get('location_type', '0') not in ('', '0'):
            continue
        point = [float(stop['stop_lon']), float(stop['stop_lat'])]
        inside = boundary_polygon.contains(Point(point))
        clearance = 1000 * distance_to_boundary_km(point, border)
        containing = [f for f in municipalities['features'] if geometry_contains(point, f['geometry'])]
        if inside and len(containing) != 1:
            raise ValueError(f'Stop {stop_id} has ambiguous municipality membership')
        service = {mode: schedules[mode].get(stop_id, {
            'lines': [], 'departures': 0, 'max_gap_minutes': None,
            'first_departure': None, 'last_departure': None,
        }) for mode in schedules}
        eligibility = {mode: stop_eligibility(inside, clearance, service[mode],
            overrides['excluded_stops'].get(stop_id), config['zone_radius_m']) for mode in schedules}
        features.append(geojson_feature('Point', point, {
            'name': stop['stop_name'], 'stop_id': stop_id,
            'division': containing[0]['properties']['NAME'] if len(containing) == 1 else '',
            'zone_m': config['zone_radius_m'], 'inside_boundary': inside,
            'boundary_clearance_m': round(clearance, 1),
            'service': service, 'eligibility': eligibility,
        }))
    centers = {mode: collection([f for f in features if f['properties']['eligibility'][mode]['center']])
               for mode in schedules}
    if any(not fc['features'] for fc in centers.values()):
        raise ValueError('A reference day has no eligible centers')
    divisions = []
    for feature in municipalities['features']:
        clipped = clip_polygons(feature['geometry'], boundary_polygon)
        if clipped:
            divisions.append(geojson_feature('MultiPolygon', clipped, {'name': feature['properties']['NAME']}))
    coverage = unary_union([shape(f['geometry']) for f in divisions]).buffer(1e-9)
    if not boundary_polygon.difference(coverage).is_empty:
        raise ValueError('Municipality inputs do not cover the entire game area')
    return {'updated': source['downloaded'], 'feed': info, 'reference_dates': config['reference_dates'],
            'alerts_reviewed': overrides['reviewed'], 'alerts_source': overrides['source'],
            'station_counts': {mode: len(fc['features']) for mode, fc in centers.items()},
            'stations': centers, 'stops': collection(features),
            'boundary': geojson_feature('Polygon', [border], {
                'name': 'Boundary streets', 'attribution': '© OpenStreetMap contributors',
                'streets': [f['properties']['name'] for f in boundary_streets['features']]}),
            'boundary_streets': boundary_streets, 'lines': line_modes,
            'boundary_comparison': boundary_comparison(area, boundary_polygon),
            'divisions': collection(divisions), 'config': config}


def write_stop_references(data):
    headings = ['day', 'reference_date', 'stop_id', 'stop', 'municipality', 'eligible_center',
                'available_boarding_in_game', 'exclusion_reasons', 'scheduled_routes',
                'departures', 'first_departure', 'last_departure', 'max_gap_minutes',
                'latitude', 'longitude']
    centers, excluded = [], []
    for mode, day in data['reference_dates'].items():
        for f in data['stops']['features']:
            p = f['properties']
            e, s = p['eligibility'][mode], p['service'][mode]
            row = [mode, day, p['stop_id'], p['name'], p['division'], e['center'], e['boarding'],
                   '; '.join(e['reasons']), ', '.join(s['lines']), s['departures'],
                   s['first_departure'], s['last_departure'], s['max_gap_minutes'],
                   *reversed(f['geometry']['coordinates'])]
            (centers if e['center'] else excluded).append(row)
    files = {'station-reference.csv': centers, 'stop-exclusions.csv': excluded}
    files.update({f'station-reference-{mode}.csv': [r for r in centers if r[0] == mode]
                  for mode in data['reference_dates']})
    for filename, rows in files.items():
        with (OUTPUT / filename).open('w', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n')
            writer.writerow(headings)
            writer.writerows(rows)


def main():
    data = build_data()
    config = data['config']
    pending = []
    if config['hiding_minutes'] is None:
        pending.append('hiding period (30-minute proposal shown)')
    if config['final_hiding_spots'] is None:
        pending.append('indoor/outdoor hiding policy')
    draft = 'Draft map for review. ' + ('Awaiting choices: ' + '; '.join(pending) + '.' if pending else 'Review the boundary and stop centers before your first game.')
    rules = (ROOT / 'RULES_STATE_COLLEGE.md').read_text()
    rules = rules.replace('__HIDING_MINUTES__', str(config['hiding_minutes'] or 30))
    rules = rules.replace('__STATUS__', draft)
    for mode, count in data['station_counts'].items():
        rules = rules.replace('__' + mode.upper() + '_COUNT__', str(count))
    boundary_names = ' → '.join(data['boundary']['properties']['streets'])
    rules = rules.replace('__BOUNDARY_STREETS__', boundary_names)
    hiding_policy = ('Final hiding spots must be outdoors and publicly accessible.'
        if config['final_hiding_spots'] == 'outdoors' else
        'Final hiding spots may be indoors or outdoors if publicly accessible throughout play, as required by your printed rulebook.'
        if config['final_hiding_spots'] == 'indoor-or-outdoor' else
        'Follow your printed hiding-spot rules, with this local access exception: '
        'indoor common areas open to all students are also allowed, provided every player '
        'can enter legitimately using their own ordinary student access throughout the round. '
        'Publicly accessible outdoor spots remain allowed. A building being accessible '
        'does not make every room inside it a valid hiding spot.'
        if config['final_hiding_spots'] == 'student-access-common-areas' else
        'Indoor/outdoor policy is awaiting your choice; do not finalize a hiding spot until the group agrees.')
    rules = rules.replace('__HIDING_POLICY__', hiding_policy)
    template = (ROOT / 'scripts/map-template.html').read_text()
    rendered = template.replace('__MAP_DATA__', json.dumps(data, separators=(',', ':')).replace('<', '\\u003c'))
    rendered = rendered.replace('__RULES_HTML__', render_markdown(rules)).replace('__STATUS__', draft)
    rendered = rendered.replace('__HIDING_MINUTES__', str(config['hiding_minutes'] or 30))
    page = render_rules_page(rules)
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'index.html').write_text(rendered)
    (OUTPUT / 'map-data.geojson.json').write_text(json.dumps(data, indent=2) + '\n')
    (OUTPUT / 'rules.html').write_text(page)
    (OUTPUT / 'RULES_STATE_COLLEGE.md').write_text(rules)
    for name in ['manifest.webmanifest', 'favicon.svg']:
        shutil.copyfile(ROOT / 'scripts' / name, OUTPUT / name)
    write_stop_references(data)
    worker = (ROOT / 'scripts/sw-template.js').read_text()
    version = hashlib.sha256((''.join(p.read_text() for p in sorted(OUTPUT.iterdir()) if p.suffix != '.js') + worker).encode()).hexdigest()[:12]
    (OUTPUT / 'sw.js').write_text(worker.replace('__CACHE_VERSION__', version))
    print(f"Built {len(data['divisions']['features'])} municipalities and separate daily center lists.")
    for mode, count in data['station_counts'].items():
        max_gap = max(f['properties']['service'][mode]['max_gap_minutes'] for f in data['stations'][mode]['features'])
        print(f'{mode}: {count} centers; largest scheduled gap in the reference window: {max_gap} minutes')



if __name__ == '__main__':
    main()
