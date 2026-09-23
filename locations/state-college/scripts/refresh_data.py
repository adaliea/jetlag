"""Download CATA's public timetable and record its provenance."""
import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://catabus.com/wp-content/uploads/google_transit.zip"

if __name__ == "__main__":
    payload = urllib.request.urlopen(SOURCE, timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(payload)) as feed:
        for name in ("stops.txt", "trips.txt", "stop_times.txt", "feed_info.txt"):
            feed.getinfo(name)
    target = ROOT / "data"
    target.mkdir(exist_ok=True)
    (target / "cata-gtfs.zip").write_bytes(payload)
    (target / "source.json").write_text(json.dumps({
        "source": SOURCE,
        "downloaded": datetime.now(timezone.utc).date().isoformat(),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }, indent=2) + "\n")
    print("Downloaded CATA feed. Run npm run build:state-college from the repository root to validate selected service dates.")
