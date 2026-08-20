import os

from dotenv import load_dotenv

load_dotenv()

# Groq LLM when GROQ_API_KEY is set; otherwise pipeline uses extractive fallback.
client = None
if os.getenv("GROQ_API_KEY"):
    from groq import Groq

    client = Groq()