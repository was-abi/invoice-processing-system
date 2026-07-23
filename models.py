# models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class LineItemResponse(BaseModel):
    """Line item from invoice"""
    description: str
    quantity: int
    unit_price: float
    total: float

class InvoiceResponse(BaseModel):
    """Invoice response model (from Context7 best practices)"""
    id: int
    invoice_number: str
    vendor_name: str
    invoice_date: datetime
    total_amount: float
    confidence_score: float
    status: str
    created_at: datetime
    line_items: List[LineItemResponse] = []

class ExtractedInvoiceData(BaseModel):
    """Data extracted by Llama"""
    invoice_number: str
    date: str
    vendor_name: str
    total_amount: float
    line_items: List[LineItemResponse]
    confidence: float

class UploadResponse(BaseModel):
    """Response after uploading invoice"""
    status: str
    message: str
    invoice_id: Optional[int] = None
    extracted_data: Optional[ExtractedInvoiceData] = None