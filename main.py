# main.py

from db_connector import connect_to_db
from scripts import (
    has_primary_key,
    load_table_data_as_dataframe,
    get_foreign_key_relationships,
    run_gnn_model,
    get_all_tables,
    heuristic_filtering_with_priority,
)


def detect_primary_key_for_all_tables(conn):
    tables = get_all_tables(conn)

    for table_name in tables:
        # Skip tables with existing primary keys
        if has_primary_key(table_name, conn):
            print(f"Table '{table_name}' already has a primary key. Skipping.")
            continue

        print(f"Processing table: {table_name}")

        # Load the table's data into a DataFrame
        df = load_table_data_as_dataframe(table_name, conn)
        if df.empty:
            print(f"Table '{table_name}' is empty or could not be loaded. Skipping.")
            print("-----------\n")
            continue

        # Load related foreign key tables
        foreign_key_tables = [
            (load_table_data_as_dataframe(fk_table, conn), fk_column)
            for fk_table, fk_column in get_foreign_key_relationships(table_name, conn)
        ]

        # Compute heuristic scores using the combined logic
        heuristic_scores, valid_columns = heuristic_filtering_with_priority(
            table_name, df, foreign_key_tables
        )

        # Exclude columns that do not meet primary key characteristics
        if not valid_columns:
            print(
                f"No valid columns for primary key in table '{table_name}'. Skipping.\n"
            )
            print("-----------\n")
            continue

        # Run the GNN model for additional scoring
        relationships = get_foreign_key_relationships(table_name, conn)
        combined_scores = run_gnn_model(table_name, df, heuristic_scores, relationships)

        # Sort candidates by combined score and prioritize columns with "id" in the name
        primary_key_candidates = sorted(
            combined_scores.items(), key=lambda x: (-x[1], "id" in x[0].lower())
        )

        # Print the results
        print(
            f"Primary key candidates for table '{table_name}': {primary_key_candidates}"
        )
        print("-----------\n")


if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        detect_primary_key_for_all_tables(conn)
        conn.close()
