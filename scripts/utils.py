# codes/scripts/utils.py

import pandas as pd
import numpy as np
import hashlib
import Levenshtein

def load_table_data_as_dataframe(table_name, conn):
    """Loads table data. For large tables, consider LIMIT or sampling for LSH."""
    query = f"SELECT * FROM {table_name} LIMIT 10000;" # Sample for performance
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error loading table '{table_name}': {e}")
        return pd.DataFrame()

def get_sieve_score(df, col):
    """
    Computes S(c) = alpha * uniqueness + beta * non_null
    alpha=0.5, beta=0.5
    """
    total = len(df)
    if total == 0: return 0.0
    
    null_count = df[col].isnull().sum()
    unique_count = df[col].nunique()
    
    uniqueness = unique_count / total
    non_nullness = 1.0 - (null_count / total)
    
    # Paper formula: Equal weight or tuned
    score = 0.5 * uniqueness + 0.5 * non_nullness
    return score, uniqueness, non_nullness

def compute_minhash_signature(values, num_perm=128):
    """
    Generates MinHash signature for a set of values.
    """
    # Create a deterministic seed based on values
    str_values = [str(v).encode('utf8') for v in values if pd.notnull(v)]
    if not str_values:
        return np.full(num_perm, np.inf)
    
    # We simulate MinHash using simple hashing for demo purposes.
    # In prod, use 'datasketch' library.
    signature = np.full(num_perm, np.inf)
    
    for v in str_values:
        # Simple hash function simulation for k permutations
        # h_k(x) = (hash(x) + k * hash(x)) % prime
        base_hash = int(hashlib.md5(v).hexdigest(), 16)
        for k in range(num_perm):
            h_k = (base_hash + k * 13) % 4294967291 # Large prime
            if h_k < signature[k]:
                signature[k] = h_k
                
    return signature

def get_semantic_embedding(header_text):
    """
    Returns FastText embedding for a column header.
    Placeholder: Returns random vector or deterministic hash vector.
    """
    # In production: load_model('cc.en.300.bin').get_word_vector(header_text)
    # Here: Deterministic random vector based on string hash
    np.random.seed(int(hashlib.md5(header_text.encode()).hexdigest(), 16) % (2**32))
    return np.random.rand(300) # 300-dim vector

def normalized_levenshtein(s1, s2):
    """Computes normalized Levenshtein similarity."""
    if not s1 or not s2: return 0.0
    maxlen = max(len(s1), len(s2))
    if maxlen == 0: return 1.0
    dist = Levenshtein.distance(s1, s2)
    return 1.0 - (dist / maxlen)