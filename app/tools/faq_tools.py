import logging
import json
from langchain_core.tools import tool
from langgraph.types import Command
from app.services.faq_service import FAQService

logger = logging.getLogger(__name__)

_faq_service = FAQService()

@tool
def search_faq_tool(query: str) -> Command:
    """
    Searches the clinic's knowledge base for an answer to the user's question.
    
    Args:
        query: The user's question or topic to search for.
        
    Returns:
        A LangGraph Command that updates the state with retrieved_docs and provides context to the LLM.
    """
    logger.info(f"Tool 'search_faq_tool' called with query: {query!r}")
    
    results = _faq_service.search_knowledge_base(query, top_k=3)
    
    if not results:
        context_str = "No relevant information found in the knowledge base."
    else:
        parts = []
        for i, res in enumerate(results, 1):
            parts.append(f"--- Document {i} ---\nTitle: {res['title']}\nContent: {res['content']}")
        context_str = "\n\n".join(parts)
        
    logger.info(f"Retrieved {len(results)} chunks from knowledge base.")
    
    # We update the state with retrieved_docs.
    # We also update 'messages' manually with the observation, OR 
    # we can just rely on ToolNode treating the Command's update as the tool response if it doesn't contain 'messages'.
    # A robust way is to just return a dict that the LLM can read as a string, but since we are updating state, 
    # we'll return Command(update={"retrieved_docs": results, "search_result": context_str}).
    # Actually, returning a dict inside update that isn't in AgentState might fail.
    # Let's just update `retrieved_docs`. If ToolNode sets the tool message content to `str(update)`, 
    # the LLM will see the JSON containing retrieved_docs, which contains title and content. This works perfectly.
    
    return Command(
        update={
            "retrieved_docs": results
        }
    )
