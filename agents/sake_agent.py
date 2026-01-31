"""
Japanese Sake Guide Agent using LangGraph.

This module implements an AI agent that helps users learn about and discover Japanese sake.
The agent can:
- Recommend sake based on user preferences
- Search for specific sake information
- Find sake rankings from trusted sources
- Search social media (Twitter, Instagram, Facebook) for sake-related content using snscrape
"""
from typing import TypedDict, Annotated, Sequence, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from .tools import create_sake_tools


class AgentState(TypedDict):
    """State definition for the sake guide agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str


# System prompt for the sake guide agent
SAKE_GUIDE_SYSTEM_PROMPT = """You are an expert Japanese Sake Sommelier and Guide. Your role is to help users discover and learn about Japanese sake (nihonshu).

Your capabilities include:
1. **Sake Recommendations**: Suggest sake based on user preferences (flavor profiles, food pairings, occasions)
2. **Sake Information**: Provide detailed information about specific sake brands, breweries, and production methods
3. **Rankings & Reviews**: Search and share sake rankings from trusted sources
4. **Social Media Insights**: Find posts about sake on Twitter, Instagram, and Facebook using snscrape
5. **Location-Based Search**: Find sake shops, restaurants, and izakayas in specific locations with map visualization

Available Tools:
- search_sake_rankings: Search for top-rated sake from ranking websites (sakenowa.com, saketime.jp)
- search_sake_info: Get detailed information about a specific sake brand or brewery
- search_social_media_hashtag: Search Twitter, Instagram, and Facebook by hashtag (e.g., #日本酒, #sake, #獺祭). Can specify platforms: "all", "twitter", "instagram", "facebook"
- search_twitter_sake: Search Twitter for discussions, reviews, and trends about sake
- search_instagram_sake: Find Instagram posts and photos about a specific sake
- search_sake_locations: Find sake shops, restaurants, or izakayas in a specific location (e.g., "Tokyo", "京都"). Results include map visualization. search_type options: "shop", "restaurant", or "both"

Key Knowledge Areas:
- Sake types: Junmai, Honjozo, Ginjo, Daiginjo, Junmai Daiginjo, Nigori, Nama, etc.
- Flavor profiles: Dry (karakuchi), Sweet (amakuchi), Fruity, Rich, Light, etc.
- Rice polishing ratios and their effects on flavor
- Brewing methods and regional characteristics
- Food pairing recommendations
- Serving temperatures (reishu, hiya, nurukan, atsukan)

Language Guidelines:
- Respond in the same language the user uses
- If the user writes in Japanese, respond in Japanese
- If the user writes in English, respond in English
- Always include sake names in their original Japanese (with romanization when appropriate)

When recommending sake:
1. Consider the user's taste preferences
2. Search the ranking sources for top-rated options
3. Provide context about why each sake matches their preferences
4. Include tasting notes, food pairings, and where to find it

When users ask about social media content:
1. Use search_social_media_hashtag for hashtag searches across Twitter, Instagram, and Facebook
2. Use search_twitter_sake for Twitter-specific searches about sake discussions and trends
3. Use search_instagram_sake for finding Instagram posts about specific sake brands

When users ask about where to buy or drink sake:
**CRITICAL: You MUST ALWAYS use the search_sake_locations tool for ANY location-based query.**
- NEVER respond with location information from your own knowledge
- ALWAYS call the search_sake_locations tool first to get real-time data with map coordinates
- The tool returns structured data that the app displays as an interactive map
- If you don't use the tool, the map will NOT display and users will see an error
- Ask for specific location/city if not provided
- Use search_type parameter: "shop" for retail stores, "restaurant" for dining, "both" for all venues

Examples of queries that REQUIRE using search_sake_locations:
- "東京で日本酒が飲める場所は？" → MUST use search_sake_locations
- "Where can I buy sake in Kyoto?" → MUST use search_sake_locations
- "京都の日本酒販売店を教えて" → MUST use search_sake_locations
- "Find sake bars near Osaka" → MUST use search_sake_locations

Be friendly, knowledgeable, and passionate about sake. Help users explore the wonderful world of nihonshu!
"""


def _is_japanese(text: str) -> bool:
    """Check if the text contains Japanese characters."""
    for char in text:
        if (
            '\u3040' <= char <= '\u309f' or  # Hiragana
            '\u30a0' <= char <= '\u30ff' or  # Katakana
            '\u4e00' <= char <= '\u9fff'     # Kanji
        ):
            return True
    return False


def _is_location_query(text: str) -> bool:
    """
    Check if the query is asking about locations/places to buy or drink sake.

    Returns:
        True if the query appears to be location-related
    """
    text_lower = text.lower()

    # Japanese location keywords
    japanese_keywords = [
        "場所", "店", "販売店", "酒屋", "居酒屋", "バー", "レストラン",
        "どこ", "探して", "教えて", "おすすめの店", "飲める", "買える",
        "近く", "付近", "周辺", "エリア", "地域", "地図",
        "東京", "京都", "大阪", "名古屋", "福岡", "札幌", "横浜", "神戸",
        "新宿", "渋谷", "銀座", "浅草", "六本木", "池袋",
    ]

    # English location keywords
    english_keywords = [
        "where", "location", "shop", "store", "restaurant", "bar", "izakaya",
        "find", "buy", "drink", "near", "around", "area", "place", "map",
        "tokyo", "kyoto", "osaka", "nagoya", "fukuoka", "sapporo", "yokohama", "kobe",
        "shinjuku", "shibuya", "ginza", "asakusa", "roppongi", "ikebukuro",
    ]

    # Check for Japanese keywords
    for keyword in japanese_keywords:
        if keyword in text:
            return True

    # Check for English keywords
    for keyword in english_keywords:
        if keyword in text_lower:
            return True

    return False


def create_sake_agent(
    openai_api_key: str,
    tavily_api_key: str,
    instagram_token: Optional[str] = None,
    google_maps_api_key: Optional[str] = None,
):
    """
    Create the Japanese Sake Guide agent using LangGraph.

    Args:
        openai_api_key: OpenAI API key
        tavily_api_key: Tavily API key
        instagram_token: Optional Instagram access token for hashtag search
        google_maps_api_key: Optional Google Maps API key for location search

    Returns:
        Compiled LangGraph agent
    """
    # Create the LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        api_key=openai_api_key,
    )

    # Create tools from tools.py
    tools = create_sake_tools(
        tavily_api_key=tavily_api_key,
        instagram_access_token=instagram_token,
        google_maps_api_key=google_maps_api_key,
    )

    # Bind tools to the LLM (default - LLM decides whether to use tools)
    llm_with_tools = llm.bind_tools(tools)

    # Bind tools with forced location tool (for location queries)
    llm_with_forced_location_tool = llm.bind_tools(
        tools,
        tool_choice={"type": "function", "function": {"name": "search_sake_locations"}}
    )

    # Create the tool node
    tool_node = ToolNode(tools)

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine if the agent should continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM made a tool call, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Otherwise, end the conversation turn
        return "end"

    def call_model(state: AgentState):
        """Call the LLM with the current state."""
        messages = state["messages"]

        # Add system message if not already present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SAKE_GUIDE_SYSTEM_PROMPT)] + list(messages)

        # Check if this is a location query from the user
        # Only force tool usage on the first call (when we haven't made tool calls yet)
        last_human_message = None
        has_tool_calls_already = False
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                has_tool_calls_already = True
                break

        # Force location tool if it's a location query and we haven't made tool calls yet
        if last_human_message and _is_location_query(last_human_message) and not has_tool_calls_already:
            response = llm_with_forced_location_tool.invoke(messages)
        else:
            response = llm_with_tools.invoke(messages)

        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile the graph
    app = workflow.compile()

    return app


def run_sake_agent(
    agent,
    user_message: str,
    chat_history: Optional[list] = None,
) -> tuple[str, list]:
    """
    Run the sake guide agent with a user message.

    Args:
        agent: Compiled LangGraph agent
        user_message: User's message/question
        chat_history: Optional list of previous messages

    Returns:
        Tuple of (agent response string, updated chat history)
    """
    # Build messages list
    messages = []

    if chat_history:
        messages.extend(chat_history)

    messages.append(HumanMessage(content=user_message))

    # Detect language from user message
    language = "ja" if _is_japanese(user_message) else "en"

    # Run the agent
    result = agent.invoke({
        "messages": messages,
        "language": language,
    })

    # Extract the final response
    final_messages = result["messages"]

    # Get the last AI message
    response_text = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break

    # CRITICAL: Extract MAP_DATA from ToolMessages
    # The LLM's final response summarizes tool output but doesn't include the MAP_DATA markers
    # We need to find MAP_DATA in ToolMessages and append it to the response
    map_data_section = ""
    for msg in final_messages:
        if isinstance(msg, ToolMessage) and msg.content:
            content = msg.content
            if "MAP_DATA_START" in content and "MAP_DATA_END" in content:
                # Extract the map data section including markers
                import re
                pattern = r'(={50,}\s*MAP_DATA_START.*?MAP_DATA_END\s*={50,})'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    map_data_section = "\n\n" + match.group(1)
                    break

    # Append MAP_DATA to response if found and not already present
    if map_data_section and "MAP_DATA_START" not in response_text:
        response_text = response_text + map_data_section

    # Update chat history
    new_history = list(final_messages)

    return response_text, new_history
