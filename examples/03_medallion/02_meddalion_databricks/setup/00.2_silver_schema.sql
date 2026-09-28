-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00.2 - Silver & Quarantine Layer Schema Definition
-- MAGIC 
-- MAGIC This notebook defines the Delta Lake table structures for the **Silver Layer** and **Quarantine Schema** in Unity Catalog.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Key Data Engineering Concepts
-- MAGIC 
-- MAGIC #### 1. Silver Layer: The Curated Single Source of Truth
-- MAGIC While Bronze stores raw string extracts verbatim, Silver represents **curated, trusted, enterprise-grade data**:
-- MAGIC - **Strict Typing**: Replaces `STRING` with strong physical types (`INT` for identifiers, `DECIMAL(10, 2)` for currency, `DATE` for calendar dates, `TIMESTAMP` for modification times).
-- MAGIC - **Data Standardization**: Canonical casing (`initcap` for names, `upper` for codes, `lower` for emails), standardized country and city names, unified order status values.
-- MAGIC - **Enrichment**: Pre-computes line totals (`quantity * unit_price`), joins category hierarchies, and fills missing line prices from product catalog lookup.
-- MAGIC - **Deduplication**: Resolves duplicate records by retaining the latest record per business key (`QUALIFY row_number() = 1`).
-- MAGIC 
-- MAGIC #### 2. The Quarantine Pattern (Data Quality Isolation)
-- MAGIC In real-world data engineering, what should a pipeline do when a record violates business rules (e.g. negative price, future order date, or missing foreign key)?
-- MAGIC 
-- MAGIC | Pipeline Strategy | Pros | Fatal Flaw |
-- MAGIC | :--- | :--- | :--- |
-- MAGIC | **Fail & Abort Pipeline** | Prevents bad data from entering | Costly downtime; a single bad line stops millions of valid transactions |
-- MAGIC | **Silently Drop Bad Rows** | Pipeline keeps running | Silent data loss; financial discrepancy; no visibility or audit trail |
-- MAGIC | **Quarantine Pattern (Recommended)** | Pipeline runs smoothly; bad rows captured with reasons | **Best Practice**: Zero downtime, 100% auditability, enables self-healing and remediation |
-- MAGIC 
-- MAGIC Each quarantine table captures:
-- MAGIC 1. The rejected record attributes.
-- MAGIC 2. `rejection_reason STRING`: Explicit reason explaining which quality check failed.
-- MAGIC 3. `_load_date DATE`: Batch partition date when the error occurred, facilitating triage.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Configure Catalog Context

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Define Silver Curated Tables
-- MAGIC 
-- MAGIC Defines 5 validated, strongly typed business entity tables in `silver`.

-- COMMAND ----------

-- 1. Silver Product Categories (Standardized lookup table)
CREATE TABLE IF NOT EXISTS silver.product_category (
    subcategory_code STRING COMMENT 'Standardized uppercase subcategory code (PK)',
    subcategory STRING COMMENT 'Cleaned subcategory name',
    category STRING COMMENT 'Standardized title-case parent category (e.g. Electronics, Home & Kitchen)',
    updated_date TIMESTAMP COMMENT 'Source update timestamp'
)
USING DELTA
COMMENT 'Silver curated product category lookup hierarchy';

-- COMMAND ----------

-- 2. Silver Customers (Cleaned customer master data)
CREATE TABLE IF NOT EXISTS silver.customers (
    customer_id INT COMMENT 'Cleaned integer customer identifier (PK)',
    customer_name STRING COMMENT 'Trimmed, title-cased customer full name',
    email STRING COMMENT 'Lowercased, validated email address (NULL if invalid format)',
    city STRING COMMENT 'Standardized city name with typos corrected',
    country STRING COMMENT 'Standardized country name (e.g. Qatar, United Arab Emirates, Saudi Arabia)',
    updated_date TIMESTAMP COMMENT 'Source update timestamp'
)
USING DELTA
COMMENT 'Silver curated customer profile dimension';

-- COMMAND ----------

-- 3. Silver Products (Cleaned product catalog with category enrichment)
CREATE TABLE IF NOT EXISTS silver.products (
    product_id INT COMMENT 'Validated integer product identifier (PK)',
    product_name STRING COMMENT 'Cleaned product name',
    subcategory_code STRING COMMENT 'Uppercase subcategory code (defaults to OTHER)',
    subcategory STRING COMMENT 'Enriched subcategory name from category lookup',
    category STRING COMMENT 'Enriched category name from category lookup',
    unit_price DECIMAL(10, 2) COMMENT 'Cleaned non-negative catalog unit price',
    updated_date TIMESTAMP COMMENT 'Source update timestamp'
)
USING DELTA
COMMENT 'Silver curated product catalog enriched with category details';

-- COMMAND ----------

-- 4. Silver Orders (Validated order headers)
CREATE TABLE IF NOT EXISTS silver.orders (
    order_id INT COMMENT 'Validated integer order identifier (PK)',
    customer_id INT COMMENT 'Verified foreign key referencing silver.customers',
    order_date DATE COMMENT 'Parsed order date (guaranteed <= processing run_date)',
    status STRING COMMENT 'Standardized fulfillment status (Completed, Pending, Shipped, Cancelled, Processing)',
    updated_date TIMESTAMP COMMENT 'Source update timestamp'
)
USING DELTA
COMMENT 'Silver curated order header transactions';

-- COMMAND ----------

-- 5. Silver Order Items (Validated line items with computed line_total)
CREATE TABLE IF NOT EXISTS silver.order_items (
    order_item_id INT COMMENT 'Validated unique order item line identifier (PK)',
    order_id INT COMMENT 'Verified foreign key referencing silver.orders',
    product_id INT COMMENT 'Verified foreign key referencing silver.products',
    product_name STRING COMMENT 'Denormalized product name for fast analytics',
    subcategory_code STRING COMMENT 'Denormalized subcategory code',
    subcategory STRING COMMENT 'Denormalized subcategory name',
    category STRING COMMENT 'Denormalized category name',
    quantity INT COMMENT 'Positive order quantity (must be > 0)',
    unit_price DECIMAL(10, 2) COMMENT 'Effective sale price (line price or catalog fallback)',
    line_total DECIMAL(12, 2) COMMENT 'Computed extended price: quantity * unit_price',
    updated_date TIMESTAMP COMMENT 'Source update timestamp'
)
USING DELTA
COMMENT 'Silver curated order line item transactions';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Define Quarantine Tables
-- MAGIC 
-- MAGIC Quarantine tables store rejected records that fail business rules.
-- MAGIC Each table contains the attempted values plus:
-- MAGIC - `rejection_reason STRING`: Explicit reason why the record was rejected.
-- MAGIC - `_load_date DATE`: Date partition when the rejection occurred.

-- COMMAND ----------

-- 1. Quarantine Products (Invalid product IDs, negative prices, bad price text)
CREATE TABLE IF NOT EXISTS quarantine.products (
    product_id INT COMMENT 'Attempted parsed product ID',
    product_name STRING COMMENT 'Product name',
    subcategory_code STRING COMMENT 'Subcategory code',
    unit_price DECIMAL(10, 2) COMMENT 'Attempted parsed price',
    updated_date TIMESTAMP COMMENT 'Update timestamp',
    rejection_reason STRING COMMENT 'Specific data quality failure description',
    _load_date DATE COMMENT 'Batch partition run date when row was quarantined'
)
USING DELTA
COMMENT 'Quarantine table storing rejected product catalog records';

-- COMMAND ----------

-- 2. Quarantine Orders (Missing order_id, future dates, unknown customer references)
CREATE TABLE IF NOT EXISTS quarantine.orders (
    order_id INT COMMENT 'Attempted parsed order ID',
    customer_id INT COMMENT 'Attempted customer ID',
    order_date DATE COMMENT 'Attempted parsed order date',
    status STRING COMMENT 'Order status',
    updated_date TIMESTAMP COMMENT 'Update timestamp',
    rejection_reason STRING COMMENT 'Specific data quality failure description',
    _load_date DATE COMMENT 'Batch partition run date when row was quarantined'
)
USING DELTA
COMMENT 'Quarantine table storing rejected order header records';

-- COMMAND ----------

-- 3. Quarantine Order Items (Non-positive quantity, unknown order/product references, missing price)
CREATE TABLE IF NOT EXISTS quarantine.order_items (
    order_item_id INT COMMENT 'Attempted parsed order item ID',
    order_id INT COMMENT 'Attempted order ID',
    product_id INT COMMENT 'Attempted product ID',
    quantity INT COMMENT 'Attempted quantity',
    line_unit_price DECIMAL(10, 2) COMMENT 'Attempted unit price',
    updated_date TIMESTAMP COMMENT 'Update timestamp',
    rejection_reason STRING COMMENT 'Specific data quality failure description',
    _load_date DATE COMMENT 'Batch partition run date when row was quarantined'
)
USING DELTA
COMMENT 'Quarantine table storing rejected order line item records';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Verify Silver & Quarantine Schemas
-- MAGIC 
-- MAGIC Query `information_schema.tables` to confirm all 5 Silver tables and 3 Quarantine tables exist.

-- COMMAND ----------

SELECT 
    table_schema,
    table_name,
    table_type,
    comment
FROM information_schema.tables
WHERE table_catalog = :catalog_name
  AND table_schema IN ('silver', 'quarantine')
ORDER BY table_schema, table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Defined 5 strongly typed Silver tables enforcing numeric (`INT`, `DECIMAL`), temporal (`DATE`, `TIMESTAMP`), and relational constraints.
-- MAGIC - Defined 3 Quarantine tables implementing the industry-standard Quarantine Pattern for non-blocking data quality enforcement.
-- MAGIC 
-- MAGIC **Next Step**: Run [`00.3_gold_schema.sql`](./00.3_gold_schema.sql) to define the Kimball Star Schema for business intelligence and reporting.
