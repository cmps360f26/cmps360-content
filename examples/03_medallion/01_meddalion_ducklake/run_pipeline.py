"""
Pipeline Runner: Medallion Architecture (Bronze -> Silver -> Gold)
==================================================================

This script executes the Medallion Lakehouse pipeline programmatically:
  1. Discovers batch extract folders in data/ (e.g. data/2026-09-17).
  2. Tracks execution state in the SQL table `bronze.pipeline_runs`.
  3. Processes pending dates chronologically through Bronze -> Silver -> Gold.
  4. Executes the exact same Marimo notebooks used interactively in class.
  5. Guarantees idempotency: rerunning updates data in-place without duplicates.

Usage:
  python run_pipeline.py                 # Process all pending dates
  python run_pipeline.py --date 2026-09-17 # Process a single date
  python run_pipeline.py --status        # Show state table without processing
  python run_pipeline.py --rerun         # Force re-run of completed dates
  python run_pipeline.py --init          # Initialize lakehouse schemas first
"""

import argparse
import os
import re
import subprocess
import sys
import duckdb

# Configure UTF-8 console output for cross-platform compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. Configuration & Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "landing_zone", "sales_data")
LAKEHOUSE_DIR = os.path.join(BASE_DIR, "lakehouse")
CATALOG_PATH = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "sales_lake_catalog.db")).replace("\\", "/")
DATA_PATH = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "sales_lake_data")).replace("\\", "/")

# Medallion layers executed in sequence for each processing date
LAYERS = [
    ("Bronze", os.path.join("pipeline", "01_bronze.py")),
    ("Silver", os.path.join("pipeline", "02_silver.py")),
    ("Gold",   os.path.join("pipeline", "03_gold.py")),
]

# Initialization notebooks required before processing data
INIT_SCRIPTS = [
    os.path.join("setup", "00_setup.py"),
    os.path.join("setup", "00.1_bronze_schema.py"),
    os.path.join("setup", "00.2_silver_schema.py"),
    os.path.join("setup", "00.3_gold_schema.py"),
]


# ---------------------------------------------------------------------------
# 2. Database & State Tracking Helpers
# ---------------------------------------------------------------------------
def run_sql(sql: str, fetch: bool = False):
    """
    Executes SQL against DuckLake and safely closes the connection.
    Closing the connection ensures file locks are released for notebook runs.
    """
    con = duckdb.connect()
    try:
        con.sql(f"""
            INSTALL ducklake; LOAD ducklake;
            ATTACH '{CATALOG_PATH}' AS sales_lake (
                TYPE DUCKLAKE, DATA_PATH '{DATA_PATH}', OVERRIDE_DATA_PATH TRUE
            );
            USE sales_lake;
        """)
        res = con.sql(sql)
        return res.fetchall() if fetch and res is not None else None
    finally:
        con.close()


def init_pipeline_runs():
    """Ensures the bronze.pipeline_runs table exists for state tracking."""
    run_sql("""
        CREATE SCHEMA IF NOT EXISTS bronze;
        CREATE TABLE IF NOT EXISTS bronze.pipeline_runs (
            run_date DATE,
            status VARCHAR,          -- 'Pending', 'In progress', 'Completed', 'Failed'
            processed_at TIMESTAMP   -- Last status transition timestamp
        );
    """)


def set_status(run_date: str, status: str):
    """
    Updates the state of a batch run date (idempotent delete-then-insert).
    DuckLake does not support PRIMARY KEY constraints, so we manage uniqueness via SQL.
    """
    run_sql(f"""
        DELETE FROM bronze.pipeline_runs WHERE run_date = DATE '{run_date}';
        INSERT INTO bronze.pipeline_runs VALUES (DATE '{run_date}', '{status}', current_timestamp);
    """)


def get_available_dates():
    """Finds all YYYY-MM-DD date extract folders in the data/ directory."""
    if not os.path.exists(DATA_DIR):
        return []
    return sorted([
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d)) and re.match(r"^\d{4}-\d{2}-\d{2}$", d)
    ])


def sync_dates():
    """Registers any new date folders in bronze.pipeline_runs with status 'Pending'."""
    init_pipeline_runs()
    for d in get_available_dates():
        run_sql(f"""
            INSERT INTO bronze.pipeline_runs (run_date, status, processed_at)
            SELECT DATE '{d}', 'Pending', NULL
            WHERE NOT EXISTS (
                SELECT 1 FROM bronze.pipeline_runs WHERE run_date = DATE '{d}'
            );
        """)


def print_status():
    """Displays a formatted summary table of all pipeline runs."""
    init_pipeline_runs()
    rows = run_sql("""
        SELECT
            CAST(run_date AS VARCHAR),
            status,
            coalesce(CAST(processed_at AS VARCHAR), '-')
        FROM bronze.pipeline_runs
        ORDER BY run_date;
    """, fetch=True)

    print("\n" + "=" * 60)
    print("Pipeline Execution Status (bronze.pipeline_runs)")
    print("=" * 60)
    print(f"{'Run Date':<14} {'Status':<16} {'Processed At':<26}")
    print("-" * 60)
    if not rows:
        print("No runs recorded yet.")
    else:
        for date, status, processed_at in rows:
            print(f"{date:<14} {status:<16} {processed_at:<26}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# 3. Notebook Execution Helpers
# ---------------------------------------------------------------------------
def get_python_exe() -> str:
    """Returns path to the Python executable, preferring the active virtualenv."""
    venv_python = os.path.expanduser("~/.venvs/py-env/Scripts/python.exe")
    return venv_python if os.path.exists(venv_python) else sys.executable


def run_notebook(script_name: str, run_date: str = None) -> bool:
    """
    Executes a Marimo notebook script as a standalone process.
    Passes run_date as a CLI argument and as the RUN_DATE environment variable.
    """
    script_path = os.path.join(BASE_DIR, script_name)
    cmd = [get_python_exe(), script_path]
    env = os.environ.copy()

    if run_date:
        cmd.append(run_date)
        env["RUN_DATE"] = run_date

    res = subprocess.run(cmd, cwd=BASE_DIR, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"\n    [Error executing {script_name}]")
        for line in res.stderr.strip().splitlines()[-5:]:
            print(f"    {line}")
        return False
    return True


def init_catalog() -> bool:
    """Runs the setup and schema creation notebooks to prepare the lakehouse."""
    print("\nInitializing DuckLake Catalog and Schema Definitions...")
    for script in INIT_SCRIPTS:
        print(f"  Running {script}...")
        if not run_notebook(script):
            print(f"  ✗ Failed on {script}.")
            return False
    print("✓ Catalog schemas and tables successfully initialized.\n")
    return True


def process_date(run_date: str) -> bool:
    """
    Runs Bronze -> Silver -> Gold layers sequentially for a single date.
    Updates bronze.pipeline_runs state before and after execution.
    """
    print(f"Processing {run_date}")
    set_status(run_date, "In progress")

    for layer_name, script_name in LAYERS:
        if not run_notebook(script_name, run_date):
            print(f"  ✗ {layer_name}")
            set_status(run_date, "Failed")
            print(f"\nPipeline halted: {layer_name} failed for date {run_date}.\n")
            return False
        print(f"  ✓ {layer_name}")

    set_status(run_date, "Completed")
    print()
    return True


# ---------------------------------------------------------------------------
# 4. Pipeline Orchestration & CLI
# ---------------------------------------------------------------------------
def get_dates_to_process(target_date: str = None, rerun: bool = False):
    """Determines which dates need processing based on CLI options and state."""
    available = get_available_dates()
    if target_date:
        if target_date not in available:
            print(f"Error: Date '{target_date}' not found in {DATA_DIR}.")
            print(f"Available dates: {', '.join(available) if available else 'None'}")
            return []
        return [target_date]

    if rerun:
        return available

    # Only process dates that are not yet Completed (Pending or Failed)
    rows = run_sql("SELECT CAST(run_date AS VARCHAR), status FROM bronze.pipeline_runs", fetch=True)
    status_map = dict(rows) if rows else {}
    return [d for d in available if status_map.get(d) != "Completed"]


def main():
    parser = argparse.ArgumentParser(description="Medallion Lakehouse Pipeline Runner")
    parser.add_argument("--date", help="Process a specific date (e.g. 2026-09-17)")
    parser.add_argument("--rerun", action="store_true", help="Re-process all dates even if completed")
    parser.add_argument("--status", action="store_true", help="Display pipeline run status table")
    parser.add_argument("--init", action="store_true", help="Re-initialize lakehouse catalog and schemas")
    args = parser.parse_args()

    # Mode 1: Display status only
    if args.status:
        if not os.path.exists(CATALOG_PATH):
            print(f"Catalog not found at {CATALOG_PATH}. Run with --init first.")
            return
        print_status()
        return

    # Mode 2: Initialize catalog if requested or missing
    if args.init or not os.path.exists(CATALOG_PATH):
        if not init_catalog():
            sys.exit(1)

    # Sync available data folders with state table
    sync_dates()

    available = get_available_dates()
    if not available:
        print(f"Error: No date extract folders (YYYY-MM-DD) found in {DATA_DIR}.")
        return

    # Determine dates to process
    dates = get_dates_to_process(target_date=args.date, rerun=args.rerun)
    if not dates:
        print("All available dates have already been successfully processed.")
        print("Use --rerun to re-process completed dates, or specify --date YYYY-MM-DD.")
        print_status()
        return

    print("\n" + "=" * 50)
    print(f"Running Medallion Pipeline for: {', '.join(dates)}")
    print("=" * 50 + "\n")

    # Process each date chronologically
    for date in dates:
        if not process_date(date):
            break

    # Show final summary table
    print_status()


if __name__ == "__main__":
    main()
