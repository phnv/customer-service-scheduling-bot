from datetime import date
from app.tools.customer_tools import (
    find_contact_tool,
    create_contact_tool,
    update_contact_tool,
    find_patient_tool,
    create_patient_tool,
)

def test_find_contact_tool(mocker):
    mock_service_class = mocker.patch("app.tools.customer_tools.CustomerService")
    mock_service = mock_service_class.return_value
    mock_service.find_contact.return_value = {"contact_id": "contact-123"}

    result = find_contact_tool.invoke({"phone": "555-1234"})

    assert result == {"contact_id": "contact-123"}
    mock_service.find_contact.assert_called_once_with(phone="555-1234", document=None, email=None)

def test_create_contact_tool(mocker):
    mock_service_class = mocker.patch("app.tools.customer_tools.CustomerService")
    mock_service = mock_service_class.return_value
    mock_service.create_contact.return_value = "contact-123"

    result = create_contact_tool.invoke({
        "full_name": "John Doe",
        "phone": "555-1234",
        "birthdate": "1990-01-01"
    })

    assert result == "contact-123"
    mock_service.create_contact.assert_called_once_with(
        full_name="John Doe", 
        phone="555-1234", 
        document=None, 
        email=None, 
        birthdate=date(1990, 1, 1)
    )

def test_update_contact_tool(mocker):
    mock_service_class = mocker.patch("app.tools.customer_tools.CustomerService")
    mock_service = mock_service_class.return_value
    mock_service.update_contact.return_value = {"contact_id": "contact-123", "email": "new@email.com"}

    result = update_contact_tool.invoke({
        "contact_id": "contact-123",
        "fields": {"email": "new@email.com"}
    })

    assert result == {"contact_id": "contact-123", "email": "new@email.com"}
    mock_service.update_contact.assert_called_once_with(contact_id="contact-123", fields={"email": "new@email.com"})

def test_find_patient_tool(mocker):
    mock_service_class = mocker.patch("app.tools.customer_tools.CustomerService")
    mock_service = mock_service_class.return_value
    mock_service.find_patient.return_value = [{"patient_id": "patient-1"}]

    result = find_patient_tool.invoke({"contact_id": "contact-123"})

    assert result == [{"patient_id": "patient-1"}]
    mock_service.find_patient.assert_called_once_with(contact_id="contact-123", patient_name=None)

def test_create_patient_tool(mocker):
    mock_service_class = mocker.patch("app.tools.customer_tools.CustomerService")
    mock_service = mock_service_class.return_value
    mock_service.create_patient.return_value = "patient-1"

    result = create_patient_tool.invoke({
        "contact_id": "contact-123",
        "full_name": "Jane Doe",
        "relationship": "spouse",
        "birthdate": "1992-05-05"
    })

    assert result == "patient-1"
    mock_service.create_patient.assert_called_once_with(
        contact_id="contact-123",
        full_name="Jane Doe",
        relationship="spouse",
        birthdate=date(1992, 5, 5)
    )
