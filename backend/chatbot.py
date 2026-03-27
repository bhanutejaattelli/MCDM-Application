import os
import time
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

# Load environment variables from root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

chatbot_bp = Blueprint('chatbot', __name__)

# List of models to try in order of preference
MODELS_TO_TRY = [
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-1.5-flash',
    'gemini-1.5-flash-8b',
]

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
model = None
model_name = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Use the first model by default, will try fallbacks on quota errors
        model_name = MODELS_TO_TRY[0]
        model = genai.GenerativeModel(model_name)
        print(f"[Chatbot] Gemini API configured with {model_name}")
    except Exception as e:
        print(f"[Chatbot] Gemini Init Error: {str(e)}")
        model = None
else:
    print("[Chatbot] WARNING: GEMINI_API_KEY not set in .env")

# System prompt defining the chatbot's identity and boundaries
SYSTEM_PROMPT = """
You are a helpful assistant for the Dynamic Cloud Service Composition System. 
Your goal is to help users understand and use the application's features.

Key features of the application:
1. Cloud service ranking: Uses Entropy Weight Method and TOPSIS algorithm.
2. Entropy Weight Method: An objective weight determination method based on the degree of variation in QoS parameters.
3. TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution): A multi-criteria decision-making method that ranks services based on their distance from the Positive Ideal Solution and Negative Ideal Solution.
4. QoS parameters: The system evaluates services based on Response Time (cost), Throughput (benefit), Security (benefit), and Cost (cost).
5. Manual service entry: Users can manually add individual cloud services to the system.
6. Excel bulk upload: Users can upload an Excel file containing multiple service records for batch processing.

Guidelines:
- Only answer questions related to the application and the concepts mentioned above.
- If a user asks something unrelated, politely inform them that you can only assist with questions regarding the Dynamic Cloud Service Composition System.
- Provide clear, concise, and professional responses.
"""


def _try_generate(prompt: str) -> str:
    """Try generating content with fallback models on quota errors."""
    global model, model_name

    for candidate_model_name in MODELS_TO_TRY:
        try:
            candidate_model = genai.GenerativeModel(candidate_model_name)
            response = candidate_model.generate_content(prompt)

            # Update default model if we had to switch
            if candidate_model_name != model_name:
                model = candidate_model
                model_name = candidate_model_name
                print(f"[Chatbot] Switched to fallback model: {model_name}")

            # Handle blocked responses
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return "I apologize, but I cannot answer that question based on my safety guidelines. Please ask something related to the cloud service system."

            try:
                return response.text.strip()
            except (AttributeError, ValueError):
                return "I'm sorry, I couldn't generate a response. Please try rephrasing your question about the system."

        except Exception as e:
            error_str = str(e)
            # If it's a quota error (429), try the next model
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                print(f"[Chatbot] Quota exceeded for {candidate_model_name}, trying next model...")
                continue
            # For other errors, raise immediately
            raise

    # All models exhausted
    raise Exception(
        "All Gemini models have exceeded their quota. "
        "Please check your API key at https://aistudio.google.com/apikey — "
        "make sure the Generative Language API is enabled in your Google Cloud project "
        "and the key has available quota."
    )


@chatbot_bp.route('/chatbot', methods=['POST'])
def chat():
    if not api_key:
        return jsonify({"error": "Gemini API key not configured. Set GEMINI_API_KEY in .env"}), 500

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {user_message}\nAssistant:"
        bot_response = _try_generate(full_prompt)
        return jsonify({"response": bot_response})

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        with open("chatbot_errors.log", "a") as f:
            f.write(f"\n--- ERROR: {str(e)} ---\n{error_msg}\n")
        print(f"Chatbot Error: {str(e)}")
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500
