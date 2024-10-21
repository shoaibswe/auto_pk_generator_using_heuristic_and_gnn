def run_gnn_model(table_name, conn, heuristic_scores):
    # Fetch relationships and column data from the database
    relationships = get_foreign_key_relationships(table_name, conn)
    columns = get_table_columns(table_name, conn)
    
    print(f"Running GNN model for table: {table_name}")

    # Filter out columns with low heuristic scores (e.g., 0 or less)
    valid_columns = [col for col in columns if heuristic_scores.get(col, 0) > 0]
    if not valid_columns:
        print(f"No valid columns to pass to the GNN model after filtering.")
        return heuristic_scores  # Return heuristic scores if no valid columns found

    # Create the graph for valid columns
    edge_index, features = create_column_graph(len(valid_columns), relationships, valid_columns)

    # Run the GNN model
    model = PrimaryKeyGNN(in_feats=10, hidden_size=20, out_feats=2)
    predictions = model(features, edge_index)

    # Extract confidence scores (e.g., softmax probabilities for the primary key)
    gnn_confidence_scores = predictions.softmax(dim=1)[:, 1]

    # Combine GNN scores with heuristic scores only for valid columns
    combined_scores = {}
    for idx, col in enumerate(valid_columns):
        col_name = col  # Assuming columns is a list of column names
        combined_scores[col_name] = gnn_confidence_scores[idx].item() + heuristic_scores.get(col_name, 0)
        print(f"Combined score for '{col_name}': {combined_scores[col_name]}")  # Debug print for GNN + heuristic score

    print(f"Final combined scores for table '{table_name}': {combined_scores}")  # Debugging final combined scores

    return combined_scores
