import logging
from app.tools.customer_tools import find_contact_tool, create_contact_tool
from app.tools.appointment_tools import check_availability_tool, reserve_slot_tool
from app.tools.qualification_tools import update_lead_tool

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_tools():
    print("=== Testing Customer Tools ===")
    find_contact_tool.invoke({"phone": "+155500001"})
    create_contact_tool.invoke({"full_name": "John Doe", "phone": "+155500099", "document": "123456789"})
    
    print("\n=== Testing Appointment Tools ===")
    check_availability_tool.invoke({"specialty": "Cardiology"})
    try:
        reserve_slot_tool.invoke({"slot_id": "1", "conversation_id": "101"})
    except ValueError as e:
        print(f"Expected failure if DB is empty/slot unavailable: {e}")
    
    print("\n=== Testing Qualification Tools ===")
    update_lead_tool.invoke({"conversation_id": "101", "fields": {"summary": "Patient has chest pain.", "priority": "high"}})
    
if __name__ == "__main__":
    test_tools()
