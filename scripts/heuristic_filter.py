# heuristic_filter.py
import re
import pandas as pd

def is_column_unique(df, column_name):
    return df[column_name].nunique() == len(df)

def is_column_non_null(df, column_name):
    return df[column_name].isnull().sum() == 0

def is_sequential(df, column_name):
    sorted_vals = df[column_name].dropna().sort_values().values
    if sorted_vals.dtype.kind in 'iuf':
        diffs = sorted_vals[1:] - sorted_vals[:-1]
        return (diffs == 1).all()
    return False

def is_uuid(df, column_name):
    import re
    uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', re.IGNORECASE)
    return df[column_name].dropna().apply(lambda x: bool(uuid_pattern.match(str(x)))).all()


def heuristic_filtering(table_name, df, snapshots=None):
    heuristic_scores = {}
    candidate_columns = []

    for col in df.columns:
        score = 0
        if is_column_unique(df, col):
            score += 20
        if is_column_non_null(df, col):
            score += 10
        if is_sequential(df, col):
            score += 10
        if is_uuid(df, col):
            score += 5
        if snapshots and has_column_changed(snapshots[0], snapshots[1], col):
            score -= 20

        heuristic_scores[col] = score
        if score > 30:  # Threshold to consider as a strong candidate
            candidate_columns.append(col)

    print(f"Heuristic scores for table '{table_name}': {heuristic_scores}")
    return heuristic_scores, candidate_columns


def has_column_changed(snapshot1, snapshot2, column_name):
    return not snapshot1[column_name].equals(snapshot2[column_name])
