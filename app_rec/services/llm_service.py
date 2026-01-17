import os
import logging
import json
import re
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

logger = logging.getLogger("uvicorn")

_groq_client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY")
)

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

async def call_llm(prompt: str, system_prompt: str | None = None, temperature: float = 0.3, max_tokens: int = 1000) -> str:
    messages = []

    if system_prompt:
        messages.append({
            'role': 'system',
            'content': system_prompt
        })

    messages.append({
        'role': 'user',
        'content': prompt
    })

    try:
        response = await _groq_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error calling Groq API: {e}")
        raise e

def clean_json_response(response_text: str) -> dict:
    """
    Helper to extract JSON from LLM response (removes Markdown ```json ... ```).
    """
    try:
        # 1. Try direct parsing
        return json.loads(response_text)
    except:
        # 2. Extract content between ```json and ```
        match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
        if match:
            clean_text = match.group(1).strip()
            return json.loads(clean_text)
        
        # 3. Fallback: try finding the first { and last }
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end != -1:
            try:
                return json.loads(response_text[start:end])
            except:
                pass
            
        return {"title": "Error Parsing", "summary": response_text}