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
    end

    subgraph "External Services"
        TAVILY[Tavily Search API]
        OPENAI[OpenAI API]
    end

    subgraph "Data Sources"
        SK[Sakenowa.com]
        ST[Saketime.jp]
        TW[Twitter/X]
        IG[Instagram]
        FB[Facebook]
    end

    UI --> SS
    SS --> AG
    AG --> SM
    SM --> LLM
    SM --> T1 & T2 & T3 & T4 & T5
    T1 & T2 & T3 & T4 & T5 --> TAVILY
    LLM --> OPENAI
    TAVILY --> SK & ST & TW & IG & FB

    style UI fill:#c41e3a,color:#fff
    style AG fill:#2b5797,color:#fff
    style TAVILY fill:#4CAF50,color:#fff
    style OPENAI fill:#10a37f,color:#fff
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
        CLIENT[TavilyClient]
    end

    subgraph "Search Tools"
        RANK[search_sake_rankings]
        INFO[search_sake_info]
        SOCIAL[search_social_media_hashtag]
        TWITTER[search_twitter_sake]
        INSTA[search_instagram_sake]
    end

    FACTORY --> CLIENT
    FACTORY --> RANK & INFO & SOCIAL & TWITTER & INSTA
    CLIENT --> RANK & INFO & SOCIAL & TWITTER & INSTA

    RANK --> |Domain Filter| SOURCES1[sakenowa.com, saketime.jp]
    INFO --> |No Filter| SOURCES2[All Web]
    SOCIAL --> |Platform Filter| SOURCES3[twitter.com, instagram.com, facebook.com]
    TWITTER --> |Site Filter| SOURCES4[twitter.com, x.com]
    INSTA --> |Domain Filter| SOURCES5[instagram.com]

    style FACTORY fill:#4CAF50,color:#fff
```

**Tool Specifications:**

| Tool | Max Results | Search Depth | Content Limit | Domain Filter |
|------|-------------|--------------|---------------|---------------|
| search_sake_rankings | 8 | advanced | 500 chars | sakenowa.com, saketime.jp |
| search_sake_info | 6 | advanced | 600 chars | None |
| search_social_media_hashtag | 10 | advanced | 300 chars | Platform-based |
| search_twitter_sake | 10 | advanced | 300 chars | twitter.com, x.com |
| search_instagram_sake | 10 | advanced | 300 chars | instagram.com |

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

### 3. Tool Execution Flow (Detailed)

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

    subgraph "Search Provider"
        TAV[tavily-python 0.3+]
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
    LCC --> TAV

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

    CHAT --> PROCESS[process_user_input]
    PROCESS --> RUN[run_sake_agent]
    RUN --> DETECT[_is_japanese]
    RUN --> INVOKE[agent.invoke]

    INVOKE --> CALL[call_model]
    INVOKE --> TOOL_NODE[ToolNode]
    TOOL_NODE --> T1 & T2 & T3 & T4 & T5

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

## Future Enhancements

### Potential Architecture Extensions

1. **Caching Layer**
   - Redis for search result caching
   - Reduce Tavily API costs

2. **User Preferences**
   - Database for user profiles
   - Personalized recommendations

3. **Image Recognition**
   - Vision API integration
   - Sake label recognition

4. **Analytics Layer**
   - Query logging
   - Usage metrics
   - Popular sake tracking

5. **Multi-Agent System**
   - Specialized agents for different tasks
   - Ranking agent, pairing agent, etc.

---

## Conclusion

The Japanese Sake Guide App demonstrates a clean, modular architecture that separates concerns across presentation, agent orchestration, and tool execution layers. The LangGraph framework provides a flexible state machine for complex agent workflows, while Streamlit enables rapid UI development. The system is designed for extensibility, with clear patterns for adding new tools, data sources, and capabilities.

**Key Strengths:**
- Clear separation of concerns
- Language-agnostic design
- Extensible tool architecture
- Error-resilient execution
- Responsive user experience

**Architecture Principles:**
- Single Responsibility: Each module has a clear purpose
- Dependency Injection: API keys bound via closures
- State Isolation: Session state per user
- Fail-Safe: Graceful error handling throughout
