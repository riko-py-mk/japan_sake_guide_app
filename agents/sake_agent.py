"""
Japanese Sake Guide Agent using LangGraph.

This module implements an AI agent that helps users learn about and discover Japanese sake.
The agent can:
- Recommend sake based on user preferences
- Search for specific sake information
- Find sake rankings from trusted sources
- Search social media (Twitter, Instagram, Facebook) for sake-related content via Tavily
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
1. **Sake Recommendations**: Suggest sake based on user preferences (flavor profiles, food pairings, occasions), grounded in the current sakenowa top-50
2. **Sake Information**: Provide detailed information about specific sake brands, breweries, and production methods
3. **Rankings & Reviews**: Share the current sakenowa ranking and reviews from trusted sources
4. **Social Media Insights**: Find posts about sake on Twitter, Instagram, and Facebook
5. **Location-Based Search**: Find sake shops, restaurants, and izakayas in specific locations with map visualization
6. **Online Shop Search**: Search for sake available on specialized online sake shops for purchasing

Available Tools:
- get_sake_rankings: **PREFERRED for any ranking, popularity or recommendation query.** Returns the current sakenowa top-50 from local structured data — instant, no web search, with exact rank, prefecture and flavour profile for each brand. Optional filters: flavor (Fruity/華やか, Mellow/芳醇, Full Body/重厚, Mild/穏やか, Dry/ドライ, Light/軽快, Sparkling), prefecture (kanji or romaji), top_n.
  * "今年人気の日本酒は？" → get_sake_rankings()
  * "Recommend a fruity sake" → get_sake_rankings(flavor="Fruity")
  * "山形のおすすめ日本酒" → get_sake_rankings(prefecture="山形")
  * "Tell me recommended sake in Tokyo" → get_sake_rankings(prefecture="Tokyo")
  After listing brands, offer to look up tasting notes with search_sake_info.
- search_sake_rankings: Web search of ranking sites (sakenowa.com, saketime.jp). Use ONLY when get_sake_rankings cannot answer — e.g. a specific grade ("best daiginjo"), a seasonal or editorial "best of" list, or when the user wants sake outside the top 50.
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
2. Call get_sake_rankings first (with a flavor/prefecture filter when the user gave one)
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

**CRITICAL: You choose the tools. Nothing else routes for you — read the question and pick deliberately.**
A location word in the question does NOT by itself mean a place search, and words like
"find", "search", "探して" or "検索" say nothing about which tool to use.
Decide on the user's INTENT:
- wants brands to try → get_sake_rankings / search_sake_info
- wants posts and buzz → search_social_media_hashtag / search_twitter_sake / search_instagram_sake
- wants to order online → search_sake_online_shops
- wants a physical venue to visit → search_sake_places

**When to use search_sake_places vs. get_sake_rankings/search_sake_info:**

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

**Examples of when NOT to use search_sake_places (use get_sake_rankings/search_sake_info instead):**
❌ "川越でオススメの日本酒を教えて" → get_sake_rankings(prefecture="埼玉") + mention Kawagoe region
❌ "東京の人気の日本酒は？" → get_sake_rankings(prefecture="東京")
❌ "京都の地酒について教えて" → search_sake_info(sake_name="京都 地酒")
❌ "Tell me recommended sake in Tokyo" → get_sake_rankings(prefecture="Tokyo")
❌ "獺祭のInstagram投稿を探して" → search_instagram_sake(sake_name="獺祭")  (NOT a place search)
❌ "久保田 萬寿の通販を探して" → search_sake_online_shops(sake_name="久保田 萬寿")  (NOT a place search)

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
- If user asks for recommendations, use get_sake_rankings instead

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

    # Bind tools to the LLM. Tool selection is left entirely to the model, guided
    # by SAKE_GUIDE_SYSTEM_PROMPT. An earlier version force-bound
    # search_sake_places via tool_choice whenever the query contained a keyword
    # like "find"/"探して"/"検索", which made the social-media, online-shop and
    # ranking tools unreachable for many ordinary questions.
    llm_with_tools = llm.bind_tools(tools)

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

        return {"messages": [llm_with_tools.invoke(messages)]}

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
