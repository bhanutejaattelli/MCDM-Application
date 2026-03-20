import os
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure we load .env from the root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_key = os.getenv("GEMINI_API_KEY")
print(f"Using API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'NONE'}")

if not api_key:
    print("Error: No GEMINI_API_KEY found in environment.")
    exit(1)

try:
    genai.configure(api_key=api_key)
    # List models to verify connectivity
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  Found model: {m.name}")
    
    print("\nTesting gemini-1.5-flash...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hello, this is a test.")
    print("Success!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"\nError: {type(e).__name__}")
    print(f"Message: {str(e)}")
    import traceback
    traceback.print_exc()
