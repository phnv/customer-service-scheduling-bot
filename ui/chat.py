import streamlit as st
import uuid
import pandas as pd
from sqlmodel import Session, select
from dotenv import load_dotenv

# Load env variables for LLM providers before app starts
load_dotenv()

from app.database.engine import engine
from app.database import models
from app.ui.application import ChatApplication
from app.ui.view_models import ChatViewModel

st.set_page_config(page_title="Customer Service Demo", layout="wide")

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "view_model" not in st.session_state:
    st.session_state.view_model = None

# -----------------------------------------------------------------------------
# Database Inspector Cache & Helper
# -----------------------------------------------------------------------------
@st.cache_data(ttl=2)
def get_table_data(table_name: str) -> pd.DataFrame:
    """Fetches all rows for a given SQLModel table."""
    model_class = getattr(models, table_name, None)
    if not model_class:
        return pd.DataFrame()
        
    with Session(engine) as session:
        results = session.exec(select(model_class)).all()
        # Convert models to dicts and create a dataframe
        data = [r.model_dump() for r in results]
        return pd.DataFrame(data)

# -----------------------------------------------------------------------------
# Main UI Layout
# -----------------------------------------------------------------------------
st.title("Customer Service Demo 🏥")
st.markdown("MVP Interface demonstrating Multi-Agent Orchestration")

col_chat, col_debug = st.columns([2, 1])

with col_chat:
    st.subheader("Chat")
    
    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Chat Input
    user_input = st.chat_input("Type your message here...")
    if user_input:
        # Append and render user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.spinner("Agent is thinking..."):
            # Call Application Layer
            view_model = ChatApplication.run(user_input, st.session_state.conversation_id)
            st.session_state.view_model = view_model
            
            # Append and render AI message
            st.session_state.chat_history.append({"role": "assistant", "content": view_model.message})
            with st.chat_message("assistant"):
                st.markdown(view_model.message)
                if view_model.payment_url:
                    st.info(f"Payment Link: {view_model.payment_url}")
                    
        st.rerun()

    # Demo Controls
    vm = st.session_state.view_model
    if vm and vm.buttons:
        if vm.buttons.show_confirm_payment or vm.buttons.show_expire_payment:
            st.markdown("---")
            st.subheader("Demo Controls")
            st.caption("Simulate external events (e.g., Webhooks)")
            
            col_b1, col_b2 = st.columns(2)
            if vm.buttons.show_confirm_payment:
                if col_b1.button("✅ Confirm Payment", use_container_width=True):
                    with st.spinner("Processing event..."):
                        new_vm = ChatApplication.handle_external_event(
                            "Payment Confirmed", 
                            {"status": "paid"}, 
                            st.session_state.conversation_id
                        )
                        st.session_state.view_model = new_vm
                        st.session_state.chat_history.append({"role": "assistant", "content": new_vm.message})
                        st.rerun()
                        
            if vm.buttons.show_expire_payment:
                if col_b2.button("⏳ Expire Payment", use_container_width=True):
                    with st.spinner("Processing event..."):
                        new_vm = ChatApplication.handle_external_event(
                            "Payment Expired", 
                            {"status": "expired"}, 
                            st.session_state.conversation_id
                        )
                        st.session_state.view_model = new_vm
                        st.session_state.chat_history.append({"role": "assistant", "content": new_vm.message})
                        st.rerun()

with col_debug:
    # Optional Debug Section
    if vm and vm.debug:
        st.subheader("Agent Debug")
        st.info(f"**Intent:** {vm.debug.intent or 'None'}\n"
                f"**Active Agent:** {vm.debug.active_agent or 'None'}\n"
                f"**Contact ID:** {vm.debug.contact_id or 'None'}\n"
                f"**Patient ID:** {vm.debug.patient_id or 'None'}\n"
                f"**Reservation ID:** {vm.debug.active_reservation_id or 'None'}")
    
    # Database Inspector
    with st.expander("▼ Database Inspector", expanded=False):
        # Extract table names from models by checking subclasses of SQLModel
        table_names = [cls.__name__ for name, cls in vars(models).items() 
                       if isinstance(cls, type) and issubclass(cls, models.SQLModel) and name != "SQLModel"]
        
        selected_table = st.selectbox("Select Table", sorted(table_names))
        
        if selected_table:
            df = get_table_data(selected_table)
            if df.empty:
                st.write("No data found.")
            else:
                st.dataframe(df, use_container_width=True)
                
            # Add a manual refresh button to clear cache
            if st.button("Refresh Data", key="refresh_db"):
                get_table_data.clear()
                st.rerun()
