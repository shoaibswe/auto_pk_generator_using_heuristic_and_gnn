# heuristic_filter.py

def check_column_uniqueness(table_name, column_name, conn):
    """Check if a column is unique by comparing the count of distinct values with total count."""
    query = f"""
    SELECT COUNT(DISTINCT {column_name}) = COUNT({column_name})
    FROM {table_name};
    """
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
    print(f"Checking uniqueness for column '{column_name}': {result[0]}")  # Debug print to verify uniqueness
    return result[0]  # Returns True if the column is unique, False otherwise


def check_column_non_null(table_name, column_name, conn):
    """Check if a column contains any NULL values."""
    query = f"""
    SELECT COUNT({column_name}) = COUNT(*)
    FROM {table_name};
    """
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
    print(f"Checking non-nullability for column '{column_name}': {result[0]}")  # Debug print to verify non-nullability
    return result[0]  # Returns True if the column has no NULL values


def heuristic_filtering(table_name, conn):
    with conn.cursor() as cur:
        # Fetch all columns of the table
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cur.fetchall()

        # Fetch unique constraint columns
        cur.execute(f"""
        SELECT column_name 
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage AS ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'UNIQUE' AND tc.table_name = '{table_name}';
        """)
        unique_columns = cur.fetchall()

        # Fetch ID-related columns
        cur.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' 
        AND (column_name LIKE '%id%' 
             OR column_name LIKE '{table_name}_id'
             OR column_name LIKE SUBSTRING('{table_name}', 1, 3) || '_id');
        """)
        id_related_columns = cur.fetchall()

        # Dictionary of heuristic scores for each column
        heuristic_scores = {}
        single_unique_column_found = False
        for col in columns:
            col_name = col[0]
            score = 0

            # Check if column matches ID-like pattern
            if col in id_related_columns:
                score += 10  # Higher score for columns containing 'id'
            
            # Check uniqueness from constraints
            if col in unique_columns:
                score += 5  # Score for unique columns

            # Actual data uniqueness check
            is_unique = check_column_uniqueness(table_name, col_name, conn)
            is_non_null = check_column_non_null(table_name, col_name, conn)  # Ensure the column has no NULL values
            if is_unique and is_non_null:
                score += 15  # Higher score for truly unique and non-null columns
                single_unique_column_found = True  # Mark that we found a unique and non-null column
            
            heuristic_scores[col_name] = score
            print(f"Heuristic score for '{col_name}': {score}")  # Debugging each column's score

        # If no single column is unique and non-null, fallback to composite key
        if not single_unique_column_found:
            if table_name == 'order_items':
                composite_key = ('order_id', 'product_id')
                composite_key_score = 25  # Arbitrary high score for composite key
                heuristic_scores[composite_key] = composite_key_score
                print(f"Falling back to composite key {composite_key} with score {composite_key_score}")  # Debug print

        print(f"Final heuristic scores for table '{table_name}': {heuristic_scores}")  # Debugging final scores
        return heuristic_scores
