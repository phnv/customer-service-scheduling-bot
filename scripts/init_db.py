import csv
import os
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Session
from app.database.engine import engine
from app.database.models import (
    Doctor, DoctorSpecialty, Service, Contact, Patient,
    Conversation, LeadQualification, AvailabilitySlot, Reservation, Appointment, Payment, ApiErrorLog
)

SEED_DIR = "seed-data"

def parse_date(date_str):
    if not date_str: return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def parse_datetime_offset(offset_days, time_str):
    if not offset_days or not time_str: return None
    days = int(offset_days)
    target_date = datetime.now().date() + timedelta(days=days)
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    return datetime.combine(target_date, time_obj)

def load_csv(model, filename, transform_row=lambda x: x):
    filepath = os.path.join(SEED_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filename} - not found.")
        return

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with Session(engine) as session:
            for row in reader:
                # convert empty strings to None
                row = {k: (v if v != "" else None) for k, v in row.items()}
                row = transform_row(row)
                instance = model(**row)
                session.add(instance)
            session.commit()
        print(f"Loaded {filename}.")

def init_db():
    print("Creating tables...")
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    
    # Generic transformers
    def default_transformer(row):
        row["created_at"] = datetime.now()
        row["updated_at"] = datetime.now()
        if "is_active" in row and isinstance(row["is_active"], str):
            row["is_active"] = row["is_active"].lower() == "true"
        if "birthdate" in row and isinstance(row["birthdate"], str):
            row["birthdate"] = parse_date(row["birthdate"])
        return row
        
    def transform_doctor(row):
        return default_transformer(row)
        
    def transform_patient(row):
        return default_transformer(row)

    def transform_slot(row):
        row = default_transformer(row)
        if "offset_days" in row and "start_time" in row:
            row["start_at"] = parse_datetime_offset(row["offset_days"], row["start_time"])
        if "offset_days" in row and "end_time" in row:
            row["end_at"] = parse_datetime_offset(row["offset_days"], row["end_time"])
        row.pop("offset_days", None)
        row.pop("start_time", None)
        row.pop("end_time", None)
        return row

    def transform_reservation(row):
        row = default_transformer(row)
        if "offset_days" in row and "expires_time" in row:
            row["reserved_until"] = parse_datetime_offset(row["offset_days"], row["expires_time"])
        row.pop("offset_days", None)
        row.pop("expires_time", None)
        return row

    def transform_appointment(row):
        row = default_transformer(row)
        if "offset_days" in row and "start_time" in row:
            row["scheduled_at"] = parse_datetime_offset(row["offset_days"], row["start_time"])
        row.pop("offset_days", None)
        row.pop("start_time", None)
        return row
        
    # Create conversations dynamically since they are missing from seed data but needed by reservations
    def create_dummy_conversations():
        with Session(engine) as session:
            res_path = os.path.join(SEED_DIR, "reservations.csv")
            if os.path.exists(res_path):
                with open(res_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        conv_id = row["conversation_id"]
                        if not session.get(Conversation, conv_id):
                            c = Conversation(
                                conversation_id=conv_id,
                                contact_id="1", # arbitrary dummy contact, assuming contact 1 exists
                                started_at=datetime.now(),
                                last_message_at=datetime.now(),
                                status="active"
                            )
                            session.add(c)
                session.commit()
                print("Generated dummy conversations for reservations.")

    print("Loading data...")
    load_csv(Doctor, "doctors.csv", transform_doctor)
    load_csv(DoctorSpecialty, "doctor_specialties.csv")
    load_csv(Service, "services.csv", default_transformer)
    load_csv(Contact, "contacts.csv", default_transformer)
    load_csv(Patient, "patients.csv", transform_patient)
    create_dummy_conversations()
    load_csv(AvailabilitySlot, "availability_slots.csv", transform_slot)
    load_csv(Reservation, "reservations.csv", transform_reservation)
    load_csv(Appointment, "appointments.csv", transform_appointment)
    
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
