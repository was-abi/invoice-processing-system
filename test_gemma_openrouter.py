# test_gemma.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("❌ ERROR: API key not found in .env file")
    exit()

print("✅ API key loaded successfully")

# Make a test call to Gemma
url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

data = {
    "model": "google/gemma-4-26b-a4b-it:free",  # Free Gemma model on OpenRouter
    "messages": [
        {
            "role": "user",
            "content": "What is 2+2? Answer in one word."
        }
    ],
    "max_tokens": 100,
    "temperature": 0.1,
}

print("\n📤 Sending request to Gemma on OpenRouter...")

try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    
    result = response.json()
    answer = result['choices'][0]['message']['content']
    
    print("✅ Success!")
    print(f"Gemma's answer: {answer}")
    
except requests.exceptions.RequestException as e:
    print(f"❌ Error: {e}")