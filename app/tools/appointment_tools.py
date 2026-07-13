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
def check_availability_tool(specialty: Optional[str] = None, start_date: Optional[str] = None) -> List[dict]:
    """Finds available appointment slots. start_date should be YYYY-MM-DD."""
    logger.info(f"Tool 'check_availability_tool' called with payload: specialty={specialty}, start_date={start_date}")
    parsed_date = date.fromisoformat(start_date) if start_date else None
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.check_availability(specialty=specialty, start_date=parsed_date)
        logger.info(f"Tool 'check_availability_tool' output: {result}")
        return result

@tool
def reserve_slot_tool(slot_id: str, conversation_id: str) -> dict:
    """Reserves an availability slot and returns a reservation_id."""
    logger.info(f"Tool 'reserve_slot_tool' called with payload: slot_id={slot_id}, conversation_id={conversation_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.reserve_slot(slot_id=slot_id, conversation_id=conversation_id)
        logger.info(f"Tool 'reserve_slot_tool' output: {result}")
        return result

@tool
def cancel_reservation_tool(reservation_id: str) -> dict:
    """Cancels a reservation and frees the slot."""
    logger.info(f"Tool 'cancel_reservation_tool' called with payload: reservation_id={reservation_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.cancel_reservation(reservation_id=reservation_id)
        logger.info(f"Tool 'cancel_reservation_tool' output: {result}")
        return result

@tool
def create_appointment_tool(reservation_id: str, patient_id: str, contact_id: str) -> dict:
    """Creates an appointment from an active reservation."""
    logger.info(f"Tool 'create_appointment_tool' called with payload: reservation_id={reservation_id}, patient_id={patient_id}, contact_id={contact_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.create_appointment(reservation_id=reservation_id, patient_id=patient_id, contact_id=contact_id)
        logger.info(f"Tool 'create_appointment_tool' output: {result}")
        return result

@tool
def cancel_appointment_tool(appointment_id: str) -> dict:
    """Cancels an existing appointment."""
    logger.info(f"Tool 'cancel_appointment_tool' called with payload: appointment_id={appointment_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.cancel_appointment(appointment_id=appointment_id)
        logger.info(f"Tool 'cancel_appointment_tool' output: {result}")
        return result

@tool
def reschedule_appointment_tool(appointment_id: str, new_slot_id: str) -> dict:
    """Reschedules an appointment to a new slot."""
    logger.info(f"Tool 'reschedule_appointment_tool' called with payload: appointment_id={appointment_id}, new_slot_id={new_slot_id}")
    with Session(engine) as session:
        service = AppointmentService(session)
        result = service.reschedule_appointment(appointment_id=appointment_id, new_slot_id=new_slot_id)
        logger.info(f"Tool 'reschedule_appointment_tool' output: {result}")
        return result
