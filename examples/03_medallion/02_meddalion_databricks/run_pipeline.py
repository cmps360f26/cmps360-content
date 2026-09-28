# Databricks notebook source
# MAGIC %md
# MAGIC # Pipeline Runner: Medallion Architecture Orchestrator
# MAGIC 
# MAGIC This notebook programmatically orchestrates the complete Databricks Medallion Lakehouse pipeline:
# MAGIC 1. **Initializes Catalog & Schemas** (optional or on first run).
# MAGIC 2. **Discovers Extract Batches** in the Unity Catalog Volume `/Volumes/<catalog_name>/bronze/landing_zone/`.
# MAGIC 3. **Tracks Execution State** in `sales_lake.bronze.pipeline_runs`.
# MAGIC 4. **Processes Batches Chronologically** through Bronze &rarr; Silver &rarr; Gold.
# MAGIC 5. **Guarantees Idempotency**: Re-running dates updates data in-place without generating duplicate records.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Configure Pipeline Widgets & Parameters
# MAGIC 
# MAGIC - `catalog_name`: Name of the Unity Catalog container (default: `sales_lake`).
# MAGIC - `target_date`: Process a single date (e.g., `2026-09-17`) or `ALL` to run all available batches.
# MAGIC - `init_catalog`: Set to `true` on the very first run to initialize schemas, tables, and raw data files.
# MAGIC - `rerun`: If `true`, forces reprocessing of batches already marked as `Completed`.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "sales_lake", "Catalog Name")
dbutils.widgets.text("target_date", "ALL", "Target Date (YYYY-MM-DD or ALL)")
dbutils.widgets.dropdown("init_catalog", "false", ["false", "true"], "Re-initialize Catalog & Schemas?")
dbutils.widgets.dropdown("rerun", "false", ["false", "true"], "Force Rerun Completed Dates?")

catalog_name = dbutils.widgets.get("catalog_name")
target_date = dbutils.widgets.get("target_date")
init_catalog_flag = dbutils.widgets.get("init_catalog").lower() == "true"
rerun_flag = dbutils.widgets.get("rerun").lower() == "true"

volume_path = f"/Volumes/{catalog_name}/bronze/landing_zone"

print("==================================================")
print("Medallion Pipeline Orchestrator Configuration")
print(f"  Catalog Name:      {catalog_name}")
print(f"  Volume Path:       {volume_path}")
print(f"  Target Date:       {target_date}")
print(f"  Re-init Catalog:   {init_catalog_flag}")
print(f"  Force Re-run:      {rerun_flag}")
print("==================================================")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Notebook Path Resolution Helper
# MAGIC 
# MAGIC Databricks `dbutils.notebook.run()` requires workspace paths. This helper resolves child notebook paths relative to the runner notebook's workspace location.

# COMMAND ----------

import os
import re
from datetime import datetime

try:
    notebook_context = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    current_notebook_path = notebook_context.notebookPath().get()
    base_dir = "/".join(current_notebook_path.split("/")[:-1])
except Exception:
    base_dir = "."

def get_notebook_path(relative_path: str) -> str:
    """Returns absolute workspace path to child notebooks."""
    clean_rel = relative_path.lstrip("./")
    if base_dir and base_dir != ".":
        return f"{base_dir}/{clean_rel}"
    return f"./{clean_rel}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: State Management & Audit Helpers
# MAGIC 
# MAGIC Uses Delta Lake `MERGE INTO` to track batch progress atomically in `bronze.pipeline_runs`.

# COMMAND ----------

def set_pipeline_status(run_date: str, status: str):
    """Updates batch execution status atomically in bronze.pipeline_runs table."""
    spark.sql(f"""
        MERGE INTO {catalog_name}.bronze.pipeline_runs AS t
        USING (SELECT DATE '{run_date}' AS run_date) AS s
            ON t.run_date = s.run_date
        WHEN MATCHED THEN UPDATE SET
            status = '{status}',
            processed_at = current_timestamp()
        WHEN NOT MATCHED THEN INSERT (run_date, status, processed_at)
        VALUES (s.run_date, '{status}', current_timestamp())
    """)

def get_available_dates():
    """Scans the Unity Catalog Volume for YYYY-MM-DD date subdirectories."""
    try:
        entries = dbutils.fs.ls(volume_path)
        date_folders = [
            e.name.rstrip("/") for e in entries 
            if e.isDir() and re.match(r"^\d{4}-\d{2}-\d{2}$", e.name.rstrip("/"))
        ]
        return sorted(date_folders)
    except Exception as e:
        print(f"Warning: Could not list {volume_path}. Error: {e}")
        return ["2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20"]

def sync_pipeline_dates():
    """Registers newly detected date folders as Pending in pipeline_runs."""
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.bronze.pipeline_runs (
            run_date DATE,
            status STRING,
            processed_at TIMESTAMP
        ) USING DELTA
    """)
    for d in get_available_dates():
        spark.sql(f"""
            MERGE INTO {catalog_name}.bronze.pipeline_runs AS t
            USING (SELECT DATE '{d}' AS run_date) AS s
                ON t.run_date = s.run_date
            WHEN NOT MATCHED THEN INSERT (run_date, status, processed_at)
            VALUES (s.run_date, 'Pending', NULL)
        """)

def print_status_table():
    """Displays a clean tabular overview of batch execution history."""
    df = spark.sql(f"""
        SELECT 
            CAST(run_date AS STRING) AS run_date,
            status,
            coalesce(CAST(processed_at AS STRING), '-') AS processed_at
        FROM {catalog_name}.bronze.pipeline_runs
        ORDER BY run_date
    """)
    print("\n" + "=" * 65)
    print("Pipeline Execution Status (sales_lake.bronze.pipeline_runs)")
    print("=" * 65)
    print(f"{'Run Date':<14} {'Status':<16} {'Processed At':<28}")
    print("-" * 65)
    for row in df.collect():
        print(f"{row.run_date:<14} {row.status:<16} {row.processed_at:<28}")
    print("=" * 65 + "\n")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Optional Lakehouse Schema Initialization
# MAGIC 
# MAGIC Runs when `init_catalog = true`. Executes setup notebooks in dependency order.

# COMMAND ----------

INIT_NOTEBOOKS = [
    "setup/00_setup",
    "setup/00.1_bronze_schema",
    "setup/00.2_silver_schema",
    "setup/00.3_gold_schema",
    "setup/00.4_load_landing_files"
]

if init_catalog_flag:
    print("\nInitializing Lakehouse Catalog, Schemas, and Volume...")
    for nb in INIT_NOTEBOOKS:
        nb_path = get_notebook_path(nb)
        print(f"  Running: {nb_path}...")
        dbutils.notebook.run(
            nb_path,
            timeout_seconds=600,
            arguments={"catalog_name": catalog_name, "volume_path": volume_path}
        )
    print("✓ Lakehouse successfully initialized.\n")

# Sync date folders with tracking table
sync_pipeline_dates()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Determine Dates to Process

# COMMAND ----------

available_dates = get_available_dates()

if target_date != "ALL":
    if target_date not in available_dates:
        raise ValueError(f"Target date {target_date} not found in {volume_path}. Available: {available_dates}")
    dates_to_run = [target_date]
elif rerun_flag:
    dates_to_run = available_dates
else:
    # Process only dates that are not Completed
    status_df = spark.sql(f"SELECT CAST(run_date AS STRING) AS r_date, status FROM {catalog_name}.bronze.pipeline_runs")
    status_map = {row.r_date: row.status for row in status_df.collect()}
    dates_to_run = [d for d in available_dates if status_map.get(d) != "Completed"]

print(f"Dates to process in this run: {dates_to_run}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Execute Medallion Pipeline (Bronze &rarr; Silver &rarr; Gold)

# COMMAND ----------

PIPELINE_STAGES = [
    ("Bronze", "pipeline/01_bronze"),
    ("Silver", "pipeline/02_silver"),
    ("Gold",   "pipeline/03_gold")
]

if not dates_to_run:
    print("All available dates are already marked as Completed.")
    print("Set 'rerun' parameter to 'true' or specify a 'target_date' to reprocess.")
else:
    for batch_date in dates_to_run:
        print(f"\n==================================================")
        print(f"Processing Batch Date: {batch_date}")
        print(f"==================================================")
        set_pipeline_status(batch_date, "In progress")
        
        batch_failed = False
        for stage_name, stage_nb in PIPELINE_STAGES:
            nb_path = get_notebook_path(stage_nb)
            print(f"  --> Executing {stage_name} layer ({nb_path})...")
            try:
                dbutils.notebook.run(
                    nb_path,
                    timeout_seconds=900,
                    arguments={
                        "catalog_name": catalog_name,
                        "run_date": batch_date,
                        "volume_path": volume_path
                    }
                )
                print(f"  ✓ {stage_name} completed.")
            except Exception as ex:
                print(f"  ✗ {stage_name} FAILED for date {batch_date}!")
                print(f"    Error: {ex}")
                set_pipeline_status(batch_date, "Failed")
                batch_failed = True
                break
                
        if not batch_failed:
            set_pipeline_status(batch_date, "Completed")
            print(f"✓ Batch date {batch_date} successfully completed through all Medallion layers!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Final Pipeline Status Summary

# COMMAND ----------

print_status_table()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary & Next Steps
# MAGIC - The Medallion Lakehouse has been executed end-to-end.
# MAGIC - Open [`analysis/04_answer_questions.sql`](./analysis/04_answer_questions.sql) to query the Gold Star Schema and inspect business KPIs!
