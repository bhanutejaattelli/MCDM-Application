import os
import google.generativeai as genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")
print(f"Key identified: {api_key[:5]}...")

try:
    genai.configure(api_key=api_key)
    print("Available Models:")
    for m in genai.list_models():
        print(f" - {m.name} ({m.display_name})")
except Exception as e:
    print(f"Error: {e}")
