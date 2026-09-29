"""
Export Gold-Layer Tables to CSV
================================
A beginner-friendly script that exports all tables from the DuckLake Gold layer
(Star Schema) into individual CSV files.

Destination folder:
  lakehouse/sales_lake_data/gold/gold.csv/
"""

import os
import sys
import duckdb


def export_gold_tables_to_csv():
    # -------------------------------------------------------------------------
    # 1. Define Paths
    # -------------------------------------------------------------------------
    # Locate the script's directory and the lakehouse folders
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lakehouse_dir = os.path.join(base_dir, "lakehouse")

    catalog_path = os.path.abspath(
        os.path.join(lakehouse_dir, "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_path = os.path.abspath(
        os.path.join(lakehouse_dir, "sales_lake_data")
    ).replace("\\", "/")

    # The existing Gold-layer directory and the target 'gold.csv' subfolder
    gold_dir = os.path.join(data_path, "gold")
    output_dir = os.path.join(gold_dir, "gold.csv")

    # Verify that the DuckLake catalog exists before proceeding
    if not os.path.exists(catalog_path):
        print(f"Error: DuckLake catalog not found at: {os.path.normpath(catalog_path)}")
        print("Please run the pipeline first (e.g., 'python run_pipeline.py').")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # 2. Create the Destination Folder
    # -------------------------------------------------------------------------
    # Automatically create the 'gold.csv' subfolder if it does not exist yet
    os.makedirs(output_dir, exist_ok=True)
    print(f"Export directory: {os.path.normpath(output_dir)}")

    # -------------------------------------------------------------------------
    # 3. Connect to DuckDB and Attach DuckLake Catalog
    # -------------------------------------------------------------------------
    con = duckdb.connect()

    try:
        # Load the DuckLake extension and attach our lakehouse catalog
        con.sql(f"""
            INSTALL ducklake;
            LOAD ducklake;
            ATTACH '{catalog_path}' AS sales_lake (
                TYPE DUCKLAKE,
                DATA_PATH '{data_path}',
                OVERRIDE_DATA_PATH TRUE
            );
            USE sales_lake;
        """)

        # ---------------------------------------------------------------------
        # 4. Discover All Gold-Layer Tables
        # ---------------------------------------------------------------------
        # Query information_schema to find all table names in the 'gold' schema
        tables_result = con.sql("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'gold'
            ORDER BY table_name;
        """).fetchall()

        table_names = [row[0] for row in tables_result]

        if not table_names:
            print("No tables found in the 'gold' schema.")
            return

        print(f"Found {len(table_names)} Gold table(s) to export: {', '.join(table_names)}\n")

        # ---------------------------------------------------------------------
        # 5. Export Each Table to a CSV File
        # ---------------------------------------------------------------------
        for table_name in table_names:
            # Name each CSV file after its table (e.g., dim_customer.csv)
            csv_path = os.path.join(output_dir, f"{table_name}.csv").replace("\\", "/")

            # COPY exports the table preserving exact column names and values
            con.sql(f"""
                COPY gold.{table_name} TO '{csv_path}' (HEADER, DELIMITER ',');
            """)

            # Count rows to provide a helpful summary
            row_count = con.sql(f"SELECT COUNT(*) FROM gold.{table_name}").fetchone()[0]
            print(f"  ✓ Exported '{table_name}' ({row_count:,} rows) -> {table_name}.csv")

        print("\nAll Gold-layer tables were successfully exported!")

    except Exception as ex:
        error_msg = str(ex)
        # Helpful guidance for students if another process has locked the catalog
        if "used by another process" in error_msg:
            print("\n" + "=" * 65)
            print("NOTE: DuckLake catalog file is currently locked by another process.")
            print("=" * 65)
            print("DuckLake is single-process. If you have an active session running")
            print("(such as 'start_server_for_powerbi.sql' in a terminal), please close")
            print("or stop it (Ctrl+C), then re-run this export script.")
            print("=" * 65)
        else:
            print(f"An error occurred: {ex}")
            raise
    finally:
        # Always close the connection to release file locks
        con.close()


if __name__ == "__main__":
    export_gold_tables_to_csv()
