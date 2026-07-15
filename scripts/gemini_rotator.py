import os
import random
import time
from langchain_openai import ChatOpenAI
from openai import RateLimitError


def get_available_keys():
    """Extracts keys from GEMINI_API_KEY, whether comma-separated or single."""
    raw_env = os.getenv("GEMINI_API_KEY", "")
    if not raw_env:
        return []
    # Split by comma and strip whitespace
    keys = [k.strip() for k in raw_env.split(",") if k.strip()]
    return keys


def get_gemini_llm(model="gemini-3.5-flash", temperature=0):
    """
    Returns a ChatOpenAI instance configured with an active Gemini API key.
    Shuffles keys to load-balance across available project pools.
    """
    keys = get_available_keys()
    if not keys:
        raise ValueError("GEMINI_API_KEY is not set or empty.")

    # Select a random key from the comma-separated list
    selected_key = random.choice(keys)

    return ChatOpenAI(
        model=model,
        api_key=selected_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        temperature=temperature,
    )
