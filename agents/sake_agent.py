"""
Japanese Sake Guide Agent using LangGraph.

This module implements an AI agent that helps users learn about and discover Japanese sake.
The agent can:
- Recommend sake based on user preferences
- Search for specific sake information
- Find sake rankings from trusted sources
- Search Instagram for sake-related content
"""
from typing import TypedDict, Annotated, Sequence, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from tavily import TavilyClient


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
4. **Social Media Insights**: Find Instagram posts and social content about sake

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

Be friendly, knowledgeable, and passionate about sake. Help users explore the wonderful world of nihonshu!
"""


def create_sake_tools(tavily_api_key: str, instagram_token: Optional[str] = None):
    """
    Create tools for the sake guide agent.

    Args:
        tavily_api_key: API key for Tavily search
        instagram_token: Optional Instagram access token

    Returns:
        List of tool functions
    """
    tavily_client = TavilyClient(api_key=tavily_api_key)

    @tool
    def search_sake_rankings(query: str) -> str:
        """
        Search for sake recommendations from ranking websites like sakenowa.com and saketime.jp.
        Use this tool when users ask for sake recommendations, popular sake, or highly-rated sake.

        Args:
            query: Search query about sake recommendations (e.g., "best fruity sake", "top daiginjo", "人気の純米大吟醸")

        Returns:
            Sake ranking information and recommendations from trusted sources.
        """
        # Detect language and enhance query
        is_japanese = any(
            '\u3040' <= c <= '\u309f' or  # Hiragana
            '\u30a0' <= c <= '\u30ff' or  # Katakana
            '\u4e00' <= c <= '\u9fff'     # Kanji
            for c in query
        )

        if is_japanese:
            enhanced_query = f"日本酒 ランキング おすすめ {query}"
        else:
            enhanced_query = f"Japanese sake ranking recommendation {query}"

        try:
            results = tavily_client.search(
                query=enhanced_query,
                search_depth="advanced",
                max_results=8,
                include_domains=["sakenowa.com", "saketime.jp"],
                include_answer=True,
            )

            output = []
            if results.get("answer"):
                output.append(f"Summary: {results['answer']}\n")

            output.append("Ranking Sources Found:")
            for idx, result in enumerate(results.get("results", []), 1):
                output.append(f"\n{idx}. {result.get('title', 'No title')}")
                output.append(f"   URL: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 500:
                        content = content[:500] + "..."
                    output.append(f"   Content: {content}")

            return "\n".join(output) if output else "No ranking information found."

        except Exception as e:
            return f"Error searching sake rankings: {str(e)}"

    @tool
    def search_sake_info(sake_name: str, additional_query: str = "") -> str:
        """
        Search for detailed information about a specific sake brand or brewery.
        Use this tool when users ask about a specific sake by name.

        Args:
            sake_name: Name of the sake to search for (e.g., "Dassai", "獺祭", "Kubota Manju")
            additional_query: Additional search terms (e.g., "tasting notes", "food pairing")

        Returns:
            Detailed information about the specified sake.
        """
        # Detect language
        is_japanese = any(
            '\u3040' <= c <= '\u309f' or
            '\u30a0' <= c <= '\u30ff' or
            '\u4e00' <= c <= '\u9fff'
            for c in sake_name
        )

        if is_japanese:
            search_query = f"日本酒 {sake_name} {additional_query} 特徴 味わい 蔵元"
        else:
            search_query = f"Japanese sake {sake_name} {additional_query} tasting notes brewery review"

        try:
            results = tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=6,
                include_answer=True,
            )

            output = []
            if results.get("answer"):
                output.append(f"Overview: {results['answer']}\n")

            output.append("Detailed Information:")
            for idx, result in enumerate(results.get("results", []), 1):
                output.append(f"\n{idx}. {result.get('title', 'No title')}")
                output.append(f"   Source: {result.get('url', '')}")
                content = result.get('content', '')
                if content:
                    if len(content) > 600:
                        content = content[:600] + "..."
                    output.append(f"   Details: {content}")

            return "\n".join(output) if output else "No detailed information found."

        except Exception as e:
            return f"Error searching sake info: {str(e)}"

    @tool
    def search_sake_instagram(sake_name: str) -> str:
        """
        Search for Instagram posts and social media content about a specific sake.
        Use this tool to find visual content, reviews, and social discussions about sake.

        Args:
            sake_name: Name of the sake to search for on Instagram

        Returns:
            Instagram and social media content about the sake.
        """
        results = []

        try:
            # Search for Instagram content via web
            ig_results = tavily_client.search(
                query=f"{sake_name} 日本酒 sake site:instagram.com",
                search_depth="basic",
                max_results=5,
            )

            if ig_results.get("results"):
                results.append("Instagram Content Found:")
                for idx, result in enumerate(ig_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")
                    content = result.get('content', '')
                    if content:
                        if len(content) > 300:
                            content = content[:300] + "..."
                        results.append(f"   Preview: {content}")

            # Also search for general social media reviews
            social_results = tavily_client.search(
                query=f"{sake_name} sake review tasting notes",
                search_depth="basic",
                max_results=3,
            )

            if social_results.get("results"):
                results.append("\n\nRelated Reviews & Content:")
                for idx, result in enumerate(social_results.get("results", []), 1):
                    results.append(f"\n{idx}. {result.get('title', 'No title')}")
                    results.append(f"   URL: {result.get('url', '')}")

        except Exception as e:
            results.append(f"Error searching social media: {str(e)}")

        if not results:
            return f"No Instagram or social media content found for '{sake_name}'."

        return "\n".join(results)

    return [search_sake_rankings, search_sake_info, search_sake_instagram]


def create_sake_agent(openai_api_key: str, tavily_api_key: str, instagram_token: Optional[str] = None):
    """
    Create the Japanese Sake Guide agent using LangGraph.

    Args:
        openai_api_key: OpenAI API key
        tavily_api_key: Tavily API key
        instagram_token: Optional Instagram access token

    Returns:
        Compiled LangGraph agent
    """
    # Create the LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        api_key=openai_api_key,
    )

    # Create tools
    tools = create_sake_tools(tavily_api_key, instagram_token)

    # Bind tools to the LLM
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
    is_japanese = any(
        '\u3040' <= c <= '\u309f' or
        '\u30a0' <= c <= '\u30ff' or
        '\u4e00' <= c <= '\u9fff'
        for c in user_message
    )
    language = "ja" if is_japanese else "en"

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

    # Update chat history
    new_history = list(final_messages)

    return response_text, new_history
