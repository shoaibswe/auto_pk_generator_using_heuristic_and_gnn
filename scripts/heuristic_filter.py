import re
import itertools

def is_date_type(col_name):
    name = str(col_name).lower().strip()
    keywords = ['created', 'updated', 'modified', 'deleted', 'date', 'time', 'timestamp', 'ts', '_at']
    return any(word in name for word in keywords)

def get_priority_level(col_name):
    name = str(col_name).lower().strip()
    if name == 'id': return 1
    if re.search(r'(_id|_key|uuid|pk|code|num|serial|no)$', name): return 2
    return 3

def run_hybrid_sieve(tables_data):
    """
    Combinatorial Sieve implementing the Apriori Pruning property.
    """
    candidates = [] 
    col_stats = {}
    rejected_valid_keys = []  # Track valid PK candidates that were filtered out

    for table, df in tables_data.items():
        if df.empty: continue
        total_rows = len(df)
        
        # --- PHASE 1: Single Column (k=1) ---
        for col in df.columns:
            if df[col].nunique() == total_rows and not df[col].isnull().any():
                if is_date_type(col):
                    # Valid PK but rejected due to being date/timestamp
                    rejected_valid_keys.append((table, (col,), "Date/Timestamp column (filtered by heuristic)"))
                    continue

                level = get_priority_level(col)
                h_score = 1.0 if level == 1 else (0.85 if level == 2 else 0.6)
                
                candidates.append((table, (col,), level))
                col_stats[(table, (col,))] = {'uniqueness': 1.0, 'level': level, 'h_score': h_score}

        # --- PHASE 2: Composite Check (k=2 to k=3) ---
        comp_ingredients = [c for c in df.columns if df[c].nunique() > 1]
        
        # UPDATE: Changed range to (2, 4) to support max_k=3 as per Theorem 1
        for k in range(2, 4): 
            found_k = 0
            for combo in itertools.combinations(comp_ingredients, k):
                if found_k > 5: break # Pruning heuristic to limit explosion
                
                # Check Uniqueness
                if not df.duplicated(subset=list(combo)).any() and not df[list(combo)].isnull().any().any():
                    
                    # Synergy Scoring
                    id_count = sum(1 for c in combo if get_priority_level(c) <= 2)
                    id_bonus = id_count * 0.15
                    has_date = any(is_date_type(c) for c in combo)
                    date_bonus = 0.15 if has_date and id_count > 0 else 0.0
                    
                    final_h_score = min(0.85, 0.40 + id_bonus + date_bonus)
                    
                    candidates.append((table, combo, 4))
                    col_stats[(table, combo)] = {'uniqueness': 1.0, 'level': 4, 'h_score': final_h_score}
                    found_k += 1
    
    return candidates, col_stats, rejected_valid_keys