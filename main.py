#MAIN.PY
from db_connector import connect_to_db
from scripts.table_identifier import get_all_tables, get_table_columns, get_foreign_key_relationships
from scripts.heuristic_filter import heuristic_filtering
from scripts.gnn_pipeline import run_gnn_model
from scripts.utils import load_table_data_as_dataframe

def detect_primary_key_for_all_tables(conn):
    tables = get_all_tables(conn)
    for table_name in tables:
        print(f"Processing table: {table_name}")

        df = load_table_data_as_dataframe(table_name, conn)
        if df.empty:
            print(f"Table '{table_name}' is empty or could not be loaded. Skipping.")
            continue

        heuristic_scores, candidate_columns = heuristic_filtering(table_name, df)
        relationships = get_foreign_key_relationships(table_name, conn)
        combined_scores = run_gnn_model(table_name, df, heuristic_scores, relationships)

        primary_key_candidates = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        print(f"Primary key candidates for table '{table_name}': {primary_key_candidates}")
        print("-----------")

if __name__ == "__main__":
    conn = connect_to_db()
    if conn:
        detect_primary_key_for_all_tables(conn)
        conn.close()
