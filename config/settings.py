"""
Configuration settings for the Japanese Sake Guide App.
"""
import streamlit as st
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Application settings loaded from Streamlit secrets."""

    openai_api_key: str
    tavily_api_key: str
    instagram_access_token: Optional[str] = None

    # Sake ranking sources
    sake_ranking_urls: tuple = (
        "https://sakenowa.com/en/ranking",
        "https://sakenowa.com/en/ranking?page=2#ranking",
        "https://www.saketime.jp/ranking/",
    )

    # Model configuration
    openai_model: str = "gpt-4o"
    temperature: float = 0.7

    # Search configuration
    max_search_results: int = 5


def get_settings() -> Settings:
    """
    Load settings from Streamlit secrets.

    Returns:
        Settings object with API keys and configuration.

    Raises:
        KeyError: If required secrets are not configured.
    """
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", "")
        tavily_key = st.secrets.get("TAVILY_API_KEY", "")
        instagram_token = st.secrets.get("INSTAGRAM_ACCESS_TOKEN", None)

        if not openai_key:
            raise KeyError("OPENAI_API_KEY is required")
        if not tavily_key:
            raise KeyError("TAVILY_API_KEY is required")

        return Settings(
            openai_api_key=openai_key,
            tavily_api_key=tavily_key,
            instagram_access_token=instagram_token,
        )
    except Exception as e:
        raise KeyError(f"Failed to load settings: {e}")
