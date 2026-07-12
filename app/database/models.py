import enum
from typing import Optional, List
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Column, String, Enum as SQLEnum

# Enums
class ServiceType(str, enum.Enum):
    INITIAL = "initial"
    RETURN = "return"
    FREE_RETURN = "free_return"

class ServiceMode(str, enum.Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"

class Relationship(str, enum.Enum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    OTHER = "other"

class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    BOOKED = "booked"
    UNAVAILABLE = "unavailable"

class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    CONVERTED = "converted"

class AppointmentStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

# Models
class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"
    doctor_id: str = Field(primary_key=True)
    registry_number: Optional[str] = None
    full_name: str
    email: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class DoctorSpecialty(SQLModel, table=True):
    __tablename__ = "doctor_specialties"
    doctor_id: str = Field(primary_key=True, foreign_key="doctors.doctor_id")
    specialty: str = Field(primary_key=True)

class Service(SQLModel, table=True):
    __tablename__ = "services"
    service_id: str = Field(primary_key=True)
    doctor_id: str = Field(foreign_key="doctors.doctor_id")
    specialty: str
    service_type: ServiceType = Field(sa_column=Column(String))
    service_mode: ServiceMode = Field(sa_column=Column(String))
    price: float
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class Contact(SQLModel, table=True):
    __tablename__ = "contacts"
    contact_id: str = Field(primary_key=True)
    full_name: str
    email: Optional[str] = None
    phone: str
    document: Optional[str] = None
    birthdate: Optional[date] = None
    created_at: datetime
    updated_at: datetime

class Patient(SQLModel, table=True):
    __tablename__ = "patients"
    patient_id: str = Field(primary_key=True)
    contact_id: str = Field(foreign_key="contacts.contact_id")
    full_name: str
    birthdate: Optional[date] = None
    relationship: Relationship = Field(sa_column=Column(String))
    created_at: datetime
    updated_at: datetime

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    conversation_id: str = Field(primary_key=True)
    contact_id: str = Field(foreign_key="contacts.contact_id")
    patient_id: Optional[str] = Field(default=None, foreign_key="patients.patient_id")
    started_at: datetime
    last_message_at: datetime
    status: ConversationStatus = Field(sa_column=Column(String))

class LeadQualification(SQLModel, table=True):
    __tablename__ = "lead_qualification"
    conversation_id: str = Field(primary_key=True, foreign_key="conversations.conversation_id")
    converted: Optional[bool] = None
    blocker: Optional[str] = None
    first_time_patient: Optional[bool] = None
    contact_reason: Optional[str] = None
    symptoms: Optional[str] = None
    symptoms_duration: Optional[str] = None
    priority: Optional[str] = None
    frustration_level: Optional[str] = None
    summary: Optional[str] = None
    qualified_by: Optional[str] = None
    updated_at: datetime

class AvailabilitySlot(SQLModel, table=True):
    __tablename__ = "availability_slots"
    slot_id: str = Field(primary_key=True)
    doctor_id: str = Field(foreign_key="doctors.doctor_id")
    service_id: str = Field(foreign_key="services.service_id")
    start_at: datetime
    end_at: datetime
    status: SlotStatus = Field(sa_column=Column(String))
    reservation_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class Reservation(SQLModel, table=True):
    __tablename__ = "reservations"
    reservation_id: str = Field(primary_key=True)
    slot_id: str = Field(foreign_key="availability_slots.slot_id")
    conversation_id: str = Field(foreign_key="conversations.conversation_id")
    status: ReservationStatus = Field(sa_column=Column(String))
    reserved_until: datetime
    created_at: datetime

class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"
    appointment_id: str = Field(primary_key=True)
    patient_id: str = Field(foreign_key="patients.patient_id")
    contact_id: str = Field(foreign_key="contacts.contact_id")
    doctor_id: str = Field(foreign_key="doctors.doctor_id")
    service_id: str = Field(foreign_key="services.service_id")
    slot_id: str = Field(foreign_key="availability_slots.slot_id")
    reservation_id: Optional[str] = Field(default=None, foreign_key="reservations.reservation_id")
    status: AppointmentStatus = Field(sa_column=Column(String))
    scheduled_at: datetime
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    payment_id: str = Field(primary_key=True)
    appointment_id: str = Field(foreign_key="appointments.appointment_id")
    order_key: Optional[str] = None
    provider_order_id: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    amount: float
    payment_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ApiErrorLog(SQLModel, table=True):
    __tablename__ = "api_error_log"
    log_id: str = Field(primary_key=True)
    created_at: datetime
    severity: str
    service_name: str
    function_name: str
    conversation_id: Optional[str] = Field(default=None, foreign_key="conversations.conversation_id")
    order_key: Optional[str] = None
    error_message: str
    stack_trace: Optional[str] = None
    payload_snapshot: Optional[str] = None
    extra_context: Optional[str] = None
