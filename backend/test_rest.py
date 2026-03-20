import os
import requests
import json
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

def test_rest():
    print(f"Testing POST generateContent with key: {api_key[:5]}...")
    # Use v1beta and gemma-3-1b-it
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-3-1b-it:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": "Say hello"}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(f"Response: {response.json()['candidates'][0]['content']['parts'][0]['text']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"REST Error: {e}")

if __name__ == "__main__":
    test_rest()
