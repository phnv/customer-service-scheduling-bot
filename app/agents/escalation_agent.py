import logging
from typing import Any, Optional

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

from app.agents.llm_factory import get_llm
from app.agents.state import AgentState
from app.prompts.config import get_prompt_variables
from app.prompts.escalation import ESCALATION_PROMPT
from app.prompts.global_prompt import GLOBAL_PROMPT
from app.prompts.utils import render_prompt

logger = logging.getLogger(__name__)

class EscalationOutput(BaseModel):
    response_message: str = Field(description="The message to send to the user")
    handoff_ready: bool = Field(description="Whether the contact info has been collected and we are ready to route to staff")
    handoff_reason: Optional[str] = Field(description="A single phrase summarizing the reason for handoff, if ready")

def escalation_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: handles human escalation interactively.
    """
    logger.info("[Escalation] Handling escalation protocol.")
    
    # 1. Prepare prompts
    raw_prompt = GLOBAL_PROMPT + "\n\n" + ESCALATION_PROMPT
    system_prompt = render_prompt(raw_prompt, **get_prompt_variables())
    
    # 2. Extract messages (system + history)
    messages = [{"role": "system", "content": system_prompt}] + state.get("messages", [])
    
    # 3. Call LLM with structured output
    llm = get_llm(temperature=0.0).with_structured_output(EscalationOutput)
    
    response: EscalationOutput = llm.invoke(messages)
    
    # 4. Prepare state updates
    state_updates: dict[str, Any] = {
        "messages": [AIMessage(content=response.response_message)]
    }
    
    if response.handoff_ready and response.handoff_reason:
        state_updates["escalation_reason"] = response.handoff_reason
        logger.info(f"[Escalation] Handoff ready. Reason: {response.handoff_reason}")
        
    return state_updates
