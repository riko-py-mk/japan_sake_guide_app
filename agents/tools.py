"""
Tools for the Japanese Sake Guide Agent.

This module provides tools for searching sake information from:
- Sake ranking websites (sakenowa.com, saketime.jp)
- General web search via Tavily
- Social media content via Tavily web search
"""
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
) -> List[Callable]:
    """
    Create tools for the sake guide agent with API keys bound.

    Args:
        tavily_api_key: API key for Tavily search
        instagram_access_token: Deprecated, kept for backward compatibility

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

    # Return all tools
    return [
        search_sake_rankings,
        search_sake_info,
        search_social_media_hashtag,
        search_twitter_sake,
        search_instagram_sake,
    ]
