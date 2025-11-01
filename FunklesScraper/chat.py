# chat.py
from .paths import ENV_PATH
import os
from dotenv import load_dotenv
from google import genai

# Load API key
load_dotenv(ENV_PATH)
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY is None:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)

def talk(message: str) -> str:
    """
    Sends a message to the Gemini model and returns its response.
    """
    prompt = f"""
    You are a helpful AI assistant.

    User: {message}

    Assistant:
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"
