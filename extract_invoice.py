# extract_invoice.py
import requests
import json
import psycopg2
from psycopg2 import sql

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

# Database config
DB_CONFIG = {
    "host": "localhost",
    "database": "invoice_db",
    "user": "postgres",
    "password": "password123",
    "port": "5432"
}

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


def save_to_database(extracted_data):
    """Save extracted invoice data to PostgreSQL with proper transaction handling"""
    
    if not extracted_data:
        print("❌ No data to save")
        return None
    
    try:
        # Use context manager for automatic transaction handling
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                print("\n💾 Saving to database...")
                
                # Insert into invoices table
                invoice_number = extracted_data.get('invoice_number')
                vendor_name = extracted_data.get('vendor_name')
                invoice_date = extracted_data.get('date')
                total_amount = extracted_data.get('total_amount')
                confidence = extracted_data.get('confidence', 0.0)
                
                cursor.execute("""
                    INSERT INTO invoices 
                    (invoice_number, vendor_name, invoice_date, total_amount, confidence_score, extracted_json, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    invoice_number,
                    vendor_name,
                    invoice_date,
                    total_amount,
                    confidence,
                    json.dumps(extracted_data),
                    'extracted'
                ))
                
                invoice_id = cursor.fetchone()[0]
                print(f"✅ Saved invoice to database (ID: {invoice_id})")
                
                # Insert line items
                line_items = extracted_data.get('line_items', [])
                for item in line_items:
                    cursor.execute("""
                        INSERT INTO line_items 
                        (invoice_id, description, quantity, unit_price, total)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (
                        invoice_id,
                        item.get('description'),
                        item.get('quantity'),
                        item.get('unit_price'),
                        item.get('total')
                    ))
                
                print(f"✅ Saved {len(line_items)} line items")
                
                # Add audit log entry
                cursor.execute("""
                    INSERT INTO audit_log (invoice_id, action, details)
                    VALUES (%s, %s, %s);
                """, (
                    invoice_id,
                    'EXTRACTED',
                    f'Invoice extracted with {len(line_items)} line items. Confidence: {confidence}'
                ))
                
                print("✅ Audit log created")
            
            # Transaction is automatically committed here
        
        return invoice_id
    
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return None


def main():
    """Main function"""
    
    print("📖 Reading sample invoice...")
    with open('sample_invoice2.txt', 'r') as f:
        invoice_text = f.read()
    
    # Extract data
    extracted_data = extract_invoice(invoice_text)
    
    if extracted_data:
        print("\n✅ Extraction successful!")
        print("\n📊 Extracted data:")
        print(json.dumps(extracted_data, indent=2))
        
        # Save to database
        invoice_id = save_to_database(extracted_data)
        
        if invoice_id:
            print(f"\n🎉 Successfully saved! Invoice ID: {invoice_id}")
        else:
            print("\n⚠️ Extraction worked but database save failed")
    else:
        print("\n❌ Extraction failed")


if __name__ == "__main__":
    main()