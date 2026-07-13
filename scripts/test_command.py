import asyncio
from langchain_core.tools import tool
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated
import os

class State(TypedDict):
    messages: Annotated[list, "add_messages"]
    retrieved_docs: list

@tool
def test_tool(query: str):
    """Test tool"""
    return Command(
        update={
            "retrieved_docs": [{"title": "test", "score": 1.0}],
            # We want the LLM to see "Found docs"
        }
    )

async def main():
    # Use a mock LLM if possible, or just call the tool node
    from langgraph.prebuilt import ToolNode
    node = ToolNode([test_tool])
    # Mock tool call
    from langchain_core.messages import AIMessage
    msg = AIMessage(content="", tool_calls=[{"name": "test_tool", "args": {"query": "test"}, "id": "1"}])
    result = await node.ainvoke({"messages": [msg]})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
