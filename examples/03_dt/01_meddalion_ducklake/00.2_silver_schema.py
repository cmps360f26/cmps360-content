import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 00.2 - Silver & Quarantine Layer Schema Definition

    This notebook defines the table structures for the **Silver Layer** and **Quarantine Schema** in the `sales_lake` catalog.

    ### Key Concepts:
    - **Silver Layer (Curated & Validated)**: Standardizes business entities with strong types (`INTEGER`, `DECIMAL`, `DATE`, `TIMESTAMP`) and enriched calculations (such as `line_total`).
    - **Quarantine Schema (Quality Isolation)**: Stores invalid or corrupt rows rejected during Silver quality checks without halting the ingestion pipeline.
    - **Rejection Tracking**: Quarantine tables include `rejection_reason VARCHAR` and `_load_date DATE` for root-cause analysis and remediation.
    """)
    return


@app.cell
def _():
    import os
    import marimo as mo

    catalog_db_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError(
            "DuckLake catalog not found. Please run 00_setup.py and 00.1_bronze_schema.py first."
        )

    print(f"Catalog DB: {catalog_db_path}")
    print(f"Data Dir:   {data_directory_path}")
    return catalog_db_path, data_directory_path, mo


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Attach DuckLake Catalog
    Connect to the `sales_lake` catalog.
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
    ## 2. Create Silver and Quarantine Tables

    Defines:
    - **Silver Tables**: `silver.product_category`, `silver.customers`, `silver.products`, `silver.orders`, and `silver.order_items`.
    - **Quarantine Tables**: `quarantine.products`, `quarantine.orders`, and `quarantine.order_items`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Silver tables (Cleaned, validated, strongly typed)
        CREATE TABLE IF NOT EXISTS silver.product_category (
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.customers (
            customer_id INTEGER,
            customer_name VARCHAR,
            email VARCHAR,
            city VARCHAR,
            country VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.products (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.orders (
            order_id INTEGER,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.order_items (
            order_item_id INTEGER,
            order_id INTEGER,
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            quantity INTEGER,
            unit_price DECIMAL(10, 2),
            line_total DECIMAL(12, 2),
            updated_date TIMESTAMP
        );

        -- Quarantine tables (Stores rejected records with failure reason)
        CREATE TABLE IF NOT EXISTS quarantine.products (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        CREATE TABLE IF NOT EXISTS quarantine.orders (
            order_id INTEGER,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR,
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        CREATE TABLE IF NOT EXISTS quarantine.order_items (
            order_item_id INTEGER,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            line_unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Verify Silver & Quarantine Schemas

    Query `information_schema.tables` to ensure all Silver and Quarantine tables exist in `sales_lake`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sales_lake'
          AND table_schema IN ('silver', 'quarantine')
        ORDER BY table_schema, table_name;
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
    - Successfully defined all Silver and Quarantine tables in `sales_lake`.
    - Next: Run `00.3_gold_schema.py` to define the Gold Star Schema tables.
    """)
    return


if __name__ == "__main__":
    app.run()
