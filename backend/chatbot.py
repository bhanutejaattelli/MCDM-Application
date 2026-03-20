import os
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

# Load environment variables from root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

chatbot_bp = Blueprint('chatbot', __name__)

# Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    try:
        # Using transport='rest' for maximum compatibility on Windows
        genai.configure(api_key=api_key, transport='rest')
        # Using gemma-3-1b-it as it was verified to have active quota for this key
        model = genai.GenerativeModel('models/gemma-3-1b-it')
    except Exception as e:
        print(f"Gemini Init Error: {str(e)}")
        model = None
else:
    model = None

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

@chatbot_bp.route('/chatbot', methods=['POST'])
def chat():
    if not model:
        return jsonify({"error": "Gemini API key not configured"}), 500

    data = request.json
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Construct the full prompt with system instructions
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {user_message}\nAssistant:"
        
        response = model.generate_content(full_prompt)
        
        # Robustly handle the response
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            return jsonify({
                "response": "I apologize, but I cannot answer that question based on my safety guidelines. Please ask something related to the cloud service system."
            })
            
        try:
            bot_response = response.text.strip()
        except (AttributeError, ValueError):
            # This happens if there are no candidates or if it was blocked
            bot_response = "I'm sorry, I couldn't generate a response. Please try rephrasing your question about the system."
            
        return jsonify({
            "response": bot_response
        })

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        # Log to file for deep debugging
        with open("chatbot_errors.log", "a") as f:
            f.write(f"\n--- ERROR: {str(e)} ---\n{error_msg}\n")
        print(f"Chatbot Error: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
