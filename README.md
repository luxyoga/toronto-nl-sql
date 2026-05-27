# Toronto Data Explorer

Ask plain English questions about Toronto building permits and neighbourhood demographics — get instant SQL answers.

![App screenshot](screenshot.png)

## Tech stack

- **[Streamlit](https://streamlit.io/)** — UI and app framework
- **[DuckDB](https://duckdb.org/)** — embedded analytical database
- **[Claude](https://www.anthropic.com/claude) (claude-sonnet-4-6)** — natural language → SQL and query explanation
- **[Toronto Open Data](https://open.toronto.ca/)** — Building Permits and Neighbourhood Profiles datasets via CKAN API
- **[pandas](https://pandas.pydata.org/)** — query result handling

## How it works

When you submit a question, the app sends it to Claude along with a system prompt that contains the live database schema and a few-shot example mapping a sample question to its correct SQL. Claude returns a raw SQL string (no markdown, no explanation) which is executed directly against a local DuckDB file. A second Claude call then takes that SQL and produces a one- or two-sentence plain English explanation of what the query does, shown below the results. The schema is injected into the prompt at request time so the model always sees accurate column names and types without any hardcoding.

## Live app

[toronto-nl-sql.streamlit.app](https://toronto-nl-sql.streamlit.app)

## Run locally

**Requirements:** Python 3.11+, an Anthropic API key.

```bash
git clone https://github.com/luxyoga/toronto-nl-sql.git
cd toronto-nl-sql

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Start the app:

```bash
streamlit run app.py
```

On first launch the app downloads the Toronto Open Data CSVs (~230k building permits, 2,383 neighbourhood profile rows) and loads them into `toronto.duckdb`. This takes about a minute. Subsequent launches are instant.

## Design decisions

### Why DuckDB instead of a traditional database?

DuckDB runs in-process with zero server setup — no Postgres instance to provision, no connection strings to manage. It reads CSVs directly with full SQL support, handles 230k-row analytical queries in milliseconds, and persists to a single file that travels with the project. For a read-heavy app with a fixed dataset it's a better fit than spinning up a client-server database.

### Why inject the schema dynamically into the prompt?

Hardcoding table and column names into a system prompt means the prompt silently drifts whenever the dataset changes. By calling `DESCRIBE` on the live DuckDB tables at request time, the model always sees the exact column names and types that exist in the database — including any future datasets added to the app. It also keeps the schema authoritative in one place (the database) rather than duplicated across code and prompts.
