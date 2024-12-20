# table_identifier.py


def get_all_tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
        )
        return [row[0] for row in cur.fetchall()]


def get_foreign_key_relationships(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(
            f"""
        SELECT kcu.column_name AS source_column,
               ccu.table_name AS target_table,
               ccu.column_name AS target_column
        FROM information_schema.key_column_usage AS kcu
        JOIN information_schema.constraint_column_usage AS ccu
        ON kcu.constraint_name = ccu.constraint_name
        WHERE kcu.table_schema = 'public' AND kcu.table_name = '{table_name}';
        """
        )
        return [(rel[0], rel[2]) for rel in cur.fetchall()]


def has_primary_key(table_name, conn):
    with conn.cursor() as cur:
        cur.execute(
            f"""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = '{table_name}'
              AND constraint_type = 'PRIMARY KEY'
        );
        """
        )
        return cur.fetchone()[0]
