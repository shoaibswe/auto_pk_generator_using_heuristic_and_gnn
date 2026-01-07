import torch
from collections import defaultdict
from .utils import compute_minhash_signature, normalized_levenshtein

def build_lsh_graph(tables_data, candidates, sim_threshold=0.5):
    """
    Nodes are now Keys (which can be single columns or tuples).
    """
    print("Building Graph (Topology Discovery)...")
    
    col_to_idx = {candidate: i for i, candidate in enumerate(candidates)}
    num_nodes = len(candidates)
    
    edges = set()
    
    # Simple pairwise check for the demo (LSH is complex for composite tuples)
    # We check: Does Table A's candidate appear in Table B?
    
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i == j: continue
            
            table_a, key_a, level_a = candidates[i]
            table_b, key_b, level_b = candidates[j]
            
            # Constraint: We only link columns of same dimension (single-to-single)
            # Composite FK detection is O(N^3), skipping for efficiency in demo
            if len(key_a) != len(key_b): continue
            
            # Check Similarity (Lexical or Value Overlap)
            # 1. Name Similarity (e.g., customer_id vs cust_id)
            name_sim = normalized_levenshtein("_".join(key_a), "_".join(key_b))
            
            if name_sim > 0.6:
                edges.add((i, j))
                
    if not edges:
        edge_index = torch.tensor([[i, i] for i in range(num_nodes)], dtype=torch.long).t()
    else:
        edge_index = torch.tensor(list(edges), dtype=torch.long).t().contiguous()

    print(f"Graph constructed: {num_nodes} nodes, {edge_index.size(1)} edges.")
    return edge_index, col_to_idx