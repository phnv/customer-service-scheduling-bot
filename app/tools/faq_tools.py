import logging
from typing import Annotated
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from app.services.faq_service import FAQService
logger = logging.getLogger(__name__)
_faq_service = FAQService()
@tool
def search_faq_tool(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Searches the clinic's knowledge base for an answer to the user's question.
    Args:
        query: The user's question or topic to search for.
    Returns:
        A LangGraph Command that updates the state with retrieved_docs and a
        ToolMessage so the ReAct agent receives the search results as context.
    """
    logger.info(f"Tool 'search_faq_tool' called with query: {query!r}")
    results = _faq_service.search_knowledge_base(query, top_k=3)
    if not results:
        context_str = "No relevant information found in the knowledge base."
    else:
        parts = []
        for i, res in enumerate(results, 1):
            parts.append(
                f"--- Document {i} ---\nTitle: {res['title']}\nContent: {res['content']}"
            )
        context_str = "\n\n".join(parts)
    logger.info(f"Retrieved {len(results)} chunks from knowledge base.")
    return Command(
        update={
            "retrieved_docs": results,
            # LangGraph requires every tool call to have a matching ToolMessage.
            # When returning a Command, we must include it explicitly.
            "messages": [
                ToolMessage(
                    content=context_str,
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )