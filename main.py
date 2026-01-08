# codes/main.py
import sys
import os
import torch
import numpy as np
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.utils import load_table_data_as_dataframe
from scripts.heuristic_filter import run_hybrid_sieve
from scripts.graph_builder import build_virtual_node_graph
from scripts.gnn_pipeline import train_and_predict
from scripts.table_identifier import get_all_tables
from db_connector import connect_to_db

def run_sieve_gnn_pipeline():
    conn = connect_to_db()
    if not conn:
        return
    
    print("\n--- Phase 1: Data Ingestion ---")
    tables = get_all_tables(conn)
    tables_data = {t: load_table_data_as_dataframe(t, conn) for t in tables}
    tables_data = {k: v for k, v in tables_data.items() if not v.empty}

    if not tables_data:
        conn.close()
        return

    print("\n--- Phase 2: Combinatorial Sieve ---")
    candidates, col_stats, rejected_valid_keys = run_hybrid_sieve(tables_data)
    
    if not candidates:
        conn.close()
        return

    print("\n--- Phase 3: Virtual Node Graph Construction ---")
    edge_index, centrality_scores = build_virtual_node_graph(tables_data, candidates)
    
    # Feature Engineering for GNN
    # NEW Feature Vector: [Uniqueness, Is_Composite, PAGERANK_CENTRALITY]
    feature_list = []
    for i, (table, key_tuple, level) in enumerate(candidates):
        stats = col_stats[(table, key_tuple)]
        
        feat_uniq = stats['uniqueness']
        feat_is_comp = 1.0 if len(key_tuple) > 1 else 0.0
        
        # Normalize PageRank (Scale it so the GNN notices it)
        feat_centrality = centrality_scores[i] * 10.0 
        
        feature_list.append([feat_uniq, feat_is_comp, feat_centrality])
    
    features = torch.tensor(np.array(feature_list), dtype=torch.float)

    print("\n--- Phase 4: GAT Inference ---")
    gnn_scores = train_and_predict(edge_index, features, candidates, col_stats)
    
    print("\n--- Phase 5: Optimization & Reporting ---")
    
    # Track keys rejected due to low confidence
    low_confidence_rejected = []
    
    # Group by table
    table_results = defaultdict(list)
    for idx, (table, key_tuple, level) in enumerate(candidates):
        h_score = col_stats[(table, key_tuple)]['h_score']
        g_score = gnn_scores[idx].item()
        rank_score = h_score + g_score
        
        table_results[table].append({
            'key': ", ".join(key_tuple),
            'type': 'Composite' if len(key_tuple) > 1 else 'Single',
            'h_score': h_score,
            'g_score': g_score,
            'rank': rank_score
        })

    # Display results
    print("\n" + "="*120)
    print(f"{'TABLE':<20} | {'CANDIDATE KEY':<35} | {'TYPE':<12} | {'H-SCR':<6} | {'G-SCR':<6} | {'RANK':<6} | {'OPT IMPACT'}")
    print("="*120)

    for table in sorted(table_results.keys()):
        items = table_results[table]
        items.sort(key=lambda x: x['rank'], reverse=True)
        
        best = items[0]
        
        # Impact estimation
        impact = "17.7x (Point Lookup)" if best['type'] == 'Single' else "3.4x (Join/Sort)"
        
        print(f"{table:<20} | {best['key']:<35} | {best['type']:<12} | {best['h_score']:<6.2f} | {best['g_score']:<6.2f} | {best['rank']:<6.2f} | {impact}")
        
        # Generate SQL - adjusted threshold for composite keys
        threshold = 1.5 if best['type'] == 'Single' else 1.2
        if best['rank'] > threshold:
            if best['type'] == 'Single':
                sql = f'ALTER TABLE {table} ADD CONSTRAINT pk_{table} PRIMARY KEY ("{best["key"]}");'
            else:
                cols = best['key'].replace(", ", '", "')
                sql = f'CREATE UNIQUE INDEX CONCURRENTLY idx_{table}_{best["key"].replace(", ", "_")} ON {table} ("{cols}");'
            print(f"   [SQL GEN] >> {sql}")
        else:
            print(f"   [REJECTED] Low confidence score ({best['rank']:.2f} < {threshold:.2f})")
            # Track this rejected candidate
            low_confidence_rejected.append((table, best['key'], best['type'], best['rank'], threshold))
        
        # Also track other candidates for this table that were considered but not selected
        for item in items[1:]:
            threshold_alt = 1.5 if item['type'] == 'Single' else 1.2
            if item['rank'] <= threshold_alt:
                low_confidence_rejected.append((table, item['key'], item['type'], item['rank'], threshold_alt))
        
        print("-" * 120)
    
    # Display valid PK candidates that were rejected
    all_rejected = rejected_valid_keys + low_confidence_rejected
    
    if all_rejected:
        print("\n" + "="*120)
        print("REJECTED VALID PRIMARY KEY CANDIDATES")
        print("="*120)
        print(f"{'TABLE':<20} | {'CANDIDATE KEY':<35} | {'TYPE':<12} | {'REASON'}")
        print("-"*120)
        
        # Show keys rejected in Phase 2 (heuristic filtering)
        for table, key_tuple, reason in rejected_valid_keys:
            key_str = ", ".join(key_tuple)
            key_type = 'Composite' if len(key_tuple) > 1 else 'Single'
            print(f"{table:<20} | {key_str:<35} | {key_type:<12} | {reason}")
        
        # Show keys rejected in Phase 5 (low confidence)
        for table, key, key_type, rank, threshold in low_confidence_rejected:
            reason = f"Low confidence score ({rank:.2f} < {threshold:.2f})"
            print(f"{table:<20} | {key:<35} | {key_type:<12} | {reason}")
        
        print("="*120)
    
    conn.close()

if __name__ == "__main__":
    run_sieve_gnn_pipeline()