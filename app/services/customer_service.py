from sqlmodel import Session, select
from typing import Optional
from app.database.models import Contact, Patient

class CustomerService:
    def __init__(self, session: Session):
        self.session = session
        
    def find_customer(self, phone: str = None, document: str = None, email: str = None) -> Optional[dict]:
        """
        Finds a customer by phone, document, or email.
        Reads from the Contact and Patient tables.
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
            
        # check if patient exists for this contact
        patient_query = select(Patient).where(Patient.contact_id == contact.contact_id)
        patient = self.session.exec(patient_query).first()
        
        return {
            "contact": contact.model_dump(),
            "patient": patient.model_dump() if patient else None
        }
        
    def register_customer(self, full_name: str, phone: str, document: str = None, email: str = None) -> dict:
        """
        Placeholder for write operation.
        """
        return {
            "status": "success",
            "message": "Customer successfully registered.",
            "data": {
                "contact_id": "mock-contact-id-123",
                "full_name": full_name,
                "phone": phone
            }
        }
