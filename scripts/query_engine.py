import os
import duckdb
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from schema import get_schema

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(__file__).parent.parent / "toronto.duckdb"
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT_TEMPLATE = """\
You are a SQL expert. Convert natural language questions into valid DuckDB SQL queries.

Rules:
- Return ONLY the raw SQL query. No explanation, no markdown, no code fences.
- Use exact column and table names from the schema below.
- For date filtering on DATE columns, use YEAR(col) or date literals.
- Queries must be read-only SELECT statements.

Schema:
{schema}

neighbourhood_profiles table structure:
- Each ROW is a demographic characteristic (e.g. 'Population, 2016', 'Median household income').
- The Characteristic column contains the row label.
- Every other column is a neighbourhood name (e.g. "Annex", "Rosedale-Moore Park").
- To look up a value for a specific neighbourhood, SELECT that neighbourhood's column WHERE Characteristic matches the label.
- neighbourhood names with spaces or special characters must be quoted with double quotes in SQL.

Examples:
Q: How many building permits were issued in 2024?
A: SELECT COUNT(*) FROM building_permits WHERE YEAR(ISSUED_DATE) = 2024

Q: What is the population of the Annex neighbourhood?
A: SELECT Characteristic, "Annex" FROM neighbourhood_profiles WHERE Characteristic = 'Population, 2016'
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(schema=get_schema())


def nl_to_sql(question: str, client: anthropic.Anthropic | None = None) -> str:
    if client is None:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=build_system_prompt(),
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text.strip()


def run_query(sql: str, con: duckdb.DuckDBPyConnection | None = None) -> pd.DataFrame:
    close = con is None
    if con is None:
        con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        if close:
            con.close()


def ask(question: str) -> tuple[str, pd.DataFrame]:
    sql = nl_to_sql(question)
    df = run_query(sql)
    return sql, df


if __name__ == "__main__":
    question = "How many building permits were issued in 2024?"
    print(f"Question: {question}\n")
    sql, df = ask(question)
    print(f"SQL: {sql}\n")
    print(f"Result:\n{df}")
