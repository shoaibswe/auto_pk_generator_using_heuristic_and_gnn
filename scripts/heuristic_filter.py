# heuristic_filter.py

import re

def check_column_uniqueness(table_name, column_name, conn):
    # Escape the column name using double quotes
    query = f'SELECT COUNT(DISTINCT "{column_name}") = COUNT("{column_name}") FROM {table_name};'
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
    return result[0]  # True if unique, False otherwise

def check_column_non_null(table_name, column_name, conn):
    # Escape the column name using double quotes
    query = f'SELECT COUNT("{column_name}") = COUNT(*) FROM {table_name};'
    with conn.cursor() as cur:
        cur.execute(query)
        result = cur.fetchone()
    return result[0]  # True if no NULL values, False otherwise


def heuristic_filtering(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cur.fetchall()
        columns = [col[0] for col in columns]

        # Split the table name on underscores and spaces to detect parts
        table_parts = re.split(r'[_\s]+', table_name.lower())

        # Detect potential ID columns by matching table parts
        id_columns = [col for col in columns if any(part in col.lower() for part in table_parts)]
        print(f"Detected columns from table parts: {id_columns}")

        heuristic_scores = {}
        candidate_columns = []

        for col in columns:
            score = 0
            if col in id_columns or '_id' in col.lower():
                print(f"Considering column '{col}' for primary key based on naming conventions.")

                is_unique = check_column_uniqueness(table_name, col, conn)
                is_non_null = check_column_non_null(table_name, col, conn)

                if is_unique and is_non_null:
                    score += 20
                    candidate_columns.append(col)
                    print(f"Column '{col}' meets all conditions with score: {score}")
                else:
                    print(f"Column '{col}' failed at least one condition. Excluding from primary key candidates.")

            heuristic_scores[col] = score

        # Handle multi-word tables by suggesting composite keys
        if len(candidate_columns) < 2 and len(id_columns) >= 2:
            print(f"Table '{table_name}' is multi-word. Suggesting composite key.")
            candidate_columns = [col for col in id_columns if col in columns]
            heuristic_scores.update({col: 20 for col in candidate_columns})

        if not candidate_columns:
            surrogate_key = 'surrogate_id'
            heuristic_scores[surrogate_key] = 30
            print(f"Fallback to surrogate key '{surrogate_key}' with score 30.")

        print(f"Final heuristic scores for table '{table_name}': {heuristic_scores}")
        return heuristic_scores, candidate_columns
