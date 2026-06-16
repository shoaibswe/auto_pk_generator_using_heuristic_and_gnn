"""Convert PostgreSQL-flavored SQL dump (CREATE TABLE + INSERT INTO) to per-table CSVs.

Handles:
  * CREATE TABLE <name> (...) blocks to learn column lists.
  * INSERT INTO <table> (cols) VALUES (...), (...), ...; (multi-row form).
  * INSERT INTO <table> VALUES (...);             (no col list -> uses CREATE TABLE order).
  * Both quoted and unquoted identifiers.
  * SQL string literals with embedded quotes (escaped via doubled '').
  * Oracle-style "Insert into" (jOOQ Sakila dump) is matched case-insensitively.

Usage:
    python sql_to_csv.py <input.sql> <output_dir>
"""
from __future__ import annotations
import csv
import re
import sys
from pathlib import Path


_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\"`]?\w+[\"`]?\s*\.\s*)?[\"`]?(\w+)[\"`]?\s*\((.*?)\)\s*(?:WITHOUT\s+OIDS\s*)?;",
    re.IGNORECASE | re.DOTALL,
)


def _parse_columns(body: str) -> list[str]:
    cols: list[str] = []
    depth = 0
    buf: list[str] = []
    parts: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())

    skip_kw = {
        "primary", "foreign", "constraint", "unique", "check", "key", "index",
    }
    for line in parts:
        line = line.strip().rstrip(",")
        if not line:
            continue
        first = line.split()[0].strip('"').strip("`").lower()
        if first in skip_kw:
            continue
        col = first
        cols.append(col)
    return cols


def _tokenize_values(s: str) -> list[str]:
    """Split a single VALUES (...) tuple body into Python-string fields."""
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        # skip leading whitespace and commas
        while i < n and s[i] in " \t\n":
            i += 1
        if i >= n:
            break
        if s[i] == ",":
            i += 1
            continue
        if s[i] == "'":
            # string literal with '' escape
            j = i + 1
            buf = []
            while j < n:
                if s[j] == "'":
                    if j + 1 < n and s[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(s[j])
                j += 1
            out.append("".join(buf))
            i = j + 1
        else:
            # unquoted token: number, NULL, TRUE, FALSE, identifier, or
            # function call (e.g. string_to_array('a,b', ',')).  Consume to
            # the next top-level comma, respecting nested parens and string
            # literals.
            j = i
            depth = 0
            in_str = False
            while j < n:
                ch = s[j]
                if in_str:
                    if ch == "'":
                        if j + 1 < n and s[j + 1] == "'":
                            j += 2
                            continue
                        in_str = False
                else:
                    if ch == "'":
                        in_str = True
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    elif ch == "," and depth == 0:
                        break
                j += 1
            tok = s[i:j].strip()
            if tok.upper() == "NULL":
                out.append("")
            elif tok.upper() == "TRUE":
                out.append("t")
            elif tok.upper() == "FALSE":
                out.append("f")
            else:
                out.append(tok)
            i = j
    return out


def _split_value_tuples(payload: str) -> list[str]:
    """Given the text after `VALUES`, split into individual `( ... )` tuples,
    respecting nested parens and string literals."""
    tuples: list[str] = []
    i = 0
    n = len(payload)
    while i < n:
        # find next opening paren
        while i < n and payload[i] != "(":
            i += 1
        if i >= n:
            break
        # scan to matching close
        depth = 0
        j = i
        in_str = False
        while j < n:
            ch = payload[j]
            if in_str:
                if ch == "'":
                    if j + 1 < n and payload[j + 1] == "'":
                        j += 2
                        continue
                    in_str = False
            else:
                if ch == "'":
                    in_str = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        tuples.append(payload[i + 1:j])
                        i = j + 1
                        break
            j += 1
        else:
            break
    return tuples


def main(in_path: str, out_dir: str) -> int:
    src_path = Path(in_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = src_path.read_text(encoding="utf-8", errors="ignore")
    # strip line comments
    text = re.sub(r"--[^\n]*", "", text)

    # 1) Learn column lists from CREATE TABLE.
    table_cols: dict[str, list[str]] = {}
    for m in _CREATE_RE.finditer(text):
        tbl = m.group(1).lower()
        cols = _parse_columns(m.group(2))
        if cols:
            table_cols[tbl] = cols

    print(f"learned columns for {len(table_cols)} tables", file=sys.stderr)

    # 2) Walk the file and stream INSERT INTO statements.  Statements may span
    # multiple lines (multi-row VALUES), so we collect by `;`.
    rows_by_table: dict[str, list[list[str]]] = {t: [] for t in table_cols}
    insert_re = re.compile(
        r"INSERT\s+INTO\s+(?:[\"`]?\w+[\"`]?\s*\.\s*)?[\"`]?(\w+)[\"`]?"
        r"(?:\s*\(([^)]+)\))?\s*VALUES\s*",
        re.IGNORECASE,
    )
    pos = 0
    n = len(text)
    while pos < n:
        m = insert_re.search(text, pos)
        if not m:
            break
        tbl = m.group(1).lower()
        col_list = m.group(2)
        if col_list:
            cols = [c.strip().strip('"').strip("`").lower() for c in col_list.split(",")]
        else:
            cols = table_cols.get(tbl)
        if cols is None:
            # unknown table; skip to next statement
            pos = m.end()
            continue
        # Find statement terminator (matching trailing semicolon outside strings).
        j = m.end()
        in_str = False
        depth = 0
        while j < n:
            ch = text[j]
            if in_str:
                if ch == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        j += 2
                        continue
                    in_str = False
            else:
                if ch == "'":
                    in_str = True
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                elif ch == ";" and depth == 0:
                    break
            j += 1
        payload = text[m.end():j]
        # parse all (...) tuples
        for tup in _split_value_tuples(payload):
            vals = _tokenize_values(tup)
            if len(vals) != len(cols):
                continue
            # Map to full table_cols order if cols is a subset
            full_cols = table_cols.get(tbl, cols)
            row_dict = dict(zip(cols, vals))
            row = [row_dict.get(c, "") for c in full_cols]
            rows_by_table.setdefault(tbl, []).append(row)
        pos = j + 1

    # 3) Emit CSVs (lowercase table_name.csv, lowercase columns).
    written = 0
    for tbl, cols in table_cols.items():
        rows = rows_by_table.get(tbl, [])
        if not rows:
            continue
        out_path = out / f"{tbl}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in rows:
                w.writerow(r)
        written += 1
        print(f"  {tbl}.csv  rows={len(rows)} cols={len(cols)}", file=sys.stderr)
    print(f"wrote {written} CSVs to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python sql_to_csv.py <input.sql> <output_dir>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
