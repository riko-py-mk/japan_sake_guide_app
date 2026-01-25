"""
Japanese Sake Guide App - Main Streamlit Application

An AI-powered assistant to help users discover and learn about Japanese sake.
Supports both English and Japanese languages.
"""
import streamlit as st
from typing import Optional

from agents.sake_agent import create_sake_agent, run_sake_agent
from utils.helpers import detect_language, EXAMPLE_PROMPTS, SAKE_TYPES


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

        # Sake types information
        st.subheader("Sake Types | 日本酒の種類")
        lang = st.session_state.language
        for sake_type in SAKE_TYPES[lang]:
            st.caption(f"• {sake_type}")

        st.divider()

        # Data sources
        st.subheader("Data Sources | データソース")
        st.caption("• [Sakenowa](https://sakenowa.com/en/ranking)")
        st.caption("• [Saketime](https://www.saketime.jp/ranking/)")
        st.caption("• Instagram (via search)")

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


def render_chat():
    """Render the chat interface."""
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


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
                st.markdown(response)

                # Add assistant message to display
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
                "- **Explore Instagram** for sake content and reviews\n\n"
                "Ask me anything about Japanese sake!"
            )
        else:
            st.markdown(
                "日本酒ガイドへようこそ！以下のことをお手伝いできます：\n\n"
                "- お好みに合わせた**おすすめの日本酒**を探す\n"
                "- **特定の銘柄や蔵元**について詳しく知る\n"
                "- ランキングサイトから**人気の日本酒**を発見する\n"
                "- **Instagram**で日本酒のコンテンツやレビューを探索する\n\n"
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
