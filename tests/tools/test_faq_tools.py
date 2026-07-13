from app.tools.faq_tools import search_faq_tool
from langgraph.types import Command

def test_search_faq_tool_with_results(mocker):
    # Mock the global _faq_service instance
    mock_service = mocker.patch("app.tools.faq_tools._faq_service")
    mock_service.search_knowledge_base.return_value = [
        {"title": "Doc 1", "content": "Answer 1"},
        {"title": "Doc 2", "content": "Answer 2"}
    ]

    # Tool invocation with the injected parameter
    result = search_faq_tool.invoke({
        "name": "search_faq_tool",
        "args": {"query": "test query"},
        "id": "call-123",
        "type": "tool_call"
    })

    assert isinstance(result, Command)
    assert result.update["retrieved_docs"] == [
        {"title": "Doc 1", "content": "Answer 1"},
        {"title": "Doc 2", "content": "Answer 2"}
    ]
    
    messages = result.update["messages"]
    assert len(messages) == 1
    assert messages[0].tool_call_id == "call-123"
    assert "Doc 1" in messages[0].content
    assert "Doc 2" in messages[0].content
    
    mock_service.search_knowledge_base.assert_called_once_with("test query", top_k=3)

def test_search_faq_tool_no_results(mocker):
    mock_service = mocker.patch("app.tools.faq_tools._faq_service")
    mock_service.search_knowledge_base.return_value = []

    result = search_faq_tool.invoke({
        "name": "search_faq_tool",
        "args": {"query": "unknown query"},
        "id": "call-456",
        "type": "tool_call"
    })

    assert isinstance(result, Command)
    assert result.update["retrieved_docs"] == []
    
    messages = result.update["messages"]
    assert len(messages) == 1
    assert messages[0].tool_call_id == "call-456"
    assert "No relevant information found" in messages[0].content
