import logging
from typing import Optional
from langchain_core.tools import tool
from sqlmodel import Session
from app.database.engine import engine
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@tool
def find_customer_tool(phone: Optional[str] = None, document: Optional[str] = None, email: Optional[str] = None) -> Optional[dict]:
    """Finds a customer by their phone number, document, or email."""
    logger.info(f"Tool 'find_customer_tool' called with payload: phone={phone}, document={document}, email={email}")
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.find_customer(phone=phone, document=document, email=email)
        logger.info(f"Tool 'find_customer_tool' output: {result}")
        return result

@tool
def register_customer_tool(full_name: str, phone: str, document: Optional[str] = None, email: Optional[str] = None) -> dict:
    """Registers a new customer in the system."""
    logger.info(f"Tool 'register_customer_tool' called with payload: full_name={full_name}, phone={phone}, document={document}, email={email}")
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.register_customer(full_name=full_name, phone=phone, document=document, email=email)
        logger.info(f"Tool 'register_customer_tool' output: {result}")
        return result
