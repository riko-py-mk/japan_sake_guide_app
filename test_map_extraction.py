#!/usr/bin/env python3
"""
Test script to verify map data extraction works correctly.
"""
import json
import re
from typing import Optional

def extract_map_data(response_text: str) -> Optional[dict]:
    """Extract map data from the agent response."""
    try:
        pattern = r'MAP_DATA_START\s*(.*?)\s*MAP_DATA_END'
        match = re.search(pattern, response_text, re.DOTALL)

        if match:
            json_str = match.group(1).strip()
            map_data = json.loads(json_str)
            print(f"✓ Successfully extracted map data with {len(map_data.get('locations', []))} locations")
            return map_data
        else:
            print("✗ No MAP_DATA markers found in response")
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {str(e)}")
    except Exception as e:
        print(f"✗ General error extracting map data: {str(e)}")

    return None

# Test case 1: Valid map data
test_response_1 = """
大船で日本酒を楽しめるお店を以下にご紹介します。地図も併せてご覧ください。

1. いつまる
   Address: 鎌倉市大船１丁目１９−１２
   Rating: 4.5⭐ (120 reviews)

2. 企久太
   Address: 鎌倉市小町２丁目９−１４ 植山ビル 2F

==================================================
MAP_DATA_START
{
  "search_location": "大船",
  "center_lat": 35.3528,
  "center_lng": 139.5328,
  "locations": [
    {
      "name": "いつまる",
      "address": "鎌倉市大船１丁目１９−１２",
      "lat": 35.3528,
      "lng": 139.5328,
      "rating": 4.5,
      "total_ratings": 120,
      "website": "https://example.com",
      "phone": "0467-12-3456",
      "photos": [],
      "reviews": [],
      "place_id": "ChIJ123"
    }
  ]
}
MAP_DATA_END
==================================================
"""

print("Test 1: Valid map data with markers")
result = extract_map_data(test_response_1)
if result:
    print(f"  Search location: {result.get('search_location')}")
    print(f"  Center: ({result.get('center_lat')}, {result.get('center_lng')})")
    print(f"  Locations: {len(result.get('locations', []))}")
else:
    print("  FAILED: No data extracted")

print("\n" + "="*50 + "\n")

# Test case 2: No map data
test_response_2 = """
日本酒について説明します。日本酒は米と水から作られる醸造酒です。
"""

print("Test 2: Response without map data")
result = extract_map_data(test_response_2)
if result is None:
    print("  ✓ Correctly detected no map data")
else:
    print("  ✗ FAILED: Should not have extracted data")

print("\n" + "="*50 + "\n")

# Test case 3: Map data with whitespace variations
test_response_3 = """
Some text before

==================================================
MAP_DATA_START
{"search_location": "Tokyo", "center_lat": 35.6762, "center_lng": 139.6503, "locations": []}
MAP_DATA_END
==================================================

Some text after
"""

print("Test 3: Map data with different whitespace")
result = extract_map_data(test_response_3)
if result:
    print(f"  ✓ Search location: {result.get('search_location')}")
else:
    print("  ✗ FAILED: No data extracted")

print("\n" + "="*50 + "\n")
print("All tests completed!")
