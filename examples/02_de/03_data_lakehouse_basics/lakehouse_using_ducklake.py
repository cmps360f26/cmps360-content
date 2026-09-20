import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md("""
    # 🏰 Lakehouse Storage Layer with DuckLake & DuckDB Catalog

    This notebook provides a hands-on guide to **DuckLake** as a modern Lakehouse storage layer using **DuckDB** for both compute engine and metadata catalog.

    ---

    ## 🎯 Objectives & Core Capabilities
    - **Lakehouse Catalog (`hr_lake`) & Decoupled Storage**: Store metadata in `lakehouse/hr_lake_catalog.db` and raw data files as Parquet in `lakehouse/hr_lake_data/`.
    - **Transactions (ACID Atomicity & Consistency)**: Execute multi-statement writes safely with atomic commits and rollbacks. Each commit can record an author and a `set_commit_message(...)` note in the snapshot log.
    You can view the parquet files using many tools such as https://github.com/mukunku/ParquetViewer/
    - **Time Travel**: Query past versions and historical snapshots of tables without restoring backups.
    - **Schema Evolution**: Modify table structures in-place (e.g., adding a performance rating column or renaming `salary` to `monthly_salary`) without rewriting existing Parquet data files.

    ---

    ## 📌 DuckDB Engine vs. DuckLake Storage Layer
    | | **DuckDB** | **DuckLake** |
    | :--- | :--- | :--- |
    | Role |Analytical SQL engine (parse, plan, compute) | Lakehouse storage layer |
    | This session | In-memory compute | Extension for DuckDB that manages metadata Catalog, ACID transactions + Parquet files on disk |
    | Persistence | Lost when the notebook stops | Kept in `lakehouse/` |
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    DuckDB is the only runtime dependency required by this notebook. Install it once in the selected Python environment if needed:

    `pip install duckdb`
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Section 1: Install DuckLake Extension & DuckDB Catalog Configuration
    - **Extension Required**: `ducklake` (installed and loaded by the SQL cells below).
    - **Catalog**: `lakehouse/hr_lake_catalog.db` stores table schemas, snapshots, transactions, and file tracking.
    - **Data Path**: `lakehouse/hr_lake_data/` stores the physical Parquet data files.
    - DuckLake persists the catalog and Parquet data on disk.
    - **Path Handling**: Absolute paths are used so output location does not depend on the current working directory.
    """)
    return


@app.cell
def _():
    import duckdb
    import marimo as mo

    return duckdb, mo


@app.cell
def _(duckdb):
    # 1.1 Reset the local lakehouse so this notebook starts from a known state.
    # WARNING: This deletes the catalog and all Parquet data from earlier runs.
    import os
    import shutil

    # Release a previous attach so catalog files can be deleted on re-run.
    try:
        duckdb.sql("DETACH DATABASE IF EXISTS hr_lake;")
    except Exception as e:
        print(f"Detach hr_lake catalog failed: {e}")
        # Take no action and continues running
        pass

    DATA_LAKE_DIR = "lakehouse"
    CATALOG_DB = os.path.join(DATA_LAKE_DIR, "hr_lake_catalog.db")
    DATA_DIRECTORY = os.path.join(DATA_LAKE_DIR, "hr_lake_data")

    if os.path.exists(DATA_LAKE_DIR):
        shutil.rmtree(DATA_LAKE_DIR)
    os.makedirs(DATA_DIRECTORY, exist_ok=True)

    # Absolute POSIX paths avoid VS Code cwd surprises and backslash-escape issues in SQL.
    catalog_db_path = os.path.abspath(CATALOG_DB).replace("\\", "/")
    data_directory_path = os.path.abspath(DATA_DIRECTORY).replace("\\", "/")

    print(f"Fresh lakehouse created at {os.path.abspath(DATA_LAKE_DIR)}")
    print(f"Catalog (DuckLake metadata): {catalog_db_path}")
    print(f"Data path (Parquet files):   {data_directory_path}")
    return catalog_db_path, data_directory_path


@app.cell
def _(mo):
    mo.md(r"""
    ### 1.2 Attach DuckLake as the `hr_lake` catalog

    This SQL cell loads the DuckLake extension and mounts the lakehouse so later queries run against it.

    - **`INSTALL ducklake` / `LOAD ducklake`**: Download (once) and enable the DuckLake extension in this DuckDB session.
    - **`ATTACH ... AS hr_lake (TYPE DUCKLAKE, DATA_PATH ...)`**: Register a DuckLake catalog named `hr_lake`. Metadata (schemas, snapshots, transactions, file tracking) is stored in `hr_lake_catalog.db`. Physical table data is stored as Parquet files under `hr_lake_data/`.
    - **`USE hr_lake`**: Make `hr_lake` the default database so `CREATE TABLE employees` and later SQL refer to the lakehouse without a catalog prefix.

    DuckDB itself stays in memory. DuckLake is what persists the catalog and Parquet files on disk.
    """)
    return


@app.cell
def _(catalog_db_path, data_directory_path, mo):
    _df = mo.sql(
        f"""
        INSTALL ducklake;
        LOAD ducklake;

        ATTACH '{catalog_db_path}' AS hr_lake (
            TYPE DUCKLAKE,
            DATA_PATH '{data_directory_path}');

        USE hr_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    DuckLake catalog attached as `hr_lake`. The storage layer is ready.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### 1.3 Create the employee table in DuckLake and add a few rows
    Optional - Call `hr_lake.set_commit_message(author, message)` **inside the open transaction, before `COMMIT`**. DuckLake stores that author and message on the snapshot, which you will query later with `ducklake_snapshots('hr_lake')`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;
        CREATE TABLE employees (
            id INTEGER,
            first_name VARCHAR,
            last_name VARCHAR,
            department VARCHAR,
            salary INTEGER
        );

        CALL hr_lake.set_commit_message(
            'admin',
            'employees table created'
        );
        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        INSERT INTO employees VALUES
        (1, 'Tariq', 'Al-Ali', 'Engineering', 32000),
        (2, 'Fatima', 'Al-Zahra', 'Marketing', 24000);

        CALL hr_lake.set_commit_message(
            'admin',
            '2 new employees added'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees ORDER BY id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🔄 Section 2: Transactions (ACID Multi-Statement Writes)

    ### Concept Explanation
    - **Atomicity**: All SQL statements inside `BEGIN TRANSACTION` commit together or roll back cleanly if an error occurs.
    - **Consistency**: Protects the catalog and storage layer against partial updates, ensuring incomplete writes never become visible.

    ### Realistic Demonstration Scenarios
    1. **Successful Transaction (`COMMIT`)**: Increase salary of Tariq Al-Ali and inserts a new employee, Omar Al-Farooq.
    2. **Failed Transaction (`ROLLBACK`)**: Simulates a realistic payroll calculation error (division by zero during a batch bonus calculation). The exception triggers `ROLLBACK`, leaving the dataset completely unchanged.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### 2.1. Group a salary update and an employee insert into one commit

    Both changes become visible together, which demonstrates atomicity. The `set_commit_message` call tags that snapshot with an author and a short description.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        UPDATE employees SET salary = 35000 WHERE first_name = 'Tariq';

        INSERT INTO employees VALUES (3, 'Omar', 'Al-Farooq', 'Engineering', 28000);

        CALL hr_lake.set_commit_message(
            'admin',
            'Raise Tariq salary and add Omar Al-Farooq'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees ORDER BY id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### 2.2. Force an error after a salary update and roll back the whole transaction

    The update to Tariq must be rolled back due to the failed bonus calculation.

    DuckDB SQL has no `try`/`except` support. If one statement fails, execution stops with no way to catch the error and run `ROLLBACK` afterward. The next cell uses Python exception handling for that cleanup.
    """)
    return


@app.cell
def _(duckdb):
    # Why a Python cell instead of a SQL cell?
    # DuckDB SQL has no try/except support — if one statement fails, execution just stops
    # and the error propagates with no way to catch it and clean up afterward.
    # Python's try/except lets us catch that error and run ROLLBACK ourselves.
    try:
        duckdb.sql("BEGIN TRANSACTION;")
        duckdb.sql("""
            UPDATE employees SET salary = 38000 WHERE id = 1;
        """)
        duckdb.sql("""
            UPDATE employees SET salary = salary + (10000 / 0) WHERE department = 'Engineering';
        """)
        duckdb.sql("COMMIT;")
    except Exception as error:
        duckdb.sql("ROLLBACK;")
        print(f"Expected payroll error; transaction rolled back: {error}")
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees ORDER BY id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## ⏱️ Section 3: Time Travel (Querying Historical Snapshots)

    ### Concept Explanation
    - **Snapshot Ledger**: DuckLake tracks immutable snapshot IDs in `hr_lake_catalog.db` whenever a transaction commits.
    - **Time Travel Queries**: Query previous versions of a table using `AT (VERSION => n)` without making file copies or restoring database backups.

    ### Demonstration Steps
    1. Inspect the snapshot log using `ducklake_snapshots('hr_lake')`. Each successful write that called `set_commit_message` shows an author and a commit message.
    2. Query **VERSION 2** (the initial state containing Tariq & Fatima before Omar was added).
    3. Compare with the current version.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            snapshot_id,
            CAST(snapshot_time AS VARCHAR) AS snapshot_time,
            author,
            commit_message
        FROM ducklake_snapshots('hr_lake');
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Step 3B: Read the version before Omar was added, then read the current table

    The historical query is read-only; it does not restore or modify the table.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees AT (VERSION => 3);
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Date-based time travel example
        -- DuckLake picks the latest snapshot whose snapshot_time is at or before that timestamp.
        -- Date-based time travel: 180 milliseconds before the current time
        SELECT * FROM employees
            AT (TIMESTAMP => current_timestamp - INTERVAL 180 MILLISECOND);
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees ORDER BY id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🧬 Section 4: Zero-Copy Schema Evolution

    ### Concept Explanation
    - **In-Place Metadata Updates**: Adding a column (`ALTER TABLE ... ADD COLUMN`) or renaming a column (`ALTER TABLE ... RENAME COLUMN`) updates the catalog schema in `hr_lake_catalog.db` without rewriting existing raw Parquet data files in `hr_lake_data/`.
    - **Backward Compatibility**: Existing records automatically display `NULL` / `NaN` for newly added columns until updated.

    ### Demonstration Steps
    1. Add `performance_rating DOUBLE` column.
    2. Rename `salary` to `monthly_salary`.
    3. Insert a new record (`Layla Mahmoud`) containing all 6 columns.
    4. Inspect the evolved table structure.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;
            ALTER TABLE employees ADD COLUMN performance_rating DOUBLE;
            ALTER TABLE employees RENAME COLUMN salary TO monthly_salary;
        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        INSERT INTO employees (id, first_name, last_name, department, monthly_salary, performance_rating)
        VALUES (4, 'Layla', 'Mahmoud', 'HR', 30000, 4.9);

        CALL hr_lake.set_commit_message(
            'admin',
            'Add Layla Mahmoud after schema evolution'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM employees ORDER BY id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 📁 Section 5: Verification & Local Workspace Structure

    Inspect your workspace directory structure after running this notebook to observe the decoupled storage design:

    - **`lakehouse/hr_lake_catalog.db`**: The DuckDB relational catalog database managing table schemas, active snapshots, transactions, and file tracking.
    - **`lakehouse/hr_lake_data/`**: A folder containing raw, queryable,  **Parquet files**.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Flush inlined rows to Parquet files on disk
        CALL ducklake_flush_inlined_data('hr_lake');
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM ducklake_list_files('hr_lake', 'employees');
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 📊 Section 6: DuckDB Engine vs. DuckLake Storage Layer Summary

    | Feature / Capability | DuckDB Engine | DuckLake Storage Layer (`hr_lake`) |
    | :--- | :--- | :--- |
    | **Primary Role** | SQL Parsing, Query Execution, In-Memory Computation | Catalog Ledger, Snapshot History, Parquet Data Layout |
    | **Catalog Database** | Default DuckDB system catalog | Dedicated `lakehouse/hr_lake_catalog.db` metadata database |
    | **Transactions** | Session-level in-memory ACID | Multi-file ACID commits logged to catalog ledger |
    | **Time Travel** | Not available for standard table structures | Instant historical queries via `AT (VERSION => n)` |
    | **Schema Evolution** | Session table schema changes | Zero-copy schema evolution without rewriting Parquet files |
    | **Storage Layout** | Monolithic local `.duckdb` file | Decoupled metadata catalog (`lakehouse/hr_lake_catalog.db`) & folder storage (`lakehouse/hr_lake_data/`) |
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🏁 Section 7: Key Takeaways & Conclusion

    1. ** Catalog & Storage Decoupling**: DuckLake separates metadata management (`lakehouse/hr_lake_catalog.db`) from raw data storage (`lakehouse/hr_lake_data/`).
    2. **ACID Transactions**: Standard SQL transactions (`BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`) ensure data integrity and rollback failed transactions. `set_commit_message(author, message)` records who changed what on each snapshot.
    3. **Time Travel**: Snapshot logs track every commit, allowing instant time-travel queries via `AT (VERSION => n)`.
    4. **Zero-Copy Schema Evolution**: Table schemas evolve in-place with `ALTER TABLE` (`ADD COLUMN`, `RENAME COLUMN`) without rewriting existing Parquet files.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🔌 Section 8: Release the Catalog for DuckDB CLI

    Run the cell first to release the `hr_lake` catalog, then restart the notebook kernel.

    You can connect the `hr_lake` from the common line using:
    ```powershell
    duckdb
    ```

    ```sql
    INSTALL ducklake;
    LOAD ducklake;

    ATTACH 'lakehouse/hr_lake_catalog.db' AS hr_lake (
        TYPE DUCKLAKE
    );

    SHOW DATABASES;
    USE hr_lake;
    SHOW TABLES;
    SELECT * FROM employees;
    ```
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Release the lakehouse catalog 
        Use memory;
        -- Detaching hr_lake releases its catalog and associated file handles.
        DETACH DATABASE IF EXISTS hr_lake;
        SHOW DATABASES;
        """
    )
    return


if __name__ == "__main__":
    app.run()
