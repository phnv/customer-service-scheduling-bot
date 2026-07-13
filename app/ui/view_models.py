from typing import Optional
from pydantic import BaseModel

class ButtonsViewModel(BaseModel):
    show_confirm_payment: bool = False
    show_expire_payment: bool = False

class DebugViewModel(BaseModel):
    active_agent: Optional[str] = None
    intent: Optional[str] = None
    contact_id: Optional[str] = None
    patient_id: Optional[str] = None
    active_reservation_id: Optional[str] = None
    retrieved_docs: Optional[list[dict]] = None

class ChatViewModel(BaseModel):
    message: str
    conversation_id: str
    buttons: ButtonsViewModel
    alerts: list[str] = []
    payment_url: Optional[str] = None
    reservation_countdown: Optional[str] = None
    debug: Optional[DebugViewModel] = None
