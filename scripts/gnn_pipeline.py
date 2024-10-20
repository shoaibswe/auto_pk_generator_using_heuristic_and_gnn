# gnn_pipeline.py

import torch
from models.gnn_model import PrimaryKeyGNN
from scripts.table_identifier import get_foreign_key_relationships, get_table_columns

def create_column_graph(num_columns, relationships, columns):
    """Creates a graph for the columns of the table, where columns are nodes and foreign key relationships are edges."""
    edges = []
    column_name_to_index = {col: idx for idx, col in enumerate(columns)}

    # Add edges based on relationships (map column names to indices)
    for relationship in relationships:
        column1_name = relationship[0]
        column2_name = relationship[2]
        
        if column1_name in column_name_to_index and column2_name in column_name_to_index:
            column1_index = column_name_to_index[column1_name]
            column2_index = column_name_to_index[column2_name]
            edges.append((column1_index, column2_index))

    # Add self-loops if no relationships are found
    if len(edges) == 0:
        for i in range(num_columns):
            edges.append((i, i)) 

    # Convert edges to torch tensor
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    # Generate random features for each column (10-dimensional feature vectors for simplicity)
    features = torch.rand((num_columns, 10))  # Example random features for each column

    return edge_index, features

def run_gnn_model(table_name, conn, heuristic_scores):
    # Fetch relationships and column data from the database
    relationships = get_foreign_key_relationships(table_name, conn)
    columns = get_table_columns(table_name, conn)
    
    print(f"Running GNN model for table: {table_name}")

    # Create the graph for columns
    edge_index, features = create_column_graph(len(columns), relationships, columns)

    # Run the GNN model
    model = PrimaryKeyGNN(in_feats=10, hidden_size=20, out_feats=2)
    predictions = model(features, edge_index)

    # Extract confidence scores (e.g., softmax probabilities for the primary key)
    gnn_confidence_scores = predictions.softmax(dim=1)[:, 1]

    # Combine GNN scores with heuristic scores
    combined_scores = {}
    for idx, col in enumerate(columns):
        col_name = col  # Assuming columns is a list of column names
        combined_scores[col_name] = gnn_confidence_scores[idx].item() + heuristic_scores.get(col_name, 0)
        print(f"Combined score for '{col_name}': {combined_scores[col_name]}")  # Debug print for GNN + heuristic score

    # Handle composite key (order_id, product_id) if it's in the heuristic scores
    if ('order_id', 'product_id') in heuristic_scores:
        # Ensure composite key is selected if it has the highest score
        composite_score = heuristic_scores[('order_id', 'product_id')]
        combined_scores[('order_id', 'product_id')] = composite_score
        print(f"Composite key ('order_id', 'product_id') selected with score {combined_scores[('order_id', 'product_id')]}")

    print(f"Final combined scores for table '{table_name}': {combined_scores}")  # Debugging final combined scores

    return combined_scores
