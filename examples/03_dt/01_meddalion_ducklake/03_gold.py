import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 03 - Gold Layer: Star Schema Modeling

    Welcome to the **Gold Layer** of the Medallion Lakehouse!

    In the Medallion Architecture:
    - **Bronze** ingests raw source extracts as-is.
    - **Silver** cleans, validates, standardizes types, and quarantines bad data.
    - **Gold** transforms trusted Silver data into a **business-ready dimensional model (Star Schema)** to power BI dashboards (e.g., Power BI), reporting, and executive analytics.

    ---

    ### What is a Star Schema?
    A **Star Schema** (designed by Ralph Kimball) organizes data into two distinct types of tables:
    1. **Fact Table (`gold.fact_sales`)**:
       - Positioned at the center of the star.
       - Contains numeric **measures** (e.g., `quantity`, `unit_price`, `sales_amount`).
       - Contains **foreign keys** pointing to surrounding dimension tables.
       - **Grain**: Exactly one row per item sold in an order (`order_item_id`).
    2. **Dimension Tables (`dim_time`, `dim_customer`, `dim_product`, `dim_status`)**:
       - Positioned as points of the star surrounding the fact table.
       - Contain rich descriptive attributes that allow business users to **filter, slice, dice, and group** the metrics (answering *Who*, *What*, *When*, *Where*, and *Status*).

    ---

    ### Incremental Loading Pattern (No Table Rebuilding)
    Earlier iterations used `CREATE OR REPLACE TABLE`, which wiped out and rebuilt tables on every run.
    In this production-grade pipeline:
    - We create tables once using **`CREATE TABLE IF NOT EXISTS`**.
    - We merge new and updated records using **`MERGE INTO`**:
      - `WHEN MATCHED THEN UPDATE`: Updates existing records (e.g., an order moving from `Pending` to `Completed`, or customer moving cities).
      - `WHEN NOT MATCHED THEN INSERT`: Appends new records.
    - Historical data is preserved across incremental loads (`2026-09-17`, `2026-09-18`, etc.).
    """)
    return


@app.cell
def _():
    import os
    import marimo as mo

    # Processing date - keep in sync with 01_bronze.py and 02_silver.py
    # Change to 2026-09-18, 2026-09-19, etc. to test incremental updates
    run_date = "2026-09-18"

    catalog_db_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError(
            "DuckLake catalog not found. Please run 00_setup.py, 01_bronze.py, and 02_silver.py first."
        )

    print(f"Building Gold Star Schema as of run_date = {run_date}")
    return catalog_db_path, data_directory_path, mo, run_date


@app.cell
def _(catalog_db_path, data_directory_path, mo):
    _df = mo.sql(
        f"""
        -- Step 0: Attach DuckLake catalog
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
    ## Build the Star Schema Model

    The diagram below shows our Star Schema dimensional model:
    ![Star Schema](star-schema-design.png)

    ### Star Schema Entity Relationships
    - `fact_sales.date` &rarr; `dim_time.date` (*When*)
    - `fact_sales.customer_id` &rarr; `dim_customer.customer_id` (*Who & Where*)
    - `fact_sales.product_id` &rarr; `dim_product.product_id` (*What*)
    - `fact_sales.status` &rarr; `dim_status.status` (*Lifecycle state*)
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 1. Dimension: `gold.dim_time`
    The time dimension provides pre-computed calendar attributes (year, quarter, month, day name, week) for daily, weekly, monthly, and quarterly trend analysis.

    **Incremental Strategy**:
    - `CREATE TABLE IF NOT EXISTS`: Creates the dimension table once.
    - `MERGE INTO ... WHEN NOT MATCHED THEN INSERT`: Calendar attributes for an existing date never change, so we only insert newly observed dates from `silver.orders`.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Create dim_time table if it does not exist
        CREATE TABLE IF NOT EXISTS gold.dim_time (
            date DATE,
            year INTEGER,
            quarter INTEGER,
            month INTEGER,
            month_name VARCHAR,
            week INTEGER,
            day INTEGER,
            day_name VARCHAR
        );

        -- 2. Incrementally insert new dates from silver.orders up to run_date
        MERGE INTO gold.dim_time AS t
        USING (
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
            WHERE order_date IS NOT NULL
              AND order_date <= DATE '{run_date}'
        ) AS s
            ON t.date = s.date
        WHEN NOT MATCHED THEN INSERT (
            date, year, quarter, month, month_name, week, day, day_name
        ) VALUES (
            s.date, s.year, s.quarter, s.month, s.month_name, s.week, s.day, s.day_name
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold dim_time MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Preview dim_time rows as of run_date
        SELECT *
        FROM gold.dim_time
        WHERE date <= DATE '{run_date}'
        ORDER BY date;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 2. Dimension: `gold.dim_customer`
    Stores customer contact details and geographic locations (city, country).

    **Incremental Strategy**:
    - `WHEN MATCHED THEN UPDATE`: If a customer updates their name, email, or relocates to a new city, their attributes are updated in-place without duplicating the row.
    - `WHEN NOT MATCHED THEN INSERT`: Adds newly registered customers.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Create dim_customer table if it does not exist
        CREATE TABLE IF NOT EXISTS gold.dim_customer (
            customer_id INTEGER,
            customer_name VARCHAR,
            email VARCHAR,
            city VARCHAR,
            country VARCHAR
        );

        -- 2. Incrementally merge customers from silver.customers
        MERGE INTO gold.dim_customer AS t
        USING silver.customers AS s
            ON t.customer_id = s.customer_id
        WHEN MATCHED THEN UPDATE SET
            customer_name = s.customer_name,
            email = s.email,
            city = s.city,
            country = s.country
        WHEN NOT MATCHED THEN INSERT (
            customer_id, customer_name, email, city, country
        ) VALUES (
            s.customer_id, s.customer_name, s.email, s.city, s.country
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold dim_customer MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Preview dim_customer rows
        SELECT * FROM gold.dim_customer ORDER BY customer_id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 3. Dimension: `gold.dim_product`
    Stores product metadata, including subcategory and category hierarchies.

    **Incremental Strategy**:
    - `WHEN MATCHED THEN UPDATE`: Updates product descriptions and classification if they were re-categorized in Silver (e.g., when the Mouse subcategory is resolved from `OTHER` to `ELEC_ACC`).
    - `WHEN NOT MATCHED THEN INSERT`: Inserts newly cataloged products. Quarantined products (like Desk or Yoga Mat) will automatically be inserted here once their validation issues are corrected in Silver.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Create dim_product table if it does not exist
        CREATE TABLE IF NOT EXISTS gold.dim_product (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR
        );

        -- 2. Incrementally merge products from silver.products
        MERGE INTO gold.dim_product AS t
        USING silver.products AS s
            ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET
            product_name = s.product_name,
            subcategory_code = s.subcategory_code,
            subcategory = s.subcategory,
            category = s.category
        WHEN NOT MATCHED THEN INSERT (
            product_id, product_name, subcategory_code, subcategory, category
        ) VALUES (
            s.product_id, s.product_name, s.subcategory_code, s.subcategory, s.category
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold dim_product MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Preview dim_product rows
        SELECT * FROM gold.dim_product ORDER BY product_id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 4. Dimension: `gold.dim_status`
    Contains distinct order fulfillment lifecycle states (`Pending`, `Processing`, `Shipped`, `Completed`, `Cancelled`).

    **Incremental Strategy**:
    - Inserts any newly encountered order statuses without duplicating existing ones.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Create dim_status table if it does not exist
        CREATE TABLE IF NOT EXISTS gold.dim_status (
            status VARCHAR
        );

        -- 2. Incrementally insert any new statuses from silver.orders up to run_date
        MERGE INTO gold.dim_status AS t
        USING (
            SELECT DISTINCT status
            FROM silver.orders
            WHERE status IS NOT NULL
              AND order_date <= DATE '{run_date}'
        ) AS s
            ON t.status = s.status
        WHEN NOT MATCHED THEN INSERT (
            status
        ) VALUES (
            s.status
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold dim_status MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Preview dim_status rows
        SELECT * FROM gold.dim_status ORDER BY status;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 5. Central Fact Table: `gold.fact_sales`
    The central fact table captures sales transactions at the **order-item grain** (one row per item in an order).

    - **Dimension Foreign Keys**: `date`, `customer_id`, `product_id`, `status`
    - **Degenerate Dimension**: `order_id` (kept in the fact for order-level tracking without needing a separate order dimension)
    - **Numerical Measures**: `quantity`, `unit_price`, `sales_amount` (`quantity * unit_price`)

    **Incremental Strategy**:
    - `WHEN MATCHED THEN UPDATE`: If an existing order's status changes from `Pending` &rarr; `Completed`, or item quantities/prices adjust, the fact row is updated in-place!
    - `WHEN NOT MATCHED THEN INSERT`: Inserts brand-new order lines.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- 1. Create fact_sales table if it does not exist
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

        -- 2. Incrementally merge order items into fact_sales up to run_date
        MERGE INTO gold.fact_sales AS t
        USING (
            SELECT
                i.order_item_id,
                o.order_id,
                o.order_date AS date,
                o.customer_id,
                i.product_id,
                o.status,
                i.quantity,
                i.unit_price,
                i.quantity * i.unit_price AS sales_amount
            FROM silver.order_items i
            JOIN silver.orders o
                ON i.order_id = o.order_id
            WHERE o.order_date <= DATE '{run_date}'
        ) AS s
            ON t.order_item_id = s.order_item_id
        WHEN MATCHED THEN UPDATE SET
            order_id = s.order_id,
            date = s.date,
            customer_id = s.customer_id,
            product_id = s.product_id,
            status = s.status,
            quantity = s.quantity,
            unit_price = s.unit_price,
            sales_amount = s.sales_amount
        WHEN NOT MATCHED THEN INSERT (
            order_item_id,
            order_id,
            date,
            customer_id,
            product_id,
            status,
            quantity,
            unit_price,
            sales_amount
        ) VALUES (
            s.order_item_id,
            s.order_id,
            s.date,
            s.customer_id,
            s.product_id,
            s.status,
            s.quantity,
            s.unit_price,
            s.sales_amount
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Gold fact_sales MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Preview fact_sales transactions as of run_date
        SELECT *
        FROM gold.fact_sales
        WHERE date <= DATE '{run_date}'
        ORDER BY order_id, order_item_id
        LIMIT 10;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Releasing the Lakehouse Catalog
    Releasing the catalog with `DETACH DATABASE` closes all active file handles so other notebooks or BI servers can safely connect to `sales_lake_catalog.db`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Release the lakehouse catalog so other notebooks / Power BI can attach
        USE memory;
        DETACH DATABASE IF EXISTS sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Summary & Educational Key Takeaways

    - **Medallion Gold Layer**: Transformed validated Silver tables into analytics-ready Star Schema dimensional model.
    - **Star Schema Dimensional Modeling**:
      - `fact_sales` models business events at the atomic line-item grain (`order_item_id`).
      - Dimension tables (`dim_time`, `dim_customer`, `dim_product`, `dim_status`) provide rich context for slicing and filtering.
    - **Incremental MERGE Pattern**:
      - Used `CREATE TABLE IF NOT EXISTS` to ensure tables are never destroyed between runs.
      - Applied `MERGE INTO` with `WHEN MATCHED THEN UPDATE` (e.g. order status changes, customer address updates) and `WHEN NOT MATCHED THEN INSERT`.
    - **Business Analytics via Star Joins**: Answered in the dedicated analytics notebook `04_answer_questions.py`.
    - **Testing Incremental Loads**:
      To simulate pipeline progression across days:
      1. Change `run_date` to `"2026-09-18"` in `01_bronze.py`, `02_silver.py`, and `03_gold.py`.
      2. Re-run `01_bronze.py`, `02_silver.py`, and `03_gold.py` (do not run `00_setup.py`, which resets the lakehouse).
      3. Run `04_answer_questions.py` to inspect the updated cumulative sales and KPIs.
    """)
    return


if __name__ == "__main__":
    app.run()
