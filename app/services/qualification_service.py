from sqlmodel import Session

class QualificationService:
    def __init__(self, session: Session):
        self.session = session
        
    def register_lead(self, conversation_id: str, summary: str, priority: str = None) -> dict:
        """Placeholder for write operation."""
        return {
            "status": "success",
            "message": "Lead registered successfully.",
            "data": {
                "conversation_id": conversation_id,
                "summary": summary,
                "priority": priority or "normal"
            }
        }
