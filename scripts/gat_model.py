# codes/scripts/gat_model.py
# GAT-based (Graph Attention Network) model for primary key prediction

import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

class PrimaryKeyGAT(torch.nn.Module):
    def __init__(self, in_feats, hidden_size, out_feats, heads=2):
        super(PrimaryKeyGAT, self).__init__()
        # GAT Layer 1: Multi-head attention
        self.conv1 = GATConv(in_feats, hidden_size, heads=heads, dropout=0.2)
        
        # GAT Layer 2: Aggregation
        self.conv2 = GATConv(hidden_size * heads, out_feats, heads=1, concat=False, dropout=0.2)

    def forward(self, x, edge_index):
        # x: [num_nodes, in_feats]
        # edge_index: [2, num_edges]
        
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv2(x, edge_index)
        
        return F.log_softmax(x, dim=1)