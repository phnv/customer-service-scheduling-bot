def render_prompt(prompt: str, **kwargs) -> str:
    """
    Replaces {{VARIABLE}} placeholders in the prompt with corresponding values from kwargs.
    """
    for key, value in kwargs.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
    return prompt
