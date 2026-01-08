import torch
from scripts.gat_model import SieveGNN

def train_and_predict(edge_index, features, candidates, col_stats):
    # Features: [Uniqueness, Is_Composite, PageRank] -> 3 dimensions
    model = SieveGNN(in_feats=3, hidden_size=32, out_feats=2, heads=4)
    model.eval()
    
    # In a real scenario, you would load state_dict here
    # model.load_state_dict(torch.load('sieve_gnn_weights.pth'))
    
    with torch.no_grad():
        out = model(features, edge_index)
        # Get probability of Class 1 (Is Primary Key)
        base_probs = out.softmax(dim=1)[:, 1]

    final_scores = []
    for i, (table, key_tuple, level) in enumerate(candidates):
        # Start with the GNN's structural confidence
        prob = base_probs[i].item()
        
        # Heuristic Injection (Weak Supervision)
        # If GNN is uncertain (0.4-0.6), lean on the Heuristic Tier
        if 0.4 < prob < 0.6:
            tier_scores = {1: 0.90, 2: 0.80, 3: 0.50, 4: 0.50}
            prob = (prob + tier_scores.get(level, 0.5)) / 2
            
        final_scores.append(prob)

    return torch.tensor(final_scores)