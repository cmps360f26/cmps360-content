-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00.1 - Bronze Layer Schema Definition
-- MAGIC 
-- MAGIC This notebook defines the Delta Lake table structures for the **Bronze Layer** in Unity Catalog.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Key Data Engineering Concepts
-- MAGIC 
-- MAGIC #### 1. The Raw Landing Pattern (Immutable History)
-- MAGIC - Bronze acts as an append-only, immutable history of incoming source extracts.
-- MAGIC - Data is ingested **verbatim** from source CSV files without transformation, filtering, or data loss.
-- MAGIC 
-- MAGIC #### 2. Why All-STRING Columns? (Permissive Schema Pattern)
-- MAGIC - Every business attribute in Bronze is defined as `STRING`.
-- MAGIC - **The Problem**: Real-world raw source data contains anomalies (e.g., `'bad_price'`, non-numeric text, non-ISO dates like `'20-09-2026'`, typos like `'shiped'`).
-- MAGIC - **The Consequence of Strict Types**: If Bronze enforced `DECIMAL` on `unit_price` or `DATE` on `order_date`, the ingestion job would crash immediately on day 1. The data pipeline would halt, and no data would land.
-- MAGIC - **The Solution**: By landing dirty data safely as `STRING`, data engineers guarantee that 100% of the raw data enters the lakehouse. Cleaning, type casting, and validation are properly handled in the Silver layer, where invalid records can be routed to Quarantine.
-- MAGIC 
-- MAGIC #### 3. Lineage & Audit Metadata
-- MAGIC Every Bronze table includes three technical metadata columns:
-- MAGIC | Audit Column | Data Type | Purpose |
-- MAGIC | :--- | :--- | :--- |
-- MAGIC | `_load_date` | `DATE` | Batch partition run date (`run_date`). Enables daily idempotent reloading. |
-- MAGIC | `_ingested_at` | `TIMESTAMP` | Exact system timestamp when the record was written to the lakehouse. |
-- MAGIC | `_source_file` | `STRING` | Full URI / path of the source CSV file, establishing end-to-end data lineage. |
-- MAGIC 
-- MAGIC #### 4. Why `USING DELTA`?
-- MAGIC Specifying `USING DELTA` configures the Delta Lake storage engine. Delta Lake adds an ACID transaction log (`_delta_log`), schema enforcement, time-travel auditing, and high-performance Parquet storage beneath standard SQL tables.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Configure Catalog & Schema Context

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);
USE SCHEMA bronze;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Define Bronze Delta Tables
-- MAGIC 
-- MAGIC We define 5 raw entity tables corresponding to the source CSV files, plus the orchestrator tracking table.

-- COMMAND ----------

-- 1. Raw Customers Landing Table
CREATE TABLE IF NOT EXISTS bronze.customers (
    customer_id STRING COMMENT 'Raw customer identifier string',
    customer_name STRING COMMENT 'Raw customer name (may contain whitespace or mixed casing)',
    email STRING COMMENT 'Raw email address (may be missing, blank, or invalid format)',
    city STRING COMMENT 'Raw city name (may contain typos, hyphens, or whitespace)',
    country STRING COMMENT 'Raw country name or country code (e.g. QA, QAT, Qatar)',
    updated_date STRING COMMENT 'Raw source system modification timestamp string',
    _load_date DATE COMMENT 'Batch partition run date',
    _ingested_at TIMESTAMP COMMENT 'System timestamp when row was written to Bronze',
    _source_file STRING COMMENT 'Full lineage path of the source CSV file'
)
USING DELTA
COMMENT 'Bronze raw extract table for customer master records';

-- COMMAND ----------

-- 2. Raw Products Landing Table
CREATE TABLE IF NOT EXISTS bronze.products (
    product_id STRING COMMENT 'Raw product identifier string',
    product_name STRING COMMENT 'Raw product commercial name',
    subcategory_code STRING COMMENT 'Raw subcategory code (e.g. ELEC_MOB, or empty)',
    unit_price STRING COMMENT 'Raw price string (may include thousands commas or bad_price text)',
    updated_date STRING COMMENT 'Raw source system modification timestamp string',
    _load_date DATE COMMENT 'Batch partition run date',
    _ingested_at TIMESTAMP COMMENT 'System timestamp when row was written to Bronze',
    _source_file STRING COMMENT 'Full lineage path of the source CSV file'
)
USING DELTA
COMMENT 'Bronze raw extract table for product catalog records';

-- COMMAND ----------

-- 3. Raw Product Category Hierarchy Landing Table
CREATE TABLE IF NOT EXISTS bronze.product_category (
    subcategory_code STRING COMMENT 'Raw subcategory code (lookup key)',
    subcategory STRING COMMENT 'Raw subcategory descriptive name',
    category STRING COMMENT 'Raw parent category descriptive name',
    updated_date STRING COMMENT 'Raw source system modification timestamp string',
    _load_date DATE COMMENT 'Batch partition run date',
    _ingested_at TIMESTAMP COMMENT 'System timestamp when row was written to Bronze',
    _source_file STRING COMMENT 'Full lineage path of the source CSV file'
)
USING DELTA
COMMENT 'Bronze raw extract table for product category hierarchy lookup';

-- COMMAND ----------

-- 4. Raw Orders Landing Table
CREATE TABLE IF NOT EXISTS bronze.orders (
    order_id STRING COMMENT 'Raw order identifier string',
    customer_id STRING COMMENT 'Raw foreign key to customer',
    order_date STRING COMMENT 'Raw order date string (may use varying formats or future dates)',
    status STRING COMMENT 'Raw fulfillment status string (may include typos or informal aliases)',
    updated_date STRING COMMENT 'Raw source system modification timestamp string',
    _load_date DATE COMMENT 'Batch partition run date',
    _ingested_at TIMESTAMP COMMENT 'System timestamp when row was written to Bronze',
    _source_file STRING COMMENT 'Full lineage path of the source CSV file'
)
USING DELTA
COMMENT 'Bronze raw extract table for order header transactions';

-- COMMAND ----------

-- 5. Raw Order Items Landing Table
CREATE TABLE IF NOT EXISTS bronze.order_items (
    order_item_id STRING COMMENT 'Raw line item identifier (may contain batch duplicates)',
    order_id STRING COMMENT 'Raw foreign key to order header',
    product_id STRING COMMENT 'Raw foreign key to product catalog',
    quantity STRING COMMENT 'Raw purchase quantity string (may include zero or negative values)',
    unit_price STRING COMMENT 'Raw price string (may be blank, requiring catalog lookup)',
    updated_date STRING COMMENT 'Raw source system modification timestamp string',
    _load_date DATE COMMENT 'Batch partition run date',
    _ingested_at TIMESTAMP COMMENT 'System timestamp when row was written to Bronze',
    _source_file STRING COMMENT 'Full lineage path of the source CSV file'
)
USING DELTA
COMMENT 'Bronze raw extract table for order line item transactions';

-- COMMAND ----------

-- 6. Pipeline Execution Tracking Table (Ensures table exists if this notebook is run standalone)
CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
    run_date DATE COMMENT 'Batch extract date (YYYY-MM-DD)',
    status STRING COMMENT 'Execution state: Pending, In progress, Completed, Failed',
    processed_at TIMESTAMP COMMENT 'Timestamp of last status update'
)
USING DELTA
COMMENT 'Operational audit table tracking daily batch ingestion status';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Verify Bronze Schema Definitions
-- MAGIC 
-- MAGIC ### SQL Feature: `information_schema.tables`
-- MAGIC System catalog view querying all registered tables in schema `bronze` under catalog `:catalog_name`.

-- COMMAND ----------

SELECT 
    table_schema,
    table_name,
    table_type,
    comment
FROM information_schema.tables
WHERE table_catalog = :catalog_name
  AND table_schema = 'bronze'
ORDER BY table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Defined 5 Bronze raw extract tables with permissive `STRING` columns so messy raw data lands reliably without job failures.
-- MAGIC - Embedded 3 audit metadata columns (`_load_date`, `_ingested_at`, `_source_file`) on every table to guarantee complete data provenance.
-- MAGIC - Ensured all tables use Delta Lake (`USING DELTA`) for ACID transactions and reliability.
-- MAGIC 
-- MAGIC **Next Step**: Run [`00.2_silver_schema.sql`](./00.2_silver_schema.sql) to define the Silver curated schema and Quarantine isolation schema.
