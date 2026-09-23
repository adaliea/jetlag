"""Summarize dated CATA service for planning; does not select hiding centers."""

import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def seconds(value):
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def read_rows(archive, name):
    if name not in archive.namelist():
        return []
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"))))


def active_services(calendar, exceptions, day):
    key = day.strftime("%Y%m%d")
    weekday = day.strftime("%A").lower()
    active = {r["service_id"] for r in calendar
              if r["start_date"] <= key <= r["end_date"] and r[weekday] == "1"}
    for row in exceptions:
        if row["date"] == key:
            if row["exception_type"] == "1":
                active.add(row["service_id"])
            elif row["exception_type"] == "2":
                active.discard(row["service_id"])
    return active


def inspect(feed, days, start="10:00:00", end="18:00:00"):
    if seconds(start) >= seconds(end):
        raise ValueError("End time must be after start time.")
    with zipfile.ZipFile(feed) as archive:
        info = read_rows(archive, "feed_info.txt")[0]
        calendar = read_rows(archive, "calendar.txt")
        exceptions = read_rows(archive, "calendar_dates.txt")
        routes = {r["route_id"]: r for r in read_rows(archive, "routes.txt")}
        trips = read_rows(archive, "trips.txt")
        times = read_rows(archive, "stop_times.txt")
        if read_rows(archive, "frequencies.txt"):
            raise ValueError("Frequency-based service requires departure expansion.")
    output = {
        "source": "https://catabus.com/wp-content/uploads/google_transit.zip",
        "feed": info, "timezone": "America/New_York",
        "window": {"start": start, "end": end},
        "note": "Raw boarding stops with at least one scheduled departure in the window. "
                "Opposite-direction stops are separate. These are not approved hiding centers "
                "or evidence of adequate all-day service or pedestrian access.",
        "days": [],
    }
    for day in days:
        key = day.strftime("%Y%m%d")
        if not info["feed_start_date"] <= key <= info["feed_end_date"]:
            raise ValueError(f"{day} is outside the feed validity period.")
        services = active_services(calendar, exceptions, day)
        active = {r["trip_id"]: r for r in trips if r["service_id"] in services}
        stops_by_route = defaultdict(set)
        for row in times:
            trip = active.get(row["trip_id"])
            if not trip or row.get("pickup_type", "0") == "1":
                continue
            departure = row["departure_time"] or row["arrival_time"]
            if departure and seconds(start) <= seconds(departure) < seconds(end):
                stops_by_route[trip["route_id"]].add(row["stop_id"])
        output["days"].append({
            "date": day.isoformat(), "weekday": day.strftime("%A"),
            "raw_stop_count": len(set().union(*stops_by_route.values())),
            "routes": [
                {"id": rid, "name": routes[rid]["route_short_name"],
                 "description": routes[rid]["route_long_name"], "stop_count": len(stops)}
                for rid, stops in sorted(stops_by_route.items(),
                    key=lambda item: routes[item[0]]["route_short_name"])
            ],
        })
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dates", nargs="+", type=date.fromisoformat)
    parser.add_argument("--feed", type=Path, default=ROOT / "data/cata-gtfs.zip")
    parser.add_argument("--start", default="10:00:00")
    parser.add_argument("--end", default="18:00:00")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.feed, args.dates, args.start, args.end)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    for day in result["days"]:
        names = ", ".join(r["name"] for r in day["routes"])
        print(f"{day['date']} {day['weekday']}: {day['raw_stop_count']} raw stops; {names}")
