import marimo

__generated_with = "0.24.2"
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
    ## 0. Processing date

    Change `run_date` to match a folder under `data/`.

    | `run_date` | Extract type |
    | :--- | :--- |
    | `2026-09-17` | First (full) load |
    | `2026-09-18` … `2026-09-20` | Incremental (new and changed rows) |
    """)
    return


@app.cell
def _():
    import os

    import marimo as mo

    # Keep this value in sync with 02_silver.py and 03_gold.py
    run_date = "2026-09-18"

    extract_dir = os.path.abspath(os.path.join("data", run_date)).replace("\\", "/")
    catalog_db_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError("DuckLake catalog not found. Run 00_setup.py first.")
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
    ## 3. Create Bronze tables if they do not exist

    All source columns are `VARCHAR`. Types are applied later in Silver.

    `CREATE TABLE` in the **DuckLake**: the table definition is stored in the catalog.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE TABLE IF NOT EXISTS bronze.customers (
            customer_id VARCHAR,
            customer_name VARCHAR,
            email VARCHAR,
            city VARCHAR,
            country VARCHAR,
            updated_date VARCHAR,
            _load_date DATE,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR
        );

        CREATE TABLE IF NOT EXISTS bronze.products (
            product_id VARCHAR,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            unit_price VARCHAR,
            updated_date VARCHAR,
            _load_date DATE,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR
        );

        CREATE TABLE IF NOT EXISTS bronze.product_category (
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            updated_date VARCHAR,
            _load_date DATE,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR
        );

        CREATE TABLE IF NOT EXISTS bronze.orders (
            order_id VARCHAR,
            customer_id VARCHAR,
            order_date VARCHAR,
            status VARCHAR,
            updated_date VARCHAR,
            _load_date DATE,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR
        );

        CREATE TABLE IF NOT EXISTS bronze.order_items (
            order_item_id VARCHAR,
            order_id VARCHAR,
            product_id VARCHAR,
            quantity VARCHAR,
            unit_price VARCHAR,
            updated_date VARCHAR,
            _load_date DATE,
            _ingested_at TIMESTAMP,
            _source_file VARCHAR
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Create bronze tables'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Load each extract file for `run_date`

    Pattern for every table:

    1. `DELETE` rows already loaded for this `_load_date` (safe re-run)
    2. `INSERT` from `read_csv`
    3. Tag the DuckLake snapshot with `set_commit_message`

    Incremental folders contain **only changed/new rows**. Bronze **appends** them as a new `_load_date`. Silver MERGEs that day's keys into the curated tables.
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

        CALL sales_lake.set_commit_message(
            'student',
            'Bronze customers load {run_date}'
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

        CALL sales_lake.set_commit_message(
            'student',
            'Bronze products load {run_date}'
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

        CALL sales_lake.set_commit_message(
            'student',
            'Bronze product_category load {run_date}'
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

        CALL sales_lake.set_commit_message(
            'student',
            'Bronze orders load {run_date}'
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

        CALL sales_lake.set_commit_message(
            'student',
            'Bronze order_items load {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Validation

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

    **Learned:** Bronze is the landing zone. Data cleaning is done in Silver. Next, open `02_silver.py` with the same `run_date`.
    """)
    return


if __name__ == "__main__":
    app.run()
