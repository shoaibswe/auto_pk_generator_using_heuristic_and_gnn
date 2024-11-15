# db_connector.py

from config import DATABASE
import psycopg2


def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DATABASE["host"],
            port=DATABASE["port"],
            user=DATABASE["user"],
            password=DATABASE["password"],
            database=DATABASE["database"],
        )
        print("Database connection successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None
