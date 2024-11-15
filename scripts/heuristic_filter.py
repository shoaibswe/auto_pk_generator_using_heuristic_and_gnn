# heuristic_filter.py

from scripts.foreign_key_scoring import calculate_foreign_key_score


def is_column_unique(df, col):
    """Check if a column contains only unique values."""
    return df[col].is_unique


def is_column_non_null(df, col):
    """Check if a column does not contain any NULL values."""
    return not df[col].isnull().any()


def is_sequential(df, col):
    """Check if a column contains sequential integer values."""
    try:
        col_data = df[col].dropna().astype(int)
        return (col_data.diff().dropna() == 1).all()
    except (ValueError, TypeError):
        return False


def is_uuid(df, column_name):
    """Check if a column contains UUID-like values."""
    import re

    uuid_pattern = re.compile(
        r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE
    )
    return (
        df[column_name].dropna().apply(lambda x: bool(uuid_pattern.match(str(x)))).all()
    )


def exclude_invalid_columns(df, valid_columns):
    """Exclude columns that do not meet primary key characteristics."""
    return [
        col
        for col in valid_columns
        if is_column_non_null(df, col) and is_column_unique(df, col)
    ]


def heuristic_filtering_with_priority(table_name, df, df_b_tables):
    """
    Combined heuristic filtering with non-null checks, foreign key scoring, and cross-table validation.
    :param table_name: Name of the table being processed.
    :param df: DataFrame for the current table.
    :param df_b_tables: List of tuples containing DataFrames and columns from other tables.
                        Example: [(df_b1, "column_b1"), (df_b2, "column_b2")]
    :return: Heuristic scores with combined adjustments.
    """
    heuristic_scores = {}
    primary_key_characteristics = set()

    for col in df.columns:
        score = 0

        # Exclude columns with NULL values
        if not is_column_non_null(df, col):
            continue

        # Add uniqueness check
        if is_column_unique(df, col):
            score += 20  # Boost for uniqueness
            primary_key_characteristics.add(col)

        # Add sequential scoring (e.g., ID-like pattern)
        if is_sequential(df, col):
            score += 10  # Boost for sequential integer values

        # Check if the column contains UUIDs
        if is_uuid(df, col):
            score += 10  # Boost for UUID-like patterns

        # Add foreign key relationship scoring
        for df_b, column_b in df_b_tables:
            fk_score = calculate_foreign_key_score(df, col, df_b, column_b)
            score += fk_score  # Add foreign key score if applicable

        heuristic_scores[col] = score

    # Exclude invalid columns based on primary key characteristics
    valid_columns = exclude_invalid_columns(df, heuristic_scores.keys())

    return heuristic_scores, valid_columns
