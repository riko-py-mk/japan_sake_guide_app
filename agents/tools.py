"""
Tools for the Japanese Sake Guide Agent.

This module provides tools for searching sake information from:
- Sake ranking websites (sakenowa.com, saketime.jp)
- General web search via Tavily
- Instagram posts and hashtag search
"""
import httpx
from typing import Optional, List, Callable
from langchain_core.tools import tool
from tavily import TavilyClient


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
    Convert text to a valid Instagram hashtag format.

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
    instagram_access_token: Optional[str] = None,
) -> List[Callable]:
    """
    Create tools for the sake guide agent with API keys bound.

    Args:
        tavily_api_key: API key for Tavily search
        instagram_access_token: Optional Instagram access token for hashtag search

    Returns:
        List of tool functions ready to use with LangGraph
    """
    tavily_client = TavilyClient(api_key=tavily_api_key)

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
    def search_sake_instagram(sake_name: str) -> str:
        """
        Search for Instagram posts and social media content about a specific sake.
        Use this tool to find visual content, reviews, and social discussions about sake.

        Args:
            sake_name: Name of the sake to search for on Instagram

        Returns:
            Instagram and social media content about the sake.
        """
        results = []

        try:
            # Search for Instagram content via web
            ig_results = tavily_client.search(
                query=f"{sake_name} 日本酒 sake site:instagram.com",
                search_depth="basic",
                max_results=5,
            )

            if ig_results.get("results"):
                results.append("Instagram Content Found:")
                for idx, result in enumerate(ig_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")
                    content = result.get('content', '')
                    if content:
                        if len(content) > 300:
                            content = content[:300] + "..."
                        results.append(f"   Preview: {content}")

            # Also search for general social media reviews
            social_results = tavily_client.search(
                query=f"{sake_name} sake review tasting notes",
                search_depth="basic",
                max_results=3,
            )

            if social_results.get("results"):
                results.append("\n\nRelated Reviews & Content:")
                for idx, result in enumerate(social_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")

        except Exception as e:
            results.append(f"Error searching social media: {str(e)}")

        if not results:
            return f"No Instagram or social media content found for '{sake_name}'."

        return "\n".join(results)

    @tool
    def search_instagram_hashtag(hashtag: str) -> str:
        """
        Search for Instagram posts by hashtag related to Japanese sake.
        Use this tool when users want to find Instagram posts with specific hashtags like #日本酒, #sake, or sake brand names.

        Args:
            hashtag: Hashtag to search for (with or without #). Examples: "日本酒", "sake", "獺祭", "dassai"

        Returns:
            Instagram posts and content found with the specified hashtag.
        """
        # Clean up the hashtag
        clean_hashtag = hashtag.lstrip('#')
        sanitized_hashtag = _sanitize_hashtag(clean_hashtag)

        results = []

        # Try Instagram Graph API if access token is available
        if instagram_access_token:
            try:
                api_results = _search_instagram_hashtag_api(
                    sanitized_hashtag,
                    instagram_access_token,
                )
                if api_results:
                    results.append(api_results)
            except Exception as e:
                results.append(f"Instagram API error: {str(e)}")

        # Always also do web search for Instagram hashtag content
        try:
            # Search for the hashtag on Instagram via web
            ig_web_results = tavily_client.search(
                query=f"#{sanitized_hashtag} site:instagram.com 日本酒 sake",
                search_depth="advanced",
                max_results=8,
            )

            if ig_web_results.get("results"):
                results.append(f"\nInstagram posts with #{sanitized_hashtag}:")
                for idx, result in enumerate(ig_web_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")
                    content = result.get('content', '')
                    if content:
                        if len(content) > 400:
                            content = content[:400] + "..."
                        results.append(f"   Content: {content}")

            # Also search for related hashtags
            related_hashtags = _get_related_sake_hashtags(clean_hashtag)
            if related_hashtags:
                related_results = tavily_client.search(
                    query=f"{' '.join(['#' + h for h in related_hashtags])} site:instagram.com",
                    search_depth="basic",
                    max_results=4,
                )

                if related_results.get("results"):
                    results.append(f"\n\nRelated hashtag content ({', '.join(['#' + h for h in related_hashtags])}):")
                    for idx, result in enumerate(related_results.get("results", []), 1):
                        results.append(f"\n{idx}. {result.get('title', 'No title')}")
                        results.append(f"   URL: {result.get('url', '')}")

        except Exception as e:
            results.append(f"Web search error: {str(e)}")

        if not results:
            return f"No Instagram content found for hashtag #{sanitized_hashtag}."

        return "\n".join(results)

    # Return all tools
    return [
        search_sake_rankings,
        search_sake_info,
        search_sake_instagram,
        search_instagram_hashtag,
    ]


def _search_instagram_hashtag_api(hashtag: str, access_token: str) -> str:
    """
    Search Instagram hashtags using the Instagram Graph API.

    Note: This requires an Instagram Business or Creator account with proper permissions.
    The Instagram Basic Display API does not support hashtag search.

    For full hashtag search, you need:
    1. Facebook Developer account
    2. Instagram Business/Creator account connected to a Facebook Page
    3. instagram_basic permission and instagram_manage_comments (for hashtag search)

    Args:
        hashtag: Hashtag to search (without #)
        access_token: Instagram Graph API access token

    Returns:
        Formatted string of Instagram results or error message
    """
    base_url = "https://graph.facebook.com/v18.0"

    try:
        # Step 1: Get the hashtag ID
        hashtag_search_url = f"{base_url}/ig_hashtag_search"
        params = {
            "user_id": "me",  # This needs to be replaced with actual user ID
            "q": hashtag,
            "access_token": access_token,
        }

        with httpx.Client(timeout=30.0) as client:
            # Search for hashtag ID
            response = client.get(hashtag_search_url, params=params)

            if response.status_code != 200:
                # API might not be available or token doesn't have permissions
                return (
                    f"Instagram API: Hashtag search for #{hashtag} requires Business account. "
                    "Using web search as fallback."
                )

            data = response.json()

            if not data.get("data"):
                return f"No Instagram hashtag found for #{hashtag}."

            hashtag_id = data["data"][0]["id"]

            # Step 2: Get recent media for the hashtag
            media_url = f"{base_url}/{hashtag_id}/recent_media"
            media_params = {
                "user_id": "me",
                "fields": "id,caption,media_type,media_url,permalink,timestamp",
                "access_token": access_token,
                "limit": 10,
            }

            media_response = client.get(media_url, params=media_params)

            if media_response.status_code != 200:
                return f"Could not fetch media for #{hashtag}."

            media_data = media_response.json()
            posts = media_data.get("data", [])

            if not posts:
                return f"No recent posts found for #{hashtag}."

            # Format results
            output = [f"Instagram API Results for #{hashtag}:"]
            for idx, post in enumerate(posts[:10], 1):
                output.append(f"\n{idx}. Post ID: {post.get('id', 'N/A')}")
                output.append(f"   Type: {post.get('media_type', 'N/A')}")
                output.append(f"   Link: {post.get('permalink', 'N/A')}")
                caption = post.get('caption', '')
                if caption:
                    if len(caption) > 200:
                        caption = caption[:200] + "..."
                    output.append(f"   Caption: {caption}")
                output.append(f"   Posted: {post.get('timestamp', 'N/A')}")

            return "\n".join(output)

    except httpx.TimeoutException:
        return "Instagram API request timed out."
    except Exception as e:
        return f"Instagram API error: {str(e)}"


def _get_related_sake_hashtags(hashtag: str) -> List[str]:
    """
    Get related sake hashtags based on the input hashtag.

    Args:
        hashtag: Original hashtag

    Returns:
        List of related hashtags
    """
    # Common sake-related hashtags
    sake_hashtags_ja = [
        "日本酒", "sake", "nihonshu", "地酒", "純米酒", "大吟醸",
        "酒蔵", "利き酒", "酒好き", "日本酒好き", "晩酌",
    ]

    sake_hashtags_en = [
        "sake", "japanesesake", "nihonshu", "sakelovers", "sakelover",
        "drinkjapan", "junmai", "daiginjo", "saketime", "kanpai",
    ]

    # Determine if input is Japanese
    is_japanese = _is_japanese(hashtag)

    # Return related hashtags (excluding the input)
    base_hashtags = sake_hashtags_ja if is_japanese else sake_hashtags_en
    related = [h for h in base_hashtags if h.lower() != hashtag.lower()]

    return related[:3]  # Return top 3 related hashtags
