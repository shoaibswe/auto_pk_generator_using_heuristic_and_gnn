import torch
import networkx as nx
from scripts.utils import normalized_levenshtein, jaccard_similarity

def build_virtual_node_graph(tables_data, candidates):
    """
    Constructs Graph G based on Definition 3 (Name Sim OR Value Overlap).
    """
    print("Building Virtual Node Topology...")
    
    num_nodes = len(candidates)
    edges = set()
    nx_graph = nx.Graph() 
    nx_graph.add_nodes_from(range(num_nodes))

    # Build edges based on name similarity and value overlap (Jaccard)
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            table_a, key_a, _ = candidates[i]
            table_b, key_b, _ = candidates[j]
            
            # Skip intra-table edges for 'overlap' check (redundant)
            if table_a == table_b:
                # Hierarchy Edge (Subset relationship)
                set_a = set(key_a)
                set_b = set(key_b)
                if set_a.issubset(set_b) or set_b.issubset(set_a):
                    edges.add((i, j))
                    nx_graph.add_edge(i, j)
                continue

            # --- SIGNAL 1: Name Similarity (Levenshtein) ---
            str_a = "_".join(key_a)
            str_b = "_".join(key_b)
            if normalized_levenshtein(str_a, str_b) > 0.75:
                edges.add((i, j))
                edges.add((j, i))
                nx_graph.add_edge(i, j)
                continue # Optimization: If names match, skip expensive data check

            # --- SIGNAL 2: Value Overlap (Jaccard) ---
            # Paper Definition 3 requirement: "value overlap > tau"
            # We only check if both are single columns for efficiency, 
            # or strictly first columns of composites.
            col_a = key_a[0]
            col_b = key_b[0]
            
            df_a = tables_data[table_a]
            df_b = tables_data[table_b]
            
            # Threshold tau = 0.1 (Loose overlap is enough for structural signal)
            if jaccard_similarity(df_a[col_a], df_b[col_b]) > 0.1:
                edges.add((i, j))
                edges.add((j, i))
                nx_graph.add_edge(i, j)

    if not edges:
        edge_index = torch.tensor([[i for i in range(num_nodes)], 
                                   [i for i in range(num_nodes)]], dtype=torch.long)
    else:
        edge_list = list(edges)
        edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    
    # PageRank for Centrality Feature
    try:
        pagerank = nx.pagerank(nx_graph, alpha=0.85)
        centrality_scores = [pagerank.get(i, 0) for i in range(num_nodes)]
    except:
        centrality_scores = [0.0] * num_nodes

    print(f"Graph Constructed: {num_nodes} nodes, {edge_index.size(1)} edges.")
    return edge_index, centrality_scores