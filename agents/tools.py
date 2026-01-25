"""
Tools for the Japanese Sake Guide Agent.

This module provides tools for searching sake information from:
- Sake ranking websites (sakenowa.com, saketime.jp)
- General web search via Tavily
- Instagram posts
"""
import httpx
from typing import Optional
from langchain_core.tools import tool
from tavily import TavilyClient


def get_tavily_client(api_key: str) -> TavilyClient:
    """Create a Tavily client with the given API key."""
    return TavilyClient(api_key=api_key)


@tool
def search_sake_rankings(
    query: str,
    tavily_api_key: str,
    language: str = "auto",
) -> str:
    """
    Search for sake recommendations from ranking websites.

    This tool searches sake ranking information from trusted sources:
    - sakenowa.com (Japanese sake database with rankings)
    - saketime.jp (Japanese sake ranking site)

    Args:
        query: Search query about sake recommendations (e.g., "best fruity sake", "top junmai daiginjo")
        tavily_api_key: Tavily API key for web search
        language: Language preference - "ja" for Japanese, "en" for English, "auto" for automatic detection

    Returns:
        String containing sake ranking information and recommendations.
    """
    client = get_tavily_client(tavily_api_key)

    # Define the ranking sources to search
    ranking_domains = [
        "sakenowa.com",
        "saketime.jp",
    ]

    # Enhance query for sake ranking search
    if language == "ja" or (language == "auto" and _is_japanese(query)):
        enhanced_query = f"日本酒 ランキング おすすめ {query}"
    else:
        enhanced_query = f"Japanese sake ranking recommendation {query}"

    try:
        results = client.search(
            query=enhanced_query,
            search_depth="advanced",
            max_results=8,
            include_domains=ranking_domains,
            include_answer=True,
        )

        # Format the results
        output = []
        if results.get("answer"):
            output.append(f"Summary: {results['answer']}\n")

        output.append("Ranking Information Sources:")
        for idx, result in enumerate(results.get("results", []), 1):
            output.append(f"\n{idx}. {result.get('title', 'No title')}")
            output.append(f"   URL: {result.get('url', '')}")
            content = result.get('content', '')
            if content:
                # Truncate long content
                if len(content) > 500:
                    content = content[:500] + "..."
                output.append(f"   Content: {content}")

        return "\n".join(output) if output else "No ranking information found."

    except Exception as e:
        return f"Error searching sake rankings: {str(e)}"


@tool
def search_sake_web(
    query: str,
    tavily_api_key: str,
    sake_name: Optional[str] = None,
    language: str = "auto",
) -> str:
    """
    Search for detailed information about a specific sake or general sake topics.

    This tool performs a comprehensive web search for sake information including:
    - Brewery details
    - Tasting notes and flavor profiles
    - Food pairing suggestions
    - Awards and reviews

    Args:
        query: Search query about sake
        tavily_api_key: Tavily API key for web search
        sake_name: Optional specific sake name to search for
        language: Language preference - "ja" for Japanese, "en" for English, "auto" for automatic

    Returns:
        String containing detailed sake information from web sources.
    """
    client = get_tavily_client(tavily_api_key)

    # Build search query
    if sake_name:
        if language == "ja" or (language == "auto" and _is_japanese(sake_name)):
            search_query = f"日本酒 {sake_name} {query} 特徴 味わい 蔵元"
        else:
            search_query = f"Japanese sake {sake_name} {query} tasting notes brewery"
    else:
        if language == "ja" or (language == "auto" and _is_japanese(query)):
            search_query = f"日本酒 {query}"
        else:
            search_query = f"Japanese sake {query}"

    try:
        results = client.search(
            query=search_query,
            search_depth="advanced",
            max_results=6,
            include_answer=True,
        )

        # Format results
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

        return "\n".join(output) if output else "No information found."

    except Exception as e:
        return f"Error searching web: {str(e)}"


@tool
def search_sake_instagram(
    sake_name: str,
    instagram_access_token: Optional[str] = None,
    tavily_api_key: Optional[str] = None,
) -> str:
    """
    Search for sake information on Instagram.

    This tool searches for Instagram posts and content about specific sake brands.
    It uses the Instagram Graph API if available, or falls back to web search.

    Args:
        sake_name: Name of the sake to search for
        instagram_access_token: Optional Instagram API access token
        tavily_api_key: Optional Tavily API key for fallback web search

    Returns:
        String containing Instagram content and social media mentions about the sake.
    """
    results = []

    # Try Instagram API if token is available
    if instagram_access_token:
        try:
            ig_results = _search_instagram_api(sake_name, instagram_access_token)
            if ig_results:
                results.append("Instagram API Results:")
                results.append(ig_results)
        except Exception as e:
            results.append(f"Instagram API not available: {str(e)}")

    # Fallback to web search for Instagram content
    if tavily_api_key:
        try:
            client = get_tavily_client(tavily_api_key)

            # Search for Instagram posts about the sake
            search_results = client.search(
                query=f"{sake_name} 日本酒 sake site:instagram.com OR Instagram",
                search_depth="basic",
                max_results=5,
                include_domains=["instagram.com"],
            )

            if search_results.get("results"):
                results.append("\nInstagram Web Search Results:")
                for idx, result in enumerate(search_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")
                    content = result.get('content', '')
                    if content:
                        if len(content) > 300:
                            content = content[:300] + "..."
                        results.append(f"   Content: {content}")

            # Also search for general social media mentions
            social_results = client.search(
                query=f"{sake_name} Japanese sake review tasting",
                search_depth="basic",
                max_results=3,
            )

            if social_results.get("results"):
                results.append("\nRelated Social Content:")
                for idx, result in enumerate(social_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")

        except Exception as e:
            results.append(f"Web search error: {str(e)}")

    if not results:
        return f"No Instagram or social media content found for '{sake_name}'."

    return "\n".join(results)


def _search_instagram_api(sake_name: str, access_token: str) -> str:
    """
    Search Instagram using the Graph API.

    Note: Instagram Basic Display API has limited search capabilities.
    This is a placeholder for more advanced Instagram integration.

    Args:
        sake_name: Name of sake to search
        access_token: Instagram access token

    Returns:
        Formatted string of Instagram results
    """
    # Instagram Graph API endpoint for hashtag search
    # Note: Full hashtag search requires Instagram Business account
    base_url = "https://graph.instagram.com"

    try:
        # Search for hashtag ID (requires Business/Creator account)
        hashtag = sake_name.replace(" ", "").lower()

        # This would require a Business account and proper permissions
        # For now, return a message about the limitations
        return (
            f"Instagram API search for #{hashtag}: "
            "Direct Instagram API search requires Business account permissions. "
            "Using web search as fallback."
        )

    except Exception as e:
        return f"Instagram API error: {str(e)}"


def _is_japanese(text: str) -> bool:
    """
    Check if the text contains Japanese characters.

    Args:
        text: Text to check

    Returns:
        True if the text contains Japanese characters
    """
    for char in text:
        # Check for Hiragana, Katakana, or Kanji
        if (
            '\u3040' <= char <= '\u309f' or  # Hiragana
            '\u30a0' <= char <= '\u30ff' or  # Katakana
            '\u4e00' <= char <= '\u9fff'     # CJK Unified Ideographs (Kanji)
        ):
            return True
    return False


def create_tools(tavily_api_key: str, instagram_token: Optional[str] = None):
    """
    Create tool instances with API keys bound.

    Args:
        tavily_api_key: Tavily API key
        instagram_token: Optional Instagram access token

    Returns:
        List of tool functions ready to use
    """
    from functools import partial

    tools = [
        partial(search_sake_rankings, tavily_api_key=tavily_api_key),
        partial(search_sake_web, tavily_api_key=tavily_api_key),
        partial(
            search_sake_instagram,
            tavily_api_key=tavily_api_key,
            instagram_access_token=instagram_token,
        ),
    ]

    return tools
