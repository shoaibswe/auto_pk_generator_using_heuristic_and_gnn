"""Parse PK / FK ground truth from a SQL DDL file.

Returns:

    pks           : dict[str, list[str]]
        table -> list of PK columns
    fk_components : list[tuple[str, str, str, str]]
        All FK column-pair components, including columns belonging to
        composite FOREIGN KEY clauses.
    fk_unary      : list[tuple[str, str, str, str]]
        Only unary FK components, i.e. entries originating from single-column
        FOREIGN KEY clauses.
    fk_relations  : list[tuple[str, tuple[str, ...], str, tuple[str, ...]]]
        Full FK relations at their declared arity.
"""
from __future__ import annotations
import re
from pathlib import Path


_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?(\w+)[\"`]?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_PK_INLINE_RE = re.compile(r"^\s*[\"`]?(\w+)[\"`]?\s+[^,]*?PRIMARY\s+KEY", re.IGNORECASE)
_PK_BLOCK_RE = re.compile(r"PRIMARY\s+KEY\s*\(([^)]+)\)", re.IGNORECASE)
_FK_BLOCK_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[\"`]?(\w+)[\"`]?\s*\(([^)]+)\)",
    re.IGNORECASE,
)
_FK_INLINE_RE = re.compile(
    r"^\s*[\"`]?(\w+)[\"`]?\s+[^,]*?REFERENCES\s+[\"`]?(\w+)[\"`]?\s*\(\s*[\"`]?(\w+)[\"`]?\s*\)",
    re.IGNORECASE,
)

# ALTER TABLE [ONLY] [schema.]table ADD [CONSTRAINT "name"] PRIMARY KEY (cols)
# Handles AdventureWorks (multi-line, schema-qualified), Sakila and Northwind
# (single-line; Northwind also omits the target column list, defaulting to PK).
_ALTER_PK_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:[\"`]?\w+[\"`]?\s*\.\s*)?[\"`]?(\w+)[\"`]?\s+"
    r"ADD\s+(?:CONSTRAINT\s+[\"`]?[\w]+[\"`]?\s+)?"
    r"PRIMARY\s+KEY\s*\(([^)]+)\)",
    re.IGNORECASE | re.DOTALL,
)
# ALTER TABLE [ONLY] [schema.]table ADD [CONSTRAINT "name"] FOREIGN KEY (cols)
#                                                          REFERENCES [schema.]tgt(cols)
_ALTER_FK_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:[\"`]?\w+[\"`]?\s*\.\s*)?[\"`]?(\w+)[\"`]?\s+"
    r"ADD\s+(?:CONSTRAINT\s+[\"`]?[\w]+[\"`]?\s+)?"
    r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*"
    r"REFERENCES\s+(?:[\"`]?\w+[\"`]?\s*\.\s*)?[\"`]?(\w+)[\"`]?"
    r"(?:\s*\(([^)]+)\))?",
    re.IGNORECASE | re.DOTALL,
)


def _split_cols(s: str) -> list[str]:
    return [c.strip().strip('"').strip("`") for c in s.split(",") if c.strip()]


def parse_ddl(ddl_path):
    text = Path(ddl_path).read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"--[^\n]*", "", text)

    pks: dict[str, list[str]] = {}
    fk_components: list[tuple[str, str, str, str]] = []
    fk_unary: list[tuple[str, str, str, str]] = []
    fk_relations: list[tuple[str, tuple[str, ...], str, tuple[str, ...]]] = []

    for m in _CREATE_RE.finditer(text):
        table = m.group(1).lower()
        body = m.group(2)

        pk_block = _PK_BLOCK_RE.search(body)
        if pk_block:
            pks[table] = [c.lower() for c in _split_cols(pk_block.group(1))]
        else:
            for line in body.splitlines():
                im = _PK_INLINE_RE.match(line)
                if im:
                    pks.setdefault(table, []).append(im.group(1).lower())

        # block-level FK: arity is len(src_cols)
        for fm in _FK_BLOCK_RE.finditer(body):
            src_cols = [c.lower() for c in _split_cols(fm.group(1))]
            tgt_table = fm.group(2).lower()
            tgt_cols = [c.lower() for c in _split_cols(fm.group(3))]
            arity = len(src_cols)
            fk_relations.append((table, tuple(src_cols), tgt_table, tuple(tgt_cols)))
            for sc, tc in zip(src_cols, tgt_cols):
                fk_components.append((table, sc, tgt_table, tc))
                if arity == 1:
                    fk_unary.append((table, sc, tgt_table, tc))

        # inline FK is always unary.  Skip lines that are actually block-style
        # CONSTRAINT ... FOREIGN KEY ... REFERENCES clauses (already handled
        # above) -- otherwise the regex captures the leading keyword
        # ("CONSTRAINT" / "FOREIGN") as the source column.
        _SKIP_INLINE = re.compile(r"\b(CONSTRAINT|FOREIGN\s+KEY)\b", re.IGNORECASE)
        for line in body.splitlines():
            if _SKIP_INLINE.search(line):
                continue
            fim = _FK_INLINE_RE.match(line)
            if fim:
                src_col = fim.group(1).lower()
                # Defensive: also reject any reserved word that slipped through.
                if src_col in {"constraint", "foreign", "primary", "unique", "check"}:
                    continue
                tup = (table, src_col, fim.group(2).lower(), fim.group(3).lower())
                fk_components.append(tup)
                fk_unary.append(tup)
                fk_relations.append((table, (tup[1],), tup[2], (tup[3],)))

    # ------------------------------------------------------------------
    # ALTER TABLE constraint statements (AdventureWorks, Sakila, Northwind).
    # Run against the same comment-stripped text, independently of any
    # CREATE TABLE matches above so it works even when the CREATE TABLE
    # blocks use vendor-specific syntax we cannot fully parse.
    # ------------------------------------------------------------------
    seen_relations = {(t, sc, tt, tc) for (t, sc, tt, tc) in fk_components}
    for m in _ALTER_PK_RE.finditer(text):
        tbl = m.group(1).lower()
        cols = [c.lower() for c in _split_cols(m.group(2))]
        if tbl and cols and tbl not in pks:
            pks[tbl] = cols
    for m in _ALTER_FK_RE.finditer(text):
        src_tbl = m.group(1).lower()
        src_cols = [c.lower() for c in _split_cols(m.group(2))]
        tgt_tbl = m.group(3).lower()
        tgt_cols_raw = m.group(4)
        if tgt_cols_raw:
            tgt_cols = [c.lower() for c in _split_cols(tgt_cols_raw)]
        else:
            # PostgreSQL: REFERENCES <tbl> with no column list defaults to the
            # target table's primary key.  Resolve from previously-parsed PKs.
            tgt_cols = list(pks.get(tgt_tbl, []))
        if not (src_tbl and tgt_tbl and src_cols and tgt_cols):
            continue
        if len(src_cols) != len(tgt_cols):
            continue
        arity = len(src_cols)
        rel = (src_tbl, tuple(src_cols), tgt_tbl, tuple(tgt_cols))
        if rel not in {(t, sc, tt, tc) for (t, sc, tt, tc) in fk_relations}:
            fk_relations.append(rel)
        for sc, tc in zip(src_cols, tgt_cols):
            tup = (src_tbl, sc, tgt_tbl, tc)
            if tup in seen_relations:
                continue
            seen_relations.add(tup)
            fk_components.append(tup)
            if arity == 1:
                fk_unary.append(tup)

    return pks, fk_components, fk_unary, fk_relations


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("usage: python -m eval.ground_truth <path/to/sql_ddl.sql>")
        sys.exit(1)
    pks, fk_components, fk_unary, fk_relations = parse_ddl(sys.argv[1])
    print(json.dumps({
        "pks": pks,
        "fk_components": fk_components,
        "fk_unary": fk_unary,
        "fk_relations": fk_relations,
    }, indent=2))

