# System Architecture Diagram - Japanese Sake Guide App

## Table of Contents
1. [High-Level Architecture](#high-level-architecture)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Technology Stack](#technology-stack)
5. [Module Relationships](#module-relationships)

---

## High-Level Architecture

The Japanese Sake Guide App is built on a three-tier architecture combining a Streamlit frontend, LangGraph agent middleware, and external API integrations.

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[Streamlit Web Interface]
        SS[Session State Manager]
        MAP[Google Maps Renderer]
    end

    subgraph "Agent Layer"
        AG[LangGraph Agent Workflow]
        SM[State Machine Controller]
        LLM[OpenAI GPT-4o]
    end

    subgraph "Tool Layer"
        T1[search_sake_rankings]
        T2[search_sake_info]
        T3[search_social_media_hashtag]
        T4[search_twitter_sake]
        T5[search_instagram_sake]
        T6[search_sake_places]
        T7[search_sake_online_shops]
    end

    subgraph "External Services"
        TAVILY[Tavily Search API]
        OPENAI[OpenAI API]
        GMAPS[Google Maps & Places API]
    end

    subgraph "Data Sources"
        SK[Sakenowa.com]
        ST[Saketime.jp]
        TW[Twitter/X]
        IG[Instagram]
        FB[Facebook]
        SHOPS[Online Sake Shops]
    end

    UI --> SS
    SS --> AG
    AG --> SM
    SM --> LLM
    SM --> T1 & T2 & T3 & T4 & T5 & T6 & T7
    T1 & T2 & T3 & T4 & T5 & T7 --> TAVILY
    T6 --> GMAPS
    LLM --> OPENAI
    TAVILY --> SK & ST & TW & IG & FB & SHOPS
    T6 --> MAP
    MAP --> UI

    style UI fill:#c41e3a,color:#fff
    style AG fill:#2b5797,color:#fff
    style TAVILY fill:#4CAF50,color:#fff
    style OPENAI fill:#10a37f,color:#fff
    style GMAPS fill:#ea4335,color:#fff
```

---

## Component Architecture

### 1. Application Entry Point (`app.py`)

**Responsibilities:**
- Page configuration and UI rendering
- API key validation
- Session state initialization and management
- Chat interface rendering
- User input processing
- Language preference management

```mermaid
graph LR
    subgraph "app.py - Main Application"
        MAIN[main function]
        INIT[initialize_session_state]
        CHECK[check_api_keys]
        AGENT_INIT[initialize_agent]
        SIDEBAR[render_sidebar]
        CHAT[render_chat]
        PROCESS[process_user_input]
        EXAMPLES[render_example_prompts]
    end

    MAIN --> INIT
    MAIN --> CHECK
    MAIN --> AGENT_INIT
    MAIN --> SIDEBAR
    MAIN --> CHAT
    MAIN --> EXAMPLES
    PROCESS --> CHAT

    style MAIN fill:#c41e3a,color:#fff
```

**Session State Variables:**
- `agent` - Compiled LangGraph StateGraph (singleton)
- `messages` - Display message history (list of dicts)
- `chat_history` - Agent message history (list of BaseMessage objects)
- `language` - Current UI language ("en" or "ja")

### 2. Agent Workflow (`agents/sake_agent.py`)

**Responsibilities:**
- LangGraph state machine orchestration
- Language detection from user input
- Agent execution and response extraction
- System prompt management

```mermaid
stateDiagram-v2
    [*] --> AgentNode
    AgentNode --> Decision: LLM Response
    Decision --> ToolsNode: Has tool_calls
    Decision --> [*]: No tool_calls
    ToolsNode --> AgentNode: Tool results

    note right of AgentNode
        call_model()
        - Add system prompt
        - Call LLM
        - Return AI response
    end note

    note right of ToolsNode
        ToolNode(tools)
        - Execute tools
        - Return results
    end note
```

**Key Components:**
- `AgentState` - TypedDict with messages and language
- `SAKE_GUIDE_SYSTEM_PROMPT` - Expert sommelier system prompt
- `create_sake_agent()` - Builds and compiles StateGraph
- `run_sake_agent()` - Invokes agent and returns response

### 3. Agent Tools (`agents/tools.py`)

**Responsibilities:**
- Tavily API integration
- Search query enhancement
- Result formatting and truncation
- Language-aware query building

```mermaid
graph TB
    subgraph "Tool Factory"
        FACTORY[create_sake_tools]
        TCLIENT[TavilyClient]
        GCLIENT[GoogleMaps Client]
    end

    subgraph "Web Search Tools"
        RANK[search_sake_rankings]
        INFO[search_sake_info]
        SOCIAL[search_social_media_hashtag]
        TWITTER[search_twitter_sake]
        INSTA[search_instagram_sake]
        SHOP[search_sake_online_shops]
    end

    subgraph "Location Tools"
        PLACES[search_sake_places]
    end

    FACTORY --> TCLIENT
    FACTORY --> GCLIENT
    FACTORY --> RANK & INFO & SOCIAL & TWITTER & INSTA & SHOP & PLACES
    TCLIENT --> RANK & INFO & SOCIAL & TWITTER & INSTA & SHOP
    GCLIENT --> PLACES

    RANK --> |Domain Filter| SOURCES1[sakenowa.com, saketime.jp]
    INFO --> |No Filter| SOURCES2[All Web]
    SOCIAL --> |Platform Filter| SOURCES3[twitter.com, instagram.com, facebook.com]
    TWITTER --> |Site Filter| SOURCES4[twitter.com, x.com]
    INSTA --> |Domain Filter| SOURCES5[instagram.com]
    SHOP --> |Domain Filter| SOURCES6[Online sake shops]
    PLACES --> |Places API| SOURCES7[Google Places with photos & reviews]

    style FACTORY fill:#4CAF50,color:#fff
    style GCLIENT fill:#ea4335,color:#fff
```

**Tool Specifications:**

| Tool | API | Max Results | Search Depth | Content Limit | Domain Filter |
|------|-----|-------------|--------------|---------------|---------------|
| search_sake_rankings | Tavily | 8 | advanced | 500 chars | sakenowa.com, saketime.jp |
| search_sake_info | Tavily | 6 | advanced | 600 chars | None |
| search_social_media_hashtag | Tavily | 10 | advanced | 300 chars | Platform-based |
| search_twitter_sake | Tavily | 10 | advanced | 300 chars | twitter.com, x.com |
| search_instagram_sake | Tavily | 10 | advanced | 300 chars | instagram.com |
| search_sake_places | Google Maps | 10 | N/A | N/A | Google Places API |
| search_sake_online_shops | Tavily | 10 | advanced | 500 chars | jizake.com, matsuzaki-shop.jp, etc. |

**search_sake_places Tool - Dual Mode Operation:**

The `search_sake_places` tool is a unified location search tool that operates in two distinct modes:

1. **Specific Sake Brand Mode** (when `sake_name` parameter is provided):
   - Finds restaurants/bars/izakayas serving a specific sake brand
   - Uses Google Places Text Search for better accuracy
   - Examples: "Find places serving Dassai in Tokyo", "写楽が飲める店は？"
   - Returns locations with sake brand badge in map markers

2. **General Location Mode** (when `sake_name` parameter is None):
   - Finds general sake shops, restaurants, or bars in a location
   - Uses Google Places Nearby Search
   - Supports `search_type` parameter: "shop", "restaurant", or "both"
   - Examples: "Find sake shops in Kyoto", "東京の日本酒バーを教えて"

Both modes return:
- Up to 10 locations with coordinates for map display
- Photos (up to 3 per location)
- Reviews (up to 3 per location)
- Ratings, addresses, phone numbers, websites
- Google Maps URLs for each location
- Structured JSON data embedded in response with `MAP_DATA_START/END` markers

### 4. Configuration (`config/settings.py`)

**Responsibilities:**
- Centralized settings management
- API key loading from Streamlit secrets
- Default configuration values

```python
@dataclass
class Settings:
    openai_api_key: str
    tavily_api_key: str
    instagram_access_token: Optional[str] = None
    sake_ranking_urls: tuple = (...)
    openai_model: str = "gpt-4o"
    temperature: float = 0.7
    max_search_results: int = 5
```

### 5. Utilities (`utils/helpers.py`)

**Responsibilities:**
- Language detection utilities
- Response formatting
- Example prompt constants

**Key Functions:**
- `detect_language(text)` - Analyzes text for Japanese characters
- `format_sake_response(response, language)` - Post-processes agent output

**Constants:**
- `EXAMPLE_PROMPTS` - 4 example prompts per language
- `SIDEBAR_EXAMPLE_PROMPTS` - Tool-categorized examples for sidebar

---

## Data Flow Diagrams

### 1. Application Startup Flow

```mermaid
sequenceDiagram
    participant User
    participant App as app.py
    participant SS as Session State
    participant Agent as sake_agent.py
    participant Tools as tools.py

    User->>App: Visit application
    App->>SS: initialize_session_state()
    SS-->>App: Create messages[], chat_history[], language
    App->>App: check_api_keys()
    App->>Agent: create_sake_agent()
    Agent->>Tools: create_sake_tools(tavily_key)
    Tools-->>Agent: Return tool list
    Agent->>Agent: Build StateGraph
    Agent-->>App: Return compiled agent
    App->>SS: Store agent in session_state
    App->>User: Render UI with sidebar & chat
```

### 2. User Message Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant App as app.py
    participant Agent as LangGraph Agent
    participant LLM as OpenAI GPT-4o
    participant Tools as Agent Tools
    participant Tavily as Tavily API

    User->>App: Submit message
    App->>App: process_user_input(msg)
    App->>Agent: run_sake_agent(agent, msg, history)
    Agent->>Agent: Detect language from message
    Agent->>LLM: invoke(messages, language)

    alt LLM decides to use tools
        LLM-->>Agent: Return tool_calls
        Agent->>Tools: Execute tool (e.g., search_sake_rankings)
        Tools->>Tavily: search(query, domains, depth)
        Tavily-->>Tools: Search results
        Tools-->>Agent: Formatted results
        Agent->>LLM: invoke(messages + tool results)
    end

    LLM-->>Agent: Final response
    Agent-->>App: (response_text, updated_history)
    App->>App: Update session_state
    App->>User: Display response
```

### 3. Map Data Flow (Location Search)

```mermaid
sequenceDiagram
    participant User
    participant App as app.py
    participant Agent as LangGraph Agent
    participant Tool as search_sake_places
    participant GMaps as Google Maps API
    participant Render as Map Renderer

    User->>App: "Find sake shops in Tokyo"
    App->>Agent: run_sake_agent()
    Agent->>Agent: Detect location query
    Agent->>Tool: search_sake_places(location="Tokyo")
    Tool->>GMaps: Geocode location
    GMaps-->>Tool: (lat, lng) coordinates
    Tool->>GMaps: places_nearby(lat, lng, keyword)
    GMaps-->>Tool: List of places
    Tool->>GMaps: place_details(place_id) × N
    GMaps-->>Tool: Details with photos, reviews
    Tool-->>Agent: JSON with MAP_DATA markers
    Agent-->>App: Response with embedded map data
    App->>App: extract_map_data(response)
    App->>Render: display_map(map_data)
    Render->>User: Interactive Google Map with markers

    Note over Tool,GMaps: Fetches up to 10 locations<br/>with photos (3 each)<br/>and reviews (3 each)
    Note over Render: Renders HTML with<br/>Google Maps JavaScript API<br/>Photos, reviews, clickable links
```

### 4. Tool Execution Flow (Detailed)

```mermaid
flowchart TD
    START([Tool Call Initiated]) --> DETECT{Detect Query Language}
    DETECT -->|Japanese| ENHANCE_JP[Enhance with Japanese keywords]
    DETECT -->|English| ENHANCE_EN[Enhance with English keywords]

    ENHANCE_JP --> BUILD_QUERY[Build Tavily Search Query]
    ENHANCE_EN --> BUILD_QUERY

    BUILD_QUERY --> FILTER{Apply Domain Filter?}
    FILTER -->|Yes| DOMAIN[Set include_domains]
    FILTER -->|No| NO_DOMAIN[Use all domains]

    DOMAIN --> SEARCH[tavily_client.search]
    NO_DOMAIN --> SEARCH

    SEARCH --> CHECK{Success?}
    CHECK -->|Yes| FORMAT[Format Results]
    CHECK -->|No| ERROR[Return Error String]

    FORMAT --> TRUNCATE[Truncate Long Content]
    TRUNCATE --> RETURN([Return Formatted String])
    ERROR --> RETURN

    style START fill:#4CAF50,color:#fff
    style RETURN fill:#c41e3a,color:#fff
```

### 4. Session State Management Flow

```mermaid
graph LR
    subgraph "User Message"
        UM[User Input]
    end

    subgraph "Display Layer"
        DM[st.session_state.messages]
        DCHAT[Chat UI Display]
    end

    subgraph "Agent Layer"
        CH[st.session_state.chat_history]
        AG[Agent Execution]
    end

    UM --> DM
    UM --> CH
    DM --> DCHAT
    CH --> AG
    AG --> CH
    AG --> DM

    style DM fill:#FFB74D,color:#000
    style CH fill:#64B5F6,color:#fff
```

**Message Object Types:**
- **Display Messages** (`st.session_state.messages`): Dicts with `{role, content}` for UI rendering
- **Agent Messages** (`st.session_state.chat_history`): LangChain message objects (HumanMessage, AIMessage, ToolMessage)

---

## Technology Stack

### Core Dependencies

```mermaid
graph TB
    subgraph "Frontend Layer"
        ST[Streamlit 1.28+]
    end

    subgraph "Agent Framework"
        LG[LangGraph 0.2+]
        LC[LangChain 0.3+]
        LCO[langchain-openai 0.2+]
        LCC[langchain-community 0.3+]
    end

    subgraph "LLM Provider"
        OPENAI[OpenAI 1.0+]
    end

    subgraph "Search & Location Providers"
        TAV[tavily-python 0.3+]
        GMAP[googlemaps 4.10+]
    end

    subgraph "Utilities"
        PYD[Pydantic 2.0+]
        DOT[python-dotenv 1.0+]
        REQ[requests 2.31+]
        HTT[httpx 0.25+]
    end

    ST --> LG
    LG --> LC
    LC --> LCO & LCC
    LCO --> OPENAI
    LCC --> TAV & GMAP

    style ST fill:#c41e3a,color:#fff
    style LG fill:#2b5797,color:#fff
    style OPENAI fill:#10a37f,color:#fff
    style TAV fill:#4CAF50,color:#fff
```

### External Services

| Service | Purpose | Authentication | Configuration |
|---------|---------|----------------|---------------|
| **OpenAI API** | LLM for agent reasoning | API Key | `OPENAI_API_KEY` in secrets |
| **Tavily API** | Web and social media search | API Key | `TAVILY_API_KEY` in secrets |
| **Google Maps & Places API** | Location search with photos, reviews, maps | API Key | `GOOGLE_MAPS_API_KEY` in secrets (optional) |
| **Streamlit Cloud** | Application hosting | OAuth | Automatic deployment |

---

## Module Relationships

### Dependency Graph

```mermaid
graph TD
    subgraph "Entry Point"
        APP[app.py]
    end

    subgraph "Agents"
        SA[agents/sake_agent.py]
        AT[agents/tools.py]
        AI[agents/__init__.py]
    end

    subgraph "Config"
        CS[config/settings.py]
        CI[config/__init__.py]
    end

    subgraph "Utils"
        UH[utils/helpers.py]
        UI[utils/__init__.py]
    end

    APP --> SA
    APP --> CS
    APP --> UH
    SA --> AT
    SA --> AI
    AT --> CS
    AI --> SA
    AI --> AT
    CS --> CI
    UH --> UI

    style APP fill:#c41e3a,color:#fff
    style SA fill:#2b5797,color:#fff
    style AT fill:#4CAF50,color:#fff
    style CS fill:#FF9800,color:#fff
    style UH fill:#9C27B0,color:#fff
```

### Function Call Hierarchy

```mermaid
graph TD
    MAIN[main - app.py] --> INIT[initialize_session_state]
    MAIN --> CHECK[check_api_keys]
    MAIN --> AGENT_INIT[initialize_agent]
    MAIN --> SIDEBAR[render_sidebar]
    MAIN --> CHAT[render_chat]
    MAIN --> EXAMPLES[render_example_prompts]

    AGENT_INIT --> CREATE[create_sake_agent]
    CREATE --> TOOLS[create_sake_tools]
    CREATE --> GRAPH[StateGraph]

    TOOLS --> T1[search_sake_rankings]
    TOOLS --> T2[search_sake_info]
    TOOLS --> T3[search_social_media_hashtag]
    TOOLS --> T4[search_twitter_sake]
    TOOLS --> T5[search_instagram_sake]
    TOOLS --> T6[search_sake_places]
    TOOLS --> T7[search_sake_online_shops]

    CHAT --> PROCESS[process_user_input]
    PROCESS --> RUN[run_sake_agent]
    RUN --> DETECT[_is_japanese]
    RUN --> INVOKE[agent.invoke]

    INVOKE --> CALL[call_model]
    INVOKE --> TOOL_NODE[ToolNode]
    TOOL_NODE --> T1 & T2 & T3 & T4 & T5 & T6 & T7

    style MAIN fill:#c41e3a,color:#fff
    style CREATE fill:#2b5797,color:#fff
    style TOOLS fill:#4CAF50,color:#fff
```

---

## Key Architectural Patterns

### 1. Closure-Based Configuration Pattern
Tools are created with API keys bound via closure to avoid passing secrets through arguments:

```python
def create_sake_tools(tavily_api_key: str):
    tavily_client = TavilyClient(api_key=tavily_api_key)

    @tool
    def search_sake_rankings(query: str):
        # tavily_client accessible via closure
        results = tavily_client.search(...)
        return results

    return [search_sake_rankings, ...]
```

### 2. LangGraph State Machine Pattern
Agent workflow uses reactive state transitions:

```
Entry → Agent Node → [Has tool_calls?] → Tools Node → Agent Node → ... → END
```

### 3. Bilingual Content Detection Pattern
Automatic language detection influences:
- Tool query enhancement
- Response language
- UI element selection

```python
def _is_japanese(text: str) -> bool:
    japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text)
    return len(japanese_chars) > len(text) * 0.2
```

### 4. Error Resilience Pattern
All tools catch exceptions and return error strings:

```python
try:
    results = tavily_client.search(...)
    return format_results(results)
except Exception as e:
    return f"Error searching: {str(e)}"
```

### 5. Content Truncation Pattern
Search results are truncated to prevent token overflow:

```python
if len(content) > 500:
    content = content[:500] + "..."
```

### 6. Structured Data Embedding Pattern
Map data is embedded in agent responses using special markers:

```python
# In search_sake_places tool:
output.append("MAP_DATA_START")
map_data = {
    "center_lat": lat,
    "center_lng": lng,
    "locations": [...]
}
output.append(json.dumps(map_data))
output.append("MAP_DATA_END")

# In app.py:
map_data = extract_map_data(response_text)
if map_data:
    display_map(map_data)
```

This pattern allows the agent to return both human-readable text and structured data for interactive components in a single response.

### 7. Map Rendering with Google Maps JavaScript API
Interactive maps are rendered using Streamlit's `components.html()`:

```python
# Generate HTML with Google Maps JavaScript API
map_html = f"""
<script src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap"></script>
<script>
    function initMap() {{
        // Create map, markers, info windows with photos and reviews
    }}
</script>
"""

# Render in Streamlit
components.html(map_html, height=650)
```

Each marker displays:
- Location name and address
- Rating with star visualization
- Up to 3 photos (fetched via Google Photos API)
- Up to 3 reviews with author and timestamp
- Clickable Google Maps and website links

---

## Performance Characteristics

### Agent Execution Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Agent Initialization** | ~2-3s | One-time cost on first message |
| **Simple Query (No Tools)** | ~2-5s | LLM response only |
| **Tool-Using Query** | ~5-15s | Depends on tool count and Tavily latency |
| **Max Tool Iterations** | Unlimited | Controlled by LLM's decision-making |
| **Tavily Search Latency** | ~1-3s | Per search call |
| **OpenAI API Latency** | ~1-2s | Per LLM call |

### Scalability Considerations

- **Session State**: Per-user isolation via Streamlit sessions
- **Agent Instance**: One compiled agent per session (singleton)
- **Concurrent Users**: Limited by Streamlit Cloud free tier
- **Token Usage**: Controlled via content truncation

---

## Security Architecture

### Secrets Management

```mermaid
graph LR
    subgraph "Secret Sources"
        ENV[.streamlit/secrets.toml]
        CLOUD[Streamlit Cloud Secrets]
    end

    subgraph "Application"
        SETTINGS[config/settings.py]
        APP[app.py]
        AGENT[agents/sake_agent.py]
        TOOLS[agents/tools.py]
    end

    ENV --> SETTINGS
    CLOUD --> SETTINGS
    SETTINGS --> APP
    SETTINGS --> AGENT
    SETTINGS --> TOOLS

    style ENV fill:#FF5722,color:#fff
    style CLOUD fill:#FF5722,color:#fff
```

**Secret Storage:**
- Local: `.streamlit/secrets.toml` (gitignored)
- Production: Streamlit Cloud Secrets UI

**Secret Usage:**
- Never logged or displayed
- Passed via closure binding in tools
- Validated on application startup

### Data Privacy

- **User Messages**: Stored only in session state (not persisted)
- **Chat History**: Cleared on browser session end
- **External API Calls**: All searches logged by provider (Tavily, OpenAI)
- **No User Authentication**: No user data collected

---

## Recently Implemented Features

The following features have been successfully implemented in the current version:

1. **✅ Google Maps Integration**
   - Interactive maps with photos and reviews
   - Dual-mode location search (specific sake brands vs. general locations)
   - Real-time place details with ratings and contact information

2. **✅ Online Shop Search**
   - Search across 7+ specialized Japanese sake online shops
   - Direct purchase links to sake products
   - Integration with jizake.com, matsuzaki-shop.jp, sakenomy.jp, and more

3. **✅ Multi-Platform Social Media Search**
   - Cross-platform hashtag search (Twitter/X, Instagram, Facebook)
   - Platform-specific search tools for targeted discovery
   - Real-time social media content aggregation

## Future Enhancements

### Potential Architecture Extensions

1. **Caching Layer**
   - Redis for search result caching
   - Reduce API costs and improve response times
   - Cache Google Places results for frequently searched locations

2. **User Preferences**
   - Database for user profiles
   - Personalized recommendations based on taste history
   - Saved favorite sake and locations

3. **Image Recognition**
   - Vision API integration
   - Sake label recognition and identification
   - Food pairing suggestions from uploaded photos

4. **Analytics Layer**
   - Query logging and usage metrics
   - Popular sake tracking and trend analysis
   - Regional search pattern analysis

5. **Multi-Agent System**
   - Specialized agents for different tasks
   - Ranking agent, pairing agent, location agent, etc.
   - Parallel agent execution for complex queries

---

## Conclusion

The Japanese Sake Guide App demonstrates a clean, modular architecture that separates concerns across presentation, agent orchestration, and tool execution layers. The LangGraph framework provides a flexible state machine for complex agent workflows, while Streamlit enables rapid UI development with rich interactive components like Google Maps. The system is designed for extensibility, with clear patterns for adding new tools, data sources, and capabilities.

**Current Capabilities:**
- 7 specialized tools covering rankings, detailed info, social media, and location search
- Multi-platform social media search (Twitter/X, Instagram, Facebook)
- Interactive Google Maps with photos, reviews, and ratings
- Dual-mode location search (specific sake brands vs. general sake locations)
- Online sake shop integration for purchasing
- Full bilingual support (English and Japanese)
- Real-time web search and location data

**Key Strengths:**
- Clear separation of concerns across layers
- Language-agnostic design with automatic detection
- Extensible tool architecture via closure-based factory pattern
- Error-resilient execution with graceful fallbacks
- Responsive user experience with interactive maps
- Structured data embedding for rich UI components

**Architecture Principles:**
- **Single Responsibility**: Each module has a clear purpose
- **Dependency Injection**: API keys bound via closures
- **State Isolation**: Session state per user
- **Fail-Safe**: Graceful error handling throughout
- **Data Embedding**: Structured data in text responses for interactive components
- **Progressive Enhancement**: Core features work without optional APIs (e.g., Google Maps)
