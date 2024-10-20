# main.py

from scripts.db_connector import connect_to_db
from scripts.heuristic_filter import heuristic_filtering
from scripts.gnn_pipeline import run_gnn_model
from scripts.rl_agent import RLAgent
from scripts.table_identifier import get_all_tables, has_primary_key

def detect_primary_key_for_all_tables(conn):
    tables = get_all_tables(conn)
    rl_agent = RLAgent()

    for table_name in tables:
        if has_primary_key(table_name, conn):
            print(f"Skipping table '{table_name}' because it already has a primary key.")
            continue

        print(f"Processing table: {table_name}")

        # Get heuristic scores
        heuristic_scores = heuristic_filtering(table_name, conn)

        # Run the GNN model and get combined GNN + heuristic scores
        combined_scores = run_gnn_model(table_name, conn, heuristic_scores)

        # Use GNN + heuristic scores as the state (hashable tuple)
        state = tuple(combined_scores.values())

        # Select the optimal primary key using RL
        optimal_primary_key = rl_agent.select_action(state, list(heuristic_scores.keys()))  # Convert to list

        print(f"Optimal Primary Key for table '{table_name}': {optimal_primary_key}")
        print("--------------------------------")

if __name__ == "__main__":
    # Connect to the PostgreSQL database
    conn = connect_to_db()

    if conn:
        detect_primary_key_for_all_tables(conn)
        conn.close()
