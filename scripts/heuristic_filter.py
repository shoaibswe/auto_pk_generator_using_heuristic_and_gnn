import re
import itertools

def is_date_type(col_name):
    name = str(col_name).lower().strip()
    keywords = ['created', 'updated', 'modified', 'date', 'time', 'timestamp', 'ts', '_at']
    return any(word in name for word in keywords)

def get_priority_level(col_name):
    name = str(col_name).lower().strip()
    if name == 'id': return 1
    if re.search(r'(_id|_key|uuid|pk|code|num|serial)$', name): return 2
    return 3

def is_potential_fk(col_name, table_name):
    """Detects if a column is likely a Foreign Key."""
    name = str(col_name).lower().strip()
    # If it contains '_id' but isn't just 'id' or '{table}_id', it's likely an FK
    if '_id' in name or '_key' in name:
        if name != 'id' and name != f"{table_name.lower()}_id":
            return True
    return False

def run_hybrid_sieve(tables_data):
    candidates = [] 
    col_stats = {}

    for table, df in tables_data.items():
        if df.empty: continue
        total_rows = len(df)
        
        # --- PHASE 1: Single ---
        for col in df.columns:
            is_uniq = df[col].nunique() == total_rows
            not_null = not df[col].isnull().any()
            
            if is_uniq and not_null and not is_date_type(col):
                level = get_priority_level(col)
                h_score = 1.0 if level == 1 else (0.8 if level == 2 else 0.5)
                candidates.append((table, (col,), level))
                col_stats[(table, (col,))] = {
                    'uniqueness': 1.0, 'level': level, 'h_score': h_score,
                    'is_fk': is_potential_fk(col, table)
                }

        # --- PHASE 2: Composite ---
        comp_ingredients = [c for c in df.columns if df[c].nunique() > 1]
        for combo in itertools.combinations(comp_ingredients, 2):
            if not df.duplicated(subset=list(combo)).any() and not df[list(combo)].isnull().any().any():
                h_score = 0.45 
                candidates.append((table, combo, 4))
                col_stats[(table, combo)] = {
                    'uniqueness': 1.0, 'level': 4, 'h_score': h_score,
                    'is_fk': any(is_potential_fk(c, table) for c in combo)
                }
                if len([c for c in candidates if c[0] == table]) > 8: break

    return candidates, col_stats