"""
Utility functions for the Japanese Sake Guide App.
"""
from typing import Literal


def detect_language(text: str) -> Literal["ja", "en"]:
    """
    Detect if text is primarily Japanese or English.

    Args:
        text: Text to analyze

    Returns:
        "ja" for Japanese, "en" for English
    """
    japanese_chars = 0
    total_chars = 0

    for char in text:
        if char.isalpha() or (
            '\u3040' <= char <= '\u309f' or  # Hiragana
            '\u30a0' <= char <= '\u30ff' or  # Katakana
            '\u4e00' <= char <= '\u9fff'     # Kanji
        ):
            total_chars += 1
            if (
                '\u3040' <= char <= '\u309f' or
                '\u30a0' <= char <= '\u30ff' or
                '\u4e00' <= char <= '\u9fff'
            ):
                japanese_chars += 1

    if total_chars == 0:
        return "en"

    # If more than 20% Japanese characters, consider it Japanese
    return "ja" if (japanese_chars / total_chars) > 0.2 else "en"


def format_sake_response(response: str, language: str = "en") -> str:
    """
    Format the agent response for display.

    Args:
        response: Raw response from the agent
        language: Language of the response

    Returns:
        Formatted response string
    """
    # Add any post-processing here if needed
    return response


# Example prompts organized by tool for the sidebar
# Each tool has example prompts demonstrating its functionality
SIDEBAR_EXAMPLE_PROMPTS = {
    "en": {
        "Sake Rankings": [
            "What are the top-rated sake this year?",
            "Best daiginjo sake recommendations",
        ],
        "Sake Info": [
            "Tell me about Dassai 23",
            "What is Kubota Manju like?",
        ],
        "Social Media Hashtags": [
            "Search #sake hashtag on social media",
            "Find posts with #nihonshu hashtag",
        ],
        "Twitter/X Search": [
            "What are people saying about sake on Twitter?",
            "Find sake reviews on X",
        ],
        "Instagram Search": [
            "Find Instagram posts about Dassai",
            "Search Instagram for Kubota sake",
        ],
        "Location Search": [
            "Find sake shops in Tokyo",
            "Where can I drink sake in Kyoto?",
        ],
        "Online Shop Search": [
            "Where can I buy Dassai online?",
            "I want to order Kubota Manju",
        ],
    },
    "ja": {
        "日本酒ランキング": [
            "今年人気の日本酒は何ですか？",
            "おすすめの大吟醸を教えて",
        ],
        "日本酒情報": [
            "獺祭23について教えてください",
            "久保田 萬寿はどんな味？",
        ],
        "SNSハッシュタグ検索": [
            "#日本酒 のSNS投稿を検索して",
            "#酒蔵巡り の投稿を探して",
        ],
        "Twitter/X検索": [
            "Twitterで日本酒の話題を探して",
            "Xで日本酒レビューを検索",
        ],
        "Instagram検索": [
            "獺祭のInstagram投稿を探して",
            "久保田のInstagram投稿を検索",
        ],
        "場所検索": [
            "東京の日本酒販売店を探して",
            "京都で日本酒が飲める場所は？",
        ],
        "オンラインショップ検索": [
            "獺祭をネットで購入したい",
            "久保田 萬寿の通販を探して",
        ],
    },
}

# Example prompts for the main area (kept for backward compatibility)
EXAMPLE_PROMPTS = {
    "en": [
        "What are the top-rated sake this year?",
        "Tell me about Dassai 23",
        "Find sake shops in Tokyo",
        "Search #sake hashtag on social media",
    ],
    "ja": [
        "今年人気の日本酒は何ですか？",
        "獺祭23について教えてください",
        "東京の日本酒販売店を探して",
        "#日本酒 のSNS投稿を検索して",
    ],
}
