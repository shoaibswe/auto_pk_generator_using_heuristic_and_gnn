import sys
import os
import torch
import numpy as np
from collections import defaultdict
from db_connector import connect_to_db

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scripts.utils import load_table_data_as_dataframe
from scripts.heuristic_filter import run_hybrid_sieve
from scripts.graph_builder import build_lsh_graph
from scripts.gnn_pipeline import train_and_predict
from scripts.table_identifier import get_all_tables

def display_ranked_results():
    conn = connect_to_db()
    if not conn: return
    
    tables = get_all_tables(conn)
    tables_data = {t: load_table_data_as_dataframe(t, conn) for t in tables if not load_table_data_as_dataframe(t, conn).empty}

    candidates, col_stats = run_hybrid_sieve(tables_data)
    if not candidates: return

    # GNN structural validation
    edge_index, _ = build_lsh_graph(tables_data, candidates)
    feature_list = []
    for table, key_tuple, level in candidates:
        stats = col_stats[(table, key_tuple)]
        feature_list.append([stats['uniqueness'], (4 - level) / 3.0, 1.0 if len(key_tuple) > 1 else 0.0])
    
    features = torch.tensor(np.array(feature_list), dtype=torch.float)
    conf_scores = train_and_predict(edge_index, features, candidates, col_stats)

    table_results = defaultdict(list)
    for idx, (table, key_tuple, level) in enumerate(candidates):
        stats = col_stats[(table, key_tuple)]
        
        # Metadata Flags
        is_fk = "FK" if stats.get('is_fk') else ""
        is_uniq = "U" # By definition of reaching here
        is_imp = "!" if level <= 2 else ""
        properties = f"[{is_uniq}{is_imp}{' '+is_fk if is_fk else ''}]"

        table_results[table].append({
            'key': ", ".join(key_tuple),
            'level': level,
            'props': properties,
            'h_score': stats['h_score'],
            'gnn_score': conf_scores[idx].item(),
            'rank': stats['h_score'] + conf_scores[idx].item()
        })

    # Display Output
    print("\n" + "="*155)
    print(f"{'TABLE':<20} | {'PRIORITY':<10} | {'PROPS':<8} | {'TYPE':<15} | {'CANDIDATE COLS':<45} | {'HEUR':<6} | {'GNN':<6} | {'RANK':<6}")
    print("="*155)

    for table in sorted(table_results.keys()):
        results = sorted(table_results[table], key=lambda x: x['rank'], reverse=True)

        for rank, item in enumerate(results[:5]):
            label = "PRIMARY" if rank == 0 else f"ALT {rank}"
            type_map = {1: "ID (Direct)", 2: "ID (Semantic)", 3: "Single", 4: "Composite"}
            
            print(f"{table:<20} | {label:<10} | {item['props']:<8} | {type_map[item['level']]:<15} | {item['key']:<45} | {item['h_score']:.2f} | {item['gnn_score']:.2f} | {item['rank']:.2f}")
        print("-" * 155)

    conn.close()

if __name__ == "__main__":
    display_ranked_results()