#utils.py

import pandas as pd

from sqlalchemy import create_engine

def load_table_data_as_dataframe(table_name, conn):
    """
    Load the entire table as a Pandas DataFrame using SQLAlchemy.
    """
    try:
        db_url = f"postgresql+psycopg2://{conn.info.user}:{conn.info.password}@{conn.info.host}:{conn.info.port}/{conn.info.dbname}"
        engine = create_engine(db_url)
        df = pd.read_sql(f"SELECT * FROM {table_name};", engine)
        return df
    except Exception as e:
        print(f"Error loading table {table_name} into DataFrame: {e}")
        return pd.DataFrame()
