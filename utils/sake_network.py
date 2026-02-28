"""
Sake Network Graph - Interactive visualization of Japanese sake rankings,
prefectures, and flavor profiles using streamlit-agraph.

Data source: Sakenowa public API (https://muro.sakenowa.com/sakenowa-data/api)
"""
import requests
import streamlit as st
from typing import Optional, Dict, List, Tuple

try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

SAKENOWA_API_BASE = "https://muro.sakenowa.com/sakenowa-data/api"

# Flavor type definitions with colors and metadata
# Mapped from sakenowa flavor chart dimensions:
#   f1=Fruity/Aromatic, f2=Mellow/Light, f3=Sweet,
#   f4=Dry/Sharp, f5=Rich/Full-body, f6=Aged/Complex
FLAVOR_TYPES = {
    "Fruity": {
        "color": "#E85D9E",
        "emoji": "🍎",
        "ja": "フルーティ・華やか",
        "desc": "Aromatic, fruity notes",
    },
    "Light": {
        "color": "#4AABDB",
        "emoji": "💧",
        "ja": "穏やか・軽快",
        "desc": "Smooth and light",
    },
    "Sweet": {
        "color": "#F4B942",
        "emoji": "🍯",
        "ja": "甘い・まろやか",
        "desc": "Sweet and mellow",
    },
    "Dry": {
        "color": "#5DBD7A",
        "emoji": "🌾",
        "ja": "辛口・シャープ",
        "desc": "Dry and crisp",
    },
    "Full Body": {
        "color": "#A0522D",
        "emoji": "🍺",
        "ja": "どっしり・重厚",
        "desc": "Rich and full-bodied",
    },
    "Aged": {
        "color": "#8B6914",
        "emoji": "🪨",
        "ja": "熟成・複雑",
        "desc": "Aged and complex",
    },
    "Sparkling": {
        "color": "#6EB5FF",
        "emoji": "✨",
        "ja": "スパークリング・発泡",
        "desc": "Sparkling with bubbles",
    },
}

# Prefecture to geographic region mapping
PREFECTURE_TO_REGION = {
    "北海道": "Hokkaido",
    "青森": "Tohoku", "岩手": "Tohoku", "宮城": "Tohoku",
    "秋田": "Tohoku", "山形": "Tohoku", "福島": "Tohoku",
    "茨城": "Kanto", "栃木": "Kanto", "群馬": "Kanto",
    "埼玉": "Kanto", "千葉": "Kanto", "東京": "Kanto", "神奈川": "Kanto",
    "新潟": "Chubu", "富山": "Chubu", "石川": "Chubu", "福井": "Chubu",
    "山梨": "Chubu", "長野": "Chubu", "岐阜": "Chubu",
    "静岡": "Chubu", "愛知": "Chubu",
    "三重": "Kinki", "滋賀": "Kinki", "京都": "Kinki",
    "大阪": "Kinki", "兵庫": "Kinki", "奈良": "Kinki", "和歌山": "Kinki",
    "鳥取": "Chugoku", "島根": "Chugoku", "岡山": "Chugoku",
    "広島": "Chugoku", "山口": "Chugoku",
    "徳島": "Shikoku", "香川": "Shikoku", "愛媛": "Shikoku", "高知": "Shikoku",
    "福岡": "Kyushu", "佐賀": "Kyushu", "長崎": "Kyushu",
    "熊本": "Kyushu", "大分": "Kyushu", "宮崎": "Kyushu",
    "鹿児島": "Kyushu", "沖縄": "Kyushu",
}

REGION_COLORS = {
    "Hokkaido": "#4682B4",
    "Tohoku": "#FF8C00",
    "Kanto": "#4169E1",
    "Chubu": "#20B2AA",
    "Kinki": "#DC143C",
    "Chugoku": "#32CD32",
    "Shikoku": "#9370DB",
    "Kyushu": "#FF6347",
    "Unknown": "#808080",
}


@st.cache_data(ttl=3600)
def fetch_sakenowa_data() -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict], Optional[Dict]]:
    """
    Fetch and cache sakenowa ranking data (brands, areas, rankings, flavor charts).

    Returns:
        Tuple of (brands_dict, areas_dict, rankings_data, flavors_dict)
        where each dict is keyed by ID, or None on failure.
    """
    try:
        brands_resp = requests.get(f"{SAKENOWA_API_BASE}/brands", timeout=15)
        brands_resp.raise_for_status()
        brands = {b["id"]: b for b in brands_resp.json().get("brands", [])}

        areas_resp = requests.get(f"{SAKENOWA_API_BASE}/areas", timeout=15)
        areas_resp.raise_for_status()
        areas = {a["id"]: a for a in areas_resp.json().get("areas", [])}

        rankings_resp = requests.get(f"{SAKENOWA_API_BASE}/rankings", timeout=15)
        rankings_resp.raise_for_status()
        rankings = rankings_resp.json()

        flavors_resp = requests.get(f"{SAKENOWA_API_BASE}/flavor-charts", timeout=15)
        flavors_resp.raise_for_status()
        flavors = {f["brandId"]: f for f in flavors_resp.json().get("flavorCharts", [])}

        return brands, areas, rankings, flavors

    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching sake data from sakenowa.com: {e}")
        return None, None, None, None
    except Exception as e:
        st.error(f"Error processing sake data: {e}")
        return None, None, None, None


def classify_flavor(brand_name: str, flavor_chart: Optional[dict]) -> str:
    """
    Classify a sake brand into its primary flavor category.

    Args:
        brand_name: Sake brand name (used to detect sparkling types by keyword)
        flavor_chart: Sakenowa flavor dict with f1-f6 float scores

    Returns:
        Flavor type key from FLAVOR_TYPES
    """
    sparkling_keywords = ["スパークリング", "発泡", "微発泡", "Sparkling", "sparkling", "awa"]
    if any(kw in brand_name for kw in sparkling_keywords):
        return "Sparkling"

    if not flavor_chart:
        return "Light"

    scores = {
        "Fruity": flavor_chart.get("f1", 0),
        "Light": flavor_chart.get("f2", 0),
        "Sweet": flavor_chart.get("f3", 0),
        "Dry": flavor_chart.get("f4", 0),
        "Full Body": flavor_chart.get("f5", 0),
        "Aged": flavor_chart.get("f6", 0),
    }
    return max(scores, key=scores.get)


def build_network_graph(top_n: int = 25) -> Tuple[List, List, List]:
    """
    Build network graph nodes and edges for the top-ranked sake.

    Graph structure:
    - Sake brand nodes (dot shape, colored by flavor type, sized by rank)
    - Prefecture nodes (box shape, colored by region)
    - Flavor type nodes (ellipse shape, large, colored by type)
    - Edges: sake → prefecture, sake → flavor type

    Args:
        top_n: Number of top-ranked sake to include

    Returns:
        Tuple of (nodes, edges, sake_info_list) where sake_info_list
        contains dicts of metadata for each sake shown in the gallery.
    """
    brands, areas, rankings_data, flavors = fetch_sakenowa_data()

    if not brands or not rankings_data:
        return [], [], []

    nodes: List[Node] = []
    edges: List[Edge] = []
    sake_info_list: List[Dict] = []

    added_prefectures: set = set()
    added_flavors: set = set()

    # Extract the overall ranking list
    all_rankings = rankings_data.get("rankings", [])
    ranking_list = []
    for r in all_rankings:
        if r.get("id") == "overall":
            ranking_list = r.get("ranking", [])
            break
    if not ranking_list and all_rankings:
        ranking_list = all_rankings[0].get("ranking", [])

    if not ranking_list:
        return [], [], []

    for ranked_item in ranking_list[:top_n]:
        brand_id = ranked_item.get("brandId")
        rank = ranked_item.get("rank", 0)

        if brand_id not in brands:
            continue

        brand = brands[brand_id]
        brand_name = brand.get("name", f"Sake #{brand_id}")
        area_id = brand.get("areaId")

        area = areas.get(area_id, {}) if areas else {}
        prefecture = area.get("name", "不明")

        flavor_chart = flavors.get(brand_id)
        flavor_type = classify_flavor(brand_name, flavor_chart)
        flavor_info = FLAVOR_TYPES[flavor_type]
        flavor_color = flavor_info["color"]

        # Node size: rank 1 = 35px, decreasing with rank
        node_size = max(12, 36 - (rank - 1) * 0.7)

        # Sake brand node
        nodes.append(Node(
            id=f"sake_{brand_id}",
            label=brand_name,
            size=int(node_size),
            shape="dot",
            color=flavor_color,
            title=f"#{rank} {brand_name} | {prefecture} | {flavor_info['emoji']} {flavor_type}",
        ))

        # Prefecture node (add once)
        if prefecture not in added_prefectures:
            region = PREFECTURE_TO_REGION.get(prefecture, "Unknown")
            pref_color = REGION_COLORS.get(region, "#808080")
            nodes.append(Node(
                id=f"pref_{prefecture}",
                label=prefecture,
                size=22,
                shape="box",
                color=pref_color,
                title=f"📍 {prefecture} ({region} Region)",
            ))
            added_prefectures.add(prefecture)

        # Flavor type node (add once)
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

        # Edge: sake → prefecture
        region = PREFECTURE_TO_REGION.get(prefecture, "Unknown")
        edges.append(Edge(
            source=f"sake_{brand_id}",
            target=f"pref_{prefecture}",
            color=REGION_COLORS.get(region, "#AAAAAA"),
            width=1,
        ))

        # Edge: sake → flavor type
        edges.append(Edge(
            source=f"sake_{brand_id}",
            target=f"flavor_{flavor_type}",
            color=flavor_color,
            width=1.5,
        ))

        sake_info_list.append({
            "brand_id": brand_id,
            "name": brand_name,
            "rank": rank,
            "prefecture": prefecture,
            "flavor_type": flavor_type,
            "flavor_info": flavor_info,
        })

    return nodes, edges, sake_info_list


def _sake_card_html(sake: Dict) -> str:
    """Build an HTML card for a single sake entry with image + fallback."""
    brand_id = sake["brand_id"]
    flavor_info = sake["flavor_info"]
    color = flavor_info.get("color", "#CCCCCC")
    emoji = flavor_info.get("emoji", "🍶")
    image_url = f"https://sakenowa.com/img/brands/{brand_id}.jpg"
    brand_page_url = f"https://sakenowa.com/brand/{brand_id}"
    rank_label = f"#{sake['rank']}"

    return f"""
    <div style="
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        text-align: center;
        background: #fff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        height: 100%;
    ">
        <a href="{brand_page_url}" target="_blank" style="text-decoration:none; color:inherit;">
            <div style="position:relative; background:#f5f5f5; min-height:120px; display:flex; align-items:center; justify-content:center;">
                <img
                    src="{image_url}"
                    style="width:100%; max-height:140px; object-fit:cover; display:block;"
                    onerror="this.style.display='none'; document.getElementById('fb_{brand_id}').style.display='flex';"
                />
                <div id="fb_{brand_id}" style="
                    display:none;
                    position:absolute; top:0; left:0; right:0; bottom:0;
                    background:{color};
                    align-items:center; justify-content:center;
                    font-size:3rem; min-height:120px;
                ">{emoji}</div>
            </div>
            <div style="padding: 8px 6px;">
                <div style="
                    background:{color};
                    color:white;
                    font-size:10px;
                    font-weight:bold;
                    padding:2px 6px;
                    border-radius:10px;
                    display:inline-block;
                    margin-bottom:4px;
                ">{rank_label}</div>
                <div style="font-size:13px; font-weight:600; color:#333; line-height:1.3; margin-bottom:3px;">{sake['name']}</div>
                <div style="font-size:11px; color:#666;">{sake['prefecture']} &nbsp;|&nbsp; {emoji} {sake['flavor_type']}</div>
            </div>
        </a>
    </div>
    """


def display_sake_gallery(sake_info_list: List[Dict], lang: str = "en"):
    """
    Display a card gallery of top-ranked sake with images from sakenowa.com.
    Images are fetched directly in the browser; broken images fall back to
    a colored emoji tile.

    Args:
        sake_info_list: List of sake metadata dicts from build_network_graph
        lang: UI language ("en" or "ja")
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

    display_sake = sake_info_list[:20]
    cols_per_row = 5

    for row_start in range(0, len(display_sake), cols_per_row):
        row_sake = display_sake[row_start: row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col_idx, sake in enumerate(row_sake):
            with cols[col_idx]:
                st.markdown(_sake_card_html(sake), unsafe_allow_html=True)


def display_sake_network():
    """
    Render the full sake network graph section including:
    - Flavor legend
    - Node-type legend
    - Interactive agraph visualization
    - Image gallery of top-ranked sake
    """
    if not AGRAPH_AVAILABLE:
        st.error(
            "⚠️ `streamlit-agraph` package is not installed.\n\n"
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

    # Controls row
    ctrl_col, legend_col = st.columns([1, 3])
    with ctrl_col:
        top_n = st.slider(
            "Sake count | 表示数" if lang == "en" else "表示する日本酒数",
            min_value=10,
            max_value=50,
            value=25,
            step=5,
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
        "🟦 **Box** = Prefecture (colored by region) &nbsp;|&nbsp; "
        "⬤ **Dot** = Sake brand (colored by flavor) &nbsp;|&nbsp; "
        "◉ **Ellipse** = Flavor type"
        if lang == "en"
        else
        "🟦 **四角** = 都道府県（地方別の色） &nbsp;|&nbsp; "
        "⬤ **丸** = 日本酒（フレーバー別の色） &nbsp;|&nbsp; "
        "◉ **楕円** = フレーバータイプ"
    )

    # Build graph
    with st.spinner(
        "Loading sake ranking data… | ランキングデータを読み込み中…"
    ):
        nodes, edges, sake_info_list = build_network_graph(top_n=top_n)

    if not nodes:
        st.error(
            "Could not load sake ranking data. Please check your internet connection and try again."
            if lang == "en"
            else "日本酒ランキングデータを読み込めませんでした。接続を確認して再度お試しください。"
        )
        return

    config = Config(
        width=1000,
        height=680,
        directed=False,
        physics=True,
        hierarchical=False,
    )

    selected_node = agraph(nodes=nodes, edges=edges, config=config)

    if selected_node:
        st.info(
            f"Selected node: **{selected_node}**"
            if lang == "en"
            else f"選択中のノード: **{selected_node}**"
        )

    # Image gallery below the graph
    display_sake_gallery(sake_info_list, lang=lang)
