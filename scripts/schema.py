import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "toronto.duckdb"


def get_schema(con: duckdb.DuckDBPyConnection | None = None) -> str:
    close = con is None
    if con is None:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        parts = []
        for table in tables:
            cols = con.execute(f"DESCRIBE {table}").fetchall()
            if table == "neighbourhood_profiles":
                # First 5 cols are metadata; remaining cols are neighbourhood names.
                # Show metadata cols explicitly, then summarise neighbourhood cols.
                meta_cols = cols[:5]
                neighbourhood_names = [c[0] for c in cols[5:]]
                col_lines = "\n".join(f"  {c[0]} {c[1]}" for c in meta_cols)
                col_lines += (
                    f"\n  -- Plus {len(neighbourhood_names)} neighbourhood columns (one per neighbourhood):\n"
                    f"  -- {', '.join(neighbourhood_names[:10])}, ... and {len(neighbourhood_names) - 10} more"
                )
            else:
                col_lines = "\n".join(f"  {c[0]} {c[1]}" for c in cols)
            parts.append(f"TABLE {table}:\n{col_lines}")
        return "\n\n".join(parts)
    finally:
        if close:
            con.close()


if __name__ == "__main__":
    print(get_schema())
