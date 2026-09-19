"""
Sake Network Graph - Interactive visualization of Japanese sake rankings,
prefectures, and flavor profiles using streamlit-agraph.

Data source: utils/sake_ranking_fallback.json
Refreshed daily at 05:00 JST by the update-sake-rankings GitHub Actions workflow.

Flavour metadata, region lookups and data loading all live in
utils/sake_rankings.py so that this module and the CI refresh script cannot
drift apart.
"""
from typing import Dict, List, Tuple

import streamlit as st

from .sake_rankings import (
    FLAVOR_TYPES,
    REGION_COLORS,
    load_ranking_data,
    load_ranking_entries,
    prefecture_region,
    region_color,
)

try:
    from streamlit_agraph import Config, Edge, Node, agraph
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _load_entries() -> List[Dict]:
    """Load and cache the ranking entries from the pre-built JSON file."""
    return load_ranking_entries()


@st.cache_data(ttl=3600)
def get_ranking_as_of() -> str:
    """Return the ISO date string when the ranking data was last fetched, or ''."""
    return load_ranking_data().get("as_of") or ""


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

        flavor_info  = FLAVOR_TYPES.get(flavor_type, FLAVOR_TYPES["Unknown"])
        flavor_color = flavor_info["color"]
        region       = prefecture_region(prefecture)

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
                color=region_color(prefecture),
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
            color=region_color(prefecture),
            width=1,
        ))
        edges.append(Edge(
            source=f"sake_{brand_id}",
            target=f"flavor_{flavor_type}",
            color=flavor_color,
            width=1.5,
        ))

    return nodes, edges


def _badges(items) -> str:
    """Render ``(color, label)`` pairs as inline coloured pills."""
    return " &nbsp; ".join(
        f'<span style="background:{color}; color:#fff; '
        f'padding:3px 9px; border-radius:12px; font-size:12px; white-space:nowrap;">'
        f'{label}</span>'
        for color, label in items
    )


def display_sake_network() -> None:
    """Render the sake network section:
    flavor legend → region legend → node-type legend → agraph.
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

    # Only legend entries actually present in the current graph are shown.
    entries = _load_entries()[:top_n]
    shown_flavors = {e["flavor_type"] for e in entries}
    shown_regions = {prefecture_region(e["prefecture"]) for e in entries}

    with legend_col:
        st.caption("**Flavor type colors:**" if lang == "en" else "**フレーバータイプの色:**")
        st.markdown(
            _badges(
                (info["color"], f'{info["emoji"]} {name}')
                for name, info in FLAVOR_TYPES.items()
                if name in shown_flavors
            ),
            unsafe_allow_html=True,
        )
        st.caption("**Region colors:**" if lang == "en" else "**地方の色:**")
        st.markdown(
            _badges(
                (color, name)
                for name, color in REGION_COLORS.items()
                if name in shown_regions
            ),
            unsafe_allow_html=True,
        )

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
