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
6. **Online Shop Search**: Search for sake available on specialized online sake shops for purchasing

Available Tools:
- search_sake_rankings: Search for top-rated sake from ranking websites (sakenowa.com, saketime.jp). Use for sake RECOMMENDATIONS and popular sake queries.
- search_sake_info: Get detailed information about a specific sake brand or brewery. Use for sake INFORMATION queries.
- search_social_media_hashtag: Search Twitter, Instagram, and Facebook by hashtag (e.g., #日本酒, #sake, #獺祭). Can specify platforms: "all", "twitter", "instagram", "facebook"
- search_twitter_sake: Search Twitter for discussions, reviews, and trends about sake
- search_instagram_sake: Find Instagram posts and photos about a specific sake
- search_sake_places: **ONLY use when user asks for PHYSICAL PLACES (shops/restaurants/bars)** - Finds sake-related places with map visualization, photos, and reviews. DO NOT use for recommendation queries. Supports two modes:
  * WITH sake_name: Finds restaurants/bars serving a SPECIFIC sake brand (e.g., sake_name="獺祭", location="Tokyo")
  * WITHOUT sake_name: Finds general sake shops/restaurants/izakayas (e.g., location="Kyoto", search_type="both")
- search_sake_online_shops: Search for a specific sake on online sake shops (jizake.com, matsuzaki-shop.jp, sakenomy.jp, yajima-jizake.co.jp, ikedasaketen.com, souta-shoten.shop, uekiya-shouten.com). Use when users want to BUY sake online.

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

When users ask about buying sake online:
- Use search_sake_online_shops when users ask where to buy or purchase a specific sake online
- Examples:
  * "獺祭をネットで買いたい" → search_sake_online_shops(sake_name="獺祭")
  * "Where can I buy Dassai online?" → search_sake_online_shops(sake_name="Dassai")
  * "久保田の通販" → search_sake_online_shops(sake_name="久保田")
  * "I want to order Kubota Manju" → search_sake_online_shops(sake_name="Kubota Manju")

**CRITICAL: When to use search_sake_places vs. search_sake_rankings/info:**

**Use search_sake_places ONLY when the user is asking about PHYSICAL PLACES (shops, restaurants, bars):**
- User wants to FIND a shop/restaurant/bar (場所、店、お店、販売店、居酒屋、バー)
- User wants to know WHERE TO BUY or DRINK sake (買える、飲める、扱っている、提供、販売している)
- User asks for shops/restaurants explicitly (shop, store, restaurant, bar, izakaya)

**DO NOT use search_sake_places when:**
- User asks for RECOMMENDATIONS in a location (オススメ、ランキング、人気、おいしい)
- User asks for INFORMATION about sake from a region (について、特徴、種類、地酒)
- User asks about sake characteristics or rankings in an area
- Query mentions a location but doesn't ask for physical places

**Examples of when to use search_sake_places:**
✅ "写楽が飲める店は？" → search_sake_places(location="Tokyo", sake_name="写楽")
✅ "Where can I drink Dassai in Kyoto?" → search_sake_places(location="Kyoto", sake_name="Dassai")
✅ "獺祭を扱っている居酒屋" → search_sake_places(location="Tokyo", sake_name="獺祭")
✅ "東京で日本酒が飲める場所は？" → search_sake_places(location="東京", search_type="restaurant")
✅ "Where can I buy sake in Kyoto?" → search_sake_places(location="Kyoto", search_type="shop")
✅ "京都の日本酒販売店を教えて" → search_sake_places(location="京都", search_type="shop")
✅ "Find sake bars near Osaka" → search_sake_places(location="Osaka", search_type="restaurant")

**Examples of when NOT to use search_sake_places (use search_sake_rankings/info instead):**
❌ "川越でオススメの日本酒を教えて" → search_sake_rankings(sake_type="") + mention Kawagoe region
❌ "東京の人気の日本酒は？" → search_sake_rankings(sake_type="")
❌ "京都の地酒について教えて" → search_sake_info(sake_name="京都 地酒")
❌ "Tell me recommended sake in Tokyo" → search_sake_rankings(sake_type="")

**Parameters for search_sake_places:**
1. **WITH sake_name** - When asking about a SPECIFIC sake brand at physical locations:
   - Extract the sake name from the query
   - Ask for location if not provided (default to Tokyo)

2. **WITHOUT sake_name** - When asking for general sake shops/restaurants:
   - Use search_type to specify "shop", "restaurant", or "both"
   - Never respond with location information from your own knowledge
   - Always call the tool first to get real-time data with map coordinates

**IMPORTANT:**
- The tool returns structured data that the app displays as an interactive map with photos, reviews, and hyperlinks
- If you don't use the tool for place queries, the map will NOT display properly
- If user asks for recommendations, use ranking/info tools instead

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
    Check if the query is specifically asking about PLACES/SHOPS/RESTAURANTS to buy or drink sake.

    Returns True ONLY when the user is asking about physical locations (shops, restaurants, bars).
    Returns False for general recommendations or information queries that happen to mention a location.

    Examples that should return True:
    - "川越で日本酒が買える店は？" (Where can I buy sake in Kawagoe?)
    - "東京の日本酒バーを教えて" (Tell me sake bars in Tokyo)
    - "獺祭が飲める場所" (Places to drink Dassai)

    Examples that should return False:
    - "川越でオススメの日本酒を教えて" (Tell me recommended sake in Kawagoe)
    - "東京の地酒について" (About Tokyo local sake)
    - "京都の日本酒ランキング" (Kyoto sake rankings)

    Returns:
        True if the query is specifically asking about physical locations
    """
    text_lower = text.lower()

    # Japanese place/action keywords - must be present for location query
    japanese_place_keywords = [
        "場所", "店", "お店", "販売店", "酒屋", "居酒屋", "バー", "レストラン",
        "飲める", "買える", "扱っている", "提供", "取り扱い", "販売している",
        "近く", "付近", "周辺", "地図", "マップ",
        "どこで買", "どこで飲", "どこで売", "どこにある",
        "探して", "見つけ", "検索"
    ]

    # English place/action keywords
    english_place_keywords = [
        "where can i buy", "where can i drink", "where to buy", "where to drink",
        "shop", "store", "restaurant", "bar", "izakaya",
        "find", "buy", "drink", "near", "around", "location", "place",
        "serving", "sell", "available at", "map"
    ]

    # Check for Japanese place keywords
    for keyword in japanese_place_keywords:
        if keyword in text:
            return True

    # Check for English place keywords
    for keyword in english_place_keywords:
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
        tool_choice={"type": "function", "function": {"name": "search_sake_places"}}
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

    # CRITICAL: For location queries, use the TOOL's output directly instead of LLM's summary
    # The LLM often generates its own location list from its knowledge, which doesn't match
    # the actual Google Places results in MAP_DATA. This causes text/map mismatch.
    # IMPORTANT: Iterate in REVERSE to get the MOST RECENT ToolMessage, not old ones from history
    import re
    for msg in reversed(final_messages):
        if isinstance(msg, ToolMessage) and msg.content:
            content = msg.content
            if "MAP_DATA_START" in content and "MAP_DATA_END" in content:
                # Found location tool output - use the tool's text directly
                # This ensures the text list matches the map markers
                response_text = content
                break

    # Update chat history
    new_history = list(final_messages)

    return response_text, new_history
