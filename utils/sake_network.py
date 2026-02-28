"""
Sake Network Graph - Interactive visualization of Japanese sake rankings,
prefectures, and flavor profiles using streamlit-agraph.

Data sources:
  Primary:  Sakenowa public API (https://muro.sakenowa.com/sakenowa-data/api)
  Fallback: utils/sake_ranking_fallback.json  (bundled static dataset)
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import streamlit as st

try:
    from streamlit_agraph import Config, Edge, Node, agraph
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"
_FALLBACK_PATH = Path(__file__).parent / "sake_ranking_fallback.json"

# Sakenowa flavor-chart API field (f1–f6) for each flavor type.
# Keeping this at module level avoids reconstructing the mapping on every call.
_FLAVOR_API_KEYS: Dict[str, str] = {
    "Fruity":     "f1",   # フルーティ・華やか
    "Light":      "f2",   # 穏やか・軽快
    "Sweet":      "f3",   # 甘い・まろやか
    "Dry":        "f4",   # 辛口・シャープ
    "Full Body":  "f5",   # どっしり・重厚
    "Aged":       "f6",   # 熟成・複雑
}

_SPARKLING_KEYWORDS = frozenset(
    ["スパークリング", "発泡", "微発泡", "Sparkling", "sparkling", "awa"]
)

FLAVOR_TYPES: Dict[str, Dict] = {
    "Fruity":    {"color": "#E85D9E", "emoji": "🍎", "ja": "フルーティ・華やか", "desc": "Aromatic, fruity notes"},
    "Light":     {"color": "#4AABDB", "emoji": "💧", "ja": "穏やか・軽快",      "desc": "Smooth and light"},
    "Sweet":     {"color": "#F4B942", "emoji": "🍯", "ja": "甘い・まろやか",    "desc": "Sweet and mellow"},
    "Dry":       {"color": "#5DBD7A", "emoji": "🌾", "ja": "辛口・シャープ",    "desc": "Dry and crisp"},
    "Full Body": {"color": "#A0522D", "emoji": "🍺", "ja": "どっしり・重厚",    "desc": "Rich and full-bodied"},
    "Aged":      {"color": "#8B6914", "emoji": "🪨", "ja": "熟成・複雑",        "desc": "Aged and complex"},
    "Sparkling": {"color": "#6EB5FF", "emoji": "✨", "ja": "スパークリング・発泡", "desc": "Sparkling with bubbles"},
}

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
    "鳥取": "Chugoku","島根": "Chugoku","岡山": "Chugoku",
    "広島": "Chugoku","山口": "Chugoku",
    "徳島": "Shikoku","香川": "Shikoku","愛媛": "Shikoku","高知": "Shikoku",
    "福岡": "Kyushu", "佐賀": "Kyushu", "長崎": "Kyushu",
    "熊本": "Kyushu", "大分": "Kyushu", "宮崎": "Kyushu",
    "鹿児島": "Kyushu","沖縄": "Kyushu",
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


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def classify_flavor(brand_name: str, flavor_chart: Optional[dict]) -> str:
    """Return the dominant flavor type for a sake brand.

    Sparkling is detected by keyword; for all others the sakenowa f1-f6
    scores are compared and the highest wins.
    """
    if any(kw in brand_name for kw in _SPARKLING_KEYWORDS):
        return "Sparkling"
    if not flavor_chart:
        return "Light"
    scores = {flavor: flavor_chart.get(key, 0) for flavor, key in _FLAVOR_API_KEYS.items()}
    return max(scores, key=scores.get)


def _get_with_retry(url: str, timeout: int = 8, max_retries: int = 3) -> dict:
    """GET *url* with exponential-backoff retries. Raises on final failure."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)   # 1 s, 2 s, 4 s
    raise last_exc


@st.cache_data(ttl=3600)
def _fetch_sakenowa_parallel() -> Tuple[Dict, Dict, Dict, Dict]:
    """Fetch all four sakenowa endpoints concurrently with retry.

    Returns (brands, areas, rankings, flavors) dicts keyed by ID.
    Raises on any failure — intentionally no Streamlit side-effects inside
    a cached function (st.error / st.warning cannot be called here).
    """
    endpoints = {
        "brands":   f"{SAKENOWA_API_BASE}/brands",
        "areas":    f"{SAKENOWA_API_BASE}/areas",
        "rankings": f"{SAKENOWA_API_BASE}/rankings",
        "flavors":  f"{SAKENOWA_API_BASE}/flavor-charts",
    }

    results: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_get_with_retry, url): key
                   for key, url in endpoints.items()}
        for future in as_completed(futures):
            results[futures[future]] = future.result()  # propagates exceptions

    brands  = {b["id"]: b for b in results["brands"].get("brands", [])}
    areas   = {a["id"]: a for a in results["areas"].get("areas", [])}
    rankings = results["rankings"]
    flavors = {f["brandId"]: f for f in results["flavors"].get("flavorCharts", [])}
    return brands, areas, rankings, flavors


def _api_entries(top_n: int) -> Optional[List[Dict]]:
    """Parse the top-N sake entries from the live sakenowa API.

    Returns None on any failure so the caller can transparently fall back.
    """
    try:
        brands, areas, rankings_data, flavors = _fetch_sakenowa_parallel()
    except Exception:
        return None

    all_rankings = rankings_data.get("rankings", [])
    ranking_list = next(
        (r.get("ranking", []) for r in all_rankings if r.get("id") == "overall"),
        all_rankings[0].get("ranking", []) if all_rankings else [],
    )
    if not ranking_list:
        return None

    entries = []
    for item in ranking_list[:top_n]:
        brand_id = item.get("brandId")
        if brand_id not in brands:
            continue
        brand = brands[brand_id]
        area  = areas.get(brand.get("areaId"), {})
        name  = brand.get("name", f"Sake #{brand_id}")
        entries.append({
            "brand_id":   brand_id,
            "name":       name,
            "rank":       item.get("rank", 0),
            "prefecture": area.get("name", "不明"),
            "flavor_type": classify_flavor(name, flavors.get(brand_id)),
        })
    return entries or None


@st.cache_data(ttl=86400)
def _load_fallback_entries() -> List[Dict]:
    """Load the bundled static sake dataset from sake_ranking_fallback.json."""
    with open(_FALLBACK_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data, key=lambda x: x["rank"])


def load_sake_entries(top_n: int) -> Tuple[List[Dict], bool]:
    """Return top-N sake entries from the live API or the static fallback.

    Returns:
        (entries, used_fallback) — used_fallback is True when the static
        dataset was used instead of the live API.
    """
    entries = _api_entries(top_n)
    if entries:
        return entries, False
    return _load_fallback_entries()[:top_n], True


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_network_graph(top_n: int = 25) -> Tuple[List, List, List, bool]:
    """Build agraph Nodes, Edges and gallery metadata for the top-N sake.

    Graph structure:
    - Dot node  : sake brand  (color = flavor type, size ∝ rank)
    - Box node  : prefecture  (color = geographic region)
    - Ellipse   : flavor type (large, always visible)
    - Edges     : sake → prefecture, sake → flavor type

    Returns:
        (nodes, edges, sake_info_list, used_fallback)
    """
    entries, used_fallback = load_sake_entries(top_n)
    if not entries:
        return [], [], [], False

    nodes: List[Node] = []
    edges: List[Edge] = []
    sake_info_list: List[Dict] = []
    added_prefectures: set = set()
    added_flavors: set = set()

    for entry in entries:
        brand_id   = entry["brand_id"]
        brand_name = entry["name"]
        rank       = entry["rank"]
        prefecture = entry["prefecture"]
        flavor_type = entry["flavor_type"]

        flavor_info  = FLAVOR_TYPES[flavor_type]
        flavor_color = flavor_info["color"]
        # Compute region once — used for both the prefecture node color and edge color
        region = PREFECTURE_TO_REGION.get(prefecture, "Unknown")

        node_size = max(12, 36 - (rank - 1) * 0.7)

        nodes.append(Node(
            id=f"sake_{brand_id}",
            label=brand_name,
            size=int(node_size),
            shape="dot",
            color=flavor_color,
            title=f"#{rank} {brand_name} | {prefecture} | {flavor_info['emoji']} {flavor_type}",
        ))

        if prefecture not in added_prefectures:
            nodes.append(Node(
                id=f"pref_{prefecture}",
                label=prefecture,
                size=22,
                shape="box",
                color=REGION_COLORS.get(region, "#808080"),
                title=f"📍 {prefecture} ({region} Region)",
            ))
            added_prefectures.add(prefecture)

        if flavor_type not in added_flavors:
            nodes.append(Node(
                id=f"flavor_{flavor_type}",
                label=f"{flavor_info['emoji']} {flavor_type}",
                size=32,
                shape="ellipse",
                color=flavor_color,
                title=f"{flavor_type}: {flavor_info['desc']} | {flavor_info['ja']}",
            ))
            added_flavors.add(flavor_type)

        edges.append(Edge(
            source=f"sake_{brand_id}",
            target=f"pref_{prefecture}",
            color=REGION_COLORS.get(region, "#AAAAAA"),
            width=1,
        ))
        edges.append(Edge(
            source=f"sake_{brand_id}",
            target=f"flavor_{flavor_type}",
            color=flavor_color,
            width=1.5,
        ))

        sake_info_list.append({
            "brand_id":   brand_id,
            "name":       brand_name,
            "rank":       rank,
            "prefecture": prefecture,
            "flavor_type": flavor_type,
            "flavor_info": flavor_info,
        })

    return nodes, edges, sake_info_list, used_fallback


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _sake_card_html(sake: Dict) -> str:
    """Build an HTML card for one sake entry with image + emoji fallback."""
    brand_id    = sake["brand_id"]
    flavor_info = sake["flavor_info"]
    color       = flavor_info.get("color", "#CCCCCC")
    emoji       = flavor_info.get("emoji", "🍶")
    image_url   = f"https://sakenowa.com/img/brands/{brand_id}.jpg"
    # Only link to real sakenowa brand pages (fallback IDs start at 90001)
    page_url = (
        f"https://sakenowa.com/brand/{brand_id}"
        if brand_id < 90000
        else f"https://sakenowa.com/en/ranking"
    )

    return f"""
    <div style="border:1px solid #e0e0e0; border-radius:10px; overflow:hidden;
                text-align:center; background:#fff;
                box-shadow:0 2px 6px rgba(0,0,0,0.08); height:100%;">
      <a href="{page_url}" target="_blank" style="text-decoration:none; color:inherit;">
        <div style="position:relative; background:#f5f5f5; min-height:120px;
                    display:flex; align-items:center; justify-content:center;">
          <img src="{image_url}"
               style="width:100%; max-height:140px; object-fit:cover; display:block;"
               onerror="this.style.display='none';
                        document.getElementById('fb_{brand_id}').style.display='flex';" />
          <div id="fb_{brand_id}"
               style="display:none; position:absolute; top:0; left:0; right:0; bottom:0;
                      background:{color}; align-items:center; justify-content:center;
                      font-size:3rem; min-height:120px;">{emoji}</div>
        </div>
        <div style="padding:8px 6px;">
          <div style="background:{color}; color:white; font-size:10px; font-weight:bold;
                      padding:2px 6px; border-radius:10px; display:inline-block;
                      margin-bottom:4px;">#{sake['rank']}</div>
          <div style="font-size:13px; font-weight:600; color:#333;
                      line-height:1.3; margin-bottom:3px;">{sake['name']}</div>
          <div style="font-size:11px; color:#666;">
            {sake['prefecture']} &nbsp;|&nbsp; {emoji} {sake['flavor_type']}
          </div>
        </div>
      </a>
    </div>
    """


def display_sake_gallery(sake_info_list: List[Dict], lang: str = "en") -> None:
    """Render a card grid of top sake with images from sakenowa.com.

    Browser-side onerror swaps a broken image for a colored emoji tile,
    so the gallery always renders even when CDN images are unavailable.
    """
    if not sake_info_list:
        return

    st.divider()
    if lang == "en":
        st.subheader("🍶 Top Sake Gallery")
        st.caption(
            "Sake bottle images from [sakenowa.com](https://sakenowa.com) • "
            "Click any card to open the sake's page."
        )
    else:
        st.subheader("🍶 人気日本酒ギャラリー")
        st.caption(
            "日本酒ラベル画像: [sakenowa.com](https://sakenowa.com) より • "
            "カードをクリックすると詳細ページが開きます。"
        )

    cols_per_row = 5
    for row_start in range(0, min(len(sake_info_list), 20), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, sake in enumerate(sake_info_list[row_start: row_start + cols_per_row]):
            with cols[col_idx]:
                st.markdown(_sake_card_html(sake), unsafe_allow_html=True)


def display_sake_network() -> None:
    """Render the complete sake network section:
    flavor legend → node-type legend → agraph → image gallery.
    """
    if not AGRAPH_AVAILABLE:
        st.error(
            "⚠️ `streamlit-agraph` is not installed.\n\n"
            "Install it with: `pip install streamlit-agraph`"
        )
        return

    lang = st.session_state.get("language", "en")

    if lang == "en":
        st.markdown(
            "Explore how Japan's top-ranked sake relate to their home **prefectures** "
            "and **flavor profiles**. Drag nodes to rearrange — click a node to see details."
        )
    else:
        st.markdown(
            "日本のトップランク日本酒と**産地（都道府県）**・**フレーバープロファイル**の関係をインタラクティブに探索。"
            "ノードをドラッグして動かしたり、クリックして詳細を確認できます。"
        )

    ctrl_col, legend_col = st.columns([1, 3])
    with ctrl_col:
        top_n = st.slider(
            "Sake count | 表示数" if lang == "en" else "表示する日本酒数",
            min_value=10, max_value=50, value=25, step=5,
            key="network_top_n",
        )
    with legend_col:
        st.caption("**Flavor type colors:**" if lang == "en" else "**フレーバータイプの色:**")
        badges = " &nbsp; ".join(
            f'<span style="background:{info["color"]}; color:#fff; '
            f'padding:3px 9px; border-radius:12px; font-size:12px; white-space:nowrap;">'
            f'{info["emoji"]} {name}</span>'
            for name, info in FLAVOR_TYPES.items()
        )
        st.markdown(badges, unsafe_allow_html=True)

    st.caption(
        "🟦 **Box** = Prefecture (by region) &nbsp;|&nbsp; "
        "⬤ **Dot** = Sake brand (by flavor) &nbsp;|&nbsp; "
        "◉ **Ellipse** = Flavor type"
        if lang == "en" else
        "🟦 **四角** = 都道府県（地方別） &nbsp;|&nbsp; "
        "⬤ **丸** = 日本酒（フレーバー別） &nbsp;|&nbsp; "
        "◉ **楕円** = フレーバータイプ"
    )

    with st.spinner("Loading sake ranking data… | ランキングデータを読み込み中…"):
        nodes, edges, sake_info_list, used_fallback = build_network_graph(top_n=top_n)

    if not nodes:
        st.error(
            "Could not load sake data. Please refresh the page."
            if lang == "en" else
            "データを読み込めませんでした。ページを再読み込みしてください。"
        )
        return

    if used_fallback:
        st.info(
            "📦 Showing curated sake data — live rankings from sakenowa.com are "
            "temporarily unavailable."
            if lang == "en" else
            "📦 キュレーション済みの日本酒データを表示しています"
            "（sakenowa.com のライブランキングは一時的に利用できません）。"
        )

    selected_node = agraph(
        nodes=nodes,
        edges=edges,
        config=Config(width=1000, height=680, directed=False, physics=True, hierarchical=False),
    )

    if selected_node:
        st.info(
            f"Selected: **{selected_node}**" if lang == "en"
            else f"選択中: **{selected_node}**"
        )

    display_sake_gallery(sake_info_list, lang=lang)
