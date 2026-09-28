import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 00.3 - Gold Layer Schema Definition (Star Schema)

    This notebook defines the dimensional model (Star Schema) tables for the **Gold Layer** in the `sales_lake` catalog.

    ### Key Concepts:
    - **Dimensional Modeling (Kimball)**:
      - **Dimension Tables**: Provide rich context for slicing, filtering, and reporting (`dim_date`, `dim_customer`, `dim_product`, `dim_status`).
      - **Fact Table**: Stores numerical business metrics (`quantity`, `unit_price`, `sales_amount`) at the atomic order-item grain (`fact_sales`).
    - **Degenerate Dimensions**: `order_id` is retained directly in `fact_sales` to allow order-level tracking without requiring a separate order dimension.
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
            "DuckLake catalog not found. Please run 00_setup.py, 00.1_bronze_schema.py, and 00.2_silver_schema.py first."
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
    ## 2. Create Gold Star Schema Tables

    Defines:
    - `gold.dim_date`: Calendar dimension (year, quarter, month, month name, week, day, day name).
    - `gold.dim_customer`: Customer profile and geographic dimension.
    - `gold.dim_product`: Product catalog hierarchy (subcategory, category).
    - `gold.dim_status`: Order fulfillment lifecycle status (`Pending`, `Completed`, etc.).
    - `gold.fact_sales`: Central transactional fact table at the order-item grain.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Date Dimension
        CREATE TABLE IF NOT EXISTS gold.dim_date (
            date DATE,
            year INTEGER,
            quarter INTEGER,
            month INTEGER,
            month_name VARCHAR,
            week INTEGER,
            day INTEGER,
            day_name VARCHAR
        );

        -- 2. Customer Dimension
        CREATE TABLE IF NOT EXISTS gold.dim_customer (
            customer_id INTEGER,
            customer_name VARCHAR,
            email VARCHAR,
            city VARCHAR,
            country VARCHAR
        );

        -- 3. Product Dimension
        CREATE TABLE IF NOT EXISTS gold.dim_product (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory VARCHAR,
            category VARCHAR
        );

        -- 4. Status Dimension
        CREATE TABLE IF NOT EXISTS gold.dim_status (
            status VARCHAR
        );

        -- 5. Central Fact Table
        CREATE TABLE IF NOT EXISTS gold.fact_sales (
            order_item_id INTEGER,
            order_id INTEGER,
            date DATE,
            customer_id INTEGER,
            product_id INTEGER,
            status VARCHAR,
            quantity INTEGER,
            unit_price DECIMAL(10, 2),
            sales_amount DECIMAL(12, 2)
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Verify Gold Schema

    Query `information_schema.tables` to confirm all 5 Gold dimensional tables exist in `sales_lake`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sales_lake'
          AND table_schema = 'gold'
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
    - Successfully defined all 4 dimension tables and the central fact table in `gold`.
    - Next:
      1. Ingest raw CSV data using `01_bronze.py`.
      2. Clean, validate, and merge records using `02_silver.py`.
      3. Populate the Star Schema using `03_gold.py`.
      4. Query business KPIs in `04_answer_questions.py`.
    """)
    return


if __name__ == "__main__":
    app.run()
