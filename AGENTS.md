# System Guidelines for AI Coding Agents

Welcome! If you are an AI coding agent or LLM assisting with this project,
adhere strictly to these architectural constraints and guidelines.

Before modifying prompts, business rules or datasets, follow the Alignment Workflow described in `docs/change_workflow.md`.

---

## 1. Layered Architecture

```
Streamlit UI
    ↓
ChatApplication (app/ui/application.py)
    ↓
app/agents/graph.py  (run_agent entry point)
    ↓
Coordinator Node  →  Intent Classification & Routing
    ↓
Reception Sub-Agent  →  Contact Identification / Registration
    ↓
Specialized Agent  →  Booking | FAQ | Escalation
    ↓
Tools  (app/tools/)
    ↓
Services  (app/services/)
    ↓
Storage  (SQLite via SQLModel | ChromaDB)
```

### Critical Rules

1. **No Direct DB Access by Agents:** LangGraph nodes must NEVER import from `app/database` or call SQLModel directly.
2. **Access via Tools:** All world-state interactions happen through `@tool`-decorated functions in `app/tools/`.
3. **Tools wrap Services:** Tools instantiate and call service classes. No business logic in tools.
4. **Services own Logic:** `app/services/` classes contain all query, mutation, and domain logic.

---

## 2. Graph Topology (Milestone 5)

```
START
  │
  ▼
[coordinator_node]
  │ sets state["intent"]
  ├─ "booking" (missing IDs) ──→ [reception_node] ──→ [booking_node] ──→ END
  ├─ "booking" (has IDs) ──────→ [booking_node] ──→ END
  ├─ "faq" ──────────────────────────→ [faq_node] ────────→ END
  └─ "escalation" ───────────────────→ [escalation_node] ─→ END
```

### Node Descriptions

| Node | Module | Pattern | Tools |
|---|---|---|---|
| `coordinator` | `app/agents/coordinator.py` | LLM structured-output | none |
| `reception` | `app/agents/reception_agent.py` | ReAct (`create_react_agent`) | find_contact, create_contact, find_patient, create_patient, select_patient |
| `booking` | `app/agents/booking_agent.py` | ReAct (`create_react_agent`) | check_availability, reserve_slot, cancel_reservation, cancel_appointment, reschedule_appointment |
| `faq` | `app/agents/faq_agent.py` | ReAct (`create_react_agent`) | search_faq (RAG via ChromaDB), search_services (live services catalogue) |
| `escalation` | `app/agents/graph.py` | Static gateway | none |

---

## 3. Shared State (`AgentState`)

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # accumulates via reducer
    conversation_id: str           # maps to DB conversations.conversation_id
    contact_id: Optional[str]      # set by Reception after identifying contact
    patient_id: Optional[str]      # set after patient selection
    active_reservation_id: Optional[str]  # set after successful reservation
    intent: Optional[str]          # set by Coordinator every turn: "booking"|"faq"|"escalation"
    flow: Optional[str]            # set by Coordinator: durable task "booking"|"faq"|None,
                                    # persists across single-turn detours (unlike intent)
    conversation_summary: Optional[str]  # set by Coordinator: rolling one-paragraph summary,
                                          # rewritten only on meaningful change
    retrieved_docs: Optional[list[dict]]  # set by FAQ agent's RAG tool
    ui_payment_url: Optional[str]
    ui_show_confirm_payment: bool
    ui_show_expire_payment: bool
```

---

## 4. Memory & Persistence

- **Checkpointer:** `MemorySaver` (in-process, non-persistent across restarts)
- **Thread ID:** `conversation_id` — ensures state continuity across multi-turn messages
- **State accumulation:** `messages` uses `add_messages` reducer — always appends, never replaces

---

## 5. LLM Configuration

Provider selected via `.env`:

```bash
LLM_PROVIDER=gemini       # Default
GEMINI_API_KEY=...
```

Supported providers: `gemini`, `openai`, `anthropic`

See `.env.example` for full configuration reference.

Factory: `app/agents/llm_factory.get_llm(temperature=0.0)`

---

## 6. Prompts

All system prompts live in `app/prompts/` as individual files per agent:

- `global_prompt.py` — `GLOBAL_PROMPT` (identity, persona, general rules, tool policy, domain boundaries)
- `coordinator.py` — `COORDINATOR_PROMPT`
- `reception.py` — `RECEPTION_PROMPT`
- `booking.py` — `BOOKING_PROMPT`
- `faq.py` — `FAQ_PROMPT`
- `escalation.py` — `ESCALATION_MESSAGE`
- `config.py` — `get_prompt_variables()` returning `ORGANIZATION_NAME` and `TODAY`
- `utils.py` — `render_prompt()` for `{{VARIABLE}}` interpolation

Never hardcode prompts inside agent files. Never reference team names or agent names in user-facing prompt text — all agents present as a single unified assistant (see Unified Persona in `agent-architecture.md`).

> **M12:** `BOOKING_TEAM_NAME` has been removed from `config.py`. Prompts must not direct users to a named team. `update_contact_tool` has been removed from the Reception agent's tool bindings.

---

## 7. Public API & UI Decoupling

The Streamlit UI **must never** interact directly with LangGraph or its internal state. 

All interactions go through the Application layer (`app/ui/application.py`):

```python
from app.ui.application import ChatApplication
from app.ui.view_models import ChatViewModel

# 1. Process a user message
view_model: ChatViewModel = ChatApplication.run(
    user_message="I'd like to book an appointment",
    conversation_id="conv-abc123"
)

# 2. Process a simulated external event (e.g. Webhook)
view_model: ChatViewModel = ChatApplication.handle_external_event(
    event_name="Payment Confirmed",
    payload={"status": "paid"},
    conversation_id="conv-abc123"
)
```

The `ChatViewModel` translates the internal `AgentState` (including UI flags) into safe, decoupled properties that Streamlit can safely render.

---

## 8. Storage & RAG

- **Database:** Use `SQLModel` for all schemas. No raw `sqlite3`.
- **RAG (Milestone 6):** Use LangChain's `MarkdownHeaderTextSplitter` for chunking.
  In Milestone 5, `search_faq_tool` is a keyword-matched stub.

---

## 9. General Best Practices

- **Type hints everywhere** — `typing` / `from __future__ import annotations`
- **Modularity** — low coupling, high cohesion
- **No external APIs** — all integrations are mocked in the Service layer
- **Logging** — use `logging.getLogger(__name__)` in every module
- **complete separation of concerns between Mlflow and LangGraph** -  Mlflow is for evaluation and LangGraph is the application

### Code Quality Rules
- Never write compatibility code.
- Never write temporary wrappers.
- Never write workaround parsers.
- Ask before adding adapters.

---

## 10. MLflow and LLMOps Guidelines
For all MLflow GenAI LLMOps implementation patterns and best practices, rely on the `mlflow-agent` instructions. 
- Always inform the user before implementing something that is not backed by official mlflow skills or documentation.
- You may access https://mlflow.org/docs/ for technical references.
- Never build workarounds around MLflow; use its intended design.

### MLflow Registry Artifacts
When interacting with registered models or prompts:
- All models and prompts must be explicitly tracked using the MLflow Model Registry and MLflow Prompt Registry.
- Avoid using hardcoded integer versions in execution code. Use and update aliases (e.g., `@champion` or `@production`) to fetch the correct artifacts at runtime. Use `scripts/manage_aliases.py` to maintain these aliases with zero downtime.

---

## 11. Agent Execution & Workflow Rules

### Skill References for Implementation Plans
Whenever executing implementation plans:
- **MLflow Skills & Documentation:** Always refer to official MLflow skills starting with `.agents/skills/searching-mlflow-docs` (reading external URL documentation, e.g. https://mlflow.org/docs/, is explicitly permitted).
- **WSL Environment:** Always adhere to environment rules in `.agents/skills/wsl-development-environment`.

### Restricted Script Execution
- **User-Exclusive Prerogative:** AI agents must **NEVER** run any evaluation scripts, scorer scripts, or dataset registration scripts (e.g., `scripts/scorers.py`, `scripts/create_datasets.py`, or evaluation runners). Executing these scripts is strictly and exclusively the user's prerogative.

