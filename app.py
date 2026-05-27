import os
import sys
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import anthropic
import duckdb
import pandas as pd

load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from schema import get_schema
from query_engine import nl_to_sql, run_query, MODEL
from load_data import setup_database

DB_PATH = Path(__file__).parent / "toronto.duckdb"


@st.cache_resource(show_spinner=False)
def _ensure_database() -> None:
    setup_database()

EXAMPLES = [
    "How many building permits were issued in 2024?",
    "What are the top 5 permit types by count?",
    "Which street has the most building permits?",
    "What is the population of the Annex neighbourhood?",
    "How many new house permits were issued per year?",
]



def explain_sql(sql: str, client: anthropic.Anthropic) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                f"Explain in one or two plain English sentences what this SQL query does. "
                f"No technical jargon, no markdown.\n\n{sql}"
            ),
        }],
    )
    return response.content[0].text.strip()


def main():
    st.set_page_config(page_title="Toronto Permit Pulse", layout="wide")
    st.title("Toronto Permit Pulse")

    if not DB_PATH.exists():
        with st.spinner("Setting up database for first time, this may take a minute..."):
            _ensure_database()
    else:
        _ensure_database()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Sidebar
    with st.sidebar:
        st.header("Database Schema")
        st.code(get_schema(), language="sql")

    # Example questions
    st.subheader("Example questions")
    cols = st.columns(len(EXAMPLES))
    for i, example in enumerate(EXAMPLES):
        if cols[i].button(example, use_container_width=True):
            st.session_state["question"] = example

    st.divider()

    with st.form("query_form"):
        question = st.text_input(
            "Ask a question about Toronto data",
            key="question",
            placeholder="e.g. How many building permits were issued in 2024?",
        )
        submitted = st.form_submit_button("Submit", type="primary")

    if submitted and st.session_state.get("question", "").strip():
        st.session_state.pop("result_sql", None)
        st.session_state.pop("result_df", None)
        st.session_state.pop("result_explanation", None)
        st.session_state.pop("result_error", None)

        with st.spinner("Generating SQL..."):
            try:
                st.session_state["result_sql"] = nl_to_sql(
                    st.session_state["question"].strip(), client=client
                )
            except Exception as e:
                st.session_state["result_error"] = f"Failed to generate SQL: {e}"

        if "result_sql" in st.session_state:
            with st.spinner("Running query..."):
                try:
                    st.session_state["result_df"] = run_query(st.session_state["result_sql"])
                except Exception as e:
                    st.session_state["result_error"] = f"Query failed: {e}"

        if "result_df" in st.session_state:
            with st.spinner("Explaining query..."):
                try:
                    st.session_state["result_explanation"] = explain_sql(
                        st.session_state["result_sql"], client
                    )
                except Exception:
                    pass

    # Render results from session state (persists across rerenders)
    if "result_error" in st.session_state:
        st.error(st.session_state["result_error"])
        if "result_sql" in st.session_state:
            st.code(st.session_state["result_sql"], language="sql")
    elif "result_df" in st.session_state:
        df = st.session_state["result_df"]
        sql = st.session_state["result_sql"]

        st.subheader("Results")
        st.dataframe(df, use_container_width=True)

        if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
            st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])

        st.subheader("Generated SQL")
        st.code(sql, language="sql")

        if "result_explanation" in st.session_state:
            st.info(st.session_state["result_explanation"])


if __name__ == "__main__":
    main()
