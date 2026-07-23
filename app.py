# app.py
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import psycopg2
from typing import List, Annotated
import os

from models import InvoiceResponse, UploadResponse, LineItemResponse, ExtractedInvoiceData

# Initialize FastAPI app
app = FastAPI(
    title="Invoice Processing System",
    description="Extract invoice data using Llama 3.2",
    version="1.0.0"
)

# Add CORS (allows browser to make requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

DB_CONFIG = {
    "host": "localhost",
    "database": "invoice_db",
    "user": "postgres",
    "password": "password123",  # Replace with YOUR password
    "port": "5432"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_invoice_from_text(invoice_text: str) -> dict:
    """Extract invoice data using Llama 3.2 (from Context7 best practices)"""
    
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
    "invoice_number": "...",
    "date": "YYYY-MM-DD",
    "vendor_name": "...",
    "total_amount": 0.00,
    "line_items": [
        {{"description": "...", "quantity": 0, "unit_price": 0.00, "total": 0.00}}
    ],
    "confidence": 0.95
}}"""
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['message']['content']
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            return None
        
        extracted_json = response_text[json_start:json_end]
        return json.loads(extracted_json)
    
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return None


def save_invoice_to_db(extracted_data: dict) -> int:
    """Save extracted invoice to database (using context manager from Context7)"""
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Insert invoice
                cursor.execute("""
                    INSERT INTO invoices 
                    (invoice_number, vendor_name, invoice_date, total_amount, 
                     confidence_score, extracted_json, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    extracted_data.get('invoice_number'),
                    extracted_data.get('vendor_name'),
                    extracted_data.get('date'),
                    extracted_data.get('total_amount'),
                    extracted_data.get('confidence', 0.0),
                    json.dumps(extracted_data),
                    'extracted'
                ))
                
                invoice_id = cursor.fetchone()[0]
                
                # Insert line items
                for item in extracted_data.get('line_items', []):
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
                
                # Insert audit log
                cursor.execute("""
                    INSERT INTO audit_log (invoice_id, action, details)
                    VALUES (%s, %s, %s);
                """, (
                    invoice_id,
                    'UPLOADED',
                    f"Invoice uploaded via web. Confidence: {extracted_data.get('confidence', 0.0)}"
                ))
        
        return invoice_id
    
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page with upload form"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice Processing System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
            h1 {
                color: #667eea;
                text-align: center;
            }
            .upload-section {
                margin: 30px 0;
            }
            input[type="file"], button {
                padding: 10px;
                margin: 10px 0;
                width: 100%;
                font-size: 16px;
                border: 2px solid #667eea;
                border-radius: 5px;
                cursor: pointer;
            }
            button {
                background: #667eea;
                color: white;
                border: none;
                font-weight: bold;
                transition: background 0.3s;
            }
            button:hover {
                background: #764ba2;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                display: none;
            }
            .result.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .result.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .loading {
                display: none;
                text-align: center;
                color: #667eea;
                font-weight: bold;
            }
            .links {
                margin-top: 30px;
                text-align: center;
            }
            .links a {
                margin: 0 10px;
                color: #667eea;
                text-decoration: none;
                font-weight: bold;
            }
            .links a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 Invoice Processing System</h1>
            <p style="text-align: center; color: #666;">
                Upload your invoices and we'll extract the data automatically using AI
            </p>
            
            <div class="upload-section">
                <form id="uploadForm">
                    <input type="file" id="fileInput" accept=".txt" required>
                    <button type="submit">🚀 Upload & Extract</button>
                </form>
                
                <div class="loading">
                    ⏳ Processing invoice... (this may take 10-30 seconds)
                </div>
                
                <div class="result" id="result"></div>
            </div>
            
            <div class="links">
                <a href="/invoices">📊 View All Invoices</a>
                <a href="/docs">📚 API Documentation</a>
            </div>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const fileInput = document.getElementById('fileInput');
                const resultDiv = document.getElementById('result');
                const loadingDiv = document.querySelector('.loading');
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                loadingDiv.style.display = 'block';
                resultDiv.style.display = 'none';
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    loadingDiv.style.display = 'none';
                    resultDiv.style.display = 'block';
                    
                    if (response.ok) {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            <h3>✅ ${data.message}</h3>
                            <p><strong>Invoice ID:</strong> ${data.invoice_id}</p>
                            <p><strong>Invoice Number:</strong> ${data.extracted_data.invoice_number}</p>
                            <p><strong>Vendor:</strong> ${data.extracted_data.vendor_name}</p>
                            <p><strong>Total Amount:</strong> $${data.extracted_data.total_amount}</p>
                            <p><strong>Confidence:</strong> ${(data.extracted_data.confidence * 100).toFixed(1)}%</p>
                        `;
                        fileInput.value = '';
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<h3>❌ Error: ${data.message}</h3>`;
                    }
                } catch (error) {
                    loadingDiv.style.display = 'none';
                    resultDiv.style.display = 'block';
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `<h3>❌ Error: ${error.message}</h3>`;
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content


@app.post("/api/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice file (.txt format)")]
) -> UploadResponse:
    """
    Upload and process an invoice
    
    - **file**: Text file containing invoice data
    
    Returns:
    - Invoice ID if successful
    - Extracted data with confidence score
    
    (Following Context7 best practices for file uploads)
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .txt files are supported"
            )
        
        # Read file
        contents = await file.read()
        invoice_text = contents.decode('utf-8')
        
        # Extract using Llama
        extracted_data = extract_invoice_from_text(invoice_text)
        
        if not extracted_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract invoice data. Please check the file format."
            )
        
        # Save to database
        invoice_id = save_invoice_to_db(extracted_data)
        
        if not invoice_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save invoice to database"
            )
        
        return UploadResponse(
            status="success",
            message=f"Invoice extracted and saved successfully",
            invoice_id=invoice_id,
            extracted_data=ExtractedInvoiceData(**extracted_data)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


@app.get("/api/invoices", response_model=List[InvoiceResponse])
async def get_all_invoices():
    """
    Retrieve all invoices with their line items
    
    (Following Context7 best practices for response models)
    """
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, invoice_number, vendor_name, invoice_date, 
                           total_amount, confidence_score, status, created_at
                    FROM invoices
                    ORDER BY created_at DESC;
                """)
                
                invoices = cursor.fetchall()
                
                result = []
                for inv in invoices:
                    # Get line items for this invoice
                    cursor.execute("""
                        SELECT description, quantity, unit_price, total
                        FROM line_items
                        WHERE invoice_id = %s
                        ORDER BY id ASC;
                    """, (inv[0],))
                    
                    line_items = [
                        LineItemResponse(
                            description=item[0],
                            quantity=item[1],
                            unit_price=item[2],
                            total=item[3]
                        )
                        for item in cursor.fetchall()
                    ]
                    
                    result.append(InvoiceResponse(
                        id=inv[0],
                        invoice_number=inv[1],
                        vendor_name=inv[2],
                        invoice_date=inv[3],
                        total_amount=inv[4],
                        confidence_score=inv[5],
                        status=inv[6],
                        created_at=inv[7],
                        line_items=line_items
                    ))
                
                return result
    
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int):
    """
    Retrieve a specific invoice by ID
    """
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, invoice_number, vendor_name, invoice_date, 
                           total_amount, confidence_score, status, created_at
                    FROM invoices
                    WHERE id = %s;
                """, (invoice_id,))
                
                invoice = cursor.fetchone()
                
                if not invoice:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Invoice with ID {invoice_id} not found"
                    )
                
                # Get line items
                cursor.execute("""
                    SELECT description, quantity, unit_price, total
                    FROM line_items
                    WHERE invoice_id = %s
                    ORDER BY id ASC;
                """, (invoice_id,))
                
                line_items = [
                    LineItemResponse(
                        description=item[0],
                        quantity=item[1],
                        unit_price=item[2],
                        total=item[3]
                    )
                    for item in cursor.fetchall()
                ]
                
                return InvoiceResponse(
                    id=invoice[0],
                    invoice_number=invoice[1],
                    vendor_name=invoice[2],
                    invoice_date=invoice[3],
                    total_amount=invoice[4],
                    confidence_score=invoice[5],
                    status=invoice[6],
                    created_at=invoice[7],
                    line_items=line_items
                )
    
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get("/invoices", response_class=HTMLResponse)
async def view_invoices():
    """View all invoices in a nice table format"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>All Invoices</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 30px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 {
                color: #667eea;
                text-align: center;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: left;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
            }
            tr:hover {
                background: #f9f9f9;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #667eea;
                text-decoration: none;
                font-weight: bold;
            }
            .back-link:hover {
                text-decoration: underline;
            }
            .loading {
                text-align: center;
                color: #667eea;
                font-weight: bold;
                padding: 20px;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back-link">← Back to Upload</a>
        
        <div class="container">
            <h1>📊 All Invoices</h1>
            
            <div id="loading" class="loading">
                Loading invoices...
            </div>
            
            <table id="invoiceTable" style="display: none;">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Invoice #</th>
                        <th>Vendor</th>
                        <th>Date</th>
                        <th>Amount</th>
                        <th>Confidence</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody id="invoiceBody">
                </tbody>
            </table>
            
            <div id="noData" style="display: none; text-align: center; color: #666; padding: 20px;">
                No invoices found. <a href="/">Upload one now!</a>
            </div>
        </div>
        
        <script>
            async function loadInvoices() {
                try {
                    const response = await fetch('/api/invoices');
                    const invoices = await response.json();
                    
                    document.getElementById('loading').style.display = 'none';
                    
                    if (invoices.length === 0) {
                        document.getElementById('noData').style.display = 'block';
                        return;
                    }
                    
                    const tbody = document.getElementById('invoiceBody');
                    invoices.forEach(inv => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${inv.id}</td>
                            <td>${inv.invoice_number}</td>
                            <td>${inv.vendor_name}</td>
                            <td>${inv.invoice_date}</td>
                            <td>$${inv.total_amount.toFixed(2)}</td>
                            <td>${(inv.confidence_score * 100).toFixed(1)}%</td>
                            <td>${new Date(inv.created_at).toLocaleString()}</td>
                        `;
                    });
                    
                    document.getElementById('invoiceTable').style.display = 'table';
                } catch (error) {
                    document.getElementById('loading').innerHTML = `
                        <p style="color: red;">❌ Error loading invoices: ${error.message}</p>
                    `;
                }
            }
            
            loadInvoices();
        </script>
    </body>
    </html>
    """
    return html_content


# ============================================================================
# STARTUP CHECK
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Check connections on startup"""
    
    print("\n" + "="*50)
    print("🚀 Invoice Processing System Starting")
    print("="*50)
    
    # Check Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        print("✅ Ollama is running")
    except:
        print("⚠️  Ollama not detected. Run: ollama serve")
    
    # Check Database
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            print("✅ PostgreSQL connected")
    except:
        print("⚠️  PostgreSQL not connected. Check your password in app.py")
    
    print("\n📱 Open browser: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("="*50 + "\n")