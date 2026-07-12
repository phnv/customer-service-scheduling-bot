from sqlmodel import Session, select
from datetime import date
from typing import List, Optional
from app.database.models import AvailabilitySlot, Service, Doctor

class AppointmentService:
    def __init__(self, session: Session):
        self.session = session
        
    def check_availability(self, specialty: Optional[str] = None, start_date: Optional[date] = None) -> List[dict]:
        """
        Finds available slots.
        """
        query = select(AvailabilitySlot, Service, Doctor).where(
            AvailabilitySlot.service_id == Service.service_id,
            AvailabilitySlot.doctor_id == Doctor.doctor_id,
            AvailabilitySlot.status == "available"
        )
        
        if specialty:
            query = query.where(Service.specialty == specialty)
            
        results = self.session.exec(query).all()
        
        available_slots = []
        for slot, service, doctor in results:
            if start_date and slot.start_at.date() != start_date:
                continue
            available_slots.append({
                "slot_id": slot.slot_id,
                "start_at": slot.start_at.isoformat(),
                "end_at": slot.end_at.isoformat(),
                "doctor_name": doctor.full_name,
                "specialty": service.specialty,
                "service_mode": service.service_mode,
                "price": service.price
            })
            
        return available_slots

    def reserve_appointment(self, slot_id: str, conversation_id: str) -> dict:
        """Placeholder for write operation."""
        return {
            "status": "success",
            "message": f"Appointment reserved successfully for slot {slot_id}.",
            "data": {
                "reservation_id": "mock-reservation-123",
                "slot_id": slot_id,
                "conversation_id": conversation_id,
                "reserved_until": "2026-12-31T23:59:59"
            }
        }

    def cancel_appointment(self, reservation_id: str) -> dict:
        """Placeholder for write operation."""
        return {
            "status": "success",
            "message": f"Reservation {reservation_id} cancelled."
        }

    def reschedule_appointment(self, reservation_id: str, new_slot_id: str) -> dict:
        """Placeholder for write operation."""
        return {
            "status": "success",
            "message": f"Reservation {reservation_id} rescheduled to slot {new_slot_id}."
        }
