"""
Tools for the Japanese Sake Guide Agent.

This module provides tools for searching sake information from:
- Sake ranking websites (sakenowa.com, saketime.jp)
- General web search via Tavily
- Social media posts via snscrape (Twitter, Instagram, Facebook)
"""
from typing import Optional, List, Callable
from langchain_core.tools import tool
from tavily import TavilyClient

# snscrape imports
try:
    import snscrape.modules.twitter as sntwitter
    import snscrape.modules.instagram as sninstagram
    import snscrape.modules.facebook as snfacebook
    SNSCRAPE_AVAILABLE = True
except ImportError:
    SNSCRAPE_AVAILABLE = False


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
        Search for social media posts by hashtag related to Japanese sake using snscrape.
        Searches Twitter, Instagram, and Facebook for posts with the specified hashtag.

        Args:
            hashtag: Hashtag to search for (with or without #). Examples: "日本酒", "sake", "獺祭", "dassai"
            platforms: Which platforms to search: "all", "twitter", "instagram", "facebook", or comma-separated like "twitter,instagram"

        Returns:
            Social media posts found with the specified hashtag from Twitter, Instagram, and Facebook.
        """
        # Clean up the hashtag
        clean_hashtag = hashtag.lstrip('#')
        sanitized_hashtag = _sanitize_hashtag(clean_hashtag)

        if not SNSCRAPE_AVAILABLE:
            return "Error: snscrape library is not installed. Please install it with: pip install snscrape"

        results = []
        platform_list = [p.strip().lower() for p in platforms.split(",")] if platforms != "all" else ["twitter", "instagram", "facebook"]

        # Search Twitter
        if "twitter" in platform_list or "all" in platform_list:
            twitter_results = _search_twitter_hashtag(sanitized_hashtag)
            if twitter_results:
                results.append(twitter_results)

        # Search Instagram
        if "instagram" in platform_list or "all" in platform_list:
            instagram_results = _search_instagram_hashtag(sanitized_hashtag)
            if instagram_results:
                results.append(instagram_results)

        # Search Facebook
        if "facebook" in platform_list or "all" in platform_list:
            facebook_results = _search_facebook_hashtag(sanitized_hashtag)
            if facebook_results:
                results.append(facebook_results)

        if not results:
            return f"No social media content found for hashtag #{sanitized_hashtag}."

        return "\n\n".join(results)

    @tool
    def search_twitter_sake(query: str) -> str:
        """
        Search Twitter for tweets about Japanese sake.
        Use this tool to find discussions, reviews, and trends about sake on Twitter.

        Args:
            query: Search query for Twitter (e.g., "獺祭", "dassai sake", "日本酒 おすすめ")

        Returns:
            Recent tweets about the specified sake or topic.
        """
        if not SNSCRAPE_AVAILABLE:
            return "Error: snscrape library is not installed. Please install it with: pip install snscrape"

        is_japanese = _is_japanese(query)
        if is_japanese:
            search_query = f"{query} 日本酒"
        else:
            search_query = f"{query} sake OR 日本酒"

        try:
            results = []
            results.append(f"Twitter search results for: {query}")
            results.append("-" * 50)

            count = 0
            max_results = 10

            scraper = sntwitter.TwitterSearchScraper(search_query)
            for idx, tweet in enumerate(scraper.get_items()):
                if count >= max_results:
                    break

                results.append(f"\n{idx + 1}. @{tweet.user.username}")
                results.append(f"   Date: {tweet.date.strftime('%Y-%m-%d %H:%M')}")

                content = tweet.rawContent
                if len(content) > 300:
                    content = content[:300] + "..."
                results.append(f"   Tweet: {content}")
                results.append(f"   URL: {tweet.url}")
                results.append(f"   Likes: {tweet.likeCount} | Retweets: {tweet.retweetCount}")

                count += 1

            if count == 0:
                return f"No tweets found for '{query}'."

            return "\n".join(results)

        except Exception as e:
            return f"Error searching Twitter: {str(e)}"

    @tool
    def search_instagram_sake(sake_name: str) -> str:
        """
        Search for Instagram posts about a specific sake using snscrape.
        Use this tool to find visual content, reviews, and photos about sake on Instagram.

        Args:
            sake_name: Name of the sake to search for on Instagram (e.g., "獺祭", "Dassai", "日本酒")

        Returns:
            Instagram posts and content about the specified sake.
        """
        if not SNSCRAPE_AVAILABLE:
            return "Error: snscrape library is not installed. Please install it with: pip install snscrape"

        sanitized_name = _sanitize_hashtag(sake_name)
        results = []

        # Search Instagram hashtag
        instagram_results = _search_instagram_hashtag(sanitized_name)
        if instagram_results:
            results.append(instagram_results)

        # Also search for related sake hashtags
        related_hashtags = _get_related_sake_hashtags(sake_name)
        for related_tag in related_hashtags[:2]:
            related_results = _search_instagram_hashtag(related_tag, max_results=3)
            if related_results:
                results.append(f"\nRelated #{related_tag}:")
                results.append(related_results)

        if not results:
            return f"No Instagram content found for '{sake_name}'."

        return "\n".join(results)

    # Return all tools
    return [
        search_sake_rankings,
        search_sake_info,
        search_social_media_hashtag,
        search_twitter_sake,
        search_instagram_sake,
    ]


def _search_twitter_hashtag(hashtag: str, max_results: int = 10) -> str:
    """
    Search Twitter for posts with a specific hashtag using snscrape.

    Args:
        hashtag: Hashtag to search (without #)
        max_results: Maximum number of results to return

    Returns:
        Formatted string of Twitter results
    """
    try:
        results = []
        results.append(f"Twitter posts with #{hashtag}:")
        results.append("-" * 40)

        count = 0
        scraper = sntwitter.TwitterHashtagScraper(hashtag)

        for idx, tweet in enumerate(scraper.get_items()):
            if count >= max_results:
                break

            results.append(f"\n{idx + 1}. @{tweet.user.username}")
            results.append(f"   Date: {tweet.date.strftime('%Y-%m-%d %H:%M')}")

            content = tweet.rawContent
            if len(content) > 300:
                content = content[:300] + "..."
            results.append(f"   Tweet: {content}")
            results.append(f"   URL: {tweet.url}")
            results.append(f"   Likes: {tweet.likeCount} | Retweets: {tweet.retweetCount}")

            count += 1

        if count == 0:
            return f"No Twitter posts found for #{hashtag}."

        return "\n".join(results)

    except Exception as e:
        return f"Twitter search error: {str(e)}"


def _search_instagram_hashtag(hashtag: str, max_results: int = 10) -> str:
    """
    Search Instagram for posts with a specific hashtag using snscrape.

    Args:
        hashtag: Hashtag to search (without #)
        max_results: Maximum number of results to return

    Returns:
        Formatted string of Instagram results
    """
    try:
        results = []
        results.append(f"Instagram posts with #{hashtag}:")
        results.append("-" * 40)

        count = 0
        scraper = sninstagram.InstagramHashtagScraper(hashtag)

        for idx, post in enumerate(scraper.get_items()):
            if count >= max_results:
                break

            results.append(f"\n{idx + 1}. @{post.username}")
            results.append(f"   Date: {post.date.strftime('%Y-%m-%d %H:%M') if post.date else 'N/A'}")

            caption = post.caption or ""
            if len(caption) > 300:
                caption = caption[:300] + "..."
            results.append(f"   Caption: {caption}")
            results.append(f"   URL: {post.url}")
            results.append(f"   Likes: {post.likes or 'N/A'} | Comments: {post.comments or 'N/A'}")

            count += 1

        if count == 0:
            return f"No Instagram posts found for #{hashtag}."

        return "\n".join(results)

    except Exception as e:
        return f"Instagram search error: {str(e)}"


def _search_facebook_hashtag(hashtag: str, max_results: int = 10) -> str:
    """
    Search Facebook for posts with a specific hashtag using snscrape.

    Args:
        hashtag: Hashtag to search (without #)
        max_results: Maximum number of results to return

    Returns:
        Formatted string of Facebook results
    """
    try:
        results = []
        results.append(f"Facebook posts with #{hashtag}:")
        results.append("-" * 40)

        count = 0
        # Facebook hashtag search - note: Facebook access may be limited
        scraper = snfacebook.FacebookHashtagScraper(hashtag)

        for idx, post in enumerate(scraper.get_items()):
            if count >= max_results:
                break

            results.append(f"\n{idx + 1}. Post ID: {post.postId if hasattr(post, 'postId') else 'N/A'}")
            results.append(f"   Date: {post.date.strftime('%Y-%m-%d %H:%M') if hasattr(post, 'date') and post.date else 'N/A'}")

            content = getattr(post, 'content', '') or getattr(post, 'text', '') or ""
            if len(content) > 300:
                content = content[:300] + "..."
            results.append(f"   Content: {content}")
            results.append(f"   URL: {post.url if hasattr(post, 'url') else 'N/A'}")

            count += 1

        if count == 0:
            return f"No Facebook posts found for #{hashtag}. (Note: Facebook access may be limited)"

        return "\n".join(results)

    except Exception as e:
        return f"Facebook search error: {str(e)}"


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
