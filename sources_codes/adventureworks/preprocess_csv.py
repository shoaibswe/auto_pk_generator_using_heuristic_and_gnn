"""Preprocess AdventureWorks CSV dumps for the Sieve-GNN pipeline.

The CSVs shipped with morenoh149/postgresDBSamples are tab-separated and
HEADERLESS — the column order is implied by the CREATE TABLE statements in
install.sql.  Sieve-GNN consumes pandas-default CSVs (comma-separated, header
in row 1).  This script:

  1. Parses every "CREATE TABLE Name(...)" block in sql_ddl.sql and records the
     ordered column-name list for that table.
  2. For every *.csv file in data/, finds the matching table (case-insensitive),
     re-emits the file with a header row and proper comma quoting.

It writes in-place; original tab-separated files are kept under data/_raw/.
"""
from __future__ import annotations
import csv
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DDL = HERE / "sql_ddl.sql"
DATA = HERE / "data"
RAW_BACKUP = DATA / "_raw"


_BLOCK_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?(\w+)[\"`]?\s*\(([^;]*?)\)\s*(?=CREATE\s+TABLE|CREATE\s+SCHEMA|;|\Z)",
    re.IGNORECASE | re.DOTALL,
)
# A "column" line starts with an identifier (optionally quoted) followed by a
# type or a CONSTRAINT/CHECK/PRIMARY/FOREIGN keyword.  We reject the keyword
# variants.
_RESERVED = {"CONSTRAINT", "CHECK", "PRIMARY", "FOREIGN", "UNIQUE", "KEY"}


def parse_columns(ddl_text: str) -> dict[str, list[str]]:
    text = re.sub(r"--[^\n]*", "", ddl_text)
    out: dict[str, list[str]] = {}
    for m in _BLOCK_RE.finditer(text):
        table = m.group(1).lower()
        body = m.group(2)
        cols: list[str] = []
        # split on commas at paren-depth 0
        depth = 0
        buf: list[str] = []
        parts: list[str] = []
        for ch in body:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        parts.append("".join(buf))
        for raw in parts:
            line = raw.strip()
            if not line:
                continue
            head = line.split()[0].strip("\"`,")
            if head.upper() in _RESERVED:
                continue
            cols.append(head)
        if cols:
            out[table] = cols
    return out


def main() -> int:
    if not DDL.exists():
        print(f"missing {DDL}", file=sys.stderr)
        return 1
    if not DATA.exists():
        print(f"missing {DATA}", file=sys.stderr)
        return 1

    columns = parse_columns(DDL.read_text(encoding="utf-8", errors="ignore"))
    print(f"[ddl] parsed {len(columns)} table column lists from {DDL.name}")

    RAW_BACKUP.mkdir(exist_ok=True)
    converted = 0
    skipped: list[str] = []
    mismatched: list[str] = []

    for csv_path in sorted(DATA.glob("*.csv")):
        table_key = csv_path.stem.lower()
        cols = columns.get(table_key)
        if cols is None:
            skipped.append(csv_path.name)
            continue

        raw_target = RAW_BACKUP / csv_path.name
        if not raw_target.exists():
            shutil.copy2(csv_path, raw_target)

        # Read TSV (no header) from the backup, write CSV (with header) in place.
        with raw_target.open("r", encoding="utf-8", errors="replace", newline="") as fin:
            reader = csv.reader(fin, delimiter="\t", quoting=csv.QUOTE_NONE)
            tmp = csv_path.with_suffix(".csv.tmp")
            with tmp.open("w", encoding="utf-8", newline="") as fout:
                writer = csv.writer(fout, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(cols)
                first_row_cols = None
                rows_written = 0
                for row in reader:
                    if first_row_cols is None:
                        first_row_cols = len(row)
                        if first_row_cols != len(cols):
                            mismatched.append(
                                f"{csv_path.name}: DDL has {len(cols)} cols, CSV has {first_row_cols}"
                            )
                    writer.writerow(row)
                    rows_written += 1
        tmp.replace(csv_path)
        converted += 1

    print(f"[done] converted {converted} CSVs")
    if skipped:
        print(f"[warn] {len(skipped)} CSV files had no matching CREATE TABLE: {skipped[:8]}{'...' if len(skipped) > 8 else ''}")
    if mismatched:
        print(f"[warn] {len(mismatched)} column-count mismatches (data still written, header column count = DDL):")
        for m in mismatched[:20]:
            print(f"   {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
