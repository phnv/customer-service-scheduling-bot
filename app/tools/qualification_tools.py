import logging
from typing import Optional, Dict, Any

import mlflow
from mlflow.entities import SpanType
from langchain_core.tools import tool
from sqlmodel import Session
from app.database.engine import engine
from app.services.qualification_service import QualificationService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@mlflow.trace(span_type=SpanType.TOOL)
@tool
def get_lead_tool(conversation_id: str) -> Optional[dict]:
    """Gets lead qualification data for a conversation."""
    logger.info(f"Tool 'get_lead_tool' called with payload: conversation_id={conversation_id}")
    with Session(engine) as session:
        service = QualificationService(session)
        result = service.get_lead(conversation_id=conversation_id)
        logger.info(f"Tool 'get_lead_tool' output: {result}")
        return result

@mlflow.trace(span_type=SpanType.TOOL)
@tool
def update_lead_tool(conversation_id: str, fields: Dict[str, Any]) -> dict:
    """Updates or inserts lead qualification fields."""
    logger.info(f"Tool 'update_lead_tool' called with payload: conversation_id={conversation_id}, fields={fields}")
    with Session(engine) as session:
        service = QualificationService(session)
        result = service.update_lead(conversation_id=conversation_id, fields=fields)
        logger.info(f"Tool 'update_lead_tool' output: {result}")
        return result
