import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import csv
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_map
from inspect_cata import active_services, seconds, read_rows
from map_support import distance_to_boundary_km, geometry_contains
from shapely.geometry import Point, Polygon, box, shape
from shapely.ops import unary_union


class ServiceTests(unittest.TestCase):
    def test_calendar_additions_and_removals(self):
        calendar = [dict(service_id='normal', start_date='20260101', end_date='20261231', saturday='1')]
        exceptions = [dict(service_id='normal', date='20261003', exception_type='2'),
                      dict(service_id='special', date='20261003', exception_type='1')]
        self.assertEqual(active_services(calendar, exceptions, date(2026, 10, 3)), {'special'})
        self.assertEqual(active_services([], exceptions, date(2026, 10, 3)), {'special'})

    def test_gtfs_time_is_numeric_and_can_pass_midnight(self):
        self.assertLess(seconds('9:05:00'), seconds('10:00:00'))
        self.assertEqual(seconds('25:01:00'), 90060)

    def test_daily_boarding_window_and_pickup_restriction(self):
        routes = {'a': {'route_short_name': 'AC'}}
        trips = {'active': {'route_id': 'a'}}
        calls = [dict(trip_id=trip, stop_id=stop, arrival_time=clock,
                      departure_time=clock, pickup_type=pickup)
                 for trip, stop, clock, pickup in [
                     ('active', 'before', '09:59:59', '0'),
                     ('active', 'start', '10:00:00', '0'),
                     ('active', 'last', '17:59:59', '0'),
                     ('active', 'end', '18:00:00', '0'),
                     ('active', 'dropoff', '12:00:00', '1'),
                     ('inactive', 'wrong_day', '12:00:00', '0')]]
        services, used = build_map.schedule_for_day(trips, calls, routes, 36000, 64800)
        self.assertEqual(set(services), {'start', 'last'})
        self.assertEqual(used, {'active'})

    def test_exclusions_and_long_waits_are_explicit(self):
        sparse_service = {'departures': 1, 'max_gap_minutes': 240}
        accepted = build_map.stop_eligibility(True, 450, sparse_service, None, 400)
        self.assertTrue(accepted['center'])  # No hidden headway or count cap.
        edge = build_map.stop_eligibility(True, 399.9, sparse_service, None, 400)
        self.assertTrue(edge['boarding'])
        self.assertFalse(edge['center'])
        self.assertIn('crosses', edge['reasons'][0])
        closed = build_map.stop_eligibility(True, 450, sparse_service, 'Closed for construction.', 400)
        self.assertFalse(closed['boarding'])
        self.assertFalse(closed['center'])
        unavailable = build_map.stop_eligibility(True, 450, {'departures': 0}, None, 400)
        self.assertFalse(unavailable['center'])
        self.assertFalse(unavailable['boarding'])


class GeometryTests(unittest.TestCase):
    def test_line_clipping_keeps_crossing_with_both_endpoints_outside(self):
        border = box(0, 0, 2, 2)
        self.assertEqual(build_map.clip_line([[-1, 1], [3, 1]], border), [[[0, 1], [2, 1]]])
        self.assertEqual(build_map.clip_line([[-1, -1], [3, -1]], border), [])

    def test_concave_border_excludes_area_inside_its_bounding_box(self):
        border = Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4), (0, 0)])
        self.assertEqual(build_map.clip_line([[-1, 2], [5, 2]], border), [[[0, 2], [1, 2]]])
        clipped = build_map.clip_polygons({'type': 'Polygon', 'coordinates': [
            [[-1, -1], [5, -1], [5, 5], [-1, 5], [-1, -1]]]}, border)
        self.assertTrue(Polygon(clipped[0][0], clipped[0][1:]).equals(border))
        self.assertFalse(border.covers(Point(2, 2)))

    def test_polygon_clipping_preserves_holes(self):
        geometry = {'type': 'Polygon', 'coordinates': [
            [[-1, -1], [3, -1], [3, 3], [-1, 3], [-1, -1]],
            [[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5], [0.5, 0.5]]
        ]}
        clipped = build_map.clip_polygons(geometry, box(0, 0, 2, 2))
        result = Polygon(clipped[0][0], clipped[0][1:])
        self.assertAlmostEqual(result.area, 3)
        self.assertFalse(result.covers(Point(1, 1)))
        self.assertFalse(geometry_contains([1, 1], geometry))
        self.assertTrue(geometry_contains([2.5, 2.5], geometry))


class GeneratedMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'map/map-data.geojson.json').read_text())

    def test_selected_stops_and_weekend_service(self):
        data = self.data
        excluded = json.loads((ROOT / 'data/service-overrides.json').read_text())['excluded_stops']
        for day in ('saturday', 'sunday'):
            features = data['stations'][day]['features']
            actual = [f['properties']['stop_id'] for f in features]
            self.assertEqual(len(actual), len(set(actual)))
            self.assertEqual(data['station_counts'][day], len(actual))
            self.assertFalse(set(actual) & set(excluded))
            for f in features:
                point = f['geometry']['coordinates']
                self.assertTrue(shape(data['boundary']['geometry']).contains(Point(point)))
                self.assertGreaterEqual(distance_to_boundary_km(point, data['boundary']['geometry']['coordinates'][0]), 0.4)
                service = f['properties']['service'][day]
                self.assertGreater(service['departures'], 0)
                self.assertTrue(f['properties']['eligibility'][day]['center'])
                self.assertFalse(any('Gameday' in name for name in service['lines']))

    def test_every_available_stop_is_included_independently_for_each_day(self):
        data = self.data
        excluded = json.loads((ROOT / 'data/service-overrides.json').read_text())['excluded_stops']
        polygon = shape(data['boundary']['geometry'])
        ring = data['boundary']['geometry']['coordinates'][0]
        with zipfile.ZipFile(ROOT / 'data/cata-gtfs.zip') as feed:
            stops = read_rows(feed, 'stops.txt')
            trips = read_rows(feed, 'trips.txt')
            times = read_rows(feed, 'stop_times.txt')
            calendar = read_rows(feed, 'calendar.txt')
            exceptions = read_rows(feed, 'calendar_dates.txt')
        for day, value in data['reference_dates'].items():
            services = active_services(calendar, exceptions, date.fromisoformat(value))
            active = {t['trip_id'] for t in trips if t['service_id'] in services}
            boarding = {t['stop_id'] for t in times if t['trip_id'] in active
                        and t.get('pickup_type', '0') != '1'
                        and (t['departure_time'] or t['arrival_time'])
                        and 36000 <= seconds(t['departure_time'] or t['arrival_time']) < 64800}
            expected = set()
            for stop in stops:
                p = [float(stop['stop_lon']), float(stop['stop_lat'])]
                if (stop.get('location_type', '0') in ('', '0') and stop['stop_id'] in boarding
                        and stop['stop_id'] not in excluded and polygon.contains(Point(p))
                        and distance_to_boundary_km(p, ring) >= 0.4):
                    expected.add(stop['stop_id'])
            actual = {f['properties']['stop_id'] for f in data['stations'][day]['features']}
            self.assertEqual(actual, expected)
        saturday = {f['properties']['stop_id'] for f in data['stations']['saturday']['features']}
        sunday = {f['properties']['stop_id'] for f in data['stations']['sunday']['features']}
        self.assertIn('420', saturday)  # North Atherton at Arbor Way.
        self.assertNotIn('420', sunday)
        self.assertTrue({'15', '16', '493', '495'} <= saturday & sunday)
        self.assertTrue({'520', '521'} <= saturday)  # Nearby stops are not merged.

    def test_daily_csvs_and_exclusion_reasons_cover_all_stops(self):
        all_ids = {f['properties']['stop_id'] for f in self.data['stops']['features']}
        with (ROOT / 'map/stop-exclusions.csv').open() as stream:
            excluded = list(csv.DictReader(stream))
        for day in ('saturday', 'sunday'):
            with (ROOT / f'map/station-reference-{day}.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            center_ids = {r['stop_id'] for r in rows}
            self.assertEqual(center_ids, {f['properties']['stop_id'] for f in self.data['stations'][day]['features']})
            self.assertTrue(all(r['day'] == day and r['eligible_center'] == 'True' for r in rows))
            day_exclusions = [r for r in excluded if r['day'] == day]
            self.assertEqual(center_ids | {r['stop_id'] for r in day_exclusions}, all_ids)
            self.assertFalse(center_ids & {r['stop_id'] for r in day_exclusions})
            self.assertTrue(all(r['exclusion_reasons'] for r in day_exclusions))

    def test_boundary_follows_connected_osm_street_edges(self):
        source = json.loads((ROOT / 'data/boundary-osm.json').read_text())
        nodes = {n['id']: [n['lon'], n['lat']] for n in source['elements'] if n['type'] == 'node'}
        ways = {w['id']: w for w in source['elements'] if w['type'] == 'way'}
        streets = json.loads((ROOT / 'data/boundary-streets.geojson').read_text())
        ring = []
        for feature in streets['features']:
            props = feature['properties']
            coordinates = feature['geometry']['coordinates']
            self.assertEqual(coordinates, [nodes[n] for n in props['osm_node_ids']])
            edges = {frozenset((a, b)) for wid in props['osm_way_ids']
                     for a, b in zip(ways[wid]['nodes'], ways[wid]['nodes'][1:])}
            for a, b in zip(props['osm_node_ids'], props['osm_node_ids'][1:]):
                self.assertIn(frozenset((a, b)), edges)
            if ring:
                self.assertEqual(ring[-1], coordinates[0])
            ring.extend(coordinates if not ring else coordinates[1:])
        self.assertEqual(ring[0], ring[-1])
        self.assertTrue(Polygon(ring).is_valid)
        self.assertEqual(self.data['boundary']['geometry']['coordinates'][0], ring)
        self.assertGreater(len(ring), 100)

    def test_route_and_municipal_layers_are_clipped_to_street_border(self):
        border = shape(self.data['boundary']['geometry']).buffer(1e-10)
        layers = [self.data['divisions'], *self.data['lines'].values()]
        for layer in layers:
            for feature in layer['features']:
                geometry = shape(feature['geometry'])
                self.assertTrue(geometry.is_valid)
                self.assertTrue(geometry.difference(border).is_empty)
        coverage = unary_union([shape(f['geometry']) for f in self.data['divisions']['features']]).buffer(1e-9)
        self.assertTrue(shape(self.data['boundary']['geometry']).difference(coverage).is_empty)

    def test_expansion_retains_previous_area_and_restores_three_centers(self):
        data = self.data
        comparison = data['boundary_comparison']
        current = shape(data['boundary']['geometry'])
        previous = shape(comparison['previous_boundary']['geometry'])
        added = shape(comparison['added_area']['geometry'])
        self.assertTrue(current.covers(previous))
        self.assertTrue(added.equals(current.difference(previous)))
        self.assertGreater(added.area, 0)
        self.assertEqual(comparison['previous_station_count'], 44)
        self.assertEqual(set(comparison['restored_stop_ids']), {'411', '409', '516'})
        restored = [f for f in data['stops']['features']
                    if f['properties']['stop_id'] in comparison['restored_stop_ids']]
        self.assertEqual(len(restored), 3)
        for f in restored:
            p = f['geometry']['coordinates']
            self.assertLess(distance_to_boundary_km(p, list(previous.exterior.coords)), 0.4)
            self.assertGreaterEqual(distance_to_boundary_km(p, list(current.exterior.coords)), 0.4)
            self.assertTrue(all(f['properties']['eligibility'][day]['center'] for day in data['reference_dates']))

    @unittest.skipUnless((ROOT / 'data/cata-gtfs.zip').exists(), 'Download source feed to check reproducibility')
    def test_build_reproduces_checked_in_files(self):
        original = build_map.OUTPUT
        try:
            with tempfile.TemporaryDirectory() as temp:
                build_map.OUTPUT = Path(temp)
                build_map.main()
                for path in Path(temp).iterdir():
                    self.assertEqual(path.read_bytes(), (ROOT / 'map' / path.name).read_bytes(), path.name)
        finally:
            build_map.OUTPUT = original


if __name__ == '__main__':
    unittest.main()
