"""
Sake Network Graph - Interactive visualization of Japanese sake rankings,
prefectures, and flavor profiles using streamlit-agraph.

Data source: utils/sake_ranking_fallback.json
Refreshed daily at 05:00 JST by the update-sake-rankings GitHub Actions workflow.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

try:
    from streamlit_agraph import Config, Edge, Node, agraph
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

_DATA_PATH = Path(__file__).parent / "sake_ranking_fallback.json"

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
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _load_data() -> dict:
    """Load and cache the full ranking payload from the pre-built JSON file."""
    with open(_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    # Support legacy format (plain list) and current format ({as_of, entries})
    if isinstance(raw, list):
        return {"as_of": None, "entries": raw}
    return raw


def _load_entries() -> List[Dict]:
    return sorted(_load_data()["entries"], key=lambda x: x["rank"])


def get_ranking_as_of() -> str:
    """Return the ISO date string when the ranking data was last fetched, or ''."""
    return _load_data().get("as_of") or ""


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_network_graph(top_n: int = 25) -> Tuple[List, List]:
    """Build agraph Nodes and Edges for the top-N sake.

    Graph structure:
    - Dot node  : sake brand  (color = flavor type, size ∝ rank)
    - Box node  : prefecture  (color = geographic region)
    - Ellipse   : flavor type (large, always visible)
    - Edges     : sake → prefecture, sake → flavor type
    """
    entries = _load_entries()[:top_n]
    if not entries:
        return [], []

    nodes: List[Node] = []
    edges: List[Edge] = []
    added_prefectures: set = set()
    added_flavors: set = set()

    for entry in entries:
        brand_id    = entry["brand_id"]
        brand_name  = entry["name"]
        rank        = entry["rank"]
        prefecture  = entry["prefecture"]
        flavor_type = entry["flavor_type"]

        flavor_info  = FLAVOR_TYPES[flavor_type]
        flavor_color = flavor_info["color"]
        region       = PREFECTURE_TO_REGION.get(prefecture, "Unknown")

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

    return nodes, edges


def display_sake_network() -> None:
    """Render the sake network section:
    flavor legend → node-type legend → agraph.
    """
    if not AGRAPH_AVAILABLE:
        st.error(
            "⚠️ `streamlit-agraph` is not installed.\n\n"
            "Install it with: `pip install streamlit-agraph`"
        )
        return

    lang = st.session_state.get("language", "en")

    as_of = get_ranking_as_of()
    if lang == "en":
        st.markdown(
            "Explore how Japan's top-ranked sake relate to their home **prefectures** "
            "and **flavor profiles**. Drag nodes to rearrange — click a node to see details."
        )
        if as_of:
            st.caption(f"Rankings as of {as_of}")
    else:
        st.markdown(
            "日本のトップランク日本酒と**産地（都道府県）**・**フレーバープロファイル**の関係をインタラクティブに探索。"
            "ノードをドラッグして動かしたり、クリックして詳細を確認できます。"
        )
        if as_of:
            st.caption(f"ランキング基準日: {as_of}")

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

    nodes, edges = build_network_graph(top_n=top_n)

    if not nodes:
        st.error(
            "Could not load sake data. Please refresh the page."
            if lang == "en" else
            "データを読み込めませんでした。ページを再読み込みしてください。"
        )
        return

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
