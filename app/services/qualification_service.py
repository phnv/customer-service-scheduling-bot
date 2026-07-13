from sqlmodel import Session
from datetime import datetime
from typing import Dict, Any, Optional
from app.database.models import LeadQualification

class QualificationService:
    def __init__(self, session: Session):
        self.session = session
        
    def get_lead(self, conversation_id: str) -> Optional[dict]:
        """Gets lead qualification for a conversation."""
        lead = self.session.get(LeadQualification, conversation_id)
        if not lead:
            return None
        return lead.model_dump()

    def update_lead(self, conversation_id: str, fields: Dict[str, Any]) -> dict:
        """Updates or inserts lead qualification fields."""
        lead = self.session.get(LeadQualification, conversation_id)
        
        now = datetime.utcnow()
        if not lead:
            lead = LeadQualification(conversation_id=conversation_id, updated_at=now)
            
        for key, value in fields.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
                
        lead.updated_at = now
        self.session.add(lead)
        self.session.commit()
        self.session.refresh(lead)
        
        return lead.model_dump()
