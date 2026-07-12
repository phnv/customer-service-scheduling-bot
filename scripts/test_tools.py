import logging
from app.tools.customer_tools import find_customer_tool, register_customer_tool
from app.tools.appointment_tools import check_availability_tool, reserve_appointment_tool
from app.tools.qualification_tools import register_lead_tool

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_tools():
    print("=== Testing Customer Tools ===")
    find_customer_tool.invoke({"phone": "+155500001"})
    register_customer_tool.invoke({"full_name": "John Doe", "phone": "+155500099"})
    
    print("\n=== Testing Appointment Tools ===")
    check_availability_tool.invoke({"specialty": "Cardiology"})
    reserve_appointment_tool.invoke({"slot_id": "1", "conversation_id": "101"})
    
    print("\n=== Testing Qualification Tools ===")
    register_lead_tool.invoke({"conversation_id": "101", "summary": "Patient has chest pain.", "priority": "high"})
    
if __name__ == "__main__":
    test_tools()
