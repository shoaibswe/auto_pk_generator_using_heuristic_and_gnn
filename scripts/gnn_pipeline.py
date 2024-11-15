#gnn_pipeline.py

import torch
from models.gnn_model import PrimaryKeyGNN

def create_column_graph(num_columns, relationships, valid_columns):
    """
    Create graph representation for GNN.
    :param num_columns: Number of valid columns in the table.
    :param relationships: List of relationships as (source, target) tuples.
    :param valid_columns: List of column names being processed.
    :return: edge_index tensor and initial features for each node.
    """
    # Map columns to node indices
    column_to_index = {col: idx for idx, col in enumerate(valid_columns)}

    edges = []
    for relationship in relationships:
        source, target = relationship[:2]  # Adjust based on your relationship data structure
        if source in column_to_index and target in column_to_index:
            edges.append((column_to_index[source], column_to_index[target]))

    if not edges:  # Handle cases with no relationships
        print("Warning: No edges found. Defaulting to self-loops.")
        edges = [(i, i) for i in range(num_columns)]  # Add self-loops to avoid empty edge_index

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    features = torch.rand((num_columns, 10))  # Random feature initialization for now
    return edge_index, features


def run_gnn_model(table_name, df, heuristic_scores, relationships):
    valid_columns = [col for col in df.columns if heuristic_scores.get(col, 0) > 0]
    if not valid_columns:
        print(f"No valid columns to process for table '{table_name}'.")
        return heuristic_scores

    if not relationships:
        print(f"No relationships found for table '{table_name}'. Adding self-loops.")
        relationships = [(col, col) for col in valid_columns]

    edge_index, features = create_column_graph(len(valid_columns), relationships, valid_columns)
    model = PrimaryKeyGNN(in_feats=10, hidden_size=20, out_feats=2)
    predictions = model(features, edge_index)

    gnn_confidence_scores = predictions.softmax(dim=1)[:, 1]
    combined_scores = {
        col: gnn_confidence_scores[idx].item() + heuristic_scores.get(col, 0)
        for idx, col in enumerate(valid_columns)
    }

    return combined_scores


