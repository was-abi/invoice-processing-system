# Invoice Processing System with Local Llama 3.2

A production-grade invoice extraction system using local Llama 3.2 (via Ollama) to extract structured data from invoices.

## Features

- ✅ Extract invoice data locally (no API costs)
- ✅ Zero external dependencies (runs on your laptop)
- ✅ Returns structured JSON output
- ✅ Extracts: Invoice number, date, vendor, amount, line items
- ✅ Confidence scoring

## Prerequisites

1. **Ollama installed** - Download from [ollama.ai](https://ollama.ai)
2. **Llama 3.2 model** - Pull it with: `ollama pull llama3.2`
3. **Python 3.11+**

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/invoice-processing-system.git
cd invoice-processing-system

# Create virtual environment
python -m venv venv

# Activate it
# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install dependencies
pip install requests
```

## Usage

### 1. Start Ollama Server

Open a terminal and start Ollama:

```bash
ollama serve
```

You should see:
Listening on 127.0.0.1:11434

### 2. Run Invoice Extraction

In another terminal (in your project folder):

```bash
python extract_invoice.py
```

## Example Input

The `sample_invoice.txt` file contains:
INVOICE
Company XYZ Inc.
123 Business St
New York, NY 10001

Invoice Number: INV-2024-001234
Date: 2024-01-15
Due Date: 2024-02-15

Bill To:
Acme Corp
456 Main Street
Chicago, IL 60601

Description Quantity Unit Price Total

Consulting Services 40 $150.00 $6,000.00
Software License 1 $2,500.00 $2,500.00
Support & Maintenance 1 $1,000.00 $1,000.00

Subtotal: $9,500.00
Tax (8%): $760.00
TOTAL DUE: $10,260.00

Payment Terms: Net 30
## Example Output

Running `python extract_invoice.py` returns:

```json
{
  "invoice_number": "INV-2024-001234",
  "date": "2024-01-15",
  "vendor_name": "Company XYZ Inc.",
  "total_amount": 10260.0,
  "line_items": [
    {
      "description": "Consulting Services",
      "quantity": 40,
      "unit_price": 150.0,
      "total": 6000.0
    },
    {
      "description": "Software License",
      "quantity": 1,
      "unit_price": 2500.0,
      "total": 2500.0
    },
    {
      "description": "Support & Maintenance",
      "quantity": 1,
      "unit_price": 1000.0,
      "total": 1000.0
    }
  ],
  "confidence": 0.95
}
```

## Files

- `extract_invoice.py` - Main invoice extraction script
- `test_llama_local.py` - Test script to verify Llama 3.2 is working
- `sample_invoice.txt` - Sample invoice for testing
- `README.md` - This file

## How It Works

1. **Reads invoice** - Loads text from `sample_invoice.txt`
2. **Sends to Llama** - Sends to local Llama 3.2 running on `localhost:11434`
3. **Extracts data** - Llama returns structured JSON
4. **Parses JSON** - Extracts data from response
5. **Returns result** - Prints formatted output

## Troubleshooting

### "Connection refused" Error
- Make sure Ollama is running: `ollama serve`
- Check if it's listening on `http://localhost:11434`

### "llama3.2 not found" Error
- Pull the model: `ollama pull llama3.2`
- Verify with: `ollama list`

### Response takes too long
- Llama 3.2 runs on CPU (slower) or GPU (if available)
- First run loads model into memory (will be slower)

## Next Steps

- [ ] Week 2: Add database storage (PostgreSQL)
- [ ] Week 3: Build FastAPI web interface
- [ ] Week 4: Add validation and human review workflow
- [ ] Week 5: Deploy to production

## License

MIT

## Author

Your Name

## Contact

[Your GitHub Profile](https://github.com/was-abi)