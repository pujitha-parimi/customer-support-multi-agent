import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(override=True)


def get_llm(temperature: float = 0.0):
    """Return a resilient Gemini chat model with automatic fallback for traffic spikes."""
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    fallback_models = ["gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]

    primary = ChatGoogleGenerativeAI(
        model=primary_model,
        temperature=temperature,
        max_retries=2,
    )

    fallbacks = [
        ChatGoogleGenerativeAI(
            model=m,
            temperature=temperature,
            max_retries=2,
        )
        for m in fallback_models
        if m != primary_model
    ]

    return primary.with_fallbacks(fallbacks)