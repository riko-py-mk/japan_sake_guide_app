"""
Google Maps link builders.

A Google Maps URL built from coordinates alone (``?api=1&query=35.70,139.64``) opens
an anonymous dropped pin: no shop name, no photos, no hours, no reviews. Passing the
place's ``place_id`` makes Google Maps open the business page instead, which is what a
user tapping "View on Google Maps" expects to see.

Kept free of third-party imports so it can be unit tested without API clients installed.
"""
from typing import Optional
from urllib.parse import quote_plus


def _place_query(name: str, address: str, lat: float, lng: float) -> str:
    """
    Build the ``query`` part of a Google Maps URL for a place.

    Google resolves the place from ``query_place_id``, but ``query`` is a required
    parameter and is what the user sees while the place loads, so prefer the shop
    name (plus address for disambiguation) over raw coordinates.
    """
    label = " ".join(part for part in (name, address) if part).strip()
    if label:
        return quote_plus(label)
    return f"{lat},{lng}"


def _google_maps_place_url(
    place_id: Optional[str],
    name: str = "",
    address: str = "",
    lat: float = 0,
    lng: float = 0,
    canonical_url: str = "",
) -> str:
    """
    Build a link that opens the PLACE ITSELF in Google Maps (not a dropped pin).

    A coordinates-only URL (``?api=1&query=35.70,139.64``) makes the Google Maps app
    show an anonymous pin with no shop name, photos, hours or reviews. Passing
    ``query_place_id`` makes Maps open the place page for that exact business.

    Args:
        place_id: Google Places ID of the shop - the key to a real place page
        name: Shop name, used as the human-readable query text
        address: Formatted address, appended to the query text for disambiguation
        lat: Latitude, used only when there is no place_id
        lng: Longitude, used only when there is no place_id
        canonical_url: The ``url`` field from Place Details (https://maps.google.com/?cid=...),
                       used as-is when available

    Returns:
        A Google Maps URL that resolves to the place page when possible
    """
    if canonical_url:
        return canonical_url
    if place_id:
        query = _place_query(name, address, lat, lng)
        return f"https://www.google.com/maps/search/?api=1&query={query}&query_place_id={place_id}"
    if lat or lng:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    return ""


def _google_maps_directions_url(
    place_id: Optional[str],
    name: str = "",
    address: str = "",
    lat: float = 0,
    lng: float = 0,
) -> str:
    """
    Build a Google Maps directions link targeting the place itself.

    Args:
        place_id: Google Places ID of the destination
        name: Shop name, used as the human-readable destination text
        address: Formatted address, appended for disambiguation
        lat: Latitude, used only when there is no place_id
        lng: Longitude, used only when there is no place_id

    Returns:
        A Google Maps directions URL, or an empty string if there is nothing to point at
    """
    if place_id:
        destination = _place_query(name, address, lat, lng)
        return (
            f"https://www.google.com/maps/dir/?api=1&destination={destination}"
            f"&destination_place_id={place_id}"
        )
    if lat or lng:
        return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    return ""
