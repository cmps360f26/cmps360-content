import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    ## 03 - Gold Layer: Star Schema Model

    This layer creates a star schema, optimized for analytics and BI use cases.

    - The central fact table (`sales_detail`) captures detailed sales transactions, linked to dimension tables including customer, product, date, and city.

    - All Gold tables are rebuilt from Silver on each run to ensure freshness and consistency.

    - The star schema structure enables performant slicing, dicing, and drill-downs in tools like Power BI.
    """)
    return


@app.cell
def _():
    import os

    import marimo as mo

    # Keep this value in sync with 01_bronze.py and 02_silver.py
    run_date = "2026-09-18"

    catalog_db_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError("DuckLake catalog not found. Run 00_setup.py first.")

    print(f"Building Gold as of run_date = {run_date}")
    return catalog_db_path, data_directory_path, mo


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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1. Star Schema Design for Sales Analytics
    The schema is centered on a sales fact table, connected to several dimensions:
    ![Star Schema](star-schema-design.png)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The schema contains:
    - *dim_time*: Calendar attributes for time-based analysis
    - *dim_customer*: Customer and geographic attributes
    - *dim_product*: Product, subcategory, and category attributes
    - *dim_status*: Order status descriptions
    - *fact_sales*: Sales transactions at the order-item level

    #### **- Relationships**
    fact_sales.date
        -> dim_time.date

    fact_sales.customer_id
        -> dim_customer.customer_id

    fact_sales.product_id
        -> dim_product.product_id

    fact_sales.status
        -> dim_status.status
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- The time dimension provides calendar attributes  for daily, weekly, monthly, quarterly, and yearly analysis.
        CREATE OR REPLACE TABLE gold.dim_time AS
        SELECT DISTINCT
            order_date AS date,
            year(order_date) AS year,
            quarter(order_date) AS quarter,
            month(order_date) AS month,
            monthname(order_date) AS month_name,
            week(order_date) AS week,
            day(order_date) AS day,
            dayname(order_date) AS day_name
        FROM silver.orders
        ORDER BY date;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- The customer dimension includes customer and location attributes for geographic analysis.
        CREATE OR REPLACE TABLE gold.dim_customer AS
        SELECT
            customer_id,
            customer_name,
            email,
            city,
            country
        FROM silver.customers;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Product hierarchy for product and category analysis.
        CREATE OR REPLACE TABLE gold.dim_product AS
        SELECT
            product_id,
            product_name,
            subcategory_code,
            subcategory,
            category
        FROM silver.products;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Order statuses for sales pipeline analysis.
        CREATE OR REPLACE TABLE gold.dim_status AS
        SELECT DISTINCT
            status
        FROM silver.orders;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Grain: One row per order item sold.
        CREATE OR REPLACE TABLE gold.fact_sales AS
        SELECT
            i.order_item_id,
            o.order_id,

            -- Dimension keys
            o.order_date AS date,
            o.customer_id,
            i.product_id,
            o.status,

            -- Measures
            i.quantity,
            i.unit_price,
            i.quantity * i.unit_price AS sales_amount

        FROM silver.order_items i
        JOIN silver.orders o
            ON i.order_id = o.order_id;
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
    ### Summary: Gold Layer Star Schema

    - Developed Gold tables structured in a Star Schema using validated Silver data.
    - The fact table (`fact_sales`) captures each sales transaction at the order item level.
    - Dimension tables (e.g., customers, products, status, city) are designed for ease of analysis and performance.
    - This design supports quick, flexible reporting and business queries (e.g., sales by date, customer, product, city).
    - Data quality, cleanup, and conformance issues are resolved at Silver, keeping Gold reporting-ready and simple.

    For incremental loads: update `run_date` in `01_bronze.py`, `02_silver.py`, and `03_gold.py`, then rerun these scripts (skip `00_setup.py`). Quarantined products (like "Desk" and "Yoga Mat") remain held back until their quality issues are resolved.
    """)
    return


if __name__ == "__main__":
    app.run()
