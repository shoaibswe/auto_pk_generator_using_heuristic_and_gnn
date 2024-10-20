# table_identifier.py
def get_all_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """)
        tables = cur.fetchall()
        return [table[0] for table in tables]

def get_table_columns(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}';
        """)
        columns = cur.fetchall()
        return [col[0] for col in columns]

def get_foreign_key_relationships(table_name, conn):
    query = f"""
    SELECT
        kcu.column_name AS referencing_column,
        ccu.table_name AS referenced_table,
        ccu.column_name AS referenced_column
    FROM
        information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
    WHERE
        constraint_type = 'FOREIGN KEY'
        AND kcu.table_name = '{table_name}';
    """
    
    with conn.cursor() as cur:
        cur.execute(query)
        relationships = cur.fetchall()
    
    return relationships

# table_identifier.py

def has_primary_key(table_name, conn):
    query = f"""
    SELECT COUNT(*)
    FROM information_schema.table_constraints
    WHERE table_name = '{table_name}' AND constraint_type = 'PRIMARY KEY';
    """
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
        return result[0] > 0  # True if there is a primary key, False otherwise
