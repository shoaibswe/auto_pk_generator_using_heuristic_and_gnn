# codes/scripts/validation.py

def validate_candidate(table, col, df, model_conf):
    """
    Stricter validation to match Paper's 95% claim.
    """
    total = len(df)
    unique = df[col].nunique()
    is_unique = (unique == total)
    
    # 1. Semantic Guardrail: Even if unique, reject low confidence
    # This stops "quantity" (which GNN should hate) from becoming a key
    if is_unique and model_conf < 0.8: 
        return "Reject (Semantic Mismatch)"

    # 2. The "Enforce" Logic
    if is_unique and model_conf >= 0.8:
        return "Enforce Primary Key"
    
    # 3. The "Dirty Key" Logic (Paper Claim)
    error_rate = (total - unique) / total
    if model_conf > 0.95 and error_rate < 0.01:
        return "Flag Dirty Key (Review)"
        
    return "Reject"