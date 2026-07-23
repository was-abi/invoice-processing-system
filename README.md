# Invoice Processing System with Local Llama 3.2

A production-grade invoice extraction system using local Llama 3.2 (via Ollama) to extract structured data from invoices through a modern web interface.

---

## Features

- ✅ **Web-Based Invoice Upload** - Beautiful HTML interface to upload invoices
- ✅ **AI-Powered Extraction** - Uses local Llama 3.2 via Ollama (no API costs)
- ✅ **Automatic Database Storage** - Saves extracted data to PostgreSQL
- ✅ **REST API** - JSON endpoints for programmatic access
- ✅ **Invoice Viewing** - View all invoices in a searchable table
- ✅ **Audit Trail** - Complete history of all operations
- ✅ **Confidence Scoring** - Know how confident Llama was in extraction
- ✅ **Line Item Support** - Extract individual line items from invoices
- ✅ **Zero External API Costs** - Everything runs locally

---

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation using Python type hints
- **Psycopg2** - PostgreSQL database adapter
- **Requests** - HTTP client for Ollama communication

### AI/ML
- **Llama 3.2** - Large language model (via Ollama)
- **Ollama** - Local LLM runner

### Database
- **PostgreSQL 18** - Relational database
- **JSONB** - For storing extracted data as JSON

### Frontend
- **HTML5** - Semantic markup
- **CSS3** - Responsive styling
- **JavaScript** - Dynamic interactions
- **Fetch API** - Asynchronous requests

---

## Prerequisites

Before starting, ensure you have:

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **Ollama Installed** - Download from [ollama.ai](https://ollama.ai)
   ```bash
   ollama pull llama3.2
   ollama serve
   ```

3. **PostgreSQL 15+** - Download from [postgresql.org](https://www.postgresql.org/download/)
   - Installation guide for your OS

4. **Git** - For version control (optional)

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/invoice-processing-system.git
cd invoice-processing-system
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**If requirements.txt doesn't exist, install manually:**

```bash
pip install fastapi uvicorn python-multipart psycopg2-binary pydantic requests
```

### Step 4: Setup Database

```bash
# Create database
createdb invoice_db

# Create tables
python init_db.py
```

Expected output:
```
📊 Creating tables...
✅ Created 'invoices' table
✅ Created 'line_items' table
✅ Created 'audit_log' table

✅ All tables created successfully!
```

### Step 5: Configure Database Connection

Edit `app.py` and update the password:

```python
DB_CONFIG = {
    "host": "localhost",
    "database": "invoice_db",
    "user": "postgres",
    "password": "YOUR_PASSWORD_HERE",  # ← Change this
    "port": "5432"
}
```

---

## Running the Application

### Terminal 1: Start Ollama

```bash
ollama serve
```

You should see:
```
Listening on 127.0.0.1:11434
```

### Terminal 2: Start FastAPI Server

```bash
uvicorn app:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Open in Browser

Visit: **http://localhost:8000**

---

## Usage Guide

### Upload an Invoice via Web

1. **Open browser:** http://localhost:8000
2. **Click file input** and select a `.txt` invoice file
3. **Click "Upload & Extract"** button
4. **Wait 10-30 seconds** for Llama to process
5. **See results** with extracted data and confidence score
6. **Data automatically saved** to PostgreSQL

### View All Invoices

1. Click **"View All Invoices"** link on homepage
2. See table with all uploaded invoices
3. View invoice numbers, vendors, amounts, dates
4. Shows confidence scores and timestamps

### Access API Documentation

1. Visit: **http://localhost:8000/docs**
2. Interactive Swagger UI to test all endpoints
3. See request/response examples

---

## API Endpoints

### Web Pages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with upload form |
| `/invoices` | GET | View all invoices (HTML table) |
| `/docs` | GET | Interactive API documentation |

### API Endpoints (JSON)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload and extract invoice |
| `/api/invoices` | GET | List all invoices (JSON) |
| `/api/invoices/{id}` | GET | Get specific invoice (JSON) |

---

## Example Usage

### Upload via cURL

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@sample_invoice.txt"
```

**Response:**
```json
{
  "status": "success",
  "message": "Invoice extracted and saved successfully",
  "invoice_id": 1,
  "extracted_data": {
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
      }
    ],
    "confidence": 0.95
  }
}
```

### Get All Invoices via cURL

```bash
curl "http://localhost:8000/api/invoices"
```

**Response:**
```json
[
  {
    "id": 1,
    "invoice_number": "INV-2024-001234",
    "vendor_name": "Company XYZ Inc.",
    "invoice_date": "2024-01-15",
    "total_amount": 10260.0,
    "confidence_score": 0.95,
    "status": "extracted",
    "created_at": "2024-01-15T10:30:00",
    "line_items": [...]
  }
]
```

### Get Specific Invoice via cURL

```bash
curl "http://localhost:8000/api/invoices/1"
```

---

## Sample Invoices for Testing

### Sample Invoice 1: Simple B2B Invoice

```
INVOICE

ABC Marketing Solutions
789 Madison Avenue
New York, NY 10016

Invoice Number: INV-2024-008901
Date: 2024-03-10
Due Date: 2024-04-10

Bill To:
StartUp Tech Inc.
321 Innovation Blvd
San Jose, CA 95110

Description                      Quantity   Unit Price    Total
================================================================
Social Media Management               1      $2,000.00  $2,000.00
Content Creation (Blog Posts)        4        $500.00   $2,000.00
Email Marketing Campaign              1      $1,500.00  $1,500.00
Analytics & Reporting                1        $750.00     $750.00

Subtotal:                                                $6,250.00
Tax (10%):                                                $625.00
TOTAL DUE:                                              $6,875.00

Payment Terms: Net 30
```

### Sample Invoice 2: Enterprise Invoice

```
INVOICE

Enterprise Solutions Corp
500 Park Avenue
Chicago, IL 60601

Invoice Number: INV-2024-012345
Date: 2024-02-28
Due Date: 2024-03-31

Bill To:
Global Manufacturing Ltd
1000 Industrial Park
Detroit, MI 48201

Description                          Quantity   Unit Price    Total
===================================================================
ERP System Implementation                1     $50,000.00  $50,000.00
Database Migration Services             80       $250.00  $20,000.00
Staff Training (5 days)                  5     $2,000.00  $10,000.00
Technical Support (12 months)            1     $15,000.00 $15,000.00
Custom Integration Development          40       $300.00  $12,000.00

Subtotal:                                                $107,000.00
Volume Discount (15%):                                  ($16,050.00)
Subtotal after discount:                                $90,950.00
Tax (7%):                                               ($6,366.50)
TOTAL DUE:                                             $84,583.50

Payment Terms: Net 60
```

### Sample Invoice 3: Service Invoice

```
INVOICE

CloudNine Consulting Group
1234 Tech Park Drive
Seattle, WA 98101

Invoice Number: INV-2024-015678
Date: 2024-03-05
Due Date: 2024-04-05

Bill To:
Digital Ventures LLC
2000 Market Street
San Francisco, CA 94103

Description                            Quantity   Unit Price    Total
====================================================================
Cloud Architecture Consulting              40      $200.00   $8,000.00
DevOps Implementation                      60      $180.00  $10,800.00
Security Audit & Hardening                30      $250.00   $7,500.00
Performance Optimization                  20      $220.00   $4,400.00
24/7 Support Package (1 month)             1      $5,000.00  $5,000.00

Subtotal:                                                   $35,700.00
Service Tax (6%):                                          $2,142.00
TOTAL DUE:                                                $37,842.00

Payment Terms: Net 45
```

---

## Database Schema

### invoices Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique invoice ID |
| invoice_number | VARCHAR(50) UNIQUE | Invoice number (e.g., INV-2024-001234) |
| vendor_name | VARCHAR(255) | Company/vendor name |
| invoice_date | DATE | Invoice date |
| total_amount | DECIMAL(10,2) | Total amount in USD |
| confidence_score | FLOAT | Llama's confidence (0.0-1.0) |
| raw_text | TEXT | Original invoice text |
| extracted_json | JSONB | Full extracted data as JSON |
| status | VARCHAR(50) | Current status (extracted, approved, etc.) |
| created_at | TIMESTAMP | When record was created |
| updated_at | TIMESTAMP | Last update time |

### line_items Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique line item ID |
| invoice_id | INTEGER FOREIGN KEY | Reference to parent invoice |
| description | VARCHAR(255) | Item description |
| quantity | INTEGER | Quantity ordered |
| unit_price | DECIMAL(10,2) | Price per unit |
| total | DECIMAL(10,2) | Total for this line |
| created_at | TIMESTAMP | When record was created |

### audit_log Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique log entry ID |
| invoice_id | INTEGER FOREIGN KEY | Reference to invoice |
| action | VARCHAR(100) | Action performed (UPLOADED, EXTRACTED, etc.) |
| details | TEXT | Details about the action |
| created_at | TIMESTAMP | When action occurred |

---

## Project Structure

```
invoice-processing-system/
├── app.py                      # FastAPI application
├── models.py                   # Pydantic data models
├── extract_invoice.py          # CLI extraction script
├── query_invoices.py           # CLI query script
├── init_db.py                  # Database initialization
├── sample_invoice.txt          # Sample invoice 1
├── sample_invoice_2.txt        # Sample invoice 2
├── sample_invoice_3.txt        # Sample invoice 3
├── sample_invoice_4.txt        # Sample invoice 4
├── sample_invoice_5.txt        # Sample invoice 5
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore file
├── README.md                   # This file
└── venv/                       # Virtual environment (not in git)
```

---

## Key Files Explained

### app.py
Main FastAPI application with:
- Web server routes (homepage, invoice viewing)
- API endpoints (file upload, data retrieval)
- Helper functions for extraction and database operations
- Startup checks for Ollama and PostgreSQL

### models.py
Pydantic data models using Context7 best practices:
- `LineItemResponse` - Single line item structure
- `InvoiceResponse` - Complete invoice with line items
- `ExtractedInvoiceData` - Data extracted by Llama
- `UploadResponse` - Response sent after upload

### init_db.py
Database initialization:
- Creates PostgreSQL tables
- Sets up relationships between tables
- Creates indexes for performance

### extract_invoice.py
Command-line extraction tool:
- Test extraction without web interface
- Batch process multiple files
- Debug extraction process

### query_invoices.py
Command-line query tool:
- View all invoices in database
- Query specific invoices
- Display with formatted output

---

## Troubleshooting

### Ollama Connection Error

**Error:** "Connection refused" or "Failed to connect to Ollama"

**Solution:**
```bash
# Check if Ollama is running
ollama serve

# In another terminal, verify:
curl http://localhost:11434/api/tags
```

### PostgreSQL Connection Error

**Error:** "psql is not recognized" or "Database connection failed"

**Solution:**
1. Verify PostgreSQL is installed
2. Check password in `app.py` matches your PostgreSQL password
3. Verify database exists:
   ```bash
   psql -U postgres -l | grep invoice_db
   ```

### Extraction Timeout

**Error:** "Request timeout" after 60 seconds

**Reason:** Llama 3.2 needs time to process (10-30 seconds is normal)

**Solution:** Be patient or use a faster machine

### File Upload Not Working

**Error:** "Only .txt files are supported"

**Solution:** Make sure your invoice file is `.txt` format, not `.pdf` or `.docx`

---

## Performance Tips

### Speed Up Extraction

1. **Use GPU acceleration** - Install Ollama with GPU support
2. **Increase timeout** - Edit timeout in `app.py` if needed
3. **Use smaller model** - Llama 2.7B is faster but less accurate

### Database Performance

1. **Use indexes** - Already included in `init_db.py`
2. **Regular backups** - Backup PostgreSQL regularly
3. **Archive old data** - Move old invoices to archive table

### Production Deployment

1. **Use environment variables** - Store passwords in `.env` file
2. **Use connection pooling** - For high-traffic scenarios
3. **Enable HTTPS** - Use SSL certificates
4. **Add authentication** - Protect API endpoints

---

## Development Roadmap

- [ ] Week 4: Add invoice validation rules
- [ ] Week 5: Email notification on extraction
- [ ] Week 6: Batch processing for multiple files
- [ ] Week 7: Advanced search and filtering
- [ ] Week 8: Export to CSV/Excel
- [ ] Week 9: Audit trail visualization
- [ ] Week 10: Machine learning model fine-tuning

---

## Best Practices Used

### Architecture
- ✅ Separation of concerns (models, routes, helpers)
- ✅ Async/await for concurrent requests
- ✅ Context managers for resource cleanup (Context7)
- ✅ Type hints for clarity and validation

### Database
- ✅ Proper normalization (invoices, line_items, audit_log)
- ✅ Foreign key relationships
- ✅ Cascade delete for data integrity
- ✅ Indexes for query performance
- ✅ Context manager pattern for connections

### API Design
- ✅ RESTful endpoints
- ✅ Proper HTTP status codes (201, 404, 500, etc.)
- ✅ Consistent error handling
- ✅ Pydantic validation (Context7 best practices)
- ✅ OpenAPI/Swagger documentation

### Code Quality
- ✅ Docstrings for all functions
- ✅ Descriptive variable names
- ✅ Error handling with try/except
- ✅ Logging for debugging
- ✅ Modular, reusable functions

---

## API Response Examples

### Success Response (Upload)

```json
{
  "status": "success",
  "message": "Invoice extracted and saved successfully",
  "invoice_id": 1,
  "extracted_data": {
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
      }
    ],
    "confidence": 0.95
  }
}
```

### Error Response

```json
{
  "detail": "Only .txt files are supported"
}
```

HTTP Status: `400 Bad Request`

---

## Contributing

To contribute:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit pull request

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues and questions:

1. Check the Troubleshooting section
2. Review API documentation at `/docs`
3. Check GitHub issues
4. Create new issue with:
   - Error message
   - Steps to reproduce
   - System information (OS, Python version, etc.)

---

## Changelog

### Version 1.0.0 (Current)
- ✅ Week 1: Local Llama 3.2 extraction
- ✅ Week 2: PostgreSQL database integration
- ✅ Week 3: FastAPI web interface
- ✅ Week 4: Production-ready code

---

## Next Steps

1. **Test with sample invoices** - Use provided test files
2. **Explore API endpoints** - Visit `/docs`
3. **View extracted data** - Check `/invoices`
4. **Integrate with your system** - Use API endpoints
5. **Deploy to production** - Follow deployment guide

---

**Happy invoice processing! 🚀**

For updates and more information, visit the [GitHub repository](https://github.com/was-abi/invoice-processing-system).