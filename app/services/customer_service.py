import uuid
from sqlmodel import Session, select
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from app.database.models import Contact, Patient

class CustomerService:
    def __init__(self, session: Session):
        self.session = session
        
    def find_contact(self, phone: Optional[str] = None, document: Optional[str] = None, email: Optional[str] = None) -> Optional[dict]:
        """
        Finds a contact by phone, document, or email.
        """
        query = select(Contact)
        if phone:
            query = query.where(Contact.phone == phone)
        elif document:
            query = query.where(Contact.document == document)
        elif email:
            query = query.where(Contact.email == email)
        else:
            return None
            
        contact = self.session.exec(query).first()
        if not contact:
            return None
        
        return contact.model_dump()
        
    def create_contact(self, full_name: str, phone: str, document: Optional[str] = None, email: Optional[str] = None, birthdate: Optional[date] = None) -> str:
        """
        Creates a new contact and returns the contact_id.
        """
        contact_id = str(uuid.uuid4())
        now = datetime.utcnow()
        new_contact = Contact(
            contact_id=contact_id,
            full_name=full_name,
            phone=phone,
            document=document,
            email=email,
            birthdate=birthdate,
            created_at=now,
            updated_at=now
        )
        self.session.add(new_contact)
        self.session.commit()
        return contact_id

    def update_contact(self, contact_id: str, fields: Dict[str, Any]) -> Optional[dict]:
        """
        Updates fields of an existing contact.
        """
        contact = self.session.get(Contact, contact_id)
        if not contact:
            return None
            
        for key, value in fields.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
                
        contact.updated_at = datetime.utcnow()
        self.session.add(contact)
        self.session.commit()
        self.session.refresh(contact)
        return contact.model_dump()

    def find_patient(self, contact_id: Optional[str] = None, patient_name: Optional[str] = None) -> List[dict]:
        """
        Finds patients by contact_id or patient_name.
        """
        query = select(Patient)
        if contact_id:
            query = query.where(Patient.contact_id == contact_id)
        if patient_name:
            query = query.where(Patient.full_name == patient_name)
            
        patients = self.session.exec(query).all()
        return [p.model_dump() for p in patients]

    def create_patient(self, contact_id: str, full_name: str, relationship: str, birthdate: Optional[date] = None) -> str:
        """
        Creates a new patient linked to a contact and returns patient_id.
        """
        patient_id = str(uuid.uuid4())
        now = datetime.utcnow()
        new_patient = Patient(
            patient_id=patient_id,
            contact_id=contact_id,
            full_name=full_name,
            relationship=relationship,
            birthdate=birthdate,
            created_at=now,
            updated_at=now
        )
        self.session.add(new_patient)
        self.session.commit()
        return patient_id
