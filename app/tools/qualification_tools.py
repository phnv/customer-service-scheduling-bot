import logging
from typing import Optional
from langchain_core.tools import tool
from sqlmodel import Session
from app.database.engine import engine
from app.services.qualification_service import QualificationService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@tool
def register_lead_tool(conversation_id: str, summary: str, priority: Optional[str] = None) -> dict:
    """Registers lead qualification information from a conversation."""
    logger.info(f"Tool 'register_lead_tool' called with payload: conversation_id={conversation_id}, summary={summary}, priority={priority}")
    with Session(engine) as session:
        service = QualificationService(session)
        result = service.register_lead(conversation_id=conversation_id, summary=summary, priority=priority)
        logger.info(f"Tool 'register_lead_tool' output: {result}")
        return result
