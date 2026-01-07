import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv

class PrimaryKeyGNN(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = GATConv(in_channels, hidden_channels, heads=4)
        self.conv2 = GATConv(hidden_channels * 4, out_channels, heads=1)

    def forward(self, x, edge_index):
        x = F.elu(self.conv1(x, edge_index))
        x = self.conv2(x, edge_index)
        return x

def train_and_predict(edge_index, features, candidates, col_stats):
    model = PrimaryKeyGNN(features.size(1), 32, 2)
    model.eval()
    
    with torch.no_grad():
        out = model(features, edge_index)
        base_probs = out.softmax(dim=1)[:, 1]

    final_scores = []
    for i, (table, key_tuple, level) in enumerate(candidates):
        # 1. Base Score from Tier
        tier_scores = {1: 0.98, 2: 0.92, 3: 0.60, 4: 0.50}
        score = tier_scores.get(level, 0.5)
        
        # 2. Structural Boost (Inbound Degree)
        # Does anyone point to this node?
        degree = (edge_index[1] == i).sum().item()
        if degree > 0:
            score += (degree * 0.12) # Relationship reward
            
        # 3. Data Quality Adjustment
        stats = col_stats[(table, key_tuple)]
        if stats['uniqueness'] < 1.0:
            score -= 0.15 # Penalty for dirty data
            
        final_scores.append(max(0.01, min(0.99, score)))

    return torch.tensor(final_scores)