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
    2. **Dimension Tables (`dim_date`, `dim_customer`, `dim_product`, `dim_status`)**:
       - Positioned as points of the star surrounding the fact table.
       - Contain rich descriptive attributes that allow business users to **filter, slice, dice, and group** the metrics (answering *Who*, *What*, *When*, *Where*, and *Status*).

    ---

    ### Incremental Loading Pattern (No Table Rebuilding)
    In this production-grade pipeline:
    - Star schema tables are defined once in `00.3_gold_schema.py`.
    - We merge new and updated records incrementally using **`MERGE INTO`**:
      - `WHEN MATCHED THEN UPDATE`: Updates existing records (e.g., an order moving from `Pending` to `Completed`, or customer moving cities).
      - `WHEN NOT MATCHED THEN INSERT`: Appends new records.
    - Historical data is preserved across incremental loads (`2026-09-17`, `2026-09-18`, etc.).

    #### Execution Modes:
    1. **Interactive Exploration**: Run cell-by-cell in Marimo (`marimo edit 03_gold.py`). Defaults to `"2026-09-17"`.
    2. **Programmatic Pipeline**: Run non-interactively via `run_pipeline.py` or terminal (`python 03_gold.py 2026-09-18`).
    """)
    return


@app.cell
def _():
    import os
    import re
    import sys

    import marimo as mo

    # Processing date configuration:
    # 1. Priority: Command-line argument (e.g., python 03_gold.py 2026-09-18)
    # 2. Priority: Environment variable (e.g., RUN_DATE=2026-09-18)
    # 3. Fallback: Default date for interactive Marimo sessions ("2026-09-17")
    cli_date = next(
        (arg for arg in sys.argv[1:] if re.match(r"^\d{4}-\d{2}-\d{2}$", arg)), None
    )
    run_date = cli_date or os.getenv("RUN_DATE", "2026-09-17")

    root_dir = ".." if os.path.exists(os.path.join("..", "run_pipeline.py")) else "."
    catalog_db_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join(root_dir, "lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError(
            "DuckLake catalog not found. Please run 00_setup.py, 00.1_bronze_schema.py, 00.2_silver_schema.py, 00.3_gold_schema.py, 01_bronze.py, and 02_silver.py first."
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
            DATA_PATH '{data_directory_path}',
            OVERRIDE_DATA_PATH TRUE
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
    - `fact_sales.date` &rarr; `dim_date.date` (*When*)
    - `fact_sales.customer_id` &rarr; `dim_customer.customer_id` (*Who & Where*)
    - `fact_sales.product_id` &rarr; `dim_product.product_id` (*What*)
    - `fact_sales.status` &rarr; `dim_status.status` (*Lifecycle state*)
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 1. Dimension: `gold.dim_date`
    The time dimension provides pre-computed calendar attributes (`year`, `quarter`, `month`, `month_name`, `week`, `day`, `day_name`) for daily, weekly, monthly, and quarterly trend analysis.

    #### Why Pre-compute a Date Dimension?
    - **Performance**: Eliminates expensive date calculations (`DATE_TRUNC`, `EXTRACT`, formatting) across millions of sales rows at query time.
    - **Consistent Labeling**: Provides uniform labels (e.g. `'September'`, `'Thursday'`) across all dashboards.
    - **Continuous Calendar (Zero-Sales Handling)**: By generating every contiguous calendar day between the first and last dates, time-series charts (`dim_date LEFT JOIN fact_sales`) show days with zero sales instead of skipping them.

    #### SQL Features Used:
    - **Common Table Expressions (CTEs)**: `WITH bounds AS (...)` finds the date range, and `days AS (...)` generates the sequence.
    - **Table-Valued Function (`generate_series`)**: Dynamically produces consecutive timestamps with `INTERVAL 1 DAY`.
    - **Calendar Extractors**: `year()`, `quarter()`, `month()`, `monthname()`, `week()`, `day()`, `dayname()`.
    - **Idempotent MERGE**: Calendar attributes for a date never change, so `WHEN NOT MATCHED THEN INSERT` safely adds newly observed dates.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Step 1: Incrementally merge continuous calendar days up to run_date
        MERGE INTO gold.dim_date AS t
        USING (
            WITH bounds AS (
                -- 1. Find the earliest and latest order dates observed up to run_date
                SELECT
                    MIN(order_date) AS first_date,
                    MAX(order_date) AS last_date
                FROM silver.orders
                WHERE order_date IS NOT NULL
                  AND order_date <= DATE '{run_date}'
            ),
            days AS (
                -- 2. Generate every contiguous calendar day in that range (no gaps)
                SELECT CAST(day_ts AS DATE) AS date
                FROM bounds
                CROSS JOIN generate_series(
                    first_date, last_date, INTERVAL 1 DAY
                ) AS generated(day_ts)
            )
            -- 3. Precompute calendar attributes for analytical slicing
            SELECT
                date,
                year(date) AS year,
                quarter(date) AS quarter,
                month(date) AS month,
                monthname(date) AS month_name,
                week(date) AS week,
                day(date) AS day,
                dayname(date) AS day_name
            FROM days
        ) AS s
            ON t.date = s.date
        WHEN NOT MATCHED THEN INSERT (
            date, year, quarter, month, month_name, week, day, day_name
        ) VALUES (
            s.date, s.year, s.quarter, s.month, s.month_name, s.week, s.day, s.day_name
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Preview dim_date rows as of run_date
        SELECT *
        FROM gold.dim_date
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

        -- Incrementally merge customers from silver.customers
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
    - `WHEN MATCHED THEN UPDATE`: Updates product descriptions and classification if they were re-categorized in Silver (e.g., when the Mouse subcategory is resolved from `Other` to `Accessories`).
    - `WHEN NOT MATCHED THEN INSERT`: Inserts newly cataloged products. Quarantined products (like Desk or Yoga Mat) will automatically be inserted here once their validation issues are corrected in Silver.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Incrementally merge products from silver.products
        MERGE INTO gold.dim_product AS t
        USING silver.products AS s
            ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET
            product_name = s.product_name,
            subcategory = s.subcategory,
            category = s.category
        WHEN NOT MATCHED THEN INSERT (
            product_id, product_name, subcategory, category
        ) VALUES (
            s.product_id, s.product_name, s.subcategory, s.category
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

        -- Incrementally insert any new statuses from silver.orders up to run_date
        MERGE INTO gold.dim_status AS t
        USING (
            SELECT DISTINCT status
            FROM silver.orders
            WHERE status IS NOT NULL
              -- '<=' is required because order statuses can originate from orders placed on prior dates
              -- (order_date < run_date) that were updated on or before run_date. Using '=' would only
              -- inspect orders created on run_date, failing to capture statuses from earlier order dates
              -- or status transitions occurring on previously created orders.
              AND order_date <= DATE '{run_date}'
        ) AS s
            ON t.status = s.status
        WHEN NOT MATCHED THEN INSERT (
            status
        ) VALUES (
            s.status
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

        -- Incrementally merge order items into fact_sales up to run_date
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
            -- '<=' is required because existing orders placed on earlier dates (order_date < run_date)
            -- frequently have their status updated (e.g., from 'Pending' to 'Completed') on later dates.
            -- Using '=' would restrict the source to only orders created on run_date, completely
            -- excluding prior orders. As a result, the WHEN MATCHED THEN UPDATE clause would never fire
            -- for earlier orders, leaving them with stale statuses and corrupting downstream sales metrics.
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
      - Dimension tables (`dim_date`, `dim_customer`, `dim_product`, `dim_status`) provide rich context for slicing and filtering.
    - **Incremental MERGE Pattern**:
      - Tables are initialized once in `00.3_gold_schema.py`.
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
