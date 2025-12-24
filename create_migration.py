import sys
import os
import psycopg2
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection details from environment variables
dbname = os.environ.get('PGDATABASE')
user = os.environ.get('PGUSER')
password = os.environ.get('PGPASSWORD')
host = os.environ.get('PGHOST')
port = os.environ.get('PGPORT')

# Connect to database
try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    conn.autocommit = False  # Use transactions
    cur = conn.cursor()
    logger.info("Connected to PostgreSQL database")
except Exception as e:
    logger.error(f"Error connecting to database: {e}")
    sys.exit(1)

try:
    # Check if the default_currency column exists in configuration table
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'configuration' 
        AND column_name = 'default_currency'
    """)
    
    if cur.fetchone() is None:
        # Column doesn't exist, add it
        logger.info("Adding default_currency column to configuration table")
        cur.execute("""
            ALTER TABLE configuration 
            ADD COLUMN default_currency VARCHAR(10) DEFAULT 'rupees'
        """)
    else:
        logger.info("default_currency column already exists in configuration table")
    
    # Check if the month and year columns exist in expense table
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'expense' 
        AND column_name = 'month'
    """)
    
    if cur.fetchone() is None:
        # Month column doesn't exist, add it
        logger.info("Adding month column to expense table")
        cur.execute("""
            ALTER TABLE expense 
            ADD COLUMN month INTEGER
        """)
        
        # Set default value for existing records
        now = "EXTRACT(MONTH FROM timestamp)"
        cur.execute(f"UPDATE expense SET month = {now}")
        
        # Make it not nullable
        cur.execute("ALTER TABLE expense ALTER COLUMN month SET NOT NULL")
    else:
        logger.info("month column already exists in expense table")
    
    # Check for year column
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'expense' 
        AND column_name = 'year'
    """)
    
    if cur.fetchone() is None:
        # Year column doesn't exist, add it
        logger.info("Adding year column to expense table")
        cur.execute("""
            ALTER TABLE expense 
            ADD COLUMN year INTEGER
        """)
        
        # Set default value for existing records
        now = "EXTRACT(YEAR FROM timestamp)"
        cur.execute(f"UPDATE expense SET year = {now}")
        
        # Make it not nullable
        cur.execute("ALTER TABLE expense ALTER COLUMN year SET NOT NULL")
    else:
        logger.info("year column already exists in expense table")
    
    # Check if the budget table exists
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name = 'budget'
    """)
    
    if cur.fetchone() is None:
        # Table doesn't exist, create it
        logger.info("Creating budget table")
        cur.execute("""
            CREATE TABLE budget (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                amount FLOAT NOT NULL,
                currency VARCHAR(10) DEFAULT 'rupees',
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (category, month, year)
            )
        """)
    else:
        logger.info("budget table already exists")
    
    # Commit all changes
    conn.commit()
    logger.info("Migration completed successfully")
    
except Exception as e:
    # Roll back any changes if something goes wrong
    conn.rollback()
    logger.error(f"Error during migration: {e}")
    sys.exit(1)
    
finally:
    # Close communication with the database
    if cur:
        cur.close()
    if conn:
        conn.close()
    logger.info("Database connection closed")