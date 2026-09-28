-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00.3 - Gold Layer Schema Definition (Kimball Star Schema)
-- MAGIC 
-- MAGIC This notebook defines the dimensional model (**Star Schema**) for the **Gold Layer** in Unity Catalog.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Kimball Dimensional Modeling Fundamentals
-- MAGIC 
-- MAGIC In a **Star Schema** (pioneered by Ralph Kimball), data is organized into two primary table structures optimized for analytical read performance, business intelligence (BI) tools (e.g., Power BI, Tableau, Databricks Lakeview Dashboards), and executive KPIs:
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
-- MAGIC #### 1. Dimension Tables (Context & Slicing)
-- MAGIC Dimension tables answer business context questions: *Who, What, When, Where, and Status*:
-- MAGIC - `gold.dim_date` (*When*): Precomputed calendar attributes (`year`, `quarter`, `month`, `month_name`, `week`, `day`, `day_name`) for instantaneous time-series slicing without runtime date formatting.
-- MAGIC - `gold.dim_customer` (*Who & Where*): Customer profile and geographic market attributes (`city`, `country`).
-- MAGIC - `gold.dim_product` (*What*): Commercial product catalog and merchandise categories (`subcategory`, `category`).
-- MAGIC - `gold.dim_status` (*Lifecycle state*): Order fulfillment pipeline statuses (`Completed`, `Pending`, `Shipped`, `Cancelled`, `Processing`).
-- MAGIC 
-- MAGIC #### 2. Fact Table (Atomic Business Measurements)
-- MAGIC The fact table sits at the center of the star:
-- MAGIC - **Fact Grain**: Exactly one row per item sold in an order (`order_item_id`). The grain defines what a single row represents.
-- MAGIC - **Additive Measures**: Numerical business metrics that can be meaningfully summed across any dimension: `quantity`, `unit_price`, `sales_amount` (`quantity * unit_price`).
-- MAGIC - **Foreign Keys**: References linking back to surrounding dimensions (`date`, `customer_id`, `product_id`, `status`).
-- MAGIC - **Degenerate Dimension**: `order_id` is an operational transaction identifier kept directly in `fact_sales` without creating a redundant, single-attribute dimension table.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Configure Catalog Context

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);
USE SCHEMA gold;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Define Gold Star Schema Tables
-- MAGIC 
-- MAGIC Defines 4 surrounding dimension tables and 1 central fact table.

-- COMMAND ----------

-- 1. Date Dimension (Calendar attributes for time-series analytics)
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date DATE COMMENT 'Calendar date (PK)',
    year INT COMMENT 'Calendar year (e.g. 2026)',
    quarter INT COMMENT 'Calendar quarter (1 to 4)',
    month INT COMMENT 'Calendar month number (1 to 12)',
    month_name STRING COMMENT 'Full month name (e.g. September)',
    week INT COMMENT 'Calendar week of year (1 to 53)',
    day INT COMMENT 'Day of the month (1 to 31)',
    day_name STRING COMMENT 'Day of the week name (e.g. Thursday, Friday)'
)
USING DELTA
COMMENT 'Gold Date Dimension: Precomputed calendar hierarchy for fast time-series analysis';

-- COMMAND ----------

-- 2. Customer Dimension (Customer profile & geographic market attributes)
CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_id INT COMMENT 'Cleaned customer identifier (PK)',
    customer_name STRING COMMENT 'Customer full name',
    email STRING COMMENT 'Customer email address',
    city STRING COMMENT 'Standardized city name',
    country STRING COMMENT 'Standardized country name'
)
USING DELTA
COMMENT 'Gold Customer Dimension: Customer demographic and geographic attributes';

-- COMMAND ----------

-- 3. Product Dimension (Product catalog and merchandise category hierarchy)
CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_id INT COMMENT 'Cleaned product identifier (PK)',
    product_name STRING COMMENT 'Product commercial name',
    subcategory STRING COMMENT 'Product subcategory descriptive name',
    category STRING COMMENT 'Parent category descriptive name'
)
USING DELTA
COMMENT 'Gold Product Dimension: Product catalog and category hierarchy';

-- COMMAND ----------

-- 4. Status Dimension (Order fulfillment lifecycle states)
CREATE TABLE IF NOT EXISTS gold.dim_status (
    status STRING COMMENT 'Order fulfillment lifecycle status (PK: Completed, Pending, Shipped, Cancelled, Processing)'
)
USING DELTA
COMMENT 'Gold Status Dimension: Order fulfillment lifecycle pipeline states';

-- COMMAND ----------

-- 5. Central Fact Table (Sales transactions at atomic order-item grain)
CREATE TABLE IF NOT EXISTS gold.fact_sales (
    order_item_id INT COMMENT 'Unique order line item identifier (PK / Fact grain)',
    order_id INT COMMENT 'Degenerate dimension: operational order identifier',
    date DATE COMMENT 'Foreign key referencing dim_date.date',
    customer_id INT COMMENT 'Foreign key referencing dim_customer.customer_id',
    product_id INT COMMENT 'Foreign key referencing dim_product.product_id',
    status STRING COMMENT 'Foreign key referencing dim_status.status',
    quantity INT COMMENT 'Additive measure: units sold in this line',
    unit_price DECIMAL(10, 2) COMMENT 'Measure: effective unit selling price',
    sales_amount DECIMAL(12, 2) COMMENT 'Additive measure: monetary line total (quantity * unit_price)'
)
USING DELTA
COMMENT 'Gold Central Sales Fact: Atomic transactional order line sales events';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Verify Gold Schema Definitions
-- MAGIC 
-- MAGIC Query `information_schema.tables` to confirm all 5 Gold tables are created in Delta Lake format.

-- COMMAND ----------

SELECT 
    table_schema,
    table_name,
    table_type,
    comment
FROM information_schema.tables
WHERE table_catalog = :catalog_name
  AND table_schema = 'gold'
ORDER BY table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Created a Ralph Kimball **Star Schema** with 4 dimension tables and 1 central fact table.
-- MAGIC - Separated numeric business measurements (`quantity`, `sales_amount`) from descriptive context (`customer`, `product`, `date`, `status`).
-- MAGIC - Modeled the fact table at the **atomic order-item grain** to provide maximum analytical flexibility.
-- MAGIC 
-- MAGIC **Next Steps**:
-- MAGIC 1. Run [`00.4_load_landing_files.py`](./00.4_load_landing_files.py) to load raw CSV extract files into the Unity Catalog Volume.
-- MAGIC 2. Run [`01_bronze.sql`](../pipeline/01_bronze.sql) to start the Medallion ingestion pipeline.
