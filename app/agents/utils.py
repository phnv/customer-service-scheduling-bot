def extract_text_content(msg_or_content) -> str:
    """
    Safely extracts text content from an LLM message or its content.
    Handles both plain strings and structured lists (e.g. from Gemini or Claude).
    """
    content = getattr(msg_or_content, "content", msg_or_content)
    
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "".join(text_parts)
    
    return str(content) if content is not None else ""
