# foreign_key_scoring.py

from scripts.utils import (
    is_column_unique,
    all_values_exist_in_b,
    b_only_contains_a_values,
)


def calculate_foreign_key_score(df_a, column_a, df_b, column_b):
    """
    Calculate an additional score for a column in table A being a foreign key to table B.
    :param df_a: DataFrame for table A.
    :param column_a: Column name in table A.
    :param df_b: DataFrame for table B.
    :param column_b: Column name in table B.
    :return: Additional score for the column.
    """
    score = 0

    # Check if the column in df_a is unique
    if is_column_unique(df_a, column_a):
        score += 10  # Boost for uniqueness

        # Check if all values in df_a[column_a] exist in df_b[column_b]
        if all_values_exist_in_b(df_a, column_a, df_b, column_b):
            score += 10  # Boost for all values matching in B

            # Check if df_b[column_b] only contains values from df_a[column_a]
            if b_only_contains_a_values(df_a, column_a, df_b, column_b):
                score += 10  # Boost for strict match

    return score


def cross_table_fk_check(df_a, column_a, df_b, column_b):
    """
    Check if column in table A satisfies a cross-table foreign key relationship with table B.
    :param df_a: DataFrame for table A.
    :param column_a: Column name in table A.
    :param df_b: DataFrame for table B.
    :param column_b: Column name in table B.
    :return: Score for cross-table foreign key validation.
    """
    score = 0

    # Check if column A is unique in table A
    if not df_a[column_a].is_unique:
        return 0  # No score if column A is not unique

    # Check if all values in column A exist in column B
    if set(df_a[column_a]).issubset(set(df_b[column_b])):
        score += 20  # Boost for column A values matching in column B

        # Check if column B contains no other values than column A
        if set(df_b[column_b]).issubset(set(df_a[column_a])):
            score += 10  # Extra boost for strict match

    return score
