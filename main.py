from scripts.db_connector import connect_to_db
from scripts.heuristic_filter import heuristic_filtering

def detect_primary_key_for_all_tables(conn):
    cur = conn.cursor()

    # Query to find tables in the public schema
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cur.fetchall()

    for table in tables:
        table_name = table[0]

        # Check if the table already has a primary key
        cur.execute(f"""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = '{table_name}' AND tc.constraint_type = 'PRIMARY KEY'
        """)
        primary_key_columns = cur.fetchall()

        # If the table already has a primary key, skip processing
        if primary_key_columns:
            print(f"Skipping table '{table_name}' because it already has a primary key.")
            continue

        print(f"Processing table: {table_name}")

        # Get heuristic scores and candidate columns
        heuristic_scores, candidate_columns = heuristic_filtering(table_name, conn)

        # If candidate columns are found, avoid generating surrogate keys
        if candidate_columns:
            if len(candidate_columns) > 1:
                print(f"Optimal Composite Key for table '{table_name}': {', '.join(candidate_columns)}")
            else:
                print(f"Optimal Primary Key for table '{table_name}': {candidate_columns[0]}")
        else:
            print(f"Warning: No suitable key found for table '{table_name}'. Please check manually.")
        print("-----------")
if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        detect_primary_key_for_all_tables(conn)
        conn.close()
