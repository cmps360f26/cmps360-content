import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 00 - Setup the Retail Sales Lakehouse

    This notebook creates a **DuckLake** environment for a Medallion Architecture pipeline.

    | Layer | Schema | What it stores |
    | :--- | :--- | :--- |
    | **Bronze** | `bronze` | Raw extracts, as received, plus load metadata |
    | **Silver** | `silver` | Clean, standardized, validated, enriched tables |
    | **Gold** | `gold` | Business-ready aggregates and KPIs (Key Performance Indicators) |
    | **Quarantine** | `quarantine` | Rows that failed Silver quality checks |

    Run the notebooks **in order**, then repeat 01–03 when you change `run_date`:

    1. `00_setup.py` — once (recreating the lakehouse)
    2. `01_bronze.py` — ingest `data/<run_date>/`
    3. `02_silver.py` — clean and validate
    4. `03_gold.py` — build KPIs

    Valid processing dates: `2026-09-17` (first load), `2026-09-18`, `2026-09-19`, `2026-09-20`.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## DuckDB vs DuckLake

    | | **DuckDB** | **DuckLake** |
    | :--- | :--- | :--- |
    | Role | SQL engine (parse, plan, compute) | Lakehouse storage layer |
    | This session | In-memory compute | Catalog + Parquet files on disk |
    | Persistence | Lost when the notebook stops | Kept in `lakehouse/` |

    **DuckLake features used in this series**

    - `ATTACH ... (TYPE DUCKLAKE, DATA_PATH ...)` — create/open the catalog
    - `CREATE SCHEMA` — Bronze / Silver / Gold / Quarantine
    - ACID `BEGIN` / `COMMIT` with `set_commit_message`
    - Snapshots via `ducklake_snapshots('sales_lake')`

    **DuckDB features** (compute, not storage): `read_csv`, `try_cast`, `MERGE INTO` for incremental Silver loads, and data cleaning using SQL.
    """)
    return


@app.cell
def _():
    import duckdb
    import marimo as mo

    return duckdb, mo


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Reset the local lakehouse

    The next cell **deletes** `lakehouse/` so this notebook always starts from an empty catalog.

    Re-run `00_setup.py` only when you want a fresh pipeline. It will remove previous Bronze, Silver, and Gold tables.
    """)
    return


@app.cell
def _(duckdb):
    # Recreate the lakehouse folder. This is local classroom setup, not a DuckLake API.
    import os
    import shutil

    try:
        duckdb.sql("DETACH DATABASE IF EXISTS sales_lake;")
    except Exception as error:
        print(f"Detach skipped: {error}")

    DATA_LAKE_DIR = "lakehouse"
    CATALOG_DB = os.path.join(DATA_LAKE_DIR, "sales_lake_catalog.db")
    DATA_DIRECTORY = os.path.join(DATA_LAKE_DIR, "sales_lake_data")

    if os.path.exists(DATA_LAKE_DIR):
        shutil.rmtree(DATA_LAKE_DIR)
    os.makedirs(DATA_DIRECTORY, exist_ok=True)

    # POSIX paths so SQL strings work on Windows and macOS/Linux.
    catalog_db_path = os.path.abspath(CATALOG_DB).replace("\\", "/")
    data_directory_path = os.path.abspath(DATA_DIRECTORY).replace("\\", "/")

    print(f"Fresh lakehouse created at {os.path.abspath(DATA_LAKE_DIR)}")
    print(f"Catalog (DuckLake metadata): {catalog_db_path}")
    print(f"Data path (Parquet files):     {data_directory_path}")
    return catalog_db_path, data_directory_path


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Attach DuckLake as `sales_lake`

    `INSTALL` & `LOAD` **DuckLake** extension, then `ATTACH` a catalog file and a data folder.

    - Metadata (schemas, tables, snapshots) → `sales_lake_catalog.db`
    - Table files (Parquet) → `sales_lake_data/`
    """)
    return


@app.cell
def _(catalog_db_path, data_directory_path, mo):
    _df = mo.sql(
        f"""
        INSTALL ducklake;
        LOAD ducklake;

        ATTACH '{catalog_db_path}' AS sales_lake (
            TYPE DUCKLAKE,
            DATA_PATH '{data_directory_path}'
        );

        USE sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Create Medallion schemas

    `CREATE SCHEMA` **in DuckLake**, not in the temporary memory database.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE SCHEMA IF NOT EXISTS bronze;
        CREATE SCHEMA IF NOT EXISTS silver;
        CREATE SCHEMA IF NOT EXISTS gold;
        CREATE SCHEMA IF NOT EXISTS quarantine;

        CALL sales_lake.set_commit_message(
            'admin',
            'Create bronze, silver, gold, and quarantine schemas'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Validate the catalog

    Expected: schemas `bronze`, `silver`, `gold`, `quarantine`, and `main`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE catalog_name = 'sales_lake'
        ORDER BY schema_name;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- DuckLake snapshot log (not available on a plain DuckDB table)
        SELECT
            snapshot_id,
            CAST(snapshot_time AS VARCHAR) AS snapshot_time,
            author,
            commit_message
        FROM ducklake_snapshots('sales_lake');
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### 5. Releasing the lakehouse catalog with DETACH DATABASE ensures all file handles are closed and the catalog can safely be used in another notebook.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Release the lakehouse catalog so it can be used in another notebook
        Use memory;
        -- Detaching sales_lake releases its catalog and associated file handles.
        DETACH DATABASE IF EXISTS sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### What to do next

    Open `01_bronze.py` and set:

    ```python
    run_date = "2026-09-17"
    ```

    Use the same `run_date` in `02_silver.py` and `03_gold.py`. After a successful full run for 17 Sep, change it to `2026-09-18` and re-run 01–03 to practice incremental loads.

    Do **not** re-run this setup notebook between those dates, or you will wipe Bronze history.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Summary

    - Created a DuckLake catalog named `sales_lake`.
    - Separated metadata (`sales_lake_catalog.db`) from Parquet data (`sales_lake_data/`).
    - Added four schemas that match the Medallion layers plus quarantine.
    - Recorded a commit message on the schema-creation snapshot.

    **Learned:** DuckDB runs the SQL; DuckLake stores the lakehouse. Schemas are the folders of the catalog. The next notebook loads raw files into `bronze`.
    """)
    return


if __name__ == "__main__":
    app.run()
