"""Schema-rendering helper (provided complete).

Loads the schema directly from sqlite and renders quoted CREATE TABLE
text suitable for prompt context. Identifiers are always double-quoted
so reserved-word table/column names (e.g. `order`) don't break either
the PRAGMA introspection here or the SQL the model emits later.
"""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "data" / "bird"


def db_path(db_id: str) -> Path:
    return DB_DIR / f"{db_id}.sqlite"


def _q(ident: str) -> str:
    """Double-quote a SQL identifier, escaping any embedded quotes."""
    return '"' + ident.replace('"', '""') + '"'


def _format_fk(ref_table: str | None, from_col: str | None, to_col: str | None) -> str | None:
    """Render a foreign key if SQLite exposes complete metadata for it."""
    if not ref_table or not from_col or not to_col:
        return None
    return f"  FOREIGN KEY ({_q(from_col)}) REFERENCES {_q(ref_table)}({_q(to_col)})"


def _is_textish_type(ctype: str | None) -> bool:
    ctype = (ctype or "").lower()
    if not ctype:
        return True
    return any(marker in ctype for marker in ["char", "text", "varchar", "string"])


def _should_sample_column(column: str, ctype: str | None) -> bool:
    """Sample compact categorical columns, not large free-text fields."""
    if not _is_textish_type(ctype):
        return False

    name = column.lower()
    if "id" in name or "text" in name or "body" in name or "comment" in name:
        return False
    if "title" in name or "description" in name or "display" in name:
        return False

    categorical_markers = [
        "name",
        "gender",
        "label",
        "element",
        "type",
        "status",
        "category",
        "class",
        "state",
        "city",
        "country",
        "code",
    ]
    return any(marker in name for marker in categorical_markers)


def _format_sample(value: Any, max_len: int = 40) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return repr(text)


def _question_terms(question: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", question.lower())
    quoted = [
        (single or double).lower()
        for single, double in re.findall(r"'([^']+)'|\"([^\"]+)\"", question)
    ]
    synonyms = {
        "male": ["m"],
        "female": ["f"],
        "chlorine": ["cl"],
        "carcinogenic": ["+"],
        "noncarcinogenic": ["-"],
    }

    terms: list[str] = []
    for term in [*quoted, *words]:
        if term not in terms:
            terms.append(term)
        for synonym in synonyms.get(term, []):
            if synonym not in terms:
                terms.append(synonym)
    return terms[:32]


def _matched_column_values(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    question: str,
    limit: int = 4,
) -> list[str]:
    terms = _question_terms(question)
    if not terms:
        return []
    placeholders = ", ".join("?" for _ in terms)
    rows = conn.execute(
        f"SELECT DISTINCT {_q(column)} FROM {_q(table)} "
        f"WHERE LOWER(CAST({_q(column)} AS TEXT)) IN ({placeholders}) "
        f"LIMIT {limit}",
        terms,
    ).fetchall()
    return [_format_sample(row[0]) for row in rows]


def _sample_column_values(conn: sqlite3.Connection, table: str, column: str, limit: int = 8) -> list[str]:
    frequent_rows = conn.execute(
        f"SELECT {_q(column)} FROM {_q(table)} "
        f"WHERE {_q(column)} IS NOT NULL AND CAST({_q(column)} AS TEXT) != '' "
        f"GROUP BY {_q(column)} "
        f"ORDER BY COUNT(*) DESC "
        f"LIMIT {limit}"
    ).fetchall()
    alpha_rows = conn.execute(
        f"SELECT DISTINCT {_q(column)} FROM {_q(table)} "
        f"WHERE {_q(column)} IS NOT NULL AND CAST({_q(column)} AS TEXT) != '' "
        f"ORDER BY CAST({_q(column)} AS TEXT) COLLATE NOCASE "
        f"LIMIT {limit}"
    ).fetchall()

    samples: list[str] = []
    seen: set[str] = set()
    for row in [*frequent_rows, *alpha_rows]:
        sample = _format_sample(row[0])
        if sample in seen:
            continue
        seen.add(sample)
        samples.append(sample)
    return samples[: limit * 2]


@lru_cache(maxsize=32)
def render_schema(db_id: str, question: str = "") -> str:
    path = db_path(db_id)
    if not path.exists():
        raise FileNotFoundError(f"DB {db_id} not found at {path}. Did you run scripts/load_data.py?")

    parts: list[str] = [f"-- Database: {db_id}"]
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        for t in tables:
            parts.append(f"\nCREATE TABLE {_q(t)} (")
            col_lines: list[str] = []
            text_columns: list[str] = []
            for _cid, name, ctype, notnull, _dflt, pk in conn.execute(f"PRAGMA table_info({_q(t)})"):
                line = f"  {_q(name)} {ctype}"
                if pk:
                    line += " PRIMARY KEY"
                if notnull and not pk:
                    line += " NOT NULL"
                col_lines.append(line)
                if _should_sample_column(name, ctype):
                    text_columns.append(name)
            for fk in conn.execute(f"PRAGMA foreign_key_list({_q(t)})"):
                # (id, seq, ref_table, from, to, on_update, on_delete, match)
                fk_line = _format_fk(fk[2], fk[3], fk[4])
                if fk_line is not None:
                    col_lines.append(fk_line)
            parts.append(",\n".join(col_lines))
            parts.append(");")
            for column in text_columns[:12]:
                samples = [
                    *_matched_column_values(conn, t, column, question),
                    *_sample_column_values(conn, t, column),
                ]
                samples = list(dict.fromkeys(samples))
                if samples:
                    parts.append(f"-- sample {_q(t)}.{_q(column)} values: {', '.join(samples)}")
    return "\n".join(parts)


def available_dbs() -> list[str]:
    if not DB_DIR.exists():
        return []
    return sorted(p.stem for p in DB_DIR.glob("*.sqlite"))
