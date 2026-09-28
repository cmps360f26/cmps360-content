import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 01 - Bronze Layer: Ingest Raw Extracts

    Bronze stores source CSVs **as-is** without any cleaning.

    What this notebook adds (minimal change):

    | Column | Meaning |
    | :--- | :--- |
    | `_load_date` | Processing date (`run_date`) — which extract folder was loaded |
    | `_ingested_at` | When this notebook wrote the rows |
    | `_source_file` | Path of the CSV file |

    Re-running the same `run_date` deletes that day's Bronze rows and loads them again (idempotent daily load). Other dates stay in Bronze.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 0. Processing Date & Dual Execution Modes

    This notebook supports two execution modes:
    1. **Interactive Exploration**: Run cell-by-cell in Marimo (`marimo edit 01_bronze.py`). Defaults to `"2026-09-17"`.
    2. **Programmatic Pipeline**: Run non-interactively via `run_pipeline.py` or terminal (`python 01_bronze.py 2026-09-18`).

    | `run_date` | Extract type |
    | :--- | :--- |
    | `2026-09-17` | First (full) load |
    | `2026-09-18` … `2026-09-20` | Incremental batches (new and changed rows) |
    """)
    return


@app.cell
def _():
    import os
    import re
    import sys

    import marimo as mo

    # Processing date configuration:
    # 1. Priority: Command-line argument (e.g., python 01_bronze.py 2026-09-18)
    # 2. Priority: Environment variable (e.g., RUN_DATE=2026-09-18)
    # 3. Fallback: Default date for interactive Marimo sessions ("2026-09-17")
    cli_date = next(
        (arg for arg in sys.argv[1:] if re.match(r"^\d{4}-\d{2}-\d{2}$", arg)), None
    )
    run_date = cli_date or os.getenv("RUN_DATE", "2026-09-17")

    root_dir = ".." if os.path.exists(os.path.join("..", "run_pipeline.py")) else "."
    project_root = os.path.abspath(os.path.join(root_dir, ".."))
    extract_dir = os.path.abspath(os.path.join(project_root, "landing_zone", "sales_data", run_date)).replace("\\", "/")
    catalog_db_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError(
            "DuckLake catalog not found. Please run 00_setup.py and 00.1_bronze_schema.py first."
        )
    if not os.path.isdir(extract_dir):
        raise FileNotFoundError(
            f"No extract folder for run_date={run_date}. Expected {extract_dir}"
        )

    print(f"run_date     = {run_date}")
    print(f"extract_dir  = {extract_dir}")
    print(f"catalog      = {catalog_db_path}")
    print(f"data files path = {data_directory_path}")
    return catalog_db_path, data_directory_path, extract_dir, mo, run_date


@app.cell
def _(mo):
    mo.md("""
    ## 1. Attach the existing DuckLake catalog

    Connect to the catalog created in setup.
    """)
    return


@app.cell
def _(catalog_db_path, data_directory_path, mo):
    _df = mo.sql(
        f"""
        INSTALL ducklake;
        LOAD ducklake;

        USE memory;
        DETACH DATABASE IF EXISTS sales_lake;

        ATTACH '{catalog_db_path}' AS sales_lake (
            TYPE DUCKLAKE,
            DATA_PATH '{data_directory_path}',
            OVERRIDE_DATA_PATH TRUE
        );

        USE sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Explore the raw CSV files using DuckDB

    `read_csv` is a **DuckDB** function. `all_varchar = true` keeps dirty values such as `bad_price` and `1,500.00` as text so Bronze does not hide quality problems.
    """)
    return


@app.cell
def _(extract_dir, mo):
    _df = mo.sql(
        f"""
        SELECT *
        FROM read_csv('{extract_dir}/customers.csv', header = true, all_varchar = true);
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Load each extract file for `run_date`

    ### Key Data Engineering Patterns:
    1. **Idempotent Ingestion**:
       - `DELETE FROM bronze.<table> WHERE _load_date = DATE '{run_date}'` ensures that if this notebook is re-executed for the same date, old rows are replaced cleanly without creating duplicate records.
    2. **Audit Metadata Enrichment**:
       - `_load_date`: Partition date identifying which daily batch this row belongs to.
       - `_ingested_at`: Real-time timestamp recording when the data entered the lakehouse.
       - `_source_file`: Lineage tracking path showing exactly where the data came from.
    3. **All-VARCHAR Landing (`all_varchar = true`)**:
       - Avoids schema-casting crashes during landing so dirty values (like `'bad_price'`) are captured as raw text for validation in Silver.
    4. **Transaction Atomicity (`BEGIN` / `COMMIT`)**:
       - Guarantees the delete-and-insert executes as a single atomic unit.
    """)
    return


@app.cell
def _(extract_dir, mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        DELETE FROM bronze.customers WHERE _load_date = DATE '{run_date}';

        INSERT INTO bronze.customers
        SELECT
            customer_id,
            customer_name,
            email,
            city,
            country,
            updated_date,
            DATE '{run_date}' AS _load_date,
            current_timestamp AS _ingested_at,
            '{extract_dir}/customers.csv' AS _source_file
        FROM read_csv('{extract_dir}/customers.csv', header = true, all_varchar = true);

        COMMIT;
        """
    )
    return


@app.cell
def _(extract_dir, mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        DELETE FROM bronze.products WHERE _load_date = DATE '{run_date}';

        INSERT INTO bronze.products
        SELECT
            product_id,
            product_name,
            subcategory_code,
            unit_price,
            updated_date,
            DATE '{run_date}' AS _load_date,
            current_timestamp AS _ingested_at,
            '{extract_dir}/products.csv' AS _source_file
        FROM read_csv('{extract_dir}/products.csv', header = true, all_varchar = true);

        COMMIT;
        """
    )
    return


@app.cell
def _(extract_dir, mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        DELETE FROM bronze.product_category WHERE _load_date = DATE '{run_date}';

        INSERT INTO bronze.product_category
        SELECT
            subcategory_code,
            subcategory,
            category,
            updated_date,
            DATE '{run_date}' AS _load_date,
            current_timestamp AS _ingested_at,
            '{extract_dir}/product_category.csv' AS _source_file
        FROM read_csv(
            '{extract_dir}/product_category.csv',
            header = true,
            all_varchar = true
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(extract_dir, mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        DELETE FROM bronze.orders WHERE _load_date = DATE '{run_date}';

        INSERT INTO bronze.orders
        SELECT
            order_id,
            customer_id,
            order_date,
            status,
            updated_date,
            DATE '{run_date}' AS _load_date,
            current_timestamp AS _ingested_at,
            '{extract_dir}/orders.csv' AS _source_file
        FROM read_csv('{extract_dir}/orders.csv', header = true, all_varchar = true);

        COMMIT;
        """
    )
    return


@app.cell
def _(extract_dir, mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        DELETE FROM bronze.order_items WHERE _load_date = DATE '{run_date}';

        INSERT INTO bronze.order_items
        SELECT
            order_item_id,
            order_id,
            product_id,
            quantity,
            unit_price,
            updated_date,
            DATE '{run_date}' AS _load_date,
            current_timestamp AS _ingested_at,
            '{extract_dir}/order_items.csv' AS _source_file
        FROM read_csv('{extract_dir}/order_items.csv', header = true, all_varchar = true);

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Validation

    For `2026-09-17` you should see about 16 customers (including a duplicate id), 16 products, 10 category rows (including a duplicate code), 18 orders, and 34 order items (including a duplicate `order_item_id`).

    Dirty values such as `bad_price`, blank emails, and `shiped` must still be visible — Bronze does not clean them.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        SELECT 'customers' AS table_name, count(*) AS row_count
        FROM bronze.customers WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'products', count(*) FROM bronze.products WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'product_category', count(*)
        FROM bronze.product_category WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'orders', count(*) FROM bronze.orders WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'order_items', count(*)
        FROM bronze.order_items WHERE _load_date = DATE '{run_date}'
        ORDER BY table_name;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### List all tables in the 'bronze' schema of the 'sales_lake' catalog.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sales_lake'
          AND table_schema = 'bronze'
        ORDER BY table_name;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Display rows from bronze.products with invalid or missing values in 'unit_price' or 'subcategory_code'.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT *
        FROM bronze.products
        WHERE unit_price IN ('bad_price', '-25.00')
           OR subcategory_code IS NULL
           OR trim(subcategory_code) = '';
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Releasing the lakehouse catalog with DETACH DATABASE ensures all file handles are closed and the catalog can safely be used in another notebook.
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
    ## Summary

    - Ingested one extract folder into DuckLake tables under `bronze`.
    - Preserved raw text values and added `_load_date`, `_ingested_at`, and `_source_file`.
    - Made the load re-runnable for the same `run_date` without touching other dates.

    **Learned:** Bronze is the landing zone. Tables are defined in `00.1_bronze_schema.py`. Data cleaning is done in Silver. Next, open `02_silver.py` with the same `run_date`.
    """)
    return


if __name__ == "__main__":
    app.run()
