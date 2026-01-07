import os
from langchain_google_genai import ChatGoogleGenerativeAI

MODEL_NAME = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash")

def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=temperature)
