# table_identifier.py

def get_all_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
    return tables

def has_primary_key(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(f"""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = '{table_name}' AND constraint_type = 'PRIMARY KEY'
        )
        """)
        result = cur.fetchone()
    return result[0]

def get_foreign_key_relationships(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(f"""
        SELECT
            tc.table_name, kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name='{table_name}';
        """)
        relationships = cur.fetchall()
    return relationships

def get_table_columns(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}';
        """)
        columns = [row[0] for row in cur.fetchall()]
    return columns
