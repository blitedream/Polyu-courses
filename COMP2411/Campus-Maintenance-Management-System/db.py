import os
from contextlib import contextmanager
from typing import Any, Iterable, List, Tuple

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def get_db_config() -> dict:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "ww050701"),
        "database": os.getenv("DB_NAME", "cmms"),
    }


@contextmanager
def get_connection():
    cfg = get_db_config()
    conn = mysql.connector.connect(**cfg)
    try:
        yield conn
    finally:
        conn.close()


def execute(query: str, params: Tuple[Any, ...] | None = None) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or tuple())
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected


def executemany(query: str, param_rows: Iterable[Tuple[Any, ...]]) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(query, list(param_rows))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        return affected


def fetch_all(query: str, params: Tuple[Any, ...] | None = None) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or tuple())
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        cur.close()
        return columns, rows


def fetch_one(query: str, params: Tuple[Any, ...] | None = None) -> Tuple[List[str], Tuple[Any, ...] | None]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or tuple())
        columns = [desc[0] for desc in cur.description] if cur.description else []
        row = cur.fetchone()
        cur.close()
        return columns, row


def describe_table(table_name: str) -> List[Tuple[str, str, str, str, str, str]]:
    # Returns tuples like (Field, Type, Null, Key, Default, Extra)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"DESCRIBE `{table_name}`")
        rows = cur.fetchall()
        cur.close()
        return rows


def get_tables() -> List[str]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        rows = [r[0] for r in cur.fetchall()]
        cur.close()
        return rows


