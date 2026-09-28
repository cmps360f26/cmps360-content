-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 00 - Lakehouse Environment Setup
-- MAGIC 
-- MAGIC Welcome to the **Databricks Lakehouse** implementation of the Retail Sales Medallion Architecture!
-- MAGIC 
-- MAGIC This notebook initializes the lakehouse environment using **Databricks Unity Catalog** and **Delta Lake**.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Why Medallion Architecture?
-- MAGIC In enterprise data platforms, data rarely arrives clean, validated, and ready for reporting. The Medallion Architecture solves this by progressively curating data across three distinct tiers:
-- MAGIC 
-- MAGIC | Layer | Unity Catalog Object | Purpose | Storage & Format |
-- MAGIC | :--- | :--- | :--- | :--- |
-- MAGIC | **Landing Zone** | `sales_lake.bronze.landing_zone` | Raw file storage for daily incoming batch CSV extracts | Unity Catalog Volume (FUSE-mounted cloud storage) |
-- MAGIC | **Bronze** | `sales_lake.bronze` | Raw extracts landed **as-is** (`STRING` schema) + ingestion audit metadata | Delta Lake Tables (Append-only raw history) |
-- MAGIC | **Silver** | `sales_lake.silver` | Cleaned, validated, strongly typed, and deduplicated business entities | Delta Lake Tables (Curated master data & facts) |
-- MAGIC | **Quarantine** | `sales_lake.quarantine` | Invalid or corrupt records that failed quality gates, with explicit rejection reasons | Delta Lake Tables (Isolated holding area for data governance) |
-- MAGIC | **Gold** | `sales_lake.gold` | Kimball Star Schema dimensional model (facts & dimensions) for BI dashboards and analytics | Delta Lake Tables (Analytical star schema) |
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Core Concept: The Unity Catalog Three-Level Namespace
-- MAGIC Databricks Unity Catalog organizes all data assets into a 3-level hierarchy:
-- MAGIC 
-- MAGIC $$\text{catalog} \longrightarrow \text{schema (database)} \longrightarrow \text{table / view / volume}$$
-- MAGIC 
-- MAGIC For example: `sales_lake.bronze.customers` or `/Volumes/sales_lake/bronze/landing_zone`.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Architectural Contrast: Local DuckLake vs. Cloud Databricks
-- MAGIC | Architecture Dimension | DuckLake (Embedded / Local) | Databricks (Cloud Lakehouse) |
-- MAGIC | :--- | :--- | :--- |
-- MAGIC | **Metastore / Governance** | Local SQLite file (`sales_lake_catalog.db`) | **Unity Catalog** centralized cloud metastore |
-- MAGIC | **Table Storage** | Local Parquet folder (`sales_lake_data/`) | **Delta Lake** on cloud object storage (S3 / ADLS / GCS) |
-- MAGIC | **File Landing** | Local folder (`landing_zone/sales_data/`) | **Unity Catalog Volumes** (`/Volumes/...`) |
-- MAGIC | **Transactions** | Explicit `BEGIN TRANSACTION` / `COMMIT` | Automatic ACID transactions via `_delta_log` |
-- MAGIC | **Concurrency** | Single-process (requires `DETACH DATABASE`) | Multi-user distributed queries with Optimistic Concurrency Control |
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Execution Roadmap
-- MAGIC 1. **Setup & Schemas (`setup/`)**: `00_setup.sql` &rarr; `00.1_bronze_schema.sql` &rarr; `00.2_silver_schema.sql` &rarr; `00.3_gold_schema.sql` &rarr; `00.4_load_landing_files.py`
-- MAGIC 2. **Bronze Ingestion (`pipeline/`)**: `01_bronze.sql` (Raw batch ingestion from Volumes into Delta tables)
-- MAGIC 3. **Silver Cleansing (`pipeline/`)**: `02_silver.sql` (Cleansing, deduplication, quarantine routing, and `MERGE INTO`)
-- MAGIC 4. **Gold Star Schema (`pipeline/`)**: `03_gold.sql` (Calendar generation, dimensional modeling, and fact `MERGE INTO`)
-- MAGIC 5. **Analytics & KPIs (`analysis/`)**: `04_answer_questions.sql` (8 business and operational KPI queries)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Configure Notebook Widgets
-- MAGIC 
-- MAGIC Databricks widgets parameterize SQL notebooks. The `catalog_name` widget defaults to `sales_lake`.
-- MAGIC 
-- MAGIC > **Classroom Tip**: If your Databricks workspace restricts creating top-level catalogs, change the widget value to `workspace` or `main`. All downstream notebooks will adapt automatically!

-- COMMAND ----------

-- Create a text widget for catalog name parameterization
CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Create Unity Catalog & Medallion Schemas
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `IDENTIFIER(:catalog_name)`: Databricks SQL clause that interprets a string parameter or widget variable as an object identifier (catalog, schema, or table name) rather than a string literal.
-- MAGIC - `CREATE SCHEMA IF NOT EXISTS`: Idempotent DDL statement that creates a database schema only if it does not already exist, preventing runtime errors on repeated executions.

-- COMMAND ----------

-- 1. Create and select the catalog
CREATE CATALOG IF NOT EXISTS IDENTIFIER(:catalog_name)
COMMENT 'CMPS 360 Retail Sales Medallion Lakehouse Catalog';

USE CATALOG IDENTIFIER(:catalog_name);

-- COMMAND ----------

-- 2. Create Medallion layer schemas
CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Bronze Layer: Raw landing tables and pipeline run audit logs';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Silver Layer: Cleansed, validated, strongly typed, and deduplicated tables';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Gold Layer: Kimball Star Schema dimensional model (facts and dimensions)';

CREATE SCHEMA IF NOT EXISTS quarantine
COMMENT 'Quarantine Schema: Records rejected by Silver quality checks for remediation';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Create Unity Catalog Storage Volume for Raw Files
-- MAGIC 
-- MAGIC ### What is a Unity Catalog Volume?
-- MAGIC Volumes are governed storage objects representing directories in cloud storage. They allow data engineers to store and read unstructured or semi-structured raw files (CSVs, JSON, images) using standard POSIX paths:
-- MAGIC `/Volumes/<catalog>/<schema>/<volume_name>`

-- COMMAND ----------

-- Create a Volume under the bronze schema to hold incoming raw batch CSV extracts
CREATE VOLUME IF NOT EXISTS bronze.landing_zone
COMMENT 'Unity Catalog Volume storing raw daily CSV batch extracts';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Create Pipeline Execution Tracking Table
-- MAGIC 
-- MAGIC In production pipelines, orchestrators must know which batch dates have been processed.
-- MAGIC The `bronze.pipeline_runs` table tracks batch state across execution cycles:
-- MAGIC - `run_date DATE`: The batch date partition (e.g. `2026-09-17`).
-- MAGIC - `status STRING`: Pipeline state (`Pending`, `In progress`, `Completed`, `Failed`).
-- MAGIC - `processed_at TIMESTAMP`: Timestamp when the batch finished processing.

-- COMMAND ----------

CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
    run_date DATE COMMENT 'Batch extract date (YYYY-MM-DD)',
    status STRING COMMENT 'Execution state: Pending, In progress, Completed, Failed',
    processed_at TIMESTAMP COMMENT 'Timestamp of last status update'
)
USING DELTA
COMMENT 'Operational audit table tracking daily batch ingestion status';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Validate Catalog & Schemas
-- MAGIC 
-- MAGIC ### SQL Feature: `information_schema.schemata`
-- MAGIC The ANSI SQL standard metadata view providing programmatic information about all schemas in the active catalog.

-- COMMAND ----------

SELECT 
    catalog_name,
    schema_name,
    comment
FROM information_schema.schemata
WHERE catalog_name = :catalog_name
  AND schema_name IN ('bronze', 'silver', 'gold', 'quarantine')
ORDER BY schema_name;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Next Steps
-- MAGIC 
-- MAGIC - Initialized catalog `${catalog_name}` with Unity Catalog schemas: `bronze`, `silver`, `gold`, `quarantine`.
-- MAGIC - Created Unity Catalog Volume `bronze.landing_zone` for raw CSV extract files.
-- MAGIC - Created `bronze.pipeline_runs` Delta table for orchestrator state management.
-- MAGIC 
-- MAGIC **Next Step**: Run [`00.1_bronze_schema.sql`](./00.1_bronze_schema.sql) to define the Bronze Delta table structures.
