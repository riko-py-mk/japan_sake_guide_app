#!/usr/bin/env python3
"""
Test script for the Google Maps link builders.

The regression this guards: a link built from coordinates alone opens a nameless
dropped pin in the Google Maps app instead of the shop's own place page.
"""
from utils.maps_links import _google_maps_directions_url, _google_maps_place_url

failures = []


def check(label: str, condition: bool):
    print(f"{'✓' if condition else '✗'} {label}")
    if not condition:
        failures.append(label)


PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"

# 1. A place_id must produce a place-page link, not a coordinate pin
url = _google_maps_place_url(PLACE_ID, name="日本酒バー", address="東京都杉並区", lat=35.700264, lng=139.645778)
check("place_id link carries query_place_id", f"query_place_id={PLACE_ID}" in url)
check("place_id link does not fall back to coordinates", "35.700264,139.645778" not in url)
check("shop name is URL-encoded into the query", "query=%E6%97%A5%E6%9C%AC" in url)

# 2. The canonical Place Details url wins when present
canonical = "https://maps.google.com/?cid=12345"
check(
    "canonical url is used as-is",
    _google_maps_place_url(PLACE_ID, name="X", canonical_url=canonical) == canonical,
)

# 3. Without a place_id, coordinates are the last resort
no_id = _google_maps_place_url(None, name="X", lat=35.7, lng=139.6)
check("coordinates used only without place_id", no_id.endswith("query=35.7,139.6"))
check("no link at all when nothing is known", _google_maps_place_url(None) == "")

# 4. Directions point at the place, not the coordinates
directions = _google_maps_directions_url(PLACE_ID, name="Sake Bar", address="Tokyo", lat=35.7, lng=139.6)
check("directions carry destination_place_id", f"destination_place_id={PLACE_ID}" in directions)
check("directions name the destination", "destination=Sake+Bar+Tokyo" in directions)
check(
    "directions fall back to coordinates without place_id",
    _google_maps_directions_url(None, lat=35.7, lng=139.6) == "https://www.google.com/maps/dir/?api=1&destination=35.7,139.6",
)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s)")
    raise SystemExit(1)
print("All checks passed")
