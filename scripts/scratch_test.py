import json
import re

def robust_json_loads(s, **kwargs):
    try:
        return json.loads(s, **kwargs)
    except json.JSONDecodeError:
        pass
    
    cleaned = s.strip()
    
    # 1. Strip markdown code blocks
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
            
    # 2. Fix invalid escaped quotes
    cleaned = cleaned.replace("\\'", "'")
    
    # 3. Handle unescaped newlines (strict=False)
    kwargs['strict'] = False
    
    try:
        return json.loads(cleaned, **kwargs)
    except json.JSONDecodeError as e:
        raise e

# Tests
cases = [
    r'{"msg": "doctor\'s appointment"}',
    "```json\n{\"msg\": \"hello\"}\n```",
    "{\"msg\": \"hello\nworld\"}"
]

for c in cases:
    try:
        print("Parsing:", repr(c))
        print("Result:", robust_json_loads(c))
    except Exception as e:
        print("Failed:", e)
