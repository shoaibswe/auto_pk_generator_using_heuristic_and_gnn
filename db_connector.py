# codes/db_connector.py
import os
from sqlalchemy import create_engine
from config import DATABASE

def connect_to_db():
    """
    Connects to PostgreSQL using SQLAlchemy (Required for Pandas).
    Update credentials as needed.
    """
    try:
        # Format: postgresql://user:password@host:port/dbname
        # Build connection URL from config
        db_url = f"postgresql://{DATABASE['user']}:{DATABASE['password']}@{DATABASE['host']}:{DATABASE['port']}/{DATABASE['database']}"
        
        engine = create_engine(db_url)
        connection = engine.connect()
        print("Database connection successful!")
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None