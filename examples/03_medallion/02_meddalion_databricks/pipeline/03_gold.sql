-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 03 - Gold Layer: Kimball Star Schema Dimensional Modeling
-- MAGIC 
-- MAGIC Welcome to the **Gold Layer Data Pipeline**!
-- MAGIC 
-- MAGIC In the Medallion Lakehouse Architecture:
-- MAGIC - **Bronze** lands raw extracts as text with audit metadata.
-- MAGIC - **Silver** validates, strongly types, deduplicates, and cleanses data entities.
-- MAGIC - **Gold** models the trusted data into an analytics-optimized **Kimball Star Schema** to power BI tools (Power BI, Tableau, Databricks Lakeview Dashboards) and executive analytics.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Kimball Star Schema Architecture
-- MAGIC 
-- MAGIC A Star Schema separates data into two core structures:
-- MAGIC 
-- MAGIC ```text
-- MAGIC                  ┌───────────────────┐
-- MAGIC                  │   gold.dim_date   │
-- MAGIC                  ├───────────────────┤
-- MAGIC                  │ date (PK)         │
-- MAGIC                  │ year, month...    │
-- MAGIC                  └─────────┬─────────┘
-- MAGIC                            │
-- MAGIC                            │ 1
-- MAGIC                            │
-- MAGIC                            │ *
-- MAGIC  ┌───────────────────┐     │     ┌───────────────────┐
-- MAGIC  │ gold.dim_customer │     │     │ gold.dim_product  │
-- MAGIC  ├───────────────────┤     │     ├───────────────────┤
-- MAGIC  │ customer_id (PK)  │     │     │ product_id (PK)   │
-- MAGIC  │ name, city...     │     │     │ name, category... │
-- MAGIC  └─────────┬─────────┘     │     └─────────┬─────────┘
-- MAGIC            │               │               │
-- MAGIC          1 │             * │             * │ 1
-- MAGIC            └─────────>  [fact_sales]  <────┘
-- MAGIC            │            (center fact)      │
-- MAGIC          1 │               │               │ 1
-- MAGIC  ┌─────────┴─────────┐     │     ┌─────────┴─────────┐
-- MAGIC  │  gold.dim_status  │     │     │  Degenerate Dim   │
-- MAGIC  ├───────────────────┤     │     ├───────────────────┤
-- MAGIC  │ status (PK)       │─────┘ *   │ order_id          │
-- MAGIC  └───────────────────┘           └───────────────────┘
-- MAGIC ```
-- MAGIC 
-- MAGIC 1. **Central Fact Table (`gold.fact_sales`)**:
-- MAGIC    - Contains numeric **business measures** (`quantity`, `unit_price`, `sales_amount`).
-- MAGIC    - Contains **foreign keys** pointing to surrounding dimension tables.
-- MAGIC    - **Grain**: Exactly one row per item sold in an order (`order_item_id`).
-- MAGIC    - **Degenerate Dimension**: `order_id` is retained directly in the fact table for order-level slicing without a redundant order dimension table.
-- MAGIC 
-- MAGIC 2. **Surrounding Dimension Tables**:
-- MAGIC    - `gold.dim_date` (*When*): Precomputed calendar hierarchy (day, week, month, quarter, year, names).
-- MAGIC    - `gold.dim_customer` (*Who & Where*): Customer profile and geographic market (city, country).
-- MAGIC    - `gold.dim_product` (*What*): Product catalog and category hierarchy (subcategory, category).
-- MAGIC    - `gold.dim_status` (*Lifecycle state*): Order fulfillment pipeline statuses (`Completed`, `Pending`, etc.).
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Incremental Loading Pattern (No Full Table Drops)
-- MAGIC - Schema structures were created once during setup.
-- MAGIC - We merge new and updated records incrementally using Delta Lake **`MERGE INTO`**:
-- MAGIC   - `WHEN MATCHED THEN UPDATE`: Updates existing dimension/fact records (e.g. when an order transitions from `Pending` &rarr; `Completed`, or customer updates city).
-- MAGIC   - `WHEN NOT MATCHED THEN INSERT`: Appends brand-new records.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 0: Configure Execution Parameters

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";
CREATE WIDGET TEXT run_date DEFAULT "2026-09-17";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Dimension: `gold.dim_date` (Contiguous Calendar Generation)
-- MAGIC 
-- MAGIC ### Why Precompute a Date Dimension?
-- MAGIC - **Ultra-Fast Queries**: Eliminates runtime date parsing (`date_format`, `date_trunc`, `weekofyear`) across millions of sales rows in BI dashboards.
-- MAGIC - **Uniform Labels**: Standardizes labels (e.g. `'September'`, `'Thursday'`) across all reports.
-- MAGIC - **Contiguous Calendar (Zero-Sales Handling)**: By generating every contiguous calendar day between the first and last dates using `sequence()` and `explode()`, time-series charts (`dim_date LEFT JOIN fact_sales`) display days with zero sales rather than skipping dates entirely.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `sequence(start, end, interval)`: Generates an array of dates from `start` to `end` with no gaps.
-- MAGIC - `explode(array)`: Unnests array elements into distinct rows.
-- MAGIC - `date_format(date, 'MMMM')`: Formats month name (e.g. `'September'`).
-- MAGIC - `date_format(date, 'EEEE')`: Formats full weekday name (e.g. `'Thursday'`).

-- COMMAND ----------

-- Incrementally merge continuous calendar days observed up to run_date
MERGE INTO gold.dim_date AS t
USING (
    WITH bounds AS (
        -- 1. Find earliest and latest order dates observed up to run_date
        SELECT
            MIN(order_date) AS first_date,
            MAX(order_date) AS last_date
        FROM silver.orders
        WHERE order_date IS NOT NULL
          AND order_date <= DATE '${run_date}'
    ),
    days AS (
        -- 2. Generate every contiguous calendar day in that range (no gaps)
        SELECT explode(sequence(first_date, last_date, interval 1 day)) AS date
        FROM bounds
    )
    -- 3. Precompute calendar attributes for analytical slicing
    SELECT
        date,
        year(date) AS year,
        quarter(date) AS quarter,
        month(date) AS month,
        date_format(date, 'MMMM') AS month_name,
        weekofyear(date) AS week,
        day(date) AS day,
        date_format(date, 'EEEE') AS day_name
    FROM days
) AS s
    ON t.date = s.date
WHEN NOT MATCHED THEN INSERT (
    date, year, quarter, month, month_name, week, day, day_name
) VALUES (
    s.date, s.year, s.quarter, s.month, s.month_name, s.week, s.day, s.day_name
);

-- COMMAND ----------

-- Preview dim_date
SELECT * FROM gold.dim_date WHERE date <= DATE '${run_date}' ORDER BY date;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Dimension: `gold.dim_customer`
-- MAGIC 
-- MAGIC Stores customer demographic and geographic market attributes.
-- MAGIC 
-- MAGIC ### Incremental Strategy (SCD Type 1):
-- MAGIC - `WHEN MATCHED THEN UPDATE`: Updates customer attributes in-place if a customer relocates (e.g., Customer 2 moving from Al Rayyan to Lusail) or modifies contact details.
-- MAGIC - `WHEN NOT MATCHED THEN INSERT`: Appends newly registered customers.

-- COMMAND ----------

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

-- COMMAND ----------

-- Preview dim_customer
SELECT * FROM gold.dim_customer ORDER BY customer_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Dimension: `gold.dim_product`
-- MAGIC 
-- MAGIC Stores product commercial metadata and merchandise hierarchy.
-- MAGIC 
-- MAGIC ### Incremental Strategy:
-- MAGIC - `WHEN MATCHED THEN UPDATE`: Updates product names and re-categorizations (e.g. when the Wireless Mouse subcategory resolves from `Other` to `Accessories`).
-- MAGIC - `WHEN NOT MATCHED THEN INSERT`: Appends new products. Previously quarantined products (like Desk 104 or Yoga Mat 115) are automatically inserted once their validation issues are corrected in Silver.

-- COMMAND ----------

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

-- COMMAND ----------

-- Preview dim_product
SELECT * FROM gold.dim_product ORDER BY product_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Dimension: `gold.dim_status`
-- MAGIC 
-- MAGIC Captures all unique fulfillment lifecycle stages.
-- MAGIC 
-- MAGIC ### Why `WHERE order_date <= DATE '${run_date}'`?
-- MAGIC Using `<=` ensures we capture order statuses originating from orders placed on prior dates (`order_date < run_date`) that were updated on or before `run_date`. Using `=` would only inspect orders created today, missing earlier statuses or status transitions.

-- COMMAND ----------

MERGE INTO gold.dim_status AS t
USING (
    SELECT DISTINCT status
    FROM silver.orders
    WHERE status IS NOT NULL
      AND order_date <= DATE '${run_date}'
) AS s
    ON t.status = s.status
WHEN NOT MATCHED THEN INSERT (
    status
) VALUES (
    s.status
);

-- COMMAND ----------

-- Preview dim_status
SELECT * FROM gold.dim_status ORDER BY status;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Central Fact Table: `gold.fact_sales`
-- MAGIC 
-- MAGIC The fact table captures sales transactions at the **atomic order-item grain** (one row per item sold).
-- MAGIC 
-- MAGIC - **Dimension Foreign Keys**: `date`, `customer_id`, `product_id`, `status`
-- MAGIC - **Degenerate Dimension**: `order_id`
-- MAGIC - **Numeric Measures**: `quantity`, `unit_price`, `sales_amount` (`quantity * unit_price`)
-- MAGIC 
-- MAGIC ### Why `WHERE o.order_date <= DATE '${run_date}'` in the Fact MERGE?
-- MAGIC In retail, orders placed on previous days frequently transition status (e.g. Order 1006 placed on 17 Sep as `Pending`, then completed on 18 Sep).
-- MAGIC - If we filtered by `o.order_date = run_date`, Order 1006's status change on the 18th would be ignored, leaving historical sales permanently marked as `Pending` in `fact_sales`!
-- MAGIC - By evaluating orders up to `run_date`, the `WHEN MATCHED THEN UPDATE SET status = s.status` clause correctly updates historical fact lines in-place, while `WHEN NOT MATCHED THEN INSERT` appends new sales lines.

-- COMMAND ----------

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
        CAST(i.quantity * i.unit_price AS DECIMAL(12, 2)) AS sales_amount
    FROM silver.order_items i
    JOIN silver.orders o
        ON i.order_id = o.order_id
    WHERE o.order_date <= DATE '${run_date}'
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

-- COMMAND ----------

-- Preview fact_sales sample transactions as of run_date
SELECT *
FROM gold.fact_sales
WHERE date <= DATE '${run_date}'
ORDER BY order_id, order_item_id
LIMIT 10;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Gold Layer Row Count Auditing

-- COMMAND ----------

SELECT 'dim_date' AS table_name, count(*) AS total_rows FROM gold.dim_date
UNION ALL
SELECT 'dim_customer', count(*) FROM gold.dim_customer
UNION ALL
SELECT 'dim_product', count(*) FROM gold.dim_product
UNION ALL
SELECT 'dim_status', count(*) FROM gold.dim_status
UNION ALL
SELECT 'fact_sales', count(*) FROM gold.fact_sales
ORDER BY table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Built a complete Ralph Kimball **Star Schema** on top of Delta Lake in `${catalog_name}.gold`.
-- MAGIC - Leveraged continuous calendar generation (`sequence` + `explode`) to prevent gaps in time-series reporting.
-- MAGIC - Applied Delta Lake `MERGE INTO` to enable incremental, in-place updates for status transitions (e.g. `Pending` &rarr; `Completed`) and customer location updates (SCD Type 1).
-- MAGIC 
-- MAGIC **Next Step**: Open [`04_answer_questions.sql`](../analysis/04_answer_questions.sql) to query business KPIs and answer analytics questions using Star Joins!
