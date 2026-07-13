import uuid
from sqlmodel import Session, select
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.database.models import AvailabilitySlot, Service, Doctor, Reservation, Appointment, SlotStatus, ReservationStatus, AppointmentStatus

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
            AvailabilitySlot.status == SlotStatus.AVAILABLE
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

    def reserve_slot(self, slot_id: str, conversation_id: str) -> dict:
        """Reserves an availability slot and returns the reservation_id."""
        slot = self.session.get(AvailabilitySlot, slot_id)
        if not slot or slot.status != SlotStatus.AVAILABLE:
            raise ValueError(f"Slot {slot_id} is not available for reservation.")
            
        reservation_id = str(uuid.uuid4())
        now = datetime.utcnow()
        reserved_until = now + timedelta(days=1)  # Default buffer, handled by external ChatViewModel
        
        # Create reservation
        new_reservation = Reservation(
            reservation_id=reservation_id,
            slot_id=slot_id,
            conversation_id=conversation_id,
            status=ReservationStatus.ACTIVE,
            reserved_until=reserved_until,
            created_at=now
        )
        
        # Update slot
        slot.status = SlotStatus.RESERVED
        slot.reservation_expires_at = reserved_until
        slot.updated_at = now
        
        self.session.add(new_reservation)
        self.session.add(slot)
        self.session.commit()
        
        return {
            "reservation_id": reservation_id,
            "slot_id": slot_id,
            "conversation_id": conversation_id,
            "status": "success"
        }

    def cancel_reservation(self, reservation_id: str) -> dict:
        """Cancels a reservation and frees the slot."""
        reservation = self.session.get(Reservation, reservation_id)
        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found.")
            
        slot = self.session.get(AvailabilitySlot, reservation.slot_id)
        
        reservation.status = ReservationStatus.CANCELLED
        self.session.add(reservation)
        
        if slot:
            slot.status = SlotStatus.AVAILABLE
            slot.reservation_expires_at = None
            slot.updated_at = datetime.utcnow()
            self.session.add(slot)
            
        self.session.commit()
        
        return {"status": "success", "reservation_id": reservation_id, "message": "Reservation cancelled."}

    def create_appointment(self, reservation_id: str, patient_id: str, contact_id: str) -> dict:
        """Creates an appointment from a reservation."""
        reservation = self.session.get(Reservation, reservation_id)
        if not reservation or reservation.status != ReservationStatus.ACTIVE:
            raise ValueError(f"Valid reservation {reservation_id} not found.")
            
        slot = self.session.get(AvailabilitySlot, reservation.slot_id)
        
        appointment_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        new_appointment = Appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            contact_id=contact_id,
            doctor_id=slot.doctor_id,
            service_id=slot.service_id,
            slot_id=slot.slot_id,
            reservation_id=reservation_id,
            status=AppointmentStatus.PENDING_PAYMENT,
            scheduled_at=now,
            created_at=now,
            updated_at=now
        )
        
        # Update slot
        slot.status = SlotStatus.BOOKED
        slot.updated_at = now
        
        # Update reservation
        reservation.status = ReservationStatus.CONVERTED
        
        self.session.add(new_appointment)
        self.session.add(slot)
        self.session.add(reservation)
        self.session.commit()
        
        return {
            "appointment_id": appointment_id,
            "status": "success",
            "message": "Appointment created pending payment."
        }

    def cancel_appointment(self, appointment_id: str) -> dict:
        """Cancels an existing appointment."""
        appointment = self.session.get(Appointment, appointment_id)
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found.")
            
        now = datetime.utcnow()
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = now
        appointment.updated_at = now
        
        slot = self.session.get(AvailabilitySlot, appointment.slot_id)
        if slot:
            slot.status = SlotStatus.AVAILABLE
            slot.updated_at = now
            self.session.add(slot)
            
        self.session.add(appointment)
        self.session.commit()
        
        return {"status": "success", "appointment_id": appointment_id, "message": "Appointment cancelled."}

    def reschedule_appointment(self, appointment_id: str, new_slot_id: str) -> dict:
        """Reschedules an appointment to a new slot."""
        appointment = self.session.get(Appointment, appointment_id)
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found.")
            
        new_slot = self.session.get(AvailabilitySlot, new_slot_id)
        if not new_slot or new_slot.status != SlotStatus.AVAILABLE:
            raise ValueError(f"New slot {new_slot_id} is not available.")
            
        old_slot = self.session.get(AvailabilitySlot, appointment.slot_id)
        
        now = datetime.utcnow()
        
        # Update old slot
        if old_slot:
            old_slot.status = SlotStatus.AVAILABLE
            old_slot.updated_at = now
            self.session.add(old_slot)
            
        # Update new slot
        new_slot.status = SlotStatus.BOOKED
        new_slot.updated_at = now
        self.session.add(new_slot)
        
        # Update appointment
        appointment.slot_id = new_slot_id
        appointment.doctor_id = new_slot.doctor_id
        appointment.service_id = new_slot.service_id
        appointment.updated_at = now
        
        self.session.add(appointment)
        self.session.commit()
        
        return {"status": "success", "appointment_id": appointment_id, "message": f"Rescheduled to slot {new_slot_id}."}
