# extract_invoice.py
import requests
import json

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

def extract_invoice(invoice_text):
    """Extract structured data from invoice using local Llama 3.2"""
    
    prompt = f"""You are an invoice extraction expert. Extract the following information from the invoice:
- Invoice number
- Date (YYYY-MM-DD format)
- Vendor/Company name
- Total amount (just the number)
- Line items (description, quantity, unit price, total)

INVOICE:
{invoice_text}

Return ONLY valid JSON (no extra text) with this structure:
{{
    "invoice_number": "INV-2024-001234",
    "date": "2024-01-15",
    "vendor_name": "Company XYZ Inc.",
    "total_amount": 10260.00,
    "line_items": [
        {{"description": "Consulting Services", "quantity": 40, "unit_price": 150.00, "total": 6000.00}},
        {{"description": "Software License", "quantity": 1, "unit_price": 2500.00, "total": 2500.00}},
        {{"description": "Support & Maintenance", "quantity": 1, "unit_price": 1000.00, "total": 1000.00}}
    ],
    "confidence": 0.95
}}"""
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
    }
    
    print("🔄 Sending invoice to local Llama 3.2 for extraction...")
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['message']['content']
        
        print(f"\n📝 Raw response from Llama:\n{response_text}\n")
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            print("❌ Could not find JSON in response")
            return None
        
        extracted_json = response_text[json_start:json_end]
        
        try:
            extracted_data = json.loads(extracted_json)
            return extracted_data
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parsing Error: {e}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        print("Make sure Ollama is running: ollama serve")
        return None


# Read sample invoice
print("📖 Reading sample invoice...")
with open('sample_invoice.txt', 'r') as f:
    invoice_text = f.read()

# Extract data
result = extract_invoice(invoice_text)

if result:
    print("\n✅ Extraction successful!")
    print("\n📊 Extracted data:")
    print(json.dumps(result, indent=2))
else:
    print("\n❌ Extraction failed")