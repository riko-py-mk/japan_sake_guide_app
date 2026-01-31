"""
Japanese Sake Guide App - Main Streamlit Application

An AI-powered assistant to help users discover and learn about Japanese sake.
Supports both English and Japanese languages.
"""
import streamlit as st
from typing import Optional
import json
import re

from agents.sake_agent import create_sake_agent, run_sake_agent
from utils.helpers import detect_language, EXAMPLE_PROMPTS, SIDEBAR_EXAMPLE_PROMPTS


# Page configuration
st.set_page_config(
    page_title="Japanese Sake Guide | 日本酒ガイド",
    page_icon="🍶",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .sake-emoji {
        font-size: 3rem;
    }
    .stChatMessage {
        padding: 1rem;
    }
    .example-prompt {
        cursor: pointer;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        background-color: rgba(196, 30, 58, 0.1);
    }
    .example-prompt:hover {
        background-color: rgba(196, 30, 58, 0.2);
    }
</style>
""", unsafe_allow_html=True)


def check_api_keys() -> tuple[bool, str]:
    """
    Check if required API keys are configured.

    Returns:
        Tuple of (success, error_message)
    """
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    tavily_key = st.secrets.get("TAVILY_API_KEY", "")

    if not openai_key:
        return False, "OPENAI_API_KEY is not configured. Please add it to your Streamlit secrets."
    if not tavily_key:
        return False, "TAVILY_API_KEY is not configured. Please add it to your Streamlit secrets."

    return True, ""


def initialize_agent():
    """Initialize the sake guide agent."""
    if "agent" not in st.session_state:
        openai_key = st.secrets.get("OPENAI_API_KEY", "")
        tavily_key = st.secrets.get("TAVILY_API_KEY", "")
        instagram_token = st.secrets.get("INSTAGRAM_ACCESS_TOKEN", None)

        st.session_state.agent = create_sake_agent(
            openai_api_key=openai_key,
            tavily_api_key=tavily_key,
            instagram_token=instagram_token,
        )


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "language" not in st.session_state:
        st.session_state.language = "en"


def render_sidebar():
    """Render the sidebar with settings and information."""
    with st.sidebar:
        st.header("Settings | 設定")

        # Language selector
        language = st.radio(
            "Language | 言語",
            options=["English", "日本語"],
            index=0 if st.session_state.language == "en" else 1,
        )
        st.session_state.language = "en" if language == "English" else "ja"

        st.divider()

        # Example prompts by tool
        lang = st.session_state.language
        if lang == "en":
            st.subheader("Example Prompts")
        else:
            st.subheader("質問の例")

        prompts_by_tool = SIDEBAR_EXAMPLE_PROMPTS[lang]
        for tool_name, prompts in prompts_by_tool.items():
            st.caption(f"**{tool_name}**")
            for prompt in prompts:
                st.caption(f"• {prompt}")

        st.divider()

        # Data sources
        st.subheader("Data Sources | データソース")
        st.caption("• [Sakenowa](https://sakenowa.com/en/ranking)")
        st.caption("• [Saketime](https://www.saketime.jp/ranking/)")
        st.caption("• Twitter/X, Instagram, Facebook")

        st.divider()

        # Clear chat button
        if st.button("Clear Chat | チャットをクリア", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()

        st.divider()

        # About section
        st.subheader("About | このアプリについて")
        if st.session_state.language == "en":
            st.caption(
                "This AI-powered app helps you discover Japanese sake. "
                "Ask about recommendations, specific brands, or sake knowledge!"
            )
        else:
            st.caption(
                "このAIアプリは日本酒の発見をお手伝いします。"
                "おすすめ、特定の銘柄、日本酒の知識について質問してください！"
            )


def render_example_prompts():
    """Render example prompt buttons."""
    lang = st.session_state.language

    if st.session_state.language == "en":
        st.caption("Try asking:")
    else:
        st.caption("こんな質問をしてみてください：")

    cols = st.columns(2)
    for idx, prompt in enumerate(EXAMPLE_PROMPTS[lang][:4]):
        col = cols[idx % 2]
        with col:
            if st.button(prompt, key=f"example_{idx}", use_container_width=True):
                return prompt
    return None


def extract_map_data(response_text: str) -> Optional[dict]:
    """
    Extract map data from the agent response.

    Args:
        response_text: The response text from the agent

    Returns:
        Dictionary with map data or None if no map data found
    """
    try:
        # Look for MAP_DATA_START and MAP_DATA_END markers
        pattern = r'MAP_DATA_START\s*\n(.*?)\nMAP_DATA_END'
        match = re.search(pattern, response_text, re.DOTALL)

        if match:
            json_str = match.group(1).strip()
            return json.loads(json_str)
    except Exception as e:
        st.error(f"Error parsing map data: {str(e)}")

    return None


def display_map(map_data: dict):
    """
    Display an interactive map with sake location markers.

    Args:
        map_data: Dictionary containing search_location and locations list
    """
    try:
        import folium
        from streamlit_folium import folium_static
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
        import time
    except ImportError:
        st.warning("Map libraries not available. Please install folium, streamlit-folium, and geopy.")
        return

    search_location = map_data.get("search_location", "Tokyo, Japan")
    locations = map_data.get("locations", [])

    if not locations:
        return

    # Initialize geocoder
    geolocator = Nominatim(user_agent="japanese_sake_guide_app")

    # Get coordinates for the search location
    try:
        time.sleep(1)  # Rate limiting
        main_location = geolocator.geocode(search_location + ", Japan")
        if main_location:
            center_lat = main_location.latitude
            center_lon = main_location.longitude
        else:
            # Default to Tokyo if geocoding fails
            center_lat = 35.6762
            center_lon = 139.6503
    except (GeocoderTimedOut, GeocoderServiceError):
        # Default to Tokyo if geocoding fails
        center_lat = 35.6762
        center_lon = 139.6503

    # Create map centered on the search location
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )

    # Add markers for each location
    # Since we don't have exact coordinates, we'll add a single marker for the search area
    # with a popup containing all the locations
    popup_html = f"<div style='width: 300px'><h4>Sake Locations in {search_location}</h4><ul>"

    for loc in locations[:10]:  # Limit to 10 locations
        name = loc.get('name', 'Unknown')
        url = loc.get('url', '#')
        description = loc.get('description', '')[:100]

        popup_html += f"<li><b><a href='{url}' target='_blank'>{name}</a></b>"
        if description:
            popup_html += f"<br><small>{description}...</small>"
        popup_html += "</li>"

    popup_html += "</ul></div>"

    # Add a marker for the search location
    folium.Marker(
        [center_lat, center_lon],
        popup=folium.Popup(popup_html, max_width=350),
        tooltip=f"Click for sake locations in {search_location}",
        icon=folium.Icon(color='red', icon='glass')
    ).add_to(m)

    # Display the map
    st.subheader("📍 Map View")
    folium_static(m, width=700, height=500)


def render_chat():
    """Render the chat interface."""
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Extract and remove map data from display
            content = message["content"]

            if message["role"] == "assistant":
                # Check for map data
                map_data = extract_map_data(content)

                # Remove map data markers from display text
                content = re.sub(r'={50,}\s*MAP_DATA_START.*?MAP_DATA_END\s*={50,}', '', content, flags=re.DOTALL)

                # Display the text content
                st.markdown(content)

                # Display map if data exists
                if map_data:
                    display_map(map_data)
            else:
                st.markdown(content)


def process_user_input(user_input: str):
    """Process user input and generate response."""
    # Add user message to display
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching for sake information... | 日本酒情報を検索中..."):
            try:
                response, new_history = run_sake_agent(
                    st.session_state.agent,
                    user_input,
                    st.session_state.chat_history,
                )

                st.session_state.chat_history = new_history

                # Check for map data
                map_data = extract_map_data(response)

                # Remove map data markers from display text
                display_text = re.sub(r'={50,}\s*MAP_DATA_START.*?MAP_DATA_END\s*={50,}', '', response, flags=re.DOTALL)

                # Display the text
                st.markdown(display_text)

                # Display map if available
                if map_data:
                    display_map(map_data)

                # Add assistant message to display (with full response including map data)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"An error occurred: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Render header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<p class="sake-emoji">🍶</p>', unsafe_allow_html=True)
    st.title("Japanese Sake Guide | 日本酒ガイド")
    st.caption("Your AI sommelier for discovering Japanese sake | 日本酒を発見するAIソムリエ")
    st.markdown('</div>', unsafe_allow_html=True)

    # Check API keys
    keys_ok, error_message = check_api_keys()

    if not keys_ok:
        st.error(error_message)
        st.info(
            "To use this app, you need to configure API keys in Streamlit secrets:\n\n"
            "1. **OPENAI_API_KEY**: Get from [OpenAI](https://platform.openai.com/api-keys)\n"
            "2. **TAVILY_API_KEY**: Get from [Tavily](https://tavily.com/)\n"
            "3. **INSTAGRAM_ACCESS_TOKEN** (optional): For Instagram search\n\n"
            "Add these to `.streamlit/secrets.toml` or in Streamlit Cloud settings."
        )
        return

    # Initialize agent
    initialize_agent()

    # Render sidebar
    render_sidebar()

    # Show welcome message if no messages
    if not st.session_state.messages:
        lang = st.session_state.language

        if lang == "en":
            st.markdown(
                "Welcome to the Japanese Sake Guide! I can help you:\n\n"
                "- **Find recommendations** based on your taste preferences\n"
                "- **Learn about specific sake** brands and breweries\n"
                "- **Discover top-rated sake** from ranking websites\n"
                "- **Explore social media** for sake content and reviews\n"
                "- **Find sake shops & restaurants** near you with interactive maps\n\n"
                "Ask me anything about Japanese sake!"
            )
        else:
            st.markdown(
                "日本酒ガイドへようこそ！以下のことをお手伝いできます：\n\n"
                "- お好みに合わせた**おすすめの日本酒**を探す\n"
                "- **特定の銘柄や蔵元**について詳しく知る\n"
                "- ランキングサイトから**人気の日本酒**を発見する\n"
                "- **SNS**で日本酒のコンテンツやレビューを探索する\n"
                "- **日本酒販売店や飲食店**をマップで探す\n\n"
                "日本酒について何でも聞いてください！"
            )

        # Show example prompts
        selected_prompt = render_example_prompts()
        if selected_prompt:
            process_user_input(selected_prompt)
            st.rerun()

    # Render chat history
    render_chat()

    # Chat input
    if st.session_state.language == "en":
        placeholder = "Ask about sake... (e.g., 'Recommend a fruity sake')"
    else:
        placeholder = "日本酒について質問... (例: 'フルーティな日本酒をおすすめして')"

    if user_input := st.chat_input(placeholder):
        process_user_input(user_input)
        st.rerun()


if __name__ == "__main__":
    main()
