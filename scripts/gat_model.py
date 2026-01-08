import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv

class SieveGNN(torch.nn.Module):
    def __init__(self, in_feats, hidden_size, out_feats, heads=4):
        super(SieveGNN, self).__init__()
        # 
        # The GAT layer aggregates features (Uniqueness, Centrality) from neighbors.
        
        # Layer 1: Multi-head attention (Capture structural context)
        self.conv1 = GATConv(in_feats, hidden_size, heads=heads, dropout=0.2)
        
        # Layer 2: Aggregation (Final classification)
        self.conv2 = GATConv(hidden_size * heads, out_feats, heads=1, concat=False, dropout=0.2)

    def forward(self, x, edge_index):
        # x: [num_nodes, 3] (Uniqueness, Is_Composite, PageRank)
        
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        
        x = F.dropout(x, p=0.2, training=self.training)
        x = self.conv2(x, edge_index)
        
        return F.log_softmax(x, dim=1)