# app.py
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import requests
import json
import psycopg2
from typing import List, Annotated, Optional
import time
import os

from models import InvoiceResponse, UploadResponse, LineItemResponse, ExtractedInvoiceData
from config import settings
from logger import app_logger, extraction_logger, db_logger, http_logger

# ============================================================================
# INITIALIZE FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.API_TITLE,
    description="Extract invoice data using Llama 3.2 - Production Ready",
    version=settings.API_VERSION,
    debug=settings.DEBUG
)

# ============================================================================
# MIDDLEWARE (Context7 Best Practice)
# ============================================================================

# HTTP Request/Response Logging Middleware
@app.middleware("http")
async def log_http_requests(request: Request, call_next):
    """
    Log all HTTP requests and responses with ECS format.
    Context7 best practice for observability.
    """
    
    start_time = time.perf_counter()
    
    # Get request body size
    body = await request.body()
    request_size = len(body)
    
    # Log incoming request
    http_logger.info(
        "HTTP request started",
        http={
            "request": {
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) or None,
                "bytes": request_size,
            }
        },
        url={
            "full": str(request.url),
            "path": request.url.path,
            "scheme": request.url.scheme,
        },
        client={
            "address": request.client.host if request.client else None,
        }
    )
    
    try:
        response = await call_next(request)
        
        process_time = time.perf_counter() - start_time
        
        # Log successful response
        http_logger.info(
            "HTTP request completed",
            http={
                "response": {
                    "status_code": response.status_code,
                    "status": "success" if response.status_code < 400 else "error",
                }
            },
            duration_ms=round(process_time * 1000, 2),
            event={
                "duration_ms": round(process_time * 1000, 2),
            }
        )
        
        return response
    
    except Exception as e:
        process_time = time.perf_counter() - start_time
        
        # Log request failure
        http_logger.error(
            "HTTP request failed",
            http={
                "response": {
                    "status_code": 500,
                    "status": "error",
                }
            },
            error=str(e),
            duration_ms=round(process_time * 1000, 2),
            event={
                "action": "http_request_failed",
                "outcome": "failure",
            },
            exc_info=True
        )
        raise


# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_invoice_from_text(invoice_text: str, invoice_id: Optional[int] = None) -> dict:
    """
    Extract invoice data using Llama 3.2 with structured logging.
    Context7 best practice: Proper error logging with context.
    """
    
    try:
        extraction_logger.info(
            "Starting invoice extraction",
            invoice={
                "id": invoice_id,
            },
            llm={
                "model": settings.OLLAMA_MODEL,
            }
        )
        
        # Validate input
        if not invoice_text or len(invoice_text.strip()) == 0:
            extraction_logger.warning(
                "Empty invoice text provided",
                invoice={"id": invoice_id},
            )
            return None
        
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
            "model": settings.OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        
        llm_start_time = time.perf_counter()
        response = requests.post(
            settings.OLLAMA_HOST + "/api/chat",
            json=payload,
            timeout=60
        )
        llm_process_time = time.perf_counter() - llm_start_time
        
        response.raise_for_status()
        
        result = response.json()
        response_text = result['message']['content']
        
        # Extract JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            extraction_logger.error(
                "Could not find JSON in Llama response",
                invoice={"id": invoice_id},
                llm={
                    "response_preview": response_text[:200],
                }
            )
            return None
        
        extracted_json = response_text[json_start:json_end]
        extracted_data = json.loads(extracted_json)
        
        extraction_logger.info(
            "Extraction successful",
            invoice={
                "id": invoice_id,
                "number": extracted_data.get('invoice_number'),
                "vendor": extracted_data.get('vendor_name'),
                "total_amount": extracted_data.get('total_amount'),
                "line_items_count": len(extracted_data.get('line_items', [])),
            },
            extraction={
                "confidence": extracted_data.get('confidence', 0.0),
                "llm_response_time_ms": round(llm_process_time * 1000, 2),
            }
        )
        
        return extracted_data
    
    except requests.exceptions.ConnectionError as e:
        extraction_logger.error(
            "Failed to connect to Ollama",
            invoice={"id": invoice_id},
            error={
                "type": "connection_error",
                "message": str(e),
            },
            llm={
                "host": settings.OLLAMA_HOST,
            }
        )
        return None
    except json.JSONDecodeError as e:
        extraction_logger.error(
            "JSON parsing error",
            invoice={"id": invoice_id},
            error={
                "type": "json_error",
                "message": str(e),
            }
        )
        return None
    except Exception as e:
        extraction_logger.error(
            "Unexpected extraction error",
            invoice={"id": invoice_id},
            error={
                "type": type(e).__name__,
                "message": str(e),
            },
            exc_info=True
        )
        return None


def save_invoice_to_db(extracted_data: dict, invoice_id: Optional[int] = None) -> int:
    """
    Save extracted invoice to database with structured logging.
    Context7 best practice: Comprehensive error logging with context.
    """
    
    try:
        db_start_time = time.perf_counter()
        
        db_logger.info(
            "Attempting to save invoice",
            invoice={"id": invoice_id},
            database={"operation": "insert"},
        )
        
        with psycopg2.connect(**settings.database_url) as conn:
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
                
                saved_invoice_id = cursor.fetchone()[0]
                
                # Insert line items
                line_count = 0
                for item in extracted_data.get('line_items', []):
                    cursor.execute("""
                        INSERT INTO line_items 
                        (invoice_id, description, quantity, unit_price, total)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (
                        saved_invoice_id,
                        item.get('description'),
                        item.get('quantity'),
                        item.get('unit_price'),
                        item.get('total')
                    ))
                    line_count += 1
                
                # Insert audit log
                cursor.execute("""
                    INSERT INTO audit_log (invoice_id, action, details)
                    VALUES (%s, %s, %s);
                """, (
                    saved_invoice_id,
                    'UPLOADED',
                    f"Invoice uploaded via web. Line items: {line_count}. Confidence: {extracted_data.get('confidence', 0.0)}"
                ))
        
        db_process_time = time.perf_counter() - db_start_time
        
        db_logger.info(
            "Invoice saved successfully",
            invoice={
                "id": saved_invoice_id,
                "number": extracted_data.get('invoice_number'),
                "line_items": line_count,
            },
            database={
                "operation": "insert_completed",
                "response_time_ms": round(db_process_time * 1000, 2),
            }
        )
        
        return saved_invoice_id
    
    except psycopg2.IntegrityError as e:
        db_logger.error(
            "Database integrity error (duplicate invoice?)",
            invoice={"id": invoice_id},
            error={
                "type": "integrity_error",
                "message": str(e),
            }
        )
        return None
    except psycopg2.OperationalError as e:
        db_logger.error(
            "Database connection error",
            invoice={"id": invoice_id},
            error={
                "type": "operational_error",
                "message": str(e),
            },
            database={
                "host": settings.DATABASE_HOST,
                "port": settings.DATABASE_PORT,
            }
        )
        return None
    except psycopg2.Error as e:
        db_logger.error(
            "Database error",
            invoice={"id": invoice_id},
            error={
                "type": "database_error",
                "message": str(e),
            },
            exc_info=True
        )
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
            .version {
                text-align: center;
                color: #999;
                font-size: 12px;
                margin-top: -10px;
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
            .status {
                padding: 10px;
                background: #e7f3ff;
                border-left: 4px solid #2196F3;
                margin-bottom: 20px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📄 Invoice Processing System</h1>
            <div class="version">v""" + settings.API_VERSION + """</div>
            <p style="text-align: center; color: #666;">
                Upload your invoices and we'll extract the data automatically using AI
            </p>
            
            <div class="status">
                ✅ System operational - All services connected
            </div>
            
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
                <a href="/docs">📚 API Docs</a>
                <a href="/health">🏥 Health Check</a>
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
                        resultDiv.innerHTML = `<h3>❌ Error: ${data.detail || data.message}</h3>`;
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


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    Used by Docker health checks and load balancers.
    """
    
    health_status = {
        "status": "healthy",
        "version": settings.API_VERSION,
        "services": {}
    }
    
    app_logger.info("Health check requested", event={"action": "health_check"})
    
    # Check Ollama
    try:
        response = requests.get(settings.OLLAMA_HOST + "/api/tags", timeout=5)
        health_status["services"]["ollama"] = "✅ running"
    except Exception as e:
        health_status["services"]["ollama"] = "❌ unavailable"
        health_status["status"] = "degraded"
        app_logger.warning(
            "Ollama health check failed",
            service={"name": "ollama", "status": "down"},
            error=str(e)
        )
    
    # Check Database
    try:
        with psycopg2.connect(**settings.database_url) as conn:
            health_status["services"]["database"] = "✅ running"
    except Exception as e:
        health_status["services"]["database"] = "❌ unavailable"
        health_status["status"] = "degraded"
        app_logger.warning(
            "Database health check failed",
            service={"name": "database", "status": "down"},
            error=str(e)
        )
    
    # Check Loki
    if settings.LOKI_ENABLED:
        try:
            response = requests.get(settings.LOKI_URL + "/ready", timeout=5)
            health_status["services"]["loki"] = "✅ running"
        except:
            health_status["services"]["loki"] = "❌ unavailable"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


@app.post("/api/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice file (.txt format)")]
) -> UploadResponse:
    """
    Upload and process an invoice.
    Extracts data using Llama 3.2 and saves to database.
    """
    
    try:
        app_logger.info(
            "File upload initiated",
            file={
                "name": file.filename,
                "content_type": file.content_type,
                "size": file.size or 0,
            }
        )
        
        # Validate file type
        if not file.filename.endswith('.txt'):
            app_logger.warning(
                "Invalid file type uploaded",
                file={"name": file.filename, "type": file.content_type},
                error={"type": "invalid_file_type"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .txt files are supported"
            )
        
        # Validate file size (max 5MB)
        if file.size and file.size > 5 * 1024 * 1024:
            app_logger.warning(
                "File size exceeds limit",
                file={"name": file.filename, "size": file.size},
                error={"type": "file_too_large", "max_size": "5MB"}
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size must be less than 5MB"
            )
        
        # Read file
        contents = await file.read()
        invoice_text = contents.decode('utf-8')
        
        # Extract using Llama
        extracted_data = extract_invoice_from_text(invoice_text)
        
        if not extracted_data:
            app_logger.error(
                "Failed to extract invoice data",
                file={"name": file.filename},
                error={"type": "extraction_failed"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to extract invoice data. Please check the file format."
            )
        
        # Save to database
        invoice_id = save_invoice_to_db(extracted_data)
        
        if not invoice_id:
            app_logger.error(
                "Failed to save invoice to database",
                file={"name": file.filename},
                error={"type": "database_save_failed"}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save invoice to database"
            )
        
        app_logger.info(
            "Invoice processed successfully",
            invoice={
                "id": invoice_id,
                "number": extracted_data.get('invoice_number'),
                "vendor": extracted_data.get('vendor_name'),
            },
            file={"name": file.filename}
        )
        
        return UploadResponse(
            status="success",
            message="Invoice extracted and saved successfully",
            invoice_id=invoice_id,
            extracted_data=ExtractedInvoiceData(**extracted_data)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            "Unexpected error during file upload",
            file={"name": file.filename},
            error={
                "type": type(e).__name__,
                "message": str(e),
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
        )


@app.get("/api/invoices", response_model=List[InvoiceResponse])
async def get_all_invoices():
    """Retrieve all invoices with their line items"""
    
    try:
        app_logger.info(
            "Retrieving all invoices",
            database={"operation": "select_all"}
        )
        
        with psycopg2.connect(**settings.database_url) as conn:
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
                
                app_logger.info(
                    "Invoices retrieved successfully",
                    database={"operation": "select_all", "count": len(result)}
                )
                
                return result
    
    except psycopg2.Error as e:
        app_logger.error(
            "Database error retrieving invoices",
            error={
                "type": "database_error",
                "message": str(e),
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int):
    """Retrieve a specific invoice by ID"""
    
    try:
        app_logger.info(
            "Retrieving specific invoice",
            invoice={"id": invoice_id},
            database={"operation": "select_one"}
        )
        
        with psycopg2.connect(**settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, invoice_number, vendor_name, invoice_date, 
                           total_amount, confidence_score, status, created_at
                    FROM invoices
                    WHERE id = %s;
                """, (invoice_id,))
                
                invoice = cursor.fetchone()
                
                if not invoice:
                    app_logger.warning(
                        "Invoice not found",
                        invoice={"id": invoice_id},
                    )
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
                
                app_logger.info(
                    "Invoice retrieved successfully",
                    invoice={"id": invoice_id, "number": invoice[1]},
                )
                
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
        app_logger.error(
            "Database error retrieving invoice",
            invoice={"id": invoice_id},
            error={
                "type": "database_error",
                "message": str(e),
            },
            exc_info=True
        )
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
# STARTUP AND SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    Verify all dependencies are available.
    """
    
    app_logger.info("=" * 70)
    app_logger.info("🚀 Invoice Processing System Starting")
    app_logger.info("=" * 70)
    app_logger.info(
        "System initialization",
        system={
            "version": settings.API_VERSION,
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
        }
    )
    
    # Check Ollama
    try:
        response = requests.get(settings.OLLAMA_HOST + "/api/tags", timeout=5)
        app_logger.info(
            "✅ Ollama connected",
            service={"name": "ollama", "status": "running", "url": settings.OLLAMA_HOST}
        )
    except Exception as e:
        app_logger.warning(
            "⚠️  Ollama not available",
            service={"name": "ollama", "status": "offline", "url": settings.OLLAMA_HOST},
            error=str(e)
        )
    
    # Check Database
    try:
        with psycopg2.connect(**settings.database_url) as conn:
            app_logger.info(
                "✅ PostgreSQL connected",
                service={
                    "name": "database",
                    "status": "running",
                    "host": settings.DATABASE_HOST,
                    "port": settings.DATABASE_PORT,
                }
            )
    except Exception as e:
        app_logger.error(
            "❌ PostgreSQL connection failed",
            service={
                "name": "database",
                "status": "offline",
                "host": settings.DATABASE_HOST,
            },
            error=str(e)
        )
    
    # Check Loki
    if settings.LOKI_ENABLED:
        try:
            response = requests.get(settings.LOKI_URL + "/ready", timeout=5)
            app_logger.info(
                "✅ Loki connected",
                service={"name": "loki", "status": "running", "url": settings.LOKI_URL}
            )
        except Exception as e:
            app_logger.warning(
                "⚠️  Loki not available",
                service={"name": "loki", "status": "offline", "url": settings.LOKI_URL},
                error=str(e)
            )
    
    app_logger.info(
        "System ready",
        system={
            "api_url": f"http://{settings.HOST}:{settings.PORT}",
            "docs_url": f"http://{settings.HOST}:{settings.PORT}/docs",
        }
    )
    app_logger.info("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    
    app_logger.info("=" * 70)
    app_logger.info("🛑 Invoice Processing System Shutting Down")
    app_logger.info("=" * 70)