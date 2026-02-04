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
    Google Maps API is optional - the app will work without it but maps won't display.

    Returns:
        Tuple of (success, error_message)
    """
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    tavily_key = st.secrets.get("TAVILY_API_KEY", "")
    google_maps_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")

    if not openai_key:
        return False, "OPENAI_API_KEY is not configured. Please add it to your Streamlit secrets."
    if not tavily_key:
        return False, "TAVILY_API_KEY is not configured. Please add it to your Streamlit secrets."

    # Google Maps is optional
    if not google_maps_key:
        print("WARNING: GOOGLE_MAPS_API_KEY not configured. Maps will not be displayed.")

    return True, ""


def initialize_agent():
    """Initialize the sake guide agent."""
    if "agent" not in st.session_state:
        openai_key = st.secrets.get("OPENAI_API_KEY", "")
        tavily_key = st.secrets.get("TAVILY_API_KEY", "")
        instagram_token = st.secrets.get("INSTAGRAM_ACCESS_TOKEN", None)
        google_maps_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")

        # Store API key status in session state
        st.session_state.google_maps_configured = bool(google_maps_key)

        # Debug logging
        print(f"DEBUG: Initializing agent")
        print(f"  - OpenAI API key: {'✓ configured' if openai_key else '✗ missing'}")
        print(f"  - Tavily API key: {'✓ configured' if tavily_key else '✗ missing'}")
        print(f"  - Google Maps API key: {'✓ configured' if google_maps_key else '✗ missing'}")

        st.session_state.agent = create_sake_agent(
            openai_api_key=openai_key,
            tavily_api_key=tavily_key,
            instagram_token=instagram_token,
            google_maps_api_key=google_maps_key,
        )


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "language" not in st.session_state:
        st.session_state.language = "ja"


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

        # API Configuration Status
        st.subheader("API Status")
        google_maps_status = st.session_state.get("google_maps_configured", False)
        if google_maps_status:
            st.success("✓ Google Maps API configured")
            st.caption("Maps with photos and reviews enabled")
        else:
            st.warning("⚠️ Google Maps API not configured")
            st.caption("Add GOOGLE_MAPS_API_KEY to enable maps")

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
        # The pattern should match across multiple lines with any whitespace
        pattern = r'MAP_DATA_START\s*(.*?)\s*MAP_DATA_END'
        match = re.search(pattern, response_text, re.DOTALL)

        if match:
            json_str = match.group(1).strip()
            map_data = json.loads(json_str)
            print(f"✓ DEBUG: Successfully extracted map data with {len(map_data.get('locations', []))} locations")
            st.info(f"🗺️ Map data found: {len(map_data.get('locations', []))} locations - preparing map...")
            return map_data
        else:
            print("✗ DEBUG: No MAP_DATA markers found in response")
            # Check if response mentions map but doesn't have data
            if "地図" in response_text or "map" in response_text.lower():
                print("  Response mentions map but no MAP_DATA markers found")
                st.warning("⚠️ Response mentions a map but map data wasn't included. This may mean the Google Maps API key is not configured.")
    except json.JSONDecodeError as e:
        print(f"✗ DEBUG: JSON decode error: {str(e)}")
        st.error(f"Error parsing map data JSON: {str(e)}")
    except Exception as e:
        print(f"✗ DEBUG: General error extracting map data: {str(e)}")
        st.error(f"Error parsing map data: {str(e)}")

    return None


def display_map(map_data: dict):
    """
    Display an interactive Google Map with sake location markers, photos, and reviews.

    Args:
        map_data: Dictionary containing center coordinates and locations list with photos and reviews
    """
    import streamlit.components.v1 as components

    print(f"DEBUG: display_map called with data: {map_data.keys() if map_data else 'None'}")

    google_maps_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
    if not google_maps_key:
        st.warning(
            "📍 **Google Maps API key not configured.**\n\n"
            "To display interactive maps with photos and reviews, please add your Google Maps API key to `.streamlit/secrets.toml`\n\n"
            "Get your API key from the [Google Cloud Console](https://console.cloud.google.com/)"
        )
        print("DEBUG: No Google Maps API key found")
        return

    search_location = map_data.get("search_location", "Tokyo, Japan")
    sake_name = map_data.get("sake_name", None)  # Get sake name if searching for specific sake
    locations = map_data.get("locations", [])
    center_lat = map_data.get("center_lat", 35.6762)
    center_lng = map_data.get("center_lng", 139.6503)

    print(f"DEBUG: Map will show {len(locations)} locations at {center_lat}, {center_lng}")
    if sake_name:
        print(f"DEBUG: Searching for restaurants serving: {sake_name}")

    if not locations:
        st.info("No locations found to display on map.")
        print("DEBUG: No locations in map data")
        return

    # Build markers data for JavaScript
    markers_json = json.dumps(locations, ensure_ascii=False)

    # Create HTML with Google Maps JavaScript API
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            #map {{
                height: 600px;
                width: 100%;
            }}
            .info-window {{
                max-width: 350px;
                font-family: Arial, sans-serif;
            }}
            .info-window h3 {{
                margin: 0 0 10px 0;
                color: #1a73e8;
                font-size: 16px;
            }}
            .info-window .rating {{
                color: #f4b400;
                margin: 5px 0;
            }}
            .info-window .address {{
                margin: 5px 0;
                font-size: 13px;
                color: #5f6368;
            }}
            .info-window .contact {{
                margin: 5px 0;
                font-size: 13px;
            }}
            .info-window .photos {{
                margin: 10px 0;
                display: flex;
                gap: 5px;
                overflow-x: auto;
            }}
            .info-window .photos img {{
                height: 100px;
                width: auto;
                border-radius: 4px;
                cursor: pointer;
            }}
            .info-window .review {{
                margin: 10px 0;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
                font-size: 12px;
            }}
            .info-window .review-author {{
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .info-window .review-text {{
                color: #202124;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            let map;
            let infoWindow;

            function initMap() {{
                const center = {{ lat: {center_lat}, lng: {center_lng} }};

                map = new google.maps.Map(document.getElementById("map"), {{
                    zoom: 13,
                    center: center,
                    mapTypeControl: true,
                    streetViewControl: true,
                    fullscreenControl: true,
                }});

                infoWindow = new google.maps.InfoWindow();

                const markers = {markers_json};

                markers.forEach((location, index) => {{
                    const marker = new google.maps.Marker({{
                        position: {{ lat: location.lat, lng: location.lng }},
                        map: map,
                        title: location.name,
                        animation: google.maps.Animation.DROP,
                    }});

                    marker.addListener("click", () => {{
                        const content = createInfoWindowContent(location);
                        infoWindow.setContent(content);
                        infoWindow.open(map, marker);

                        // Attach event listeners after InfoWindow opens
                        google.maps.event.addListenerOnce(infoWindow, 'domready', () => {{
                            const gmapsLink = document.getElementById('gmaps-link-' + location.place_id);
                            if (gmapsLink) {{
                                gmapsLink.addEventListener('click', (e) => {{
                                    e.preventDefault();
                                    window.open(location.google_maps_url, '_blank');
                                }});
                            }}

                            const websiteLink = document.getElementById('website-link-' + location.place_id);
                            if (websiteLink) {{
                                websiteLink.addEventListener('click', (e) => {{
                                    e.preventDefault();
                                    window.open(location.website, '_blank');
                                }});
                            }}
                        }});
                    }});
                }});
            }}

            function createInfoWindowContent(location) {{
                let html = '<div class="info-window">';

                // Title with sake name badge if applicable
                html += `<h3>${{location.name}}</h3>`;
                if (location.sake_name) {{
                    html += `<div style="background: #c41e3a; color: white; padding: 3px 8px; border-radius: 4px; display: inline-block; font-size: 11px; margin-bottom: 8px;">🍶 Serving ${{location.sake_name}}</div>`;
                }}

                // Rating
                if (location.rating && location.rating > 0) {{
                    const stars = '⭐'.repeat(Math.round(location.rating));
                    html += `<div class="rating">${{stars}} ${{location.rating}} (${{location.total_ratings || 0}} reviews)</div>`;
                }}

                // Address
                if (location.address) {{
                    html += `<div class="address">📍 ${{location.address}}</div>`;
                }}

                // Google Maps link
                if (location.google_maps_url) {{
                    html += `<div class="contact">🗺️ <a href="#" id="gmaps-link-${{location.place_id}}" style="color: #1a73e8; cursor: pointer; text-decoration: underline;">View on Google Maps</a></div>`;
                }}

                // Website
                if (location.website) {{
                    html += `<div class="contact">🌐 <a href="#" id="website-link-${{location.place_id}}" style="color: #1a73e8; cursor: pointer; text-decoration: underline;">Website</a></div>`;
                }}

                // Phone
                if (location.phone) {{
                    html += `<div class="contact">📞 ${{location.phone}}</div>`;
                }}

                // Photos
                if (location.photos && location.photos.length > 0) {{
                    html += '<div class="photos">';
                    location.photos.forEach(photo => {{
                        const photoUrl = `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${{photo.width}}&photo_reference=${{photo.photo_reference}}&key={google_maps_key}`;
                        html += `<img src="${{photoUrl}}" alt="Photo" onclick="window.open('${{photoUrl}}', '_blank')">`;
                    }});
                    html += '</div>';
                }}

                // Reviews
                if (location.reviews && location.reviews.length > 0) {{
                    html += '<div style="margin-top: 10px;"><strong>Recent Reviews:</strong></div>';
                    location.reviews.slice(0, 2).forEach(review => {{
                        const reviewStars = '⭐'.repeat(review.rating);
                        html += `
                            <div class="review">
                                <div class="review-author">${{review.author}} ${{reviewStars}}</div>
                                <div class="review-text">${{review.text}}...</div>
                                <div style="font-size: 11px; color: #5f6368; margin-top: 5px;">${{review.time}}</div>
                            </div>
                        `;
                    }});
                }}

                html += '</div>';
                return html;
            }}
        </script>
        <script async defer
            src="https://maps.googleapis.com/maps/api/js?key={google_maps_key}&callback=initMap">
        </script>
    </body>
    </html>
    """

    # Display the map
    if sake_name:
        st.subheader(f"📍 Restaurants serving {sake_name} - Map View")
    else:
        st.subheader("📍 Map View with Photos & Reviews")

    try:
        print(f"DEBUG: Attempting to render map HTML (length: {len(map_html)} chars)")
        components.html(map_html, height=650)
        print("DEBUG: Map HTML rendered successfully")
    except Exception as e:
        st.error(f"Error displaying map: {str(e)}")
        print(f"DEBUG: Error rendering map: {str(e)}")


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

                # DEBUG: Show raw response in expander
                with st.expander("🔍 Debug: Show raw response"):
                    st.code(response[:2000], language="text")
                    if len(response) > 2000:
                        st.caption(f"... (response truncated, total length: {len(response)} chars)")
                    st.caption(f"Contains 'MAP_DATA': {'MAP_DATA' in response}")

                # Check for map data
                map_data = extract_map_data(response)

                # Remove map data markers from display text
                display_text = re.sub(r'={50,}\s*MAP_DATA_START.*?MAP_DATA_END\s*={50,}', '', response, flags=re.DOTALL)

                # Display the text
                st.markdown(display_text)

                # Display map if available
                if map_data:
                    display_map(map_data)
                else:
                    # Show diagnostic if response looks like it should have a map
                    if "地図" in response or "場所" in response or "location" in response.lower():
                        st.info("💡 Tip: If you expected to see a map, please ensure GOOGLE_MAPS_API_KEY is configured in your secrets.")

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
            "**Required:**\n"
            "1. **OPENAI_API_KEY**: Get from [OpenAI](https://platform.openai.com/api-keys)\n"
            "2. **TAVILY_API_KEY**: Get from [Tavily](https://tavily.com/)\n\n"
            "**Optional (for enhanced features):**\n"
            "3. **GOOGLE_MAPS_API_KEY**: Get from [Google Cloud Console](https://console.cloud.google.com/) - Required for interactive maps with photos and reviews\n"
            "4. **INSTAGRAM_ACCESS_TOKEN**: For enhanced Instagram search\n\n"
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
