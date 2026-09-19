"""
Shared access to the daily sake ranking snapshot.

This module is the single source of truth for:
- the sakenowa flavour-chart axis mapping (``FLAVOR_AXES``)
- flavour display metadata (``FLAVOR_TYPES``)
- prefecture → region lookup (``prefecture_region``)
- loading/filtering ``utils/sake_ranking_fallback.json``

It deliberately imports nothing outside the standard library so that both the
Streamlit app and ``scripts/update_sake_rankings.py`` (which runs in CI with
only ``requests`` installed) can share it.
"""
from pathlib import Path
from typing import Dict, List, Optional
import json

DATA_PATH = Path(__file__).parent / "sake_ranking_fallback.json"

# ---------------------------------------------------------------------------
# Flavour axes
# ---------------------------------------------------------------------------
# sakenowa's flavour chart is a six-axis radar. The axes, in order, are:
#   f1 華やか / f2 芳醇 / f3 重厚 / f4 穏やか / f5 ドライ / f6 軽快
# Keep this mapping and FLAVOR_TYPES in lockstep — an earlier version had the
# axes shifted, which labelled 40% of the top 50 as "Aged" (熟成).
FLAVOR_AXES: Dict[str, str] = {
    "Fruity":    "f1",   # 華やか
    "Mellow":    "f2",   # 芳醇
    "Full Body": "f3",   # 重厚
    "Mild":      "f4",   # 穏やか
    "Dry":       "f5",   # ドライ
    "Light":     "f6",   # 軽快
}

# "Sparkling" is keyword-derived from the brand name, not an axis.
# "Unknown" is used when sakenowa has no flavour chart for a brand.
FLAVOR_TYPES: Dict[str, Dict] = {
    "Fruity":    {"color": "#E85D9E", "emoji": "🍎", "ja": "華やか",       "desc": "Aromatic and floral"},
    "Mellow":    {"color": "#F4B942", "emoji": "🍯", "ja": "芳醇",         "desc": "Rich and mellow"},
    "Full Body": {"color": "#A0522D", "emoji": "🍺", "ja": "重厚",         "desc": "Heavy and full-bodied"},
    "Mild":      {"color": "#5DBD7A", "emoji": "🌾", "ja": "穏やか",       "desc": "Gentle and quiet"},
    "Dry":       {"color": "#8B6914", "emoji": "🪨", "ja": "ドライ",       "desc": "Dry and crisp"},
    "Light":     {"color": "#4AABDB", "emoji": "💧", "ja": "軽快",         "desc": "Light and smooth"},
    "Sparkling": {"color": "#6EB5FF", "emoji": "✨", "ja": "スパークリング", "desc": "Sparkling with bubbles"},
    "Unknown":   {"color": "#9E9E9E", "emoji": "❔", "ja": "データなし",    "desc": "No flavour data available"},
}

FALLBACK_FLAVOR = "Unknown"

# Accepted user spellings → canonical flavour name.
_FLAVOR_ALIASES: Dict[str, str] = {
    "fruity": "Fruity", "aromatic": "Fruity", "floral": "Fruity",
    "華やか": "Fruity", "フルーティ": "Fruity", "はなやか": "Fruity",
    "mellow": "Mellow", "rich": "Mellow", "芳醇": "Mellow", "ほうじゅん": "Mellow",
    "full body": "Full Body", "full-bodied": "Full Body", "fullbody": "Full Body",
    "heavy": "Full Body", "重厚": "Full Body", "じゅうこう": "Full Body", "濃醇": "Full Body",
    "mild": "Mild", "gentle": "Mild", "穏やか": "Mild", "おだやか": "Mild",
    "dry": "Dry", "karakuchi": "Dry", "ドライ": "Dry", "辛口": "Dry",
    "light": "Light", "crisp": "Light", "smooth": "Light",
    "軽快": "Light", "けいかい": "Light", "淡麗": "Light",
    "sparkling": "Sparkling", "スパークリング": "Sparkling", "発泡": "Sparkling",
}

# ---------------------------------------------------------------------------
# Prefectures
# ---------------------------------------------------------------------------
# sakenowa returns prefecture names WITH their suffix ("秋田県", "京都府",
# "東京都", "北海道"), so every lookup here is done on the suffix-stripped
# stem via _prefecture_stem().
PREFECTURE_TO_REGION: Dict[str, str] = {
    "北海道": "Hokkaido",
    "青森": "Tohoku", "岩手": "Tohoku", "宮城": "Tohoku",
    "秋田": "Tohoku", "山形": "Tohoku", "福島": "Tohoku",
    "茨城": "Kanto",  "栃木": "Kanto",  "群馬": "Kanto",
    "埼玉": "Kanto",  "千葉": "Kanto",  "東京": "Kanto",  "神奈川": "Kanto",
    "新潟": "Chubu",  "富山": "Chubu",  "石川": "Chubu",  "福井": "Chubu",
    "山梨": "Chubu",  "長野": "Chubu",  "岐阜": "Chubu",
    "静岡": "Chubu",  "愛知": "Chubu",
    "三重": "Kinki",  "滋賀": "Kinki",  "京都": "Kinki",
    "大阪": "Kinki",  "兵庫": "Kinki",  "奈良": "Kinki",  "和歌山": "Kinki",
    "鳥取": "Chugoku", "島根": "Chugoku", "岡山": "Chugoku",
    "広島": "Chugoku", "山口": "Chugoku",
    "徳島": "Shikoku", "香川": "Shikoku", "愛媛": "Shikoku", "高知": "Shikoku",
    "福岡": "Kyushu", "佐賀": "Kyushu", "長崎": "Kyushu",
    "熊本": "Kyushu", "大分": "Kyushu", "宮崎": "Kyushu",
    "鹿児島": "Kyushu", "沖縄": "Kyushu",
}

REGION_COLORS: Dict[str, str] = {
    "Hokkaido": "#4682B4",
    "Tohoku":   "#FF8C00",
    "Kanto":    "#4169E1",
    "Chubu":    "#20B2AA",
    "Kinki":    "#DC143C",
    "Chugoku":  "#32CD32",
    "Shikoku":  "#9370DB",
    "Kyushu":   "#FF6347",
    "Unknown":  "#808080",
}

# Romaji → kanji stem, so English-speaking users can filter by prefecture.
_ROMAJI_TO_PREFECTURE: Dict[str, str] = {
    "hokkaido": "北海道", "aomori": "青森", "iwate": "岩手", "miyagi": "宮城",
    "akita": "秋田", "yamagata": "山形", "fukushima": "福島", "ibaraki": "茨城",
    "tochigi": "栃木", "gunma": "群馬", "saitama": "埼玉", "chiba": "千葉",
    "tokyo": "東京", "kanagawa": "神奈川", "niigata": "新潟", "toyama": "富山",
    "ishikawa": "石川", "fukui": "福井", "yamanashi": "山梨", "nagano": "長野",
    "gifu": "岐阜", "shizuoka": "静岡", "aichi": "愛知", "mie": "三重",
    "shiga": "滋賀", "kyoto": "京都", "osaka": "大阪", "hyogo": "兵庫",
    "nara": "奈良", "wakayama": "和歌山", "tottori": "鳥取", "shimane": "島根",
    "okayama": "岡山", "hiroshima": "広島", "yamaguchi": "山口",
    "tokushima": "徳島", "kagawa": "香川", "ehime": "愛媛", "kochi": "高知",
    "fukuoka": "福岡", "saga": "佐賀", "nagasaki": "長崎", "kumamoto": "熊本",
    "oita": "大分", "miyazaki": "宮崎", "kagoshima": "鹿児島", "okinawa": "沖縄",
}


def _prefecture_stem(prefecture: str) -> str:
    """Strip the 都/道/府/県 suffix. ``"秋田県" -> "秋田"``, ``"北海道" -> "北海道"``."""
    stem = (prefecture or "").strip()
    if stem == "北海道":
        return stem
    if stem.endswith(("都", "府", "県")):
        return stem[:-1]
    return stem


def prefecture_region(prefecture: str) -> str:
    """Return the geographic region for a prefecture name, or ``"Unknown"``."""
    return PREFECTURE_TO_REGION.get(_prefecture_stem(prefecture), "Unknown")


def region_color(prefecture: str) -> str:
    """Return the display colour for a prefecture's region."""
    return REGION_COLORS.get(prefecture_region(prefecture), REGION_COLORS["Unknown"])


def normalize_flavor(value: str) -> Optional[str]:
    """Resolve a user-supplied flavour term to a canonical name, or ``None``."""
    if not value:
        return None
    key = value.strip().lower()
    if key in _FLAVOR_ALIASES:
        return _FLAVOR_ALIASES[key]
    for name in FLAVOR_TYPES:
        if key == name.lower():
            return name
    return None


def normalize_prefecture(value: str) -> Optional[str]:
    """Resolve a user-supplied prefecture (kanji or romaji) to its kanji stem."""
    if not value:
        return None
    raw = value.strip()
    stem = _prefecture_stem(raw)
    if stem in PREFECTURE_TO_REGION:
        return stem
    return _ROMAJI_TO_PREFECTURE.get(raw.lower())


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_ranking_data(path: Optional[Path] = None) -> dict:
    """Load the ranking snapshot as ``{"as_of": str | None, "entries": list}``.

    Tolerates the legacy on-disk format (a bare list of entries).
    """
    with open(path or DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return {"as_of": None, "entries": raw}
    return {"as_of": raw.get("as_of"), "entries": raw.get("entries", [])}


def load_ranking_entries(path: Optional[Path] = None) -> List[Dict]:
    """Return all ranking entries sorted by rank."""
    return sorted(load_ranking_data(path)["entries"], key=lambda e: e.get("rank", 0))


def filter_entries(
    entries: List[Dict],
    flavor: Optional[str] = None,
    prefecture: Optional[str] = None,
    top_n: Optional[int] = None,
) -> List[Dict]:
    """Filter ranking entries by canonical flavour and/or prefecture stem.

    ``flavor`` and ``prefecture`` are matched exactly against canonical values,
    so pass them through ``normalize_flavor`` / ``normalize_prefecture`` first.
    """
    result = entries
    if flavor:
        result = [e for e in result if e.get("flavor_type") == flavor]
    if prefecture:
        result = [e for e in result if _prefecture_stem(e.get("prefecture", "")) == prefecture]
    if top_n is not None:
        result = result[:top_n]
    return result


def flavor_distribution(entries: List[Dict]) -> Dict[str, int]:
    """Count entries per flavour type, most common first."""
    counts: Dict[str, int] = {}
    for entry in entries:
        name = entry.get("flavor_type", FALLBACK_FLAVOR)
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
