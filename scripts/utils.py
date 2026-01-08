import pandas as pd
import numpy as np
import hashlib
import Levenshtein

def load_table_data_as_dataframe(table_name, conn):
    """Loads table data. For large tables, consider LIMIT or sampling."""
    query = f"SELECT * FROM {table_name} LIMIT 10000;" 
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error loading table '{table_name}': {e}")
        return pd.DataFrame()

def normalized_levenshtein(s1, s2):
    """Computes normalized Levenshtein similarity (Name Similarity)."""
    if not s1 or not s2: return 0.0
    maxlen = max(len(s1), len(s2))
    if maxlen == 0: return 1.0
    dist = Levenshtein.distance(s1, s2)
    return 1.0 - (dist / maxlen)

def jaccard_similarity(series_a, series_b):
    """
    Computes Jaccard Index (Value Overlap) for Definition 3.
    J(A,B) = |A n B| / |A u B|
    """
    set_a = set(series_a.dropna())
    set_b = set(series_b.dropna())
    
    if not set_a or not set_b:
        return 0.0
        
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    
    return intersection / union if union > 0 else 0.0