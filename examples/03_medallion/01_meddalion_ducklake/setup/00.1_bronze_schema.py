import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 00.1 - Bronze Layer Schema Definition

    This notebook defines the table structures for the **Bronze Layer** in the `sales_lake` catalog.

    ### Key Concepts:
    - **Landing Zone**: Bronze stores raw incoming data extracted from CSV files.
    - **All-VARCHAR Types**: All entity attributes are defined as `VARCHAR` to ensure extracts load reliably without type casting failures on dirty data (e.g., `'bad_price'` or ill-formatted dates).
    - **Audit & Ingestion Metadata**: Each table includes tracking columns:
      - `_load_date DATE`: Processing batch partition date (`run_date`).
      - `_ingested_at TIMESTAMP`: Exact timestamp when rows were inserted.
      - `_source_file VARCHAR`: Path of the source CSV file.
    """)
    return


@app.cell
def _():
    import os
    import marimo as mo

    root_dir = ".." if os.path.exists(os.path.join("..", "run_pipeline.py")) else "."
    catalog_db_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError(
            "DuckLake catalog not found. Please run 00_setup.py first."
        )

    print(f"Catalog DB: {catalog_db_path}")
    print(f"Data Dir:   {data_directory_path}")
    return catalog_db_path, data_directory_path, mo


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Attach DuckLake Catalog
    Connect to the `sales_lake` catalog initialized in `00_setup.py`.
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
    ## 2. Create Bronze Tables

    Defines the following 5 raw landing tables within the `bronze` schema:
    1. `bronze.customers`: Customer accounts and location details.
    2. `bronze.products`: Product catalog and prices.
    3. `bronze.product_category`: Product subcategory and category hierarchy.
    4. `bronze.orders`: Orders header records.
    5. `bronze.order_items`: Order line items.
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

        -- Pipeline execution tracking table (pipeline state management)
        CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
            run_date DATE,
            status VARCHAR,          -- 'Pending', 'In progress', 'Completed', 'Failed'
            processed_at TIMESTAMP   -- Last processing attempt timestamp
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Verify Bronze Schema

    Query `information_schema.tables` to confirm all 5 Bronze tables exist in `sales_lake`.
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
    #### 4. Release Catalog File Lock
    Detaching `sales_lake` releases file locks so subsequent notebooks can access the lakehouse.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        USE memory;
        DETACH DATABASE IF EXISTS sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Summary & Next Step
    - Successfully defined all 5 Bronze raw landing tables in `sales_lake`.
    - Next: Run `00.2_silver_schema.py` to create the Silver and Quarantine schemas.
    """)
    return


if __name__ == "__main__":
    app.run()
