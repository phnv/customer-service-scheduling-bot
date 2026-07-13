import logging
from typing import Optional, Dict, Any, List
from datetime import date
from langchain_core.tools import tool
from sqlmodel import Session
from app.database.engine import engine
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@tool
def find_contact_tool(phone: Optional[str] = None, document: Optional[str] = None, email: Optional[str] = None) -> Optional[dict]:
    """Finds a contact by their phone number, document, or email."""
    logger.info(f"Tool 'find_contact_tool' called with payload: phone={phone}, document={document}, email={email}")
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.find_contact(phone=phone, document=document, email=email)
        logger.info(f"Tool 'find_contact_tool' output: {result}")
        return result

@tool
def create_contact_tool(full_name: str, phone: str, document: Optional[str] = None, email: Optional[str] = None, birthdate: Optional[str] = None) -> str:
    """Creates a new contact in the system. Birthdate should be in YYYY-MM-DD format."""
    logger.info(f"Tool 'create_contact_tool' called with payload: full_name={full_name}, phone={phone}, document={document}, email={email}, birthdate={birthdate}")
    
    parsed_date = date.fromisoformat(birthdate) if birthdate else None
    
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.create_contact(full_name=full_name, phone=phone, document=document, email=email, birthdate=parsed_date)
        logger.info(f"Tool 'create_contact_tool' output: {result}")
        return result

@tool
def update_contact_tool(contact_id: str, fields: Dict[str, Any]) -> Optional[dict]:
    """Updates an existing contact with the provided fields."""
    logger.info(f"Tool 'update_contact_tool' called with payload: contact_id={contact_id}, fields={fields}")
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.update_contact(contact_id=contact_id, fields=fields)
        logger.info(f"Tool 'update_contact_tool' output: {result}")
        return result

@tool
def find_patient_tool(contact_id: Optional[str] = None, patient_name: Optional[str] = None) -> List[dict]:
    """Finds patients by contact_id or patient_name."""
    logger.info(f"Tool 'find_patient_tool' called with payload: contact_id={contact_id}, patient_name={patient_name}")
    with Session(engine) as session:
        service = CustomerService(session)
        result = service.find_patient(contact_id=contact_id, patient_name=patient_name)
        logger.info(f"Tool 'find_patient_tool' output: {result}")
        return result

@tool
def create_patient_tool(contact_id: str, full_name: str, relationship: str, birthdate: Optional[str] = None) -> str:
    """Creates a new patient in the system. Birthdate should be in YYYY-MM-DD format."""
    logger.info(f"Tool 'create_patient_tool' called with payload: contact_id={contact_id}, full_name={full_name}, relationship={relationship}, birthdate={birthdate}")
    
    parsed_date = date.fromisoformat(birthdate) if birthdate else None

    with Session(engine) as session:
        service = CustomerService(session)
        result = service.create_patient(contact_id=contact_id, full_name=full_name, relationship=relationship, birthdate=parsed_date)
        logger.info(f"Tool 'create_patient_tool' output: {result}")
        return result
