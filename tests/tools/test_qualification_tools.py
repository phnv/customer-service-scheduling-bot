from app.tools.qualification_tools import get_lead_tool, update_lead_tool

def test_get_lead_tool(mocker):
    mock_service_class = mocker.patch("app.tools.qualification_tools.QualificationService")
    mock_service = mock_service_class.return_value
    mock_service.get_lead.return_value = {"conversation_id": "conv-1", "symptoms": "headache"}

    result = get_lead_tool.invoke({"conversation_id": "conv-1"})

    assert result == {"conversation_id": "conv-1", "symptoms": "headache"}
    mock_service.get_lead.assert_called_once_with(conversation_id="conv-1")

def test_update_lead_tool(mocker):
    mock_service_class = mocker.patch("app.tools.qualification_tools.QualificationService")
    mock_service = mock_service_class.return_value
    mock_service.update_lead.return_value = {"conversation_id": "conv-1", "symptoms": "migraine"}

    result = update_lead_tool.invoke({
        "conversation_id": "conv-1",
        "fields": {"symptoms": "migraine"}
    })

    assert result == {"conversation_id": "conv-1", "symptoms": "migraine"}
    mock_service.update_lead.assert_called_once_with(conversation_id="conv-1", fields={"symptoms": "migraine"})
