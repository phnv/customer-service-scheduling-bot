import logging
from typing import Optional
from app.agents.graph import run_agent
from app.ui.view_models import ChatViewModel, ButtonsViewModel, DebugViewModel

logger = logging.getLogger(__name__)

class ChatApplication:
    @staticmethod
    def run(user_message: str, conversation_id: Optional[str] = None) -> ChatViewModel:
        """
        Executes the LangGraph agent workflow and returns a ViewModel for the UI.
        """
        logger.info(f"ChatApplication running for conversation {conversation_id}")
        response, state = run_agent(user_message, conversation_id)
        
        return ChatApplication._build_view_model(response, state)

    @staticmethod
    def handle_external_event(event_name: str, payload: dict, conversation_id: str) -> ChatViewModel:
        """
        Simulates an external webhook (e.g. from payment gateway) by injecting a system event 
        into the conversation and letting the agent react to it.
        """
        logger.info(f"ChatApplication handling external event: {event_name}")
        # Format the event as a hidden system message that the agent will see
        system_msg = f"[System Event: {event_name}] payload={payload}"
        
        # We process this simulated event through the graph
        response, state = run_agent(system_msg, conversation_id)
        return ChatApplication._build_view_model(response, state)

    @staticmethod
    def _build_view_model(response: str, state: dict) -> ChatViewModel:
        """
        Maps the raw LangGraph AgentState to the decoupled ChatViewModel.
        """
        # Ensure conversation_id is extracted properly
        conversation_id = state.get("conversation_id", "unknown")
        
        buttons = ButtonsViewModel(
            show_confirm_payment=state.get("ui_show_confirm_payment", False),
            show_expire_payment=state.get("ui_show_expire_payment", False)
        )
        
        debug = DebugViewModel(
            active_agent=state.get("intent", "unknown"), # using intent to indicate active sub-graph
            intent=state.get("intent"),
            contact_id=state.get("contact_id"),
            patient_id=state.get("patient_id"),
            active_reservation_id=state.get("active_reservation_id"),
            retrieved_docs=state.get("retrieved_docs")
        )
        
        return ChatViewModel(
            message=response,
            conversation_id=conversation_id,
            buttons=buttons,
            payment_url=state.get("ui_payment_url"),
            debug=debug
        )
