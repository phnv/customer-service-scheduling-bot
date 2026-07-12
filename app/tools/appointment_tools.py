import logging
from typing import Optional, List
from datetime import date
from langchain_core.tools import tool
from sqlmodel import Session
from app.database.engine import engine
from app.services.appointment_service import AppointmentService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@tool
def check_availability_tool(specialty: Optional[str] = None, start_date: Optional[date] = None) -> List[dict]:
    """Finds available appointment slots, optionally filtered by specialty and start date."""
    logger.info(f"Tool 'check_availability_tool' called with payload: specialty={specialty}, start_date={start_date}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.check_availability(specialty=specialty, start_date=start_date)
        logger.info(f"Tool 'check_availability_tool' output length: {len(result)}")
        return result

@tool
def reserve_appointment_tool(slot_id: str, conversation_id: str) -> dict:
    """Reserves an available appointment slot."""
    logger.info(f"Tool 'reserve_appointment_tool' called with payload: slot_id={slot_id}, conversation_id={conversation_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.reserve_appointment(slot_id=slot_id, conversation_id=conversation_id)
        logger.info(f"Tool 'reserve_appointment_tool' output: {result}")
        return result

@tool
def cancel_appointment_tool(reservation_id: str) -> dict:
    """Cancels an existing appointment reservation."""
    logger.info(f"Tool 'cancel_appointment_tool' called with payload: reservation_id={reservation_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.cancel_appointment(reservation_id=reservation_id)
        logger.info(f"Tool 'cancel_appointment_tool' output: {result}")
        return result

@tool
def reschedule_appointment_tool(reservation_id: str, new_slot_id: str) -> dict:
    """Reschedules an appointment to a new slot."""
    logger.info(f"Tool 'reschedule_appointment_tool' called with payload: reservation_id={reservation_id}, new_slot_id={new_slot_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.reschedule_appointment(reservation_id=reservation_id, new_slot_id=new_slot_id)
        logger.info(f"Tool 'reschedule_appointment_tool' output: {result}")
        return result
