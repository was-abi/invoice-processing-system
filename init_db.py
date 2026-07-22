# init_db.py
import psycopg2
from psycopg2 import sql

# Database connection details
DB_CONFIG = {
    "host": "localhost",
    "database": "invoice_db",
    "user": "postgres",
    "password": "password123",
    "port": "5432"
}

def create_tables():
    """Create tables for invoice processing using context manager best practices"""
    
    try:
        # Use context manager for proper connection handling
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                print("📊 Creating tables...")
                
                # Table 1: Store invoices
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS invoices (
                        id SERIAL PRIMARY KEY,
                        invoice_number VARCHAR(50) UNIQUE NOT NULL,
                        vendor_name VARCHAR(255),
                        invoice_date DATE,
                        total_amount DECIMAL(10, 2),
                        confidence_score FLOAT,
                        raw_text TEXT,
                        extracted_json JSONB,
                        status VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                print("✅ Created 'invoices' table")
                
                # Table 2: Store line items
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS line_items (
                        id SERIAL PRIMARY KEY,
                        invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
                        description VARCHAR(255),
                        quantity INTEGER,
                        unit_price DECIMAL(10, 2),
                        total DECIMAL(10, 2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                print("✅ Created 'line_items' table")
                
                # Table 3: Audit log
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id SERIAL PRIMARY KEY,
                        invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
                        action VARCHAR(100),
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                print("✅ Created 'audit_log' table")
                
                # Create indexes for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number 
                    ON invoices(invoice_number);
                """)
                print("✅ Created index on invoice_number")
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_created_at 
                    ON invoices(created_at);
                """)
                print("✅ Created index on created_at")
                
            # Transaction is automatically committed on successful exit
        
        print("\n✅ All tables created successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    create_tables()