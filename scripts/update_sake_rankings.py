#!/usr/bin/env python3
"""
Fetch the current sakenowa.com rankings and write utils/sake_ranking_fallback.json.

Invoked daily by the update-sake-rankings GitHub Actions workflow (05:00 JST).
The Streamlit app reads this pre-built file directly; it makes no live API calls.

Usage:
    python scripts/update_sake_rankings.py [--top-n 50]
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import requests

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"
OUTPUT_PATH = Path(__file__).parent.parent / "utils" / "sake_ranking_fallback.json"
DEFAULT_TOP_N = 50

# Sakenowa flavor-chart fields (f1–f6) mapped to display names
_FLAVOR_KEYS: Dict[str, str] = {
    "Fruity":     "f1",   # フルーティ・華やか
    "Light":      "f2",   # 穏やか・軽快
    "Sweet":      "f3",   # 甘い・まろやか
    "Dry":        "f4",   # 辛口・シャープ
    "Full Body":  "f5",   # どっしり・重厚
    "Aged":       "f6",   # 熟成・複雑
}

_SPARKLING_KEYWORDS = frozenset(
    ["スパークリング", "発泡", "微発泡", "Sparkling", "sparkling", "awa"]
)


def classify_flavor(brand_name: str, flavor_chart: Optional[dict]) -> str:
    """Return the dominant flavor type for a sake brand."""
    if any(kw in brand_name for kw in _SPARKLING_KEYWORDS):
        return "Sparkling"
    if not flavor_chart:
        return "Light"
    scores = {flavor: flavor_chart.get(key, 0) for flavor, key in _FLAVOR_KEYS.items()}
    return max(scores, key=scores.get)


def fetch(url: str, retries: int = 3, timeout: int = 15) -> dict:
    """GET *url* with exponential-backoff retry. Raises on final failure."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = 2 ** attempt          # 1 s, 2 s, 4 s
                print(f"  Retry {attempt + 1} for {url} (waiting {wait}s): {exc}")
                time.sleep(wait)
    raise last_exc


def build_entries(top_n: int) -> List[Dict]:
    """Fetch all required sakenowa endpoints and return a ranked entry list."""
    print("Fetching brands …")
    brands_data = fetch(f"{SAKENOWA_API_BASE}/brands")
    print("Fetching breweries …")
    breweries_data = fetch(f"{SAKENOWA_API_BASE}/breweries")
    print("Fetching areas …")
    areas_data = fetch(f"{SAKENOWA_API_BASE}/areas")
    print("Fetching rankings …")
    rankings_data = fetch(f"{SAKENOWA_API_BASE}/rankings")
    print("Fetching flavor charts …")
    flavors_data = fetch(f"{SAKENOWA_API_BASE}/flavor-charts")

    # --- Structural diagnostics (helps catch API key changes in CI logs) ---
    print(f"  brands      keys={list(brands_data.keys())}  "
          f"first={next(iter(brands_data.get('brands') or brands_data.get('brand') or []), None)}")
    print(f"  breweries   keys={list(breweries_data.keys())}  "
          f"first={next(iter(breweries_data.get('breweries') or breweries_data.get('brewery') or []), None)}")
    print(f"  areas       keys={list(areas_data.keys())}  "
          f"first={next(iter(areas_data.get('areas') or areas_data.get('area') or []), None)}")
    print(f"  flavor-charts keys={list(flavors_data.keys())}  "
          f"first={next(iter(flavors_data.get('flavorChart') or flavors_data.get('flavorCharts') or []), None)}")

    # Brand → breweryId → brewery → areaId → area (two-hop lookup for prefecture)
    brands     = {b["id"]: b for b in (brands_data.get("brands") or brands_data.get("brand") or [])}
    breweries  = {b["id"]: b for b in (breweries_data.get("breweries") or breweries_data.get("brewery") or [])}
    areas      = {a["id"]: a for a in (areas_data.get("areas") or areas_data.get("area") or [])}
    # flavor-charts key is "flavorChart" (singular) in the actual API response
    flavors    = {f["brandId"]: f for f in (flavors_data.get("flavorChart") or flavors_data.get("flavorCharts") or [])}

    # The /rankings response shape is:
    #   { "yearMonth": "YYYYMM", "overall": [{rank, brandId, score}, ...], "areas": [...] }
    # "overall" is a top-level key — NOT a nested rankings array.
    year_month = rankings_data.get("yearMonth", "unknown")
    print(f"Rankings period: {year_month}  (overall entries: {len(rankings_data.get('overall', []))})")

    ranking_list = rankings_data.get("overall", [])
    if not ranking_list:
        # Log the actual keys to aid debugging if the shape changes again
        print(f"DEBUG rankings keys: {list(rankings_data.keys())}", file=sys.stderr)
        raise RuntimeError(
            "No overall ranking data found. "
            f"Available keys: {list(rankings_data.keys())}"
        )

    entries: List[Dict] = []
    for item in ranking_list[:top_n]:
        brand_id = item.get("brandId")
        if brand_id not in brands:
            continue
        brand      = brands[brand_id]
        brewery_id = brand.get("breweryId")
        brewery    = breweries.get(brewery_id, {})
        area_id    = brewery.get("areaId")
        area       = areas.get(area_id, {})
        name       = brand.get("name", f"Sake #{brand_id}")
        prefecture = area.get("name", "不明")

        # Detailed trace for the first entry so CI logs confirm the lookup chain
        if len(entries) == 0:
            print(f"  [trace rank-1] brand={brand}  brewery_id={brewery_id}"
                  f"  brewery={brewery}  area_id={area_id}  area={area}"
                  f"  prefecture={prefecture!r}")

        entries.append({
            "rank":        item.get("rank", 0),
            "brand_id":    brand_id,
            "name":        name,
            "prefecture":  prefecture,
            "flavor_type": classify_flavor(name, flavors.get(brand_id)),
        })

    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Update sake_ranking_fallback.json")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N,
                        help=f"Number of top-ranked sake to fetch (default: {DEFAULT_TOP_N})")
    args = parser.parse_args()

    try:
        entries = build_entries(args.top_n)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    payload = {
        "as_of": date.today().isoformat(),   # e.g. "2026-02-28"
        "entries": entries,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Written {len(entries)} entries to {OUTPUT_PATH}  (as_of {payload['as_of']})")


if __name__ == "__main__":
    main()
