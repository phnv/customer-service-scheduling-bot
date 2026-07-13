from datetime import datetime, timezone
from sqlmodel import Session, select
from app.database.models import Contact, Doctor

def test_create_and_read_contact(db_session: Session):
    contact_id = "test-contact-123"
    new_contact = Contact(
        contact_id=contact_id,
        full_name="John Doe",
        email="john.doe@example.com",
        phone="555-1234",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(new_contact)
    db_session.commit()

    # Read it back
    contact = db_session.exec(select(Contact).where(Contact.contact_id == contact_id)).first()
    assert contact is not None
    assert contact.full_name == "John Doe"
    assert contact.email == "john.doe@example.com"
    assert contact.phone == "555-1234"

def test_create_and_read_doctor(db_session: Session):
    doctor_id = "test-doctor-456"
    new_doctor = Doctor(
        doctor_id=doctor_id,
        full_name="Dr. Smith",
        email="smith@clinic.com",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(new_doctor)
    db_session.commit()

    # Read it back
    doctor = db_session.exec(select(Doctor).where(Doctor.doctor_id == doctor_id)).first()
    assert doctor is not None
    assert doctor.full_name == "Dr. Smith"
    assert doctor.email == "smith@clinic.com"
