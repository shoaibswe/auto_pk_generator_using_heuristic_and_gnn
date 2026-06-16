# AdventureWorks (Microsoft OLTP) — Sieve-GNN integration

Real public OLTP schema published by Microsoft. The PostgreSQL port used here
is Lorin Thwaits' `Adventureworks for Postgres` mirror, which exposes the
same 68 base tables, 5 schemas, and 90 declared foreign-key constraints as
the original SQL Server `AdventureWorks2014_OLTP` distribution.

## Files

| File                           | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `install.sql`                  | Source DDL as fetched (unmodified)              |
| `sql_ddl.sql`                  | Ground-truth DDL consumed by `eval.ground_truth`|
| `data/` (initially empty)      | Where `*.csv` table dumps must be placed        |
| `schema_final.json` (pending)  | Sieve-GNN predicted schema (write after run)    |
| `relationships.csv` (pending)  | Sieve-GNN predicted FK edges (write after run)  |

`sql_ddl.sql` is a verbatim copy of `install.sql`; the parser
(`eval/ground_truth.py`) reads `ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY`
and `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ... REFERENCES` blocks
directly, so no transformation is required.

## Ground-truth size (parsed)

* tables with declared PK : **68**
* FK relations             : **90**  (89 unary, 1 composite arity-2)
* FK components            : **91**

(Verify with `python -m eval.ground_truth adventureworks/sql_ddl.sql`.)

## Obtaining the CSV data

The DDL ships in this repo; the row-level CSV dumps are ~25 MB compressed and
must be fetched manually (they are not committed). Two reproducible options:

### Option A — official CSV dump bundled with the Postgres mirror

```bash
# from paper_final/adventureworks/
curl -L -o aw_csv.zip https://github.com/morenoh149/postgresDBSamples/archive/refs/heads/master.tar.gz
# extract just the CSV files from the adventureworks/ subdir
mkdir -p data
tar -xzf aw_csv.zip --strip-components=2 \
    -C data --wildcards 'postgresDBSamples-master/adventureworks/*.csv'
```

### Option B — load via psql and export

```bash
createdb adventureworks
psql -d adventureworks -f sql_ddl.sql
# then for each schema-qualified table:
psql -d adventureworks -c "\copy person.address TO 'data/address.csv' CSV HEADER"
# ... repeat for the other 67 tables
```

After CSVs are in `data/`, run the Sieve-GNN notebook
(`paper_final/dvdrental/Sieve_GNN.ipynb` is the reference; adjust `CONFIG`
paths to point at this directory) and write `schema_final.json` /
`relationships.csv` here. Then re-run:

```bash
python -m eval.score_artefacts adventureworks
python -m eval.ind_baseline    adventureworks
```

## Source

* DDL mirror: https://github.com/morenoh149/postgresDBSamples (MIT)
* Original schema: Microsoft AdventureWorks2014 OLTP, public-domain sample
