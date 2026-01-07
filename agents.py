import os
import re
import time
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI

MODEL_NAME = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")

def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=temperature)

def invoke_with_retry(runnable, prompt: str, retries: int = 4, default_delay: int = 10) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return runnable.invoke(prompt)
        except Exception as e:
            msg = str(e)
            if "RESOURCE_EXHAUSTED" not in msg and "429" not in msg:
                raise
            last_error = e
            if attempt < retries - 1:
                match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", msg)
                delay = int(match.group(1)) + 1 if match else default_delay
                time.sleep(delay)
    raise last_error
