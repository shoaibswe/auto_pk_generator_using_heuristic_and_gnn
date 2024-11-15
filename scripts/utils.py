# utils.py

import pandas as pd


def load_table_data_as_dataframe(table_name, conn):
    query = f"SELECT * FROM {table_name};"
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error loading table '{table_name}': {e}")
        return pd.DataFrame()


# helpers.py


def is_column_unique(df, column):
    return df[column].is_unique


def all_values_exist_in_b(df_a, column_a, df_b, column_b):
    return set(df_a[column_a]).issubset(set(df_b[column_b]))


def b_only_contains_a_values(df_a, column_a, df_b, column_b):
    return set(df_b[column_b]).issubset(set(df_a[column_a]))


def is_column_non_null(df, col):
    return not df[col].isnull().any()


def is_sequential(df, col):
    try:
        col_data = df[col].dropna().astype(int)
        return (col_data.diff().dropna() == 1).all()
    except (ValueError, TypeError):
        return False


def is_uuid(df, column_name):
    import re

    uuid_pattern = re.compile(
        r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.IGNORECASE
    )
    return (
        df[column_name].dropna().apply(lambda x: bool(uuid_pattern.match(str(x)))).all()
    )
