from datetime import date
from app.tools.appointment_tools import (
    check_availability_tool,
    reserve_slot_tool,
    cancel_reservation_tool,
    create_appointment_tool,
    cancel_appointment_tool,
    reschedule_appointment_tool,
)

def test_check_availability_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.check_availability.return_value = [{"slot_id": "slot-123"}]

    # invoke tool
    result = check_availability_tool.invoke({"specialty": "Cardiology", "start_date": "2026-10-10"})

    assert result == [{"slot_id": "slot-123"}]
    mock_service.check_availability.assert_called_once_with(specialty="Cardiology", start_date=date(2026, 10, 10))

def test_reserve_slot_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.reserve_slot.return_value = {"reservation_id": "res-1"}

    result = reserve_slot_tool.invoke({"slot_id": "slot-123", "conversation_id": "conv-1"})

    assert result == {"reservation_id": "res-1"}
    mock_service.reserve_slot.assert_called_once_with(slot_id="slot-123", conversation_id="conv-1")

def test_cancel_reservation_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.cancel_reservation.return_value = {"status": "cancelled"}

    result = cancel_reservation_tool.invoke({"reservation_id": "res-1"})

    assert result == {"status": "cancelled"}
    mock_service.cancel_reservation.assert_called_once_with(reservation_id="res-1")

def test_create_appointment_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.create_appointment.return_value = {"appointment_id": "app-1"}

    result = create_appointment_tool.invoke({
        "reservation_id": "res-1",
        "patient_id": "pat-1",
        "contact_id": "con-1"
    })

    assert result == {"appointment_id": "app-1"}
    mock_service.create_appointment.assert_called_once_with(reservation_id="res-1", patient_id="pat-1", contact_id="con-1")

def test_cancel_appointment_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.cancel_appointment.return_value = {"status": "cancelled"}

    result = cancel_appointment_tool.invoke({"appointment_id": "app-1"})

    assert result == {"status": "cancelled"}
    mock_service.cancel_appointment.assert_called_once_with(appointment_id="app-1")

def test_reschedule_appointment_tool(mocker):
    mock_service_class = mocker.patch("app.tools.appointment_tools.AppointmentService")
    mock_service = mock_service_class.return_value
    mock_service.reschedule_appointment.return_value = {"appointment_id": "app-1-new"}

    result = reschedule_appointment_tool.invoke({"appointment_id": "app-1", "new_slot_id": "slot-456"})

    assert result == {"appointment_id": "app-1-new"}
    mock_service.reschedule_appointment.assert_called_once_with(appointment_id="app-1", new_slot_id="slot-456")
