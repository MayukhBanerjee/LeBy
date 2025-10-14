# chat_tester.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

def start_flash_chat():
    """
    Initializes a real conversational chat session with the Gemini 1.5 Flash model.
    """
    print("--- Gemini 1.5 Flash Chat Tester ---")
    
    try:
        # Load API Key from .env file
        print("Loading API key...")
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            print("\n❌ ERROR: 'GOOGLE_API_KEY' not found in your .env file.")
            return

        genai.configure(api_key=api_key)
        print("API key configured.")

        # Initialize the correct 1.5 Flash model and start a chat session
        print("Initializing model: gemini-1.5-flash-latest...")
        model = genai.GenerativeModel('gemini-2.0-flash')
        chat = model.start_chat(history=[]) # Start with an empty history

        print("\n✅ Model initialized. You can now start chatting.")
        print("Type 'exit' or 'quit' to end the session.\n")

        # Start the conversation loop
        while True:
            user_input = input("You: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye! 👋")
                break
                
            if not user_input.strip():
                continue

            response = chat.send_message(user_input)
            print(f"\nGemini: {response.text}\n")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("\nPlease check your API key and internet connection.")

if __name__ == "__main__":
    start_flash_chat()