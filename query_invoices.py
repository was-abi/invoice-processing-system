# query_invoices.py
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "database": "invoice_db",
    "user": "postgres",
    "password": "password123",
    "port": "5432"
}

def get_all_invoices():
    """Retrieve all invoices from database"""
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, invoice_number, vendor_name, total_amount, confidence_score, created_at
                    FROM invoices
                    ORDER BY created_at DESC;
                """)
                
                invoices = cursor.fetchall()
                
                if not invoices:
                    print("No invoices found in database")
                    return
                
                # Display results
                print("\n📋 Invoices in Database:\n")
                for inv in invoices:
                    print(f"ID: {inv[0]}")
                    print(f"Invoice #: {inv[1]}")
                    print(f"Vendor: {inv[2]}")
                    print(f"Amount: ${inv[3]}")
                    print(f"Confidence: {inv[4]}")
                    print(f"Created: {inv[5]}")
                    print("-" * 50)
    
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")


def get_invoice_details(invoice_id):
    """Get full details of an invoice including line items"""
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                # Get invoice
                cursor.execute("""
                    SELECT id, invoice_number, vendor_name, invoice_date, 
                           total_amount, confidence_score, created_at
                    FROM invoices 
                    WHERE id = %s;
                """, (invoice_id,))
                
                invoice = cursor.fetchone()
                
                if not invoice:
                    print(f"❌ Invoice ID {invoice_id} not found")
                    return
                
                print(f"\n📄 Invoice Details (ID: {invoice[0]}):\n")
                print(f"Invoice #: {invoice[1]}")
                print(f"Vendor: {invoice[2]}")
                print(f"Date: {invoice[3]}")
                print(f"Total: ${invoice[4]}")
                print(f"Confidence: {invoice[5]}")
                print(f"Created: {invoice[6]}")
                
                # Get line items
                cursor.execute("""
                    SELECT description, quantity, unit_price, total 
                    FROM line_items 
                    WHERE invoice_id = %s
                    ORDER BY id ASC;
                """, (invoice_id,))
                
                line_items = cursor.fetchall()
                
                if line_items:
                    print("\n📝 Line Items:")
                    print("-" * 70)
                    for item in line_items:
                        print(f"Description: {item[0]}")
                        print(f"  Qty: {item[1]} | Unit Price: ${item[2]} | Total: ${item[3]}")
                
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")


if __name__ == "__main__":
    # Show all invoices
    get_all_invoices()
    
    # Show details of first invoice
    print("\n" + "="*50)
    get_invoice_details(2)