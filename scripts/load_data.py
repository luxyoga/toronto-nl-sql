import requests
import pandas as pd
import duckdb
from pathlib import Path

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = Path(__file__).parent.parent / "toronto.duckdb"

DATASETS = {
    "building-permits-active-permits": "building_permits.csv",
    "neighbourhood-profiles": "neighbourhood_profiles.csv",
}

# CSV filename -> DuckDB table name
TABLE_NAMES = {
    "building_permits.csv": "building_permits",
    "neighbourhood_profiles.csv": "neighbourhood_profiles",
}


def get_csv_resource(package_name: str) -> str | None:
    url = f"{CKAN_BASE}/api/3/action/package_show"
    resp = requests.get(url, params={"id": package_name}, timeout=30)
    resp.raise_for_status()
    resources = resp.json()["result"]["resources"]
    for r in resources:
        if r.get("format", "").upper() == "CSV":
            return r["url"]
    return None


def download(resource_url: str, dest: Path) -> None:
    print(f"  Downloading {resource_url}")
    with requests.get(resource_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        dest.write_bytes(r.content)
    df = pd.read_csv(dest, low_memory=False)
    print(f"  Saved {dest.name}: {len(df):,} rows x {len(df.columns)} cols")


def load_to_duckdb() -> None:
    print(f"\nLoading CSVs into DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))
    for filename, table in TABLE_NAMES.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            print(f"  Skipping {filename} (not found)")
            continue
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv('{csv_path}', "
            f"header=true, delim=',', quote='\"', escape='\"', strict_mode=false, null_padding=true)"
        )
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE {table}").fetchall())
        print(f"  {table}: {count:,} rows x {cols} cols")

    print("\nTest queries:")
    row = con.execute(
        "SELECT PERMIT_NUM, PERMIT_TYPE, STATUS, ISSUED_DATE FROM building_permits LIMIT 1"
    ).fetchone()
    print(f"  building_permits sample: {row}")

    row = con.execute(
        "SELECT * FROM neighbourhood_profiles LIMIT 1"
    ).fetchone()
    print(f"  neighbourhood_profiles sample (first 4 cols): {row[:4]}")

    con.close()


def main():
    DATA_DIR.mkdir(exist_ok=True)
    for package, filename in DATASETS.items():
        dest = DATA_DIR / filename
        if dest.exists():
            print(f"\nSkipping {filename} (already downloaded)")
            continue
        print(f"\nFetching {package}")
        url = get_csv_resource(package)
        if url is None:
            print(f"  No CSV resource found for {package}")
            continue
        download(url, dest)

    load_to_duckdb()


if __name__ == "__main__":
    main()
