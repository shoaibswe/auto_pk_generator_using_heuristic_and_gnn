# gnn_model.py

import torch
from torch_geometric.nn import GCNConv
import torch.nn.functional as F


class PrimaryKeyGNN(torch.nn.Module):
    def __init__(self, in_feats, hidden_size, out_feats):
        super(PrimaryKeyGNN, self).__init__()
        self.conv1 = GCNConv(in_feats, hidden_size)
        self.conv2 = GCNConv(hidden_size, out_feats)
        self.norm = torch.nn.BatchNorm1d(hidden_size)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = self.norm(x)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return F.log_softmax(x, dim=1)
