# System Guidelines for AI Coding Agents

Welcome! If you are an AI coding agent or LLM assisting with this project,
adhere strictly to these architectural constraints and guidelines.

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
  ├─ "booking" ──→ [reception_node] ──→ [booking_node] ──→ END
  ├─ "faq" ──────────────────────────→ [faq_node] ────────→ END
  └─ "escalation" ───────────────────→ [escalation_node] ─→ END
```

### Node Descriptions

| Node | Module | Pattern | Tools |
|---|---|---|---|
| `coordinator` | `app/agents/coordinator.py` | LLM structured-output | none |
| `reception` | `app/agents/reception_agent.py` | ReAct (`create_react_agent`) | find_customer, register_customer |
| `booking` | `app/agents/booking_agent.py` | ReAct (`create_react_agent`) | check_availability, reserve, cancel, reschedule, register_lead |
| `faq` | `app/agents/faq_agent.py` | ReAct (`create_react_agent`) | search_faq (stub → RAG in M6) |
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
    intent: Optional[str]          # set by Coordinator: "booking"|"faq"|"escalation"
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

All system prompts live in `app/prompts/prompts.py` as named string constants:

- `COORDINATOR_PROMPT`
- `RECEPTION_PROMPT`
- `BOOKING_PROMPT`
- `FAQ_PROMPT`
- `ESCALATION_MESSAGE`

Never hardcode prompts inside agent files.

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
