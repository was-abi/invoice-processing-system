# test_llama_local.py
import requests
import json

# Ollama API runs on localhost:11434
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

def test_llama():
    """Test if local Llama 3.2 is working"""
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "What is 2+2? Answer in one word."
            }
        ],
        "stream": False,  # Don't stream, just get full response
    }
    
    print("📤 Sending request to local Llama 3.2...")
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        answer = result['message']['content']
        
        print("✅ Success!")
        print(f"Llama's answer: {answer}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        print("Make sure Ollama is running: ollama serve")

if __name__ == "__main__":
    test_llama()