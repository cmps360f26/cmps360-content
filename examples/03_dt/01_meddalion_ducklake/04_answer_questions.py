import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    # 04 - Answering Business Questions with the Star Schema

    Welcome to the **Analytics & Reporting** notebook of the Medallion Lakehouse!

    In `03_gold.py`, we created an incremental **Star Schema** with:
    - **`gold.fact_sales`**: Central fact table storing sales transactions at the order-item grain.
    - **`gold.dim_time`**: Calendar dimension for daily, weekly, and monthly time-series analysis.
    - **`gold.dim_customer`**: Customer and geographic dimension.
    - **`gold.dim_product`**: Product catalog and category hierarchy.
    - **`gold.dim_status`**: Order fulfillment pipeline statuses.

    ---

    ### Star Join Pattern in Dimensional Analytics
    In modern data architectures and BI tools (such as Power BI), analytical queries perform **Star Joins**:
    - The central fact table (`fact_sales`) supplies numerical measures (`quantity`, `unit_price`, `sales_amount`).
    - The dimension tables provide descriptive attributes to slice, filter, and group metrics.

    > **Accounting & Business Rule: Realized Revenue**
    > In sales analytics, gross realized revenue includes **only fulfilled orders** (`status IN ('Completed', 'Shipped')`). Orders that are `Pending`, `Processing`, or `Cancelled` represent pipeline or lost sales and are excluded from revenue KPIs.
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
            "DuckLake catalog not found. Please run 00_setup.py, 01_bronze.py, 02_silver.py, and 03_gold.py first."
        )

    print("Connected to DuckLake Gold Star Schema.")
    return catalog_db_path, data_directory_path, mo


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


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 1: Fulfilled Sales & Total Realized Revenue
    **Business Question**: What is our total realized revenue, total order volume, and number of fulfilled order line items across the business?

    **Star Schema Pattern**:
    Query `fact_sales` and filter by `dim_status.status IN ('Completed', 'Shipped')`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Total Realized Sales Summary
        SELECT
            COUNT(*) AS fulfilled_order_lines,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(f.quantity) AS total_units_sold,
            ROUND(SUM(f.sales_amount), 2) AS total_sales_amount
        FROM gold.fact_sales f
        JOIN gold.dim_status s
            ON f.status = s.status
        WHERE s.status IN ('Completed', 'Shipped');
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 2: Daily Sales Trend
    **Business Question**: How are order volumes, unit sales, and revenue trending across calendar dates and weeks?

    **Star Schema Pattern**:
    Join `fact_sales` with `dim_time` on `date`. Group by calendar attributes (`date`, `day_name`, `week`) to analyze daily performance without runtime date calculations.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Daily Sales and Order Volume
        SELECT
            t.date,
            t.day_name,
            t.week,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.sales_amount), 2) AS total_sales
        FROM gold.fact_sales f
        JOIN gold.dim_time t
            ON f.date = t.date
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY t.date, t.day_name, t.week
        ORDER BY t.date;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 3: Product Performance Ranking
    **Business Question**: Which individual products generate the highest revenue, and how many units were sold?

    **Star Schema Pattern**:
    Join `fact_sales` with `dim_product` on `product_id`. Aggregate by product name, category, and subcategory.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Top-Performing Products by Revenue
        SELECT
            p.product_id,
            p.product_name,
            p.subcategory,
            p.category,
            SUM(f.quantity) AS units_sold,
            COUNT(DISTINCT f.order_id) AS orders_count,
            ROUND(SUM(f.sales_amount), 2) AS revenue
        FROM gold.fact_sales f
        JOIN gold.dim_product p
            ON f.product_id = p.product_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY p.product_id, p.product_name, p.subcategory, p.category
        ORDER BY revenue DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 4: Sales by Category & Subcategory
    **Business Question**: What is the revenue contribution of each merchandise category and subcategory?

    **Star Schema Pattern**:
    Demonstrates **hierarchical roll-up** (`fact_sales` &rarr; `dim_product.subcategory` &rarr; `dim_product.category`).
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Category & Subcategory Performance
        SELECT
            p.category,
            p.subcategory,
            SUM(f.quantity) AS units_sold,
            COUNT(DISTINCT f.order_id) AS orders_count,
            ROUND(SUM(f.sales_amount), 2) AS revenue
        FROM gold.fact_sales f
        JOIN gold.dim_product p
            ON f.product_id = p.product_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY p.category, p.subcategory
        ORDER BY revenue DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 5: Customer Summary & Top Spenders
    **Business Question**: Who are our highest-value customers by total spend, order count, and purchase volume?

    **Star Schema Pattern**:
    Join `fact_sales` with `dim_customer` on `customer_id`. Computes customer lifetime value (CLV) and purchase habits.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Top Customers by Spend
        SELECT
            c.customer_id,
            c.customer_name,
            c.city,
            c.country,
            COUNT(DISTINCT f.order_id) AS orders_count,
            SUM(f.quantity) AS units_purchased,
            ROUND(SUM(f.sales_amount), 2) AS total_spent
        FROM gold.fact_sales f
        JOIN gold.dim_customer c
            ON f.customer_id = c.customer_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY c.customer_id, c.customer_name, c.city, c.country
        ORDER BY total_spent DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 6: Sales by City & Geographic Distribution
    **Business Question**: Which geographic markets drive our sales volume and unique customer reach?

    **Star Schema Pattern**:
    Join `fact_sales` with `dim_customer` on `customer_id` and group by geographic attributes (`city`, `country`).
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Geographic Sales & Customer Reach
        SELECT
            c.city,
            c.country,
            COUNT(DISTINCT f.order_id) AS total_orders,
            COUNT(DISTINCT f.customer_id) AS unique_customers,
            ROUND(SUM(f.sales_amount), 2) AS total_sales
        FROM gold.fact_sales f
        JOIN gold.dim_customer c
            ON f.customer_id = c.customer_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY c.city, c.country
        ORDER BY total_sales DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Question 7: Order Pipeline Breakdown by Status
    **Business Question**: How many orders and what total monetary value exist across all stages of the fulfillment pipeline?

    **Star Schema Pattern**:
    Join `fact_sales` with `dim_status` without filtering to provide full operational visibility across `Pending`, `Processing`, `Completed`, `Shipped`, and `Cancelled` orders.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Business KPI: Full Operational Pipeline by Order Status
        SELECT
            s.status,
            COUNT(DISTINCT f.order_id) AS order_count,
            ROUND(SUM(f.sales_amount), 2) AS pipeline_value
        FROM gold.fact_sales f
        JOIN gold.dim_status s
            ON f.status = s.status
        GROUP BY s.status
        ORDER BY order_count DESC;
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
    ### Summary: Dimensional Reporting Insights

    - **Star Joins in Action**: Directly joined the central fact table (`gold.fact_sales`) with surrounding dimensions (`dim_time`, `dim_customer`, `dim_product`, `dim_status`).
    - **Business vs. Operational Questions**:
      - Realized revenue questions (Q1–Q6) filter for fulfilled orders (`status IN ('Completed', 'Shipped')`).
      - Pipeline operations (Q7) examine all orders regardless of status.
    - **Cumulative Lakehouse Analytics**: Analyzed the full, cumulative state of the Gold Star Schema across all loaded dates.
    """)
    return


if __name__ == "__main__":
    app.run()
