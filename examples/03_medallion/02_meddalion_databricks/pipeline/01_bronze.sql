-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 01 - Bronze Layer: Ingest Raw Extracts into Delta Lake
-- MAGIC 
-- MAGIC Welcome to the **Bronze Ingestion Pipeline**!
-- MAGIC 
-- MAGIC In the Medallion Lakehouse Architecture:
-- MAGIC - **Bronze** ingests raw daily source CSV extracts **as-is**, without filtering, business transformations, or data loss.
-- MAGIC - All business entity columns are stored as `STRING` so dirty data (such as `'bad_price'` or non-ISO dates) lands safely without pipeline crashes.
-- MAGIC - Every record is enriched with ingestion audit metadata:
-- MAGIC 
-- MAGIC | Metadata Column | Data Type | Description |
-- MAGIC | :--- | :--- | :--- |
-- MAGIC | `_load_date` | `DATE` | The batch processing partition date (`run_date`). |
-- MAGIC | `_ingested_at` | `TIMESTAMP` | System timestamp when records were written to Delta Lake. |
-- MAGIC | `_source_file` | `STRING` | Full file path for end-to-end data lineage and provenance. |
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Core Data Engineering Patterns:
-- MAGIC 
-- MAGIC 1. **Idempotent Batch Ingestion**:
-- MAGIC    - In production, pipelines fail due to network blips or bad nodes, or must be re-run for backfills.
-- MAGIC    - An ingestion pipeline is **idempotent** if running it multiple times produces the exact same result as running it once.
-- MAGIC    - Deleting existing rows matching `_load_date = DATE '${run_date}'` before inserting ensures re-running the same date replaces that day's data without creating duplicate records.
-- MAGIC    - Other dates in the Bronze layer remain completely untouched!
-- MAGIC 
-- MAGIC 2. **Permissive Ingestion (`inferSchema => false`)**:
-- MAGIC    - Using `read_files()` with `inferSchema => false` treats every column as text.
-- MAGIC    - This guarantees that malformed values (such as `'bad_price'` or `'-25.00'`) never cause ingestion job failures.
-- MAGIC 
-- MAGIC 3. **Delta Lake ACID Transactions**:
-- MAGIC    - Each table write commits atomically to Delta Lake's transaction log (`_delta_log`), ensuring readers never see partial or corrupt data.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 0: Configure Execution Parameters
-- MAGIC 
-- MAGIC Set the batch date to process.
-- MAGIC 
-- MAGIC | `run_date` | Extract Role |
-- MAGIC | :--- | :--- |
-- MAGIC | `2026-09-17` | Initial full batch load |
-- MAGIC | `2026-09-18` &hellip; `2026-09-20` | Daily incremental batch loads |

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";
CREATE WIDGET TEXT run_date DEFAULT "2026-09-17";
CREATE WIDGET TEXT volume_path DEFAULT "/Volumes/sales_lake/bronze/landing_zone";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);
USE SCHEMA bronze;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Ingest Customers Extract
-- MAGIC 
-- MAGIC ### SQL Feature: `read_files()`
-- MAGIC Databricks SQL table-valued function that reads files directly from cloud storage or Unity Catalog Volumes:
-- MAGIC - `format => 'csv'`: Specifies CSV parsing.
-- MAGIC - `header => true`: Uses the first row as column headers.
-- MAGIC - `inferSchema => false`: Prevents automatic type casting, keeping all values as strings.

-- COMMAND ----------

-- 1. Idempotent cleanup: delete existing rows for this run_date
DELETE FROM bronze.customers WHERE _load_date = DATE '${run_date}';

-- 2. Ingest raw CSV data with audit metadata columns
INSERT INTO bronze.customers
SELECT
    customer_id,
    customer_name,
    email,
    city,
    country,
    updated_date,
    DATE '${run_date}' AS _load_date,
    current_timestamp() AS _ingested_at,
    '${volume_path}/${run_date}/customers.csv' AS _source_file
FROM read_files(
    '${volume_path}/${run_date}/customers.csv',
    format => 'csv',
    header => true,
    inferSchema => false
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Ingest Products Extract

-- COMMAND ----------

DELETE FROM bronze.products WHERE _load_date = DATE '${run_date}';

INSERT INTO bronze.products
SELECT
    product_id,
    product_name,
    subcategory_code,
    unit_price,
    updated_date,
    DATE '${run_date}' AS _load_date,
    current_timestamp() AS _ingested_at,
    '${volume_path}/${run_date}/products.csv' AS _source_file
FROM read_files(
    '${volume_path}/${run_date}/products.csv',
    format => 'csv',
    header => true,
    inferSchema => false
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Ingest Product Categories Extract

-- COMMAND ----------

DELETE FROM bronze.product_category WHERE _load_date = DATE '${run_date}';

INSERT INTO bronze.product_category
SELECT
    subcategory_code,
    subcategory,
    category,
    updated_date,
    DATE '${run_date}' AS _load_date,
    current_timestamp() AS _ingested_at,
    '${volume_path}/${run_date}/product_category.csv' AS _source_file
FROM read_files(
    '${volume_path}/${run_date}/product_category.csv',
    format => 'csv',
    header => true,
    inferSchema => false
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Ingest Orders Extract

-- COMMAND ----------

DELETE FROM bronze.orders WHERE _load_date = DATE '${run_date}';

INSERT INTO bronze.orders
SELECT
    order_id,
    customer_id,
    order_date,
    status,
    updated_date,
    DATE '${run_date}' AS _load_date,
    current_timestamp() AS _ingested_at,
    '${volume_path}/${run_date}/orders.csv' AS _source_file
FROM read_files(
    '${volume_path}/${run_date}/orders.csv',
    format => 'csv',
    header => true,
    inferSchema => false
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Ingest Order Items Extract

-- COMMAND ----------

DELETE FROM bronze.order_items WHERE _load_date = DATE '${run_date}';

INSERT INTO bronze.order_items
SELECT
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    updated_date,
    DATE '${run_date}' AS _load_date,
    current_timestamp() AS _ingested_at,
    '${volume_path}/${run_date}/order_items.csv' AS _source_file
FROM read_files(
    '${volume_path}/${run_date}/order_items.csv',
    format => 'csv',
    header => true,
    inferSchema => false
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Validation & Row Count Auditing
-- MAGIC 
-- MAGIC Inspect row counts for `${run_date}` across all 5 Bronze tables using `UNION ALL`.
-- MAGIC 
-- MAGIC **Expected counts for `2026-09-17` (Initial Batch)**:
-- MAGIC - `customers`: 16 rows (including 1 duplicate ID)
-- MAGIC - `products`: 16 rows (including invalid prices)
-- MAGIC - `product_category`: 12 rows (including 1 duplicate subcategory code)
-- MAGIC - `orders`: 18 rows
-- MAGIC - `order_items`: 36 rows

-- COMMAND ----------

SELECT 'customers' AS table_name, count(*) AS row_count
FROM bronze.customers WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'products', count(*) FROM bronze.products WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'product_category', count(*) FROM bronze.product_category WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'orders', count(*) FROM bronze.orders WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'order_items', count(*) FROM bronze.order_items WHERE _load_date = DATE '${run_date}'
ORDER BY table_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 7: Data Quality Exploration (Dirty Data Captured Verbatim)
-- MAGIC 
-- MAGIC Verify that Bronze safely preserved intentionally dirty records (e.g. `'bad_price'`, `'-25.00'`, missing category code).
-- MAGIC In Bronze, these records land as raw text without throwing cast exceptions.

-- COMMAND ----------

SELECT 
    product_id,
    product_name,
    subcategory_code,
    unit_price,
    _load_date,
    _source_file
FROM bronze.products
WHERE _load_date = DATE '${run_date}'
  AND (unit_price IN ('bad_price', '-25.00') OR subcategory_code IS NULL OR trim(subcategory_code) = '');

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Ingested all raw CSV extracts for batch date `${run_date}` into Delta Lake tables in `${catalog_name}.bronze`.
-- MAGIC - Demonstrated the **Idempotent Ingestion Pattern** (`DELETE` + `INSERT`) guaranteeing repeatable execution.
-- MAGIC - Attached audit columns (`_load_date`, `_ingested_at`, `_source_file`) for full data lineage.
-- MAGIC 
-- MAGIC **Next Step**: Open [`02_silver.sql`](./02_silver.sql) with the same `run_date` to clean, standardize, validate, and merge records into the Silver layer.
