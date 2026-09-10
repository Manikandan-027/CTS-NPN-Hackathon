import os

from dotenv import load_dotenv


load_dotenv()


def create_groq_client():
    """
    Create and return a Groq client using GROQ_API_KEY.

    The API key is never hardcoded or printed.
    """
    try:
        from groq import Groq
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Groq SDK is not installed. Add 'groq' to the project dependencies and install it in the environment."
        ) from exc

    api_key = (os.getenv("GROQ_API_KEY") or "").strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Set it in the .env file or environment."
        )

    try:
        return Groq(api_key=api_key)
    except Exception as exc:
        raise RuntimeError(
            "Unable to initialize Groq client. Check the API key and connectivity."
        ) from exc