# CLAUDE.md - Development Guide for Japanese Sake Guide App

This document provides context for AI assistants working on this repository.

## Project Overview

A Streamlit web application that uses an AI agent to help users discover and learn about Japanese sake. The app supports both English and Japanese languages.

## Tech Stack

- **Frontend**: Streamlit
- **Agent Framework**: LangGraph (from LangChain)
- **LLM**: OpenAI GPT-4o
- **Web Search**: Tavily API
- **Social Media**: snscrape (Twitter, Instagram, Facebook)
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
│   ├── tools.py           # All agent tools (Tavily search, snscrape for social media)
│   └── sake_agent.py      # LangGraph agent workflow
├── config/
│   ├── __init__.py
│   └── settings.py        # Settings loaded from Streamlit secrets
└── utils/
    ├── __init__.py
    └── helpers.py         # Helper functions, constants (SAKE_TYPES, EXAMPLE_PROMPTS)
```

## Key Architecture Decisions

### Agent Tools (agents/tools.py)

All tools are defined in `tools.py` and created via `create_sake_tools()` factory function:

```python
def create_sake_tools(tavily_api_key: str, instagram_access_token: Optional[str] = None) -> List[Callable]:
    # Returns list of @tool decorated functions with API keys bound via closure
```

**Available Tools:**
1. `search_sake_rankings` - Searches sakenowa.com and saketime.jp
2. `search_sake_info` - Detailed info about specific sake
3. `search_social_media_hashtag` - Search Twitter, Instagram, and Facebook by hashtag using snscrape
4. `search_twitter_sake` - Twitter search for sake discussions and trends
5. `search_instagram_sake` - Instagram posts about a specific sake brand

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

### Data Sources

Sake rankings are fetched from:
- https://sakenowa.com/en/ranking
- https://sakenowa.com/en/ranking?page=2#ranking
- https://www.saketime.jp/ranking/

## Development Guidelines

### Language Support

- Always consider both Japanese and English in all features
- Use `_is_japanese(text)` helper to detect language
- Agent responds in the same language the user writes

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
# Note: snscrape does not require API keys for social media search
```

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

## Future Enhancement Ideas

- Add sake image recognition
- Integrate with sake shop APIs for purchasing
- Add user preference learning
- Implement sake pairing recommendations with specific dishes
- Add brewery location maps
