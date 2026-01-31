"""
Tools for the Japanese Sake Guide Agent.

This module provides tools for searching sake information from:
- Sake ranking websites (sakenowa.com, saketime.jp)
- General web search via Tavily
- Social media content via Tavily web search
- Location-based searches for sake shops and restaurants using Google Places API
"""
from typing import Optional, List, Callable, Dict, Any
import json
from langchain_core.tools import tool
from tavily import TavilyClient
import googlemaps
from googlemaps.exceptions import ApiError


def _is_japanese(text: str) -> bool:
    """
    Check if the text contains Japanese characters.

    Args:
        text: Text to check

    Returns:
        True if the text contains Japanese characters
    """
    for char in text:
        if (
            '\u3040' <= char <= '\u309f' or  # Hiragana
            '\u30a0' <= char <= '\u30ff' or  # Katakana
            '\u4e00' <= char <= '\u9fff'     # CJK Unified Ideographs (Kanji)
        ):
            return True
    return False


def _sanitize_hashtag(text: str) -> str:
    """
    Convert text to a valid hashtag format.

    Args:
        text: Text to convert to hashtag

    Returns:
        Sanitized hashtag string (without #)
    """
    # Remove spaces and special characters, keep Japanese characters
    sanitized = ""
    for char in text:
        if char.isalnum() or (
            '\u3040' <= char <= '\u309f' or  # Hiragana
            '\u30a0' <= char <= '\u30ff' or  # Katakana
            '\u4e00' <= char <= '\u9fff'     # Kanji
        ):
            sanitized += char
    return sanitized.lower()


def create_sake_tools(
    tavily_api_key: str,
    instagram_access_token: Optional[str] = None,  # Kept for backward compatibility, not used
    google_maps_api_key: Optional[str] = None,
) -> List[Callable]:
    """
    Create tools for the sake guide agent with API keys bound.

    Args:
        tavily_api_key: API key for Tavily search
        instagram_access_token: Deprecated, kept for backward compatibility
        google_maps_api_key: API key for Google Maps and Places API

    Returns:
        List of tool functions ready to use with LangGraph
    """
    tavily_client = TavilyClient(api_key=tavily_api_key)
    gmaps_client = googlemaps.Client(key=google_maps_api_key) if google_maps_api_key else None

    @tool
    def search_sake_rankings(query: str) -> str:
        """
        Search for sake recommendations from ranking websites like sakenowa.com and saketime.jp.
        Use this tool when users ask for sake recommendations, popular sake, or highly-rated sake.

        Args:
            query: Search query about sake recommendations (e.g., "best fruity sake", "top daiginjo", "人気の純米大吟醸")

        Returns:
            Sake ranking information and recommendations from trusted sources.
        """
        is_japanese = _is_japanese(query)

        if is_japanese:
            enhanced_query = f"日本酒 ランキング おすすめ {query}"
        else:
            enhanced_query = f"Japanese sake ranking recommendation {query}"

        try:
            results = tavily_client.search(
                query=enhanced_query,
                search_depth="advanced",
                max_results=8,
                include_domains=["sakenowa.com", "saketime.jp"],
                include_answer=True,
            )

            output = []
            if results.get("answer"):
                output.append(f"Summary: {results['answer']}\n")

            output.append("Ranking Sources Found:")
            for idx, result in enumerate(results.get("results", []), 1):
                output.append(f"\n{idx}. {result.get('title', 'No title')}")
                output.append(f"   URL: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 500:
                        content = content[:500] + "..."
                    output.append(f"   Content: {content}")

            return "\n".join(output) if output else "No ranking information found."

        except Exception as e:
            return f"Error searching sake rankings: {str(e)}"

    @tool
    def search_sake_info(sake_name: str, additional_query: str = "") -> str:
        """
        Search for detailed information about a specific sake brand or brewery.
        Use this tool when users ask about a specific sake by name.

        Args:
            sake_name: Name of the sake to search for (e.g., "Dassai", "獺祭", "Kubota Manju")
            additional_query: Additional search terms (e.g., "tasting notes", "food pairing")

        Returns:
            Detailed information about the specified sake.
        """
        is_japanese = _is_japanese(sake_name)

        if is_japanese:
            search_query = f"日本酒 {sake_name} {additional_query} 特徴 味わい 蔵元"
        else:
            search_query = f"Japanese sake {sake_name} {additional_query} tasting notes brewery review"

        try:
            results = tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=6,
                include_answer=True,
            )

            output = []
            if results.get("answer"):
                output.append(f"Overview: {results['answer']}\n")

            output.append("Detailed Information:")
            for idx, result in enumerate(results.get("results", []), 1):
                output.append(f"\n{idx}. {result.get('title', 'No title')}")
                output.append(f"   Source: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 600:
                        content = content[:600] + "..."
                    output.append(f"   Details: {content}")

            return "\n".join(output) if output else "No detailed information found."

        except Exception as e:
            return f"Error searching sake info: {str(e)}"

    @tool
    def search_social_media_hashtag(hashtag: str, platforms: str = "all") -> str:
        """
        Search for social media content by hashtag related to Japanese sake.
        Searches Twitter/X, Instagram, and Facebook for posts with the specified hashtag.

        Args:
            hashtag: Hashtag to search for (with or without #). Examples: "日本酒", "sake", "獺祭", "dassai"
            platforms: Which platforms to search: "all", "twitter", "instagram", "facebook", or comma-separated like "twitter,instagram"

        Returns:
            Social media content found with the specified hashtag.
        """
        # Clean up the hashtag
        clean_hashtag = hashtag.lstrip('#')
        sanitized_hashtag = _sanitize_hashtag(clean_hashtag)

        results = []
        platform_list = [p.strip().lower() for p in platforms.split(",")] if platforms != "all" else ["twitter", "instagram", "facebook"]

        # Build domain list based on platforms
        include_domains = []
        if "twitter" in platform_list or "x" in platform_list:
            include_domains.extend(["twitter.com", "x.com"])
        if "instagram" in platform_list:
            include_domains.append("instagram.com")
        if "facebook" in platform_list:
            include_domains.append("facebook.com")

        is_japanese = _is_japanese(clean_hashtag)
        if is_japanese:
            search_query = f"#{sanitized_hashtag} 日本酒 sake"
        else:
            search_query = f"#{sanitized_hashtag} Japanese sake 日本酒"

        try:
            search_results = tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=10,
                include_domains=include_domains if include_domains else None,
                include_answer=True,
            )

            if search_results.get("answer"):
                results.append(f"Summary: {search_results['answer']}")

            results.append(f"\nSocial media content for #{sanitized_hashtag}:")
            results.append("-" * 50)

            for idx, result in enumerate(search_results.get("results", []), 1):
                results.append(f"\n{idx}. {result.get('title', 'No title')}")
                results.append(f"   URL: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 300:
                        content = content[:300] + "..."
                    results.append(f"   Content: {content}")

            if len(results) <= 3:  # Only header lines
                return f"No social media content found for hashtag #{sanitized_hashtag}."

            return "\n".join(results)

        except Exception as e:
            return f"Error searching social media: {str(e)}"

    @tool
    def search_twitter_sake(query: str) -> str:
        """
        Search Twitter/X for posts about Japanese sake.
        Use this tool to find discussions, reviews, and trends about sake on Twitter/X.

        Args:
            query: Search query for Twitter/X (e.g., "獺祭", "dassai sake", "日本酒 おすすめ")

        Returns:
            Posts about the specified sake or topic from Twitter/X.
        """
        is_japanese = _is_japanese(query)
        if is_japanese:
            search_query = f"{query} 日本酒 site:twitter.com OR site:x.com"
        else:
            search_query = f"{query} sake 日本酒 site:twitter.com OR site:x.com"

        try:
            results = []
            results.append(f"Twitter/X search results for: {query}")
            results.append("-" * 50)

            search_results = tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=10,
                include_domains=["twitter.com", "x.com"],
                include_answer=True,
            )

            if search_results.get("answer"):
                results.append(f"Summary: {search_results['answer']}\n")

            for idx, result in enumerate(search_results.get("results", []), 1):
                results.append(f"\n{idx}. {result.get('title', 'No title')}")
                results.append(f"   URL: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 300:
                        content = content[:300] + "..."
                    results.append(f"   Content: {content}")

            if len(results) <= 2:  # Only header lines
                return f"No Twitter/X posts found for '{query}'."

            return "\n".join(results)

        except Exception as e:
            return f"Error searching Twitter/X: {str(e)}"

    @tool
    def search_instagram_sake(sake_name: str) -> str:
        """
        Search for Instagram posts about a specific sake.
        Use this tool to find visual content, reviews, and photos about sake on Instagram.

        Args:
            sake_name: Name of the sake to search for on Instagram (e.g., "獺祭", "Dassai", "日本酒")

        Returns:
            Instagram posts and content about the specified sake.
        """
        sanitized_name = _sanitize_hashtag(sake_name)
        is_japanese = _is_japanese(sake_name)

        if is_japanese:
            search_query = f"{sake_name} #{sanitized_name} 日本酒 site:instagram.com"
        else:
            search_query = f"{sake_name} #{sanitized_name} Japanese sake site:instagram.com"

        try:
            results = []
            results.append(f"Instagram content for '{sake_name}':")
            results.append("-" * 50)

            search_results = tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=10,
                include_domains=["instagram.com"],
                include_answer=True,
            )

            if search_results.get("answer"):
                results.append(f"Summary: {search_results['answer']}\n")

            for idx, result in enumerate(search_results.get("results", []), 1):
                results.append(f"\n{idx}. {result.get('title', 'No title')}")
                results.append(f"   URL: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 300:
                        content = content[:300] + "..."
                    results.append(f"   Content: {content}")

            if len(results) <= 2:  # Only header lines
                return f"No Instagram content found for '{sake_name}'."

            return "\n".join(results)

        except Exception as e:
            return f"Error searching Instagram: {str(e)}"

    @tool
    def search_restaurants_with_sake(sake_name: str, location: str = "Tokyo") -> str:
        """
        Search for restaurants, izakayas, or bars that serve a specific sake brand using Google Places API.
        Returns location data with photos and reviews that can be displayed on a map.

        Use this tool when users ask about where to drink or find a specific sake brand (e.g., "写楽", "獺祭", "Dassai").

        Args:
            sake_name: Name of the sake brand to search for (e.g., "写楽", "獺祭", "Dassai", "Kubota")
            location: City, region, or area to search (e.g., "Tokyo", "Kyoto", "東京", "京都"). Defaults to Tokyo.

        Returns:
            JSON string with restaurant information including names, addresses, coordinates, photos, and reviews for map display.
        """
        if not gmaps_client:
            return "Google Maps API key not configured. Please add GOOGLE_MAPS_API_KEY to your secrets."

        is_japanese = _is_japanese(sake_name)

        try:
            print(f"DEBUG: search_restaurants_with_sake called with sake_name='{sake_name}', location='{location}'")

            # Geocode the location to get coordinates
            print(f"DEBUG: Geocoding location: {location}")
            geocode_result = gmaps_client.geocode(location)
            if not geocode_result:
                error_msg = f"Could not find location: {location}. Please try a different search term."
                print(f"DEBUG: {error_msg}")
                return error_msg

            center_location = geocode_result[0]['geometry']['location']
            lat, lng = center_location['lat'], center_location['lng']
            print(f"DEBUG: Geocoded to ({lat}, {lng})")

            output = []
            locations_data = []

            if is_japanese:
                output.append(f"{location}で{sake_name}を提供しているお店をご紹介します:")
            else:
                output.append(f"Restaurants serving {sake_name} in {location}:")
            output.append("-" * 50)

            # Build search keywords for specific sake brand
            search_keywords = []
            if is_japanese:
                # Japanese queries
                search_keywords.extend([
                    f"{sake_name} 居酒屋",
                    f"{sake_name} 日本酒バー",
                    f"{sake_name} レストラン",
                    f"{sake_name} 日本酒",
                ])
            else:
                # English queries
                search_keywords.extend([
                    f"{sake_name} sake restaurant",
                    f"{sake_name} izakaya",
                    f"{sake_name} sake bar",
                    f"{sake_name} Japanese restaurant",
                ])

            print(f"DEBUG: Searching with {len(search_keywords)} keywords: {search_keywords}")

            # Search for places using Places API Text Search (better for specific sake names)
            all_places = []
            api_errors = []
            for keyword in search_keywords:
                try:
                    print(f"DEBUG: Searching for keyword: {keyword}")
                    # Use text search instead of nearby search for better results with sake names
                    places_result = gmaps_client.places(
                        query=keyword,
                        location=(lat, lng),
                        radius=10000,  # 10km radius
                        language='ja' if is_japanese else 'en'
                    )
                    num_results = len(places_result.get('results', []))
                    print(f"DEBUG: Found {num_results} results for '{keyword}'")
                    all_places.extend(places_result.get('results', []))
                except Exception as e:
                    error_detail = f"Error searching for '{keyword}': {str(e)}"
                    print(f"DEBUG: {error_detail}")
                    api_errors.append(error_detail)
                    continue

            print(f"DEBUG: Total places found before deduplication: {len(all_places)}")

            if not all_places and api_errors:
                # All API calls failed
                error_summary = "\n".join(api_errors[:3])  # Show first 3 errors
                return f"Google Maps API error while searching for locations:\n{error_summary}\n\nPlease check:\n1. Places API is enabled in Google Cloud Console\n2. Your API key has access to Places API\n3. Billing is enabled for your Google Cloud project"

            # Remove duplicates based on place_id
            seen_ids = set()
            unique_places = []
            for place in all_places:
                place_id = place.get('place_id')
                if place_id and place_id not in seen_ids:
                    seen_ids.add(place_id)
                    unique_places.append(place)

            print(f"DEBUG: Unique places after deduplication: {len(unique_places)}")

            # Limit to top 10 places
            unique_places = unique_places[:10]
            print(f"DEBUG: Processing top {len(unique_places)} places")

            # Fetch detailed information for each place
            for idx, place in enumerate(unique_places, 1):
                place_id = place.get('place_id')
                name = place.get('name', 'Unknown')
                address = place.get('formatted_address', '')

                # Get place details including photos and reviews
                try:
                    place_details = gmaps_client.place(
                        place_id=place_id,
                        fields=['name', 'formatted_address', 'geometry', 'rating', 'user_ratings_total',
                                'photos', 'reviews', 'website', 'formatted_phone_number', 'opening_hours', 'url']
                    ).get('result', {})

                    # Extract information
                    full_address = place_details.get('formatted_address', address)
                    rating = place_details.get('rating', 0)
                    total_ratings = place_details.get('user_ratings_total', 0)
                    website = place_details.get('website', '')
                    phone = place_details.get('formatted_phone_number', '')
                    google_maps_url = place_details.get('url', '')
                    location_coords = place_details.get('geometry', {}).get('location', {'lat': 0, 'lng': 0})

                    # Extract photos (up to 3)
                    photos = []
                    photos_data = place_details.get('photos', [])[:3]
                    for photo in photos_data:
                        photo_ref = photo.get('photo_reference')
                        if photo_ref:
                            photos.append({
                                'photo_reference': photo_ref,
                                'width': photo.get('width', 400),
                                'height': photo.get('height', 400)
                            })

                    # Extract reviews (up to 3)
                    reviews = []
                    reviews_data = place_details.get('reviews', [])[:3]
                    for review in reviews_data:
                        reviews.append({
                            'author': review.get('author_name', 'Anonymous'),
                            'rating': review.get('rating', 0),
                            'text': review.get('text', '')[:200],  # Limit review length
                            'time': review.get('relative_time_description', '')
                        })

                    # Add to output
                    output.append(f"\n{idx}. {name}")
                    output.append(f"   Address: {full_address}")
                    if rating > 0:
                        output.append(f"   Rating: {rating}⭐ ({total_ratings} reviews)")
                    if website:
                        output.append(f"   Website: {website}")
                    if google_maps_url:
                        output.append(f"   Google Maps: {google_maps_url}")
                    if phone:
                        output.append(f"   Phone: {phone}")

                    # Store location data for map
                    locations_data.append({
                        "name": name,
                        "address": full_address,
                        "lat": location_coords['lat'],
                        "lng": location_coords['lng'],
                        "rating": rating,
                        "total_ratings": total_ratings,
                        "website": website,
                        "phone": phone,
                        "google_maps_url": google_maps_url,
                        "photos": photos,
                        "reviews": reviews,
                        "place_id": place_id,
                        "sake_name": sake_name
                    })

                except Exception as e:
                    # If detailed fetch fails, use basic info
                    output.append(f"\n{idx}. {name}")
                    output.append(f"   Address: {address}")

                    locations_data.append({
                        "name": name,
                        "address": address,
                        "lat": place.get('geometry', {}).get('location', {}).get('lat', 0),
                        "lng": place.get('geometry', {}).get('location', {}).get('lng', 0),
                        "rating": place.get('rating', 0),
                        "place_id": place_id,
                        "sake_name": sake_name
                    })

            # Check if we found any locations
            if not locations_data:
                print("DEBUG: No locations found to display")
                if is_japanese:
                    return f"{location}で{sake_name}を提供しているお店が見つかりませんでした。別の地域や銘柄で試してください。"
                else:
                    return f"No restaurants serving {sake_name} found in {location}. Try a different area or sake brand."

            # Add special marker for map data (the app will parse this)
            print(f"DEBUG: Adding MAP_DATA markers with {len(locations_data)} locations")
            output.append("\n" + "="*50)
            output.append("MAP_DATA_START")
            map_json = json.dumps({
                "search_location": location,
                "sake_name": sake_name,
                "center_lat": lat,
                "center_lng": lng,
                "locations": locations_data
            }, ensure_ascii=False)
            output.append(map_json)
            output.append("MAP_DATA_END")
            output.append("="*50)

            if is_japanese:
                output.append(f"\n{sake_name}を扱っている他のお店もたくさんあります。地図情報も参考にしてください。")
            else:
                output.append(f"\nThere are many other locations serving {sake_name}. Please refer to the map for more details.")

            result = "\n".join(output)
            print(f"DEBUG: Returning result with {len(result)} characters, contains MAP_DATA: {'MAP_DATA' in result}")
            return result

        except ApiError as e:
            error_msg = f"Google Maps API error: {str(e)}. Please check your API key and quota."
            print(f"DEBUG: {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error searching for restaurants with {sake_name}: {str(e)}"
            print(f"DEBUG: {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    @tool
    def search_sake_locations(location: str, search_type: str = "both") -> str:
        """
        Search for sake shops, restaurants, or izakayas in a specific location using Google Places API.
        Returns location data with photos and reviews that can be displayed on a map.

        Use this tool when users ask for sake shops, restaurants, or places to drink sake in a specific area (without specifying a particular sake brand).

        Args:
            location: City, region, or area to search (e.g., "Tokyo", "Kyoto", "東京", "京都")
            search_type: Type of venue to search - "shop" (sake shops/liquor stores), "restaurant" (restaurants/izakayas), or "both"

        Returns:
            JSON string with location information including venue names, addresses, coordinates, photos, and reviews for map display.
        """
        if not gmaps_client:
            return "Google Maps API key not configured. Please add GOOGLE_MAPS_API_KEY to your secrets."

        is_japanese = _is_japanese(location)

        try:
            print(f"DEBUG: search_sake_locations called with location='{location}', search_type='{search_type}'")

            # Geocode the location to get coordinates
            print(f"DEBUG: Geocoding location: {location}")
            geocode_result = gmaps_client.geocode(location)
            if not geocode_result:
                error_msg = f"Could not find location: {location}. Please try a different search term."
                print(f"DEBUG: {error_msg}")
                return error_msg

            center_location = geocode_result[0]['geometry']['location']
            lat, lng = center_location['lat'], center_location['lng']
            print(f"DEBUG: Geocoded to ({lat}, {lng})")

            output = []
            locations_data = []

            if is_japanese:
                output.append(f"{location}の日本酒スポットをいくつかご紹介します:")
            else:
                output.append(f"Sake locations in {location}:")
            output.append("-" * 50)

            # Define search keywords based on type
            search_keywords = []
            if search_type in ["shop", "both"]:
                if is_japanese:
                    search_keywords.extend(["日本酒販売店", "酒屋", "日本酒専門店"])
                else:
                    search_keywords.extend(["sake shop", "liquor store sake"])

            if search_type in ["restaurant", "both"]:
                if is_japanese:
                    search_keywords.extend(["日本酒レストラン", "居酒屋", "日本酒バー"])
                else:
                    search_keywords.extend(["sake restaurant", "izakaya", "sake bar"])

            print(f"DEBUG: Searching with {len(search_keywords)} keywords: {search_keywords}")

            # Search for places using Places API Nearby Search
            all_places = []
            api_errors = []
            for keyword in search_keywords:
                try:
                    print(f"DEBUG: Searching for keyword: {keyword}")
                    places_result = gmaps_client.places_nearby(
                        location=(lat, lng),
                        radius=5000,  # 5km radius
                        keyword=keyword,
                        language='ja' if is_japanese else 'en'
                    )
                    num_results = len(places_result.get('results', []))
                    print(f"DEBUG: Found {num_results} results for '{keyword}'")
                    all_places.extend(places_result.get('results', []))
                except Exception as e:
                    error_detail = f"Error searching for '{keyword}': {str(e)}"
                    print(f"DEBUG: {error_detail}")
                    api_errors.append(error_detail)
                    continue

            print(f"DEBUG: Total places found before deduplication: {len(all_places)}")

            if not all_places and api_errors:
                # All API calls failed
                error_summary = "\n".join(api_errors[:3])  # Show first 3 errors
                return f"Google Maps API error while searching for locations:\n{error_summary}\n\nPlease check:\n1. Places API is enabled in Google Cloud Console\n2. Your API key has access to Places API\n3. Billing is enabled for your Google Cloud project"

            # Remove duplicates based on place_id
            seen_ids = set()
            unique_places = []
            for place in all_places:
                place_id = place.get('place_id')
                if place_id and place_id not in seen_ids:
                    seen_ids.add(place_id)
                    unique_places.append(place)

            print(f"DEBUG: Unique places after deduplication: {len(unique_places)}")

            # Limit to top 10 places
            unique_places = unique_places[:10]
            print(f"DEBUG: Processing top {len(unique_places)} places")

            # Fetch detailed information for each place
            for idx, place in enumerate(unique_places, 1):
                place_id = place.get('place_id')
                name = place.get('name', 'Unknown')
                address = place.get('vicinity', '')

                # Get place details including photos and reviews
                try:
                    place_details = gmaps_client.place(
                        place_id=place_id,
                        fields=['name', 'formatted_address', 'geometry', 'rating', 'user_ratings_total',
                                'photos', 'reviews', 'website', 'formatted_phone_number', 'opening_hours']
                    ).get('result', {})

                    # Extract information
                    full_address = place_details.get('formatted_address', address)
                    rating = place_details.get('rating', 0)
                    total_ratings = place_details.get('user_ratings_total', 0)
                    website = place_details.get('website', '')
                    phone = place_details.get('formatted_phone_number', '')
                    location_coords = place_details.get('geometry', {}).get('location', {'lat': 0, 'lng': 0})

                    # Extract photos (up to 3)
                    photos = []
                    photos_data = place_details.get('photos', [])[:3]
                    for photo in photos_data:
                        photo_ref = photo.get('photo_reference')
                        if photo_ref:
                            photos.append({
                                'photo_reference': photo_ref,
                                'width': photo.get('width', 400),
                                'height': photo.get('height', 400)
                            })

                    # Extract reviews (up to 3)
                    reviews = []
                    reviews_data = place_details.get('reviews', [])[:3]
                    for review in reviews_data:
                        reviews.append({
                            'author': review.get('author_name', 'Anonymous'),
                            'rating': review.get('rating', 0),
                            'text': review.get('text', '')[:200],  # Limit review length
                            'time': review.get('relative_time_description', '')
                        })

                    # Add to output
                    output.append(f"\n{idx}. {name}")
                    output.append(f"   Address: {full_address}")
                    if rating > 0:
                        output.append(f"   Rating: {rating}⭐ ({total_ratings} reviews)")
                    if website:
                        output.append(f"   Website: {website}")
                    if phone:
                        output.append(f"   Phone: {phone}")

                    # Store location data for map
                    locations_data.append({
                        "name": name,
                        "address": full_address,
                        "lat": location_coords['lat'],
                        "lng": location_coords['lng'],
                        "rating": rating,
                        "total_ratings": total_ratings,
                        "website": website,
                        "phone": phone,
                        "photos": photos,
                        "reviews": reviews,
                        "place_id": place_id
                    })

                except Exception as e:
                    # If detailed fetch fails, use basic info
                    output.append(f"\n{idx}. {name}")
                    output.append(f"   Address: {address}")

                    locations_data.append({
                        "name": name,
                        "address": address,
                        "lat": place.get('geometry', {}).get('location', {}).get('lat', 0),
                        "lng": place.get('geometry', {}).get('location', {}).get('lng', 0),
                        "rating": place.get('rating', 0),
                        "place_id": place_id
                    })

            # Check if we found any locations
            if not locations_data:
                print("DEBUG: No locations found to display")
                return f"No sake locations found in {location}. Try searching a specific neighborhood or district, or try a different search term."

            # Add special marker for map data (the app will parse this)
            print(f"DEBUG: Adding MAP_DATA markers with {len(locations_data)} locations")
            output.append("\n" + "="*50)
            output.append("MAP_DATA_START")
            map_json = json.dumps({
                "search_location": location,
                "center_lat": lat,
                "center_lng": lng,
                "locations": locations_data
            }, ensure_ascii=False)
            output.append(map_json)
            output.append("MAP_DATA_END")
            output.append("="*50)

            if is_japanese:
                output.append("\n他にも多くの場所がありますので、興味がある方は訪れてみてください。地図情報も参考にしてください。")
            else:
                output.append("\nThere are many other locations as well. Please refer to the map for more details.")

            result = "\n".join(output)
            print(f"DEBUG: Returning result with {len(result)} characters, contains MAP_DATA: {'MAP_DATA' in result}")
            return result

        except ApiError as e:
            error_msg = f"Google Maps API error: {str(e)}. Please check your API key and quota."
            print(f"DEBUG: {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error searching sake locations: {str(e)}"
            print(f"DEBUG: {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

    # Return all tools
    return [
        search_sake_rankings,
        search_sake_info,
        search_social_media_hashtag,
        search_twitter_sake,
        search_instagram_sake,
        search_restaurants_with_sake,
        search_sake_locations,
    ]
