# CLAUDE.md - Development Guide for Japanese Sake Guide App

This document provides context for AI assistants working on this repository.

## Project Overview

A Streamlit web application that uses an AI agent to help users discover and learn about Japanese sake. The app supports both English and Japanese languages.

## Tech Stack

- **Frontend**: Streamlit
- **Agent Framework**: LangGraph (from LangChain)
- **LLM**: OpenAI GPT-4o
- **Web Search**: Tavily API (also used for social media content search)
- **Deployment**: Streamlit Cloud

## Project Structure

```
japan_sake_guide_app/
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python dependencies
├── secrets.toml.example    # Example secrets configuration
├── CLAUDE.md              # This file
├── README.md              # User-facing documentation
├── .gitignore
├── .streamlit/
│   └── config.toml        # Streamlit theme and server config
├── agents/
│   ├── __init__.py        # Exports: create_sake_tools, create_sake_agent, run_sake_agent
│   ├── tools.py           # All agent tools (Tavily search for web and social media)
│   └── sake_agent.py      # LangGraph agent workflow
├── config/
│   ├── __init__.py
│   └── settings.py        # Settings loaded from Streamlit secrets
└── utils/
    ├── __init__.py
    ├── helpers.py         # Helper functions, constants (SAKE_TYPES, EXAMPLE_PROMPTS)
    └── maps_links.py      # Google Maps URL builders (place pages, directions)
```

## Key Architecture Decisions

### Agent Tools (agents/tools.py)

All tools are defined in `tools.py` and created via `create_sake_tools()` factory function:

```python
def create_sake_tools(tavily_api_key: str, instagram_access_token: Optional[str] = None, google_maps_api_key: Optional[str] = None) -> List[Callable]:
    # Returns list of @tool decorated functions with API keys bound via closure
```

**Available Tools:**
1. `get_sake_rankings` - **Preferred for ranking/recommendation queries.** Reads the local
   `utils/sake_ranking_fallback.json` snapshot (sakenowa top-50, refreshed daily by CI).
   Optional `flavor` / `prefecture` / `top_n` filters; no network call.
2. `search_sake_rankings` - Web-search fallback over sakenowa.com and saketime.jp, for
   queries the local snapshot cannot answer (specific grades, editorial lists, outside top 50)
3. `search_sake_info` - Detailed info about specific sake
4. `search_social_media_hashtag` - Search Twitter/X, Instagram, and Facebook by hashtag via Tavily
5. `search_twitter_sake` - Twitter/X search for sake discussions and trends via Tavily
6. `search_instagram_sake` - Instagram posts about a specific sake brand via Tavily
7. `search_sake_places` - **Unified location search tool** using Google Places API with interactive map:
   - WITH sake_name: Find restaurants/bars serving a specific sake brand (e.g., "写楽", "獺祭")
   - WITHOUT sake_name: Find general sake shops, restaurants, or izakayas in a location
8. `search_sake_online_shops` - Search for sake available on online sake shops

### Agent Workflow (agents/sake_agent.py)

Uses LangGraph's StateGraph pattern:

```
[Entry] → [Agent Node] → [Conditional: has tool_calls?]
                              ├── Yes → [Tool Node] → [Agent Node]
                              └── No  → [END]
```

Key components:
- `AgentState`: TypedDict with `messages` and `language`
- `create_sake_agent()`: Builds and compiles the LangGraph workflow
- `run_sake_agent()`: Executes agent with user message

### Ranking Data Pipeline

`scripts/update_sake_rankings.py` runs daily (05:00 JST, GitHub Actions) against the
sakenowa API and commits `utils/sake_ranking_fallback.json`. The app never calls that
API at request time — both the network graph and the `get_sake_rankings` tool read the
committed snapshot.

**Flavour axes:** sakenowa's flavour chart is a six-axis radar —
`f1 華やか / f2 芳醇 / f3 重厚 / f4 穏やか / f5 ドライ / f6 軽快`. The mapping lives in
`FLAVOR_AXES` in `utils/sake_rankings.py` and is imported by both the CI script and the
app; do not redefine it elsewhere. An earlier duplicate definition had the axes shifted,
which mislabelled ~40% of the top 50 as "Aged".

**Prefectures:** the API returns names *with* their suffix (`秋田県`, `京都府`, `東京都`),
so always resolve regions via `prefecture_region()` / `region_color()`, which strip the
suffix before lookup.

### Google Maps Links

Links to Google Maps must open the **shop's place page**, not a dropped pin. Build them
with `_google_maps_place_url()` / `_google_maps_directions_url()` from
`utils/maps_links.py`, which pass `query_place_id` (or the canonical `url` from Place
Details). A coordinates-only URL such as
`https://www.google.com/maps/search/?api=1&query=35.70,139.64` opens the Maps app on an
anonymous pin with no name, photos, hours or reviews — only use it when no `place_id` is
available. Never reintroduce coordinates as the preferred form: an earlier version did,
which is how the "shows just a position" bug appeared.

Note that Place Details can fail (e.g. only *Places API (New)* enabled on the Cloud
project) while Text/Nearby Search still succeeds. That path must still emit a place-page
link from the `place_id` returned by the search, and it logs the underlying error.

### Data Sources

Sake rankings are also web-searched from:
- https://sakenowa.com/en/ranking
- https://sakenowa.com/en/ranking?page=2#ranking
- https://www.saketime.jp/ranking/

## Development Guidelines

### Language Support

- Always consider both Japanese and English in all features
- Use `_is_japanese(text)` helper to detect language
- Agent responds in the same language the user writes

### Tool Routing

Tool selection is done entirely by the LLM, guided by `SAKE_GUIDE_SYSTEM_PROMPT`.
Do **not** reintroduce keyword-based forcing via `tool_choice`: a previous version
force-bound `search_sake_places` whenever a query contained "find"/"探して"/"検索",
which made the social-media, online-shop and ranking tools unreachable for many
ordinary questions. Fix routing problems in the system prompt instead.

### Adding New Tools

1. Add the tool function inside `create_sake_tools()` in `agents/tools.py`
2. Decorate with `@tool` from `langchain_core.tools`
3. Add to the return list at the end of `create_sake_tools()`
4. Update the system prompt in `sake_agent.py` to document the new tool

Example:
```python
@tool
def new_tool_name(param: str) -> str:
    """
    Tool description for the LLM.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    # Implementation using tavily_client or other APIs
    return result
```

### Secrets Management

Required secrets (in `.streamlit/secrets.toml` or Streamlit Cloud):
```toml
OPENAI_API_KEY = "sk-..."
TAVILY_API_KEY = "tvly-..."
GOOGLE_MAPS_API_KEY = "AIza..."  # Optional but required for map features
```

Note: Google Maps API key is optional but required for location-based features (searching restaurants by sake brand or general sake locations).

### Running Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up secrets
cp secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your API keys

# Run the app
streamlit run app.py
```

## Common Patterns

### Error Handling in Tools

Tools should catch exceptions and return error strings rather than raising:
```python
try:
    results = tavily_client.search(...)
    return formatted_results
except Exception as e:
    return f"Error searching: {str(e)}"
```

### Truncating Long Content

When displaying search results, truncate long content:
```python
if len(content) > 500:
    content = content[:500] + "..."
```

### Session State

Streamlit session state keys used:
- `st.session_state.agent` - Compiled LangGraph agent
- `st.session_state.messages` - Chat display messages
- `st.session_state.chat_history` - Full message history for agent
- `st.session_state.language` - Current UI language ("en" or "ja")

## Testing Considerations

When testing the agent:
1. Test with both English and Japanese queries
2. Test ranking searches with various sake types
3. Test specific sake name lookups (e.g., "Dassai", "獺祭")
4. Test social media hashtag searches (e.g., "#日本酒", "#sake")
5. Test Twitter search for sake discussions
6. Test Instagram search for sake-related photos and posts
7. Test cross-platform search using search_social_media_hashtag
8. Test `search_sake_places` with sake_name (e.g., "写楽が飲める店は？", "Where can I drink Dassai in Tokyo?")
9. Test `search_sake_places` without sake_name (e.g., "東京の日本酒バー", "sake shops in Kyoto")
10. Verify map displays correctly with photos, reviews, and clickable Google Maps links
11. Test online shop search for purchasing sake

## Future Enhancement Ideas

- Add sake image recognition
- Integrate with sake shop APIs for purchasing
- Add user preference learning
- Implement sake pairing recommendations with specific dishes
- Add brewery location maps
