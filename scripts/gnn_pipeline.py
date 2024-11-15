# gnn_pipeline.py

import torch
from models.gnn_model import PrimaryKeyGNN


def create_column_graph(num_columns, relationships, valid_columns):
    column_to_index = {col: idx for idx, col in enumerate(valid_columns)}
    edges = [(column_to_index[src], column_to_index[tgt]) for src, tgt in relationships]

    if not edges:
        print("Warning: No edges found. Defaulting to self-loops.")
        edges = [(i, i) for i in range(num_columns)]

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    features = torch.rand((num_columns, 10))  # Random feature initialization
    return edge_index, features


def run_gnn_model(table_name, df, heuristic_scores, relationships):
    valid_columns = [col for col in df.columns if heuristic_scores.get(col, 0) > 0]
    if not valid_columns:
        print(f"No valid columns to process for table '{table_name}'.")
        return heuristic_scores

    edge_index, features = create_column_graph(
        len(valid_columns), relationships, valid_columns
    )

    model = PrimaryKeyGNN(in_feats=10, hidden_size=20, out_feats=2)
    model.eval()

    with torch.no_grad():
        predictions = model(features, edge_index)

    gnn_confidence_scores = predictions.softmax(dim=1)[:, 1]

    combined_scores = {
        col: gnn_confidence_scores[idx].item() + heuristic_scores.get(col, 0)
        for idx, col in enumerate(valid_columns)
    }

    return combined_scores
