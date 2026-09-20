import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    ## 03 - Gold Layer: Business-Ready Metrics

    Gold tables are small, aggregated, and report-ready. They are rebuilt from silver.sales_detail on every run.

    Revenue includes only Completed and Shipped orders. Other statuses remain in Silver and are excluded from sales KPIs.
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
    return catalog_db_path, data_directory_path, mo, run_date


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
    ### 1. Fulfilled sales only

    Create a Gold input view of Completed and Shipped lines. `CREATE OR REPLACE TABLE` is stored in **DuckLake**.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.fulfilled_sales AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            order_id,
            order_date,
            customer_id,
            customer_name,
            city,
            country,
            product_id,
            product_name,
            subcategory,
            category,
            quantity,
            unit_price,
            line_total
        FROM silver.sales_detail
        WHERE status IN ('Completed', 'Shipped');

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold fulfilled_sales as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT count(*) AS fulfilled_lines, round(sum(line_total), 2) AS gross_sales
        FROM gold.fulfilled_sales;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 2. Daily sales

    KPI grain: one row per order date.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.daily_sales AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            order_date,
            count(DISTINCT order_id) AS total_orders,
            sum(quantity) AS units_sold,
            round(sum(line_total), 2) AS total_sales
        FROM gold.fulfilled_sales
        GROUP BY order_date
        ORDER BY order_date;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold daily_sales as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.daily_sales ORDER BY order_date;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### 3. Product performance

    Which products generate revenue.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.product_performance AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            product_id,
            product_name,
            subcategory,
            category,
            sum(quantity) AS units_sold,
            count(DISTINCT order_id) AS orders_count,
            round(sum(line_total), 2) AS revenue
        FROM gold.fulfilled_sales
        GROUP BY product_id, product_name, subcategory, category;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold product_performance as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.product_performance ORDER BY revenue DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ##4. Sales by category
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.sales_by_category AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            category,
            subcategory,
            sum(quantity) AS units_sold,
            count(DISTINCT order_id) AS orders_count,
            round(sum(line_total), 2) AS revenue
        FROM gold.fulfilled_sales
        GROUP BY category, subcategory;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold sales_by_category as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.sales_by_category ORDER BY revenue DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### 5. Customer summary
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.customer_summary AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            customer_id,
            customer_name,
            city,
            country,
            count(DISTINCT order_id) AS orders_count,
            sum(quantity) AS units_purchased,
            round(sum(line_total), 2) AS total_spent
        FROM gold.fulfilled_sales
        GROUP BY customer_id, customer_name, city, country;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold customer_summary as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.customer_summary ORDER BY total_spent DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### 6. Sales by city
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.sales_by_city AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            city,
            country,
            count(DISTINCT order_id) AS total_orders,
            count(DISTINCT customer_id) AS unique_customers,
            round(sum(line_total), 2) AS total_sales
        FROM gold.fulfilled_sales
        GROUP BY city, country;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold sales_by_city as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.sales_by_city ORDER BY total_sales DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 7. Orders by status
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE gold.orders_by_status AS
        SELECT
            DATE '{run_date}' AS as_of_date,
            status,
            count(*) AS order_count
        FROM silver.orders
        GROUP BY status;

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold orders_by_status as of {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM gold.orders_by_status ORDER BY order_count DESC;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Display the available tables in each lakehouse schema.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sales_lake'
          AND table_schema IN ('bronze', 'silver', 'gold', 'quarantine')
        ORDER BY table_schema, table_name;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### DuckLake snapshot log

    Each Bronze / Silver / Gold write that used `set_commit_message` appears here. This is **DuckLake** time-travel metadata.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            snapshot_id,
            CAST(snapshot_time AS VARCHAR) AS snapshot_time,
            author,
            commit_message
        FROM ducklake_snapshots('sales_lake')
        ORDER BY snapshot_id;
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
    ### Summary

    - Created Gold KPI tables using validated Silver data.
    - Gold tables answer key business questions (sales by day, product, city, customer) and should remain simple, with Silver handling data quality.

    For incremental loads: set `run_date = "2026-09-18"` in `01_bronze.py`, `02_silver.py`, and `03_gold.py`, then rerun those notebooks (skip `00_setup.py`). "Desk" and "Yoga Mat" will remain quarantined until `2026-09-19`.
    """)
    return


if __name__ == "__main__":
    app.run()
