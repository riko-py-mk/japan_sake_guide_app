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


# Example sake types for UI suggestions
SAKE_TYPES = {
    "en": [
        "Junmai - Pure rice sake",
        "Honjozo - Added alcohol sake",
        "Ginjo - Premium sake (40% polishing)",
        "Daiginjo - Super premium sake (50%+ polishing)",
        "Junmai Daiginjo - Pure rice super premium",
        "Nigori - Cloudy/unfiltered sake",
        "Nama - Unpasteurized sake",
        "Sparkling sake",
    ],
    "ja": [
        "純米酒 - 米と米麹だけで造った酒",
        "本醸造 - 醸造アルコール添加",
        "吟醸酒 - 精米歩合60%以下",
        "大吟醸 - 精米歩合50%以下",
        "純米大吟醸 - 米のみの大吟醸",
        "にごり酒 - 濁った酒",
        "生酒 - 火入れしていない酒",
        "スパークリング日本酒",
    ]
}

# Example prompts for the UI
EXAMPLE_PROMPTS = {
    "en": [
        "What are the top-rated sake this year?",
        "Tell me about Dassai 23",
        "Recommend a fruity sake for beginners",
        "What sake pairs well with sushi?",
        "What's the difference between Junmai and Ginjo?",
        "Find Instagram posts about Kubota sake",
    ],
    "ja": [
        "今年人気の日本酒は何ですか？",
        "獺祭23について教えてください",
        "初心者におすすめのフルーティな日本酒は？",
        "寿司に合う日本酒を教えてください",
        "純米酒と吟醸酒の違いは何ですか？",
        "久保田のInstagram投稿を探して",
    ]
}
