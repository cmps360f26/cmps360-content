import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _(mo):
    mo.md(r"""
    ## 02 - Silver Layer: Clean and Validate

    Bronze stores raw extracts as text. Silver converts them into typed, trusted tables.

    Rows that fail validation are kept in the `quarantine` schema, along with the reason.

    #### Data loading flow
    1. Read Bronze rows with `_load_date = run_date`.
    2. Clean and validate using SQL.
    3. **MERGE** valid rows into Silver: update if the key exists, insert if new.
    4. Insert invalid rows into `quarantine`.
    #

    Silver is loaded incrementally: only new/changed rows for each run_date are processed (not all history).

    Ensure `run_date` matches in `01_bronze.py` and `03_gold.py`.
    """)
    return


@app.cell
def _():
    import os
    import marimo as mo

    # Keep this value in sync with 01_bronze.py and 03_gold.py
    run_date = "2026-09-18"

    catalog_db_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_catalog.db")
    ).replace("\\", "/")
    data_directory_path = os.path.abspath(
        os.path.join("lakehouse", "sales_lake_data")
    ).replace("\\", "/")

    if not os.path.exists(catalog_db_path):
        raise FileNotFoundError("DuckLake catalog not found. Run 00_setup.py first.")

    print(f"Building Silver for run_date = {run_date}")
    print(f"Only Bronze rows with _load_date = {run_date} will be processed.")
    return catalog_db_path, data_directory_path, mo, run_date


@app.cell
def _(mo):
    mo.md(r"""
    ### 1. Attach the DuckLake catalog
    """)
    return


@app.cell
def _(catalog_db_path, data_directory_path, mo):
    _df = mo.sql(
        f"""
        INSTALL ducklake;
        LOAD ducklake;

        USE memory;
        DETACH DATABASE IF EXISTS sales_lake;

        ATTACH '{catalog_db_path}' AS sales_lake (
            TYPE DUCKLAKE,
            DATA_PATH '{data_directory_path}'
        );

        USE sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 2. Understanding the MERGE Pattern
    The `MERGE INTO` command lets us update or insert rows in a table, depending on whether the key (like an ID) already exists:
    | What happens when?         | MERGE does this                    | Example                          |
    |---------------------- | -----------------------------------|----------------------------------|
    | Key is new            | `WHEN NOT MATCHED THEN INSERT`      | Adding new customer 16 on 18 Sep |
    | Key already exists    | `WHEN MATCHED THEN UPDATE`          | Updating address for customer 2  |

    **Important:**
    - Only create the Silver tables once using `CREATE TABLE IF NOT EXISTS`.
    - Do **not** use `CREATE OR REPLACE` every time. That would erase existing data!

    - Temporary scratch tables are made in memory for cleaning and preparing data.
    Only the good, cleaned rows are saved into DuckLake’s `silver` and `quarantine` tables on disk.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 3. Create typed Silver and Quarantine tables

    Bronze columns are all `VARCHAR`. Silver applies types: integers, decimals, dates.

    `CREATE TABLE IF NOT EXISTS` is safe to re-run. It does not delete existing Silver rows.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE TABLE IF NOT EXISTS silver.product_category (
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.customers (
            customer_id INTEGER,
            customer_name VARCHAR,
            email VARCHAR,
            city VARCHAR,
            country VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.products (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.orders (
            order_id INTEGER,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR,
            updated_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS silver.order_items (
            order_item_id INTEGER,
            order_id INTEGER,
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            subcategory VARCHAR,
            category VARCHAR,
            quantity INTEGER,
            unit_price DECIMAL(10, 2),
            line_total DECIMAL(12, 2),
            updated_date TIMESTAMP
        );

        -- Quarantine keeps rejected rows plus a reason and the run_date that rejected them
        CREATE TABLE IF NOT EXISTS quarantine.products (
            product_id INTEGER,
            product_name VARCHAR,
            subcategory_code VARCHAR,
            unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        CREATE TABLE IF NOT EXISTS quarantine.orders (
            order_id INTEGER,
            customer_id INTEGER,
            order_date DATE,
            status VARCHAR,
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        CREATE TABLE IF NOT EXISTS quarantine.order_items (
            order_item_id INTEGER,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            line_unit_price DECIMAL(10, 2),
            updated_date TIMESTAMP,
            rejection_reason VARCHAR,
            _load_date DATE
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Create silver and quarantine tables'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 4. Explore Bronze data before cleaning

    These queries only look at `_load_date = run_date`.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- List customer_ids that appear more than once (duplicates)
        SELECT customer_id, customer_name, email, updated_date
        FROM bronze.customers
        WHERE _load_date = DATE '{run_date}'
          AND customer_id IN (
                SELECT customer_id
                FROM bronze.customers
                WHERE _load_date = DATE '{run_date}'
                GROUP BY customer_id
                HAVING COUNT(*) > 1
          )
        ORDER BY customer_id, updated_date;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- List products with invalid price. These products should go to quarantine.
        SELECT product_id, product_name, unit_price
        FROM bronze.products
        WHERE _load_date = DATE '{run_date}'
          AND try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2)) IS NULL;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 5. Product Category Cleaning and Standardization

    Cleaning rules:

    - Trim text; store codes in upper case
    - `electronics` / `Electronics` → `ELECTRONICS`
    - Blank subcategory name → `Unknown`
    - If file to load has the same code twice, keep the row with the latest `updated_date`
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Step 1: clean Bronze rows (one output row per input row)
        CREATE OR REPLACE TABLE memory.stg_category_cleaned AS
        SELECT
            upper(trim(subcategory_code)) AS subcategory_code,
            subcategory,
            CASE
                WHEN lower(trim(category)) IN ('electronics', 'electronic')
                    THEN 'Electronics'
                WHEN category IS NULL OR trim(category) = '' THEN 'Other'
                ELSE trim(category)
            END AS category,
            -- try_strptime converts a text string into a datetime, but returns NULL instead of an error when the conversion fails.
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.product_category
        WHERE _load_date = DATE '{run_date}'
          AND trim(subcategory_code) <> '';

        SELECT * FROM memory.stg_category_cleaned ORDER BY subcategory_code, updated_date;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Step 2: Get latest record per subcategory_code to eliminate duplicates
        -- QUALIFY keeps only the latest row per subcategory_code (row_number = 1)
        CREATE OR REPLACE TABLE memory.stg_category AS
        SELECT
            subcategory_code,
            subcategory,
            category,
            updated_date
        FROM memory.stg_category_cleaned
        QUALIFY row_number() OVER (
            PARTITION BY subcategory_code
            ORDER BY updated_date DESC
        ) = 1;

        SELECT * FROM memory.stg_category ORDER BY subcategory_code;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Step 3: Merge staged data into Silver:
        -- insert new subcategories and update existing ones.
        MERGE INTO silver.product_category AS t
        USING memory.stg_category AS s
            ON t.subcategory_code = s.subcategory_code
        WHEN MATCHED THEN UPDATE SET
            subcategory = s.subcategory,
            category = s.category,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (
            subcategory_code, subcategory, category, updated_date
        ) VALUES (
            s.subcategory_code, s.subcategory, s.category, s.updated_date
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Silver product_category MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM silver.product_category ORDER BY subcategory_code;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ###  6. Customers Cleaning and Standardization

    Cleaning rules:

    - Trim names
    - Lower-case emails; if the value has no `@` and `.`, store NULL (keep the customer)
    - Fix city typos (`Dohaa` → `Doha`); replace hyphens with spaces (`Al-Wakrah` → `Al Wakrah`)
    - Map country labels to full country names: QAT → `Qatar`, UAE → `United Arab Emirates`, KSA → `Saudi Arabia`
    - Keep the latest row per `customer_id`
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE memory.stg_customers_cleaned AS
        SELECT
            try_cast(trim(customer_id) AS INTEGER) AS customer_id,
            CASE
                WHEN customer_name IS NULL OR trim(customer_name) = '' THEN NULL
                ELSE trim(customer_name)
            END AS customer_name,
            CASE
                WHEN email IS NULL OR trim(email) = '' THEN NULL
                WHEN lower(trim(email)) LIKE '%@%.%' THEN lower(trim(email))
                ELSE NULL
            END AS email,
            CASE
                WHEN city IS NULL OR trim(city) = '' THEN NULL
                WHEN lower(trim(replace(city, '-', ' '))) IN ('doha', 'dohaa')
                    THEN 'Doha'
                ELSE trim(replace(city, '-', ' '))
            END AS city,
            CASE
                WHEN lower(trim(replace(city, '-', ' ')))  IN ('doha', 'dohaa') THEN 'Qatar'
                WHEN country IS NULL OR trim(country) = '' THEN NULL
                WHEN upper(trim(country)) IN ('QATAR', 'QA', 'QAT') THEN 'Qatar'
                WHEN upper(trim(country)) IN ('UAE', 'UNITED ARAB EMIRATES', 'ARE')
                    THEN 'United Arab Emirates'
                WHEN upper(trim(country)) IN ('KSA', 'SAUDI ARABIA', 'SA', 'SAU')
                    THEN 'Saudi Arabia'
                ELSE trim(country)
            END AS country,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.customers
        WHERE _load_date = DATE '{run_date}';

        SELECT * FROM memory.stg_customers_cleaned ORDER BY customer_id, updated_date;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Keep the latest row for each customer and ignore null customer IDs.
        CREATE OR REPLACE TABLE memory.stg_customers AS
        SELECT
            customer_id,
            customer_name,
            email,
            city,
            country,
            updated_date
        FROM memory.stg_customers_cleaned
        WHERE customer_id IS NOT NULL
        QUALIFY row_number() OVER (
            PARTITION BY customer_id
            ORDER BY updated_date DESC
        ) = 1;

        -- Verify that each customer_id appears only once.
        SELECT
            customer_id,
            count(*) AS rows
        FROM memory.stg_customers
        GROUP BY customer_id
        HAVING count(*) > 1;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        MERGE INTO silver.customers AS t
        USING memory.stg_customers AS s
            ON t.customer_id = s.customer_id
        WHEN MATCHED THEN UPDATE SET
            customer_name = s.customer_name,
            email = s.email,
            city = s.city,
            country = s.country,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (
            customer_id, customer_name, email, city, country, updated_date
        ) VALUES (
            s.customer_id, s.customer_name, s.email, s.city, s.country,
            s.updated_date
        );

        CALL sales_lake.set_commit_message(
            'admin',
            'Silver customers MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        SELECT 'bronze.customers ' || '{run_date}' AS source, count(*) AS row_count
        FROM bronze.customers WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'silver.customers', count(*) FROM silver.customers;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM silver.customers ORDER BY customer_id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 7. Products Cleaning and Standardization

    A product is **valid** when:
    - `product_id` is an integer
    - `unit_price` is a number and `>= 0`

    Blank or unknown `subcategory_code` is mapped to **`OTHER`** (enrichment, not a reject).

    Invalid products go to `quarantine.products`. If a later extract corrects the price, MERGE will load the product into Silver and the quarantine row for that key is removed.
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE memory.stg_products_cleaned AS
        SELECT
            try_cast(trim(product_id) AS INTEGER) AS product_id,
            CASE
                WHEN product_name IS NULL OR trim(product_name) = '' THEN NULL
                ELSE trim(product_name)
            END AS product_name,
            CASE
                WHEN subcategory_code IS NULL OR trim(subcategory_code) = ''
                    THEN 'OTHER'
                ELSE upper(trim(subcategory_code))
            END AS subcategory_code,
            -- remove thousands separators such as 1,500.00 before casting
            try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2))
                AS unit_price,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.products
        WHERE _load_date = DATE '{run_date}';

        SELECT product_id, product_name, subcategory_code, unit_price
        FROM memory.stg_products_cleaned
        ORDER BY product_id;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Keep the latest product record and enrich it with category details.
        CREATE OR REPLACE TABLE memory.stg_products AS
        SELECT
            p.product_id,
            p.product_name,
            coalesce(c.subcategory_code, 'OTHER') AS subcategory_code,
            coalesce(c.subcategory, 'Other') AS subcategory,
            coalesce(c.category, 'Other') AS category,
            p.unit_price,
            p.updated_date
        FROM memory.stg_products_cleaned AS p
        LEFT JOIN silver.product_category AS c
            ON p.subcategory_code = c.subcategory_code
        QUALIFY row_number() OVER (
            PARTITION BY p.product_id
            ORDER BY p.updated_date DESC
        ) = 1;

        -- Review the staged product data.
        SELECT *
        FROM memory.stg_products
        ORDER BY product_id;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Valid products: MERGE into Silver
        MERGE INTO silver.products AS t
        USING (
            SELECT *
            FROM memory.stg_products
            WHERE product_id IS NOT NULL
              AND unit_price IS NOT NULL
              AND unit_price >= 0
        ) AS s
            ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET
            product_name = s.product_name,
            subcategory_code = s.subcategory_code,
            subcategory = s.subcategory,
            category = s.category,
            unit_price = s.unit_price,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (
            product_id, product_name, subcategory_code, subcategory, category,
            unit_price, updated_date
        ) VALUES (
            s.product_id, s.product_name, s.subcategory_code, s.subcategory,
            s.category, s.unit_price, s.updated_date
        );

        -- Refresh quarantine for keys we processed in this run
        DELETE FROM quarantine.products
        WHERE product_id IN (SELECT product_id FROM memory.stg_products);

        INSERT INTO quarantine.products
        SELECT
            product_id,
            product_name,
            subcategory_code,
            unit_price,
            updated_date,
            CASE
                WHEN product_id IS NULL THEN 'Invalid product_id'
                WHEN unit_price IS NULL THEN 'Invalid unit_price'
                WHEN unit_price < 0 THEN 'unit_price must be >= 0'
                ELSE 'Invalid product'
            END AS rejection_reason,
            DATE '{run_date}' AS _load_date
        FROM memory.stg_products
        WHERE product_id IS NULL
           OR unit_price IS NULL
           OR unit_price < 0;

        CALL sales_lake.set_commit_message(
            'admin',
            'Silver products MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        SELECT 'bronze.products ' || '{run_date}' AS table_name, count(*) AS row_count
        FROM bronze.products WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'silver.products' AS table_name, count(*) AS row_count FROM silver.products
        UNION ALL
        SELECT 'quarantine.products', count(*) FROM quarantine.products;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM quarantine.products;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 8. Orders Cleaning and Standardization

    Parse `order_date` with three common formats. Reject the row when:
    - `order_id` or `order_date` is missing
    - `order_date` is after `run_date` (a future date)
    - `customer_id` is not in `silver.customers`
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE memory.stg_orders_cleaned AS
        SELECT
            try_cast(trim(order_id) AS INTEGER) AS order_id,
            try_cast(trim(customer_id) AS INTEGER) AS customer_id,
            -- Try ISO date, then slash date, then day-first date
            CAST(
                coalesce(
                    try_strptime(trim(order_date), '%Y-%m-%d'),
                    try_strptime(trim(order_date), '%Y/%m/%d'),
                    try_strptime(trim(order_date), '%d-%m-%Y')
                ) AS DATE
            ) AS order_date,
            CASE
                WHEN status IS NULL OR trim(status) = '' THEN 'Unknown'
                WHEN lower(trim(status)) IN ('complete', 'completed', 'done')
                    THEN 'Completed'
                WHEN lower(trim(status)) = 'pending' THEN 'Pending'
                WHEN lower(trim(status)) IN ('shipped', 'shiped') THEN 'Shipped'
                WHEN lower(trim(status)) IN ('cancelled', 'canceled') THEN 'Cancelled'
                WHEN lower(trim(status)) = 'processing' THEN 'Processing'
                ELSE trim(status)
            END AS status,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.orders
        WHERE _load_date = DATE '{run_date}';

        SELECT order_id, customer_id, order_date, status
        FROM memory.stg_orders_cleaned
        ORDER BY order_id;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Keep the latest version of each order.
        -- QUALIFY filters on the row_number() result.
        CREATE OR REPLACE TABLE memory.stg_orders AS
        SELECT
            order_id,
            customer_id,
            order_date,
            status,
            updated_date
        FROM memory.stg_orders_cleaned
        QUALIFY row_number() OVER (
            PARTITION BY order_id
            ORDER BY updated_date DESC
        ) = 1;

        -- Review the staged order data.
        SELECT *
        FROM memory.stg_orders
        ORDER BY order_id;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        -- Upsert valid orders into Silver: must reference a known customer, have a valid id, and date not in the future
        MERGE INTO silver.orders AS t
        USING (
            SELECT o.*
            FROM memory.stg_orders AS o
            INNER JOIN silver.customers AS c
                ON o.customer_id = c.customer_id
            WHERE o.order_id IS NOT NULL         -- Require valid order_id
              AND o.order_date IS NOT NULL       -- Require a valid order_date
              AND o.order_date <= DATE '{run_date}' -- Order date is not in the future
        ) AS s
            ON t.order_id = s.order_id
        WHEN MATCHED THEN UPDATE SET
            customer_id = s.customer_id,
            order_date = s.order_date,
            status = s.status,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (
            order_id, customer_id, order_date, status, updated_date
        ) VALUES (
            s.order_id, s.customer_id, s.order_date, s.status, s.updated_date
        );

        -- Remove from quarantine any order now present in staged orders (i.e., recheck every run)
        DELETE FROM quarantine.orders
        WHERE order_id IN (SELECT order_id FROM memory.stg_orders);

        -- Insert invalid orders into quarantine with reason
        INSERT INTO quarantine.orders
        SELECT
            o.order_id,
            o.customer_id,
            o.order_date,
            o.status,
            o.updated_date,
            CASE
                WHEN o.order_id IS NULL THEN 'Invalid order_id'             -- Missing order ID
                WHEN o.order_date IS NULL THEN 'Invalid order_date'         -- Missing order date
                WHEN o.order_date > DATE '{run_date}' THEN 'Future order_date' -- Date is after processing date
                WHEN c.customer_id IS NULL THEN 'Unknown customer'          -- Customer does not exist in Silver
                ELSE 'Invalid order'                                        -- Fallback catch-all
            END AS rejection_reason,
            DATE '{run_date}' AS _load_date
        FROM memory.stg_orders AS o
        LEFT JOIN silver.customers AS c
            ON o.customer_id = c.customer_id
        WHERE o.order_id IS NULL
           OR o.order_date IS NULL
           OR o.order_date > DATE '{run_date}'
           OR c.customer_id IS NULL;

        -- Record this MERGE operation in the commit log
        CALL sales_lake.set_commit_message(
            'admin',
            'Silver orders MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        SELECT 'bronze.orders ' || '{run_date}' AS table_name, count(*) AS row_count
        FROM bronze.orders WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'silver.orders' AS table_name, count(*) AS row_count FROM silver.orders
        UNION ALL
        SELECT 'quarantine.orders', count(*) FROM quarantine.orders;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM quarantine.orders;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 9. Order items Cleaning and Standardization

    A line is **valid** when:

    - `order_item_id` is unique (keep the latest based on `updated_date` if duplicated)
    - `quantity` is an integer `> 0`
    - the order exists in Silver
    - the product exists in Silver
    - use the line price if available; if it is blank, use the catalog price

    `line_total = quantity * unit_price`
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE memory.stg_items_cleaned AS
        SELECT
            try_cast(trim(order_item_id) AS INTEGER) AS order_item_id,
            try_cast(trim(order_id) AS INTEGER) AS order_id,
            try_cast(trim(product_id) AS INTEGER) AS product_id,
            try_cast(trim(quantity) AS INTEGER) AS quantity,
            try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2))
                AS line_unit_price,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.order_items
        WHERE _load_date = DATE '{run_date}';

        SELECT * FROM memory.stg_items_cleaned ORDER BY order_item_id, updated_date;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Keep the latest version of each order item.
        -- Enrich with product details and use the product price when the line price is missing.
        CREATE OR REPLACE TABLE memory.stg_items AS
        SELECT
            i.order_item_id,
            i.order_id,
            i.product_id,
            i.quantity,
            i.line_unit_price,
            coalesce(i.line_unit_price, p.unit_price) AS unit_price,
            p.product_name,
            p.subcategory_code,
            p.subcategory,
            p.category,
            i.updated_date
        FROM memory.stg_items_cleaned AS i
        LEFT JOIN silver.orders AS o
            ON i.order_id = o.order_id
        LEFT JOIN silver.products AS p
            ON i.product_id = p.product_id
        -- Keep only the most recent row for each order_item_id (latest updated_date)
        QUALIFY row_number() OVER (
            PARTITION BY i.order_item_id
            ORDER BY i.updated_date DESC
        ) = 1;

        -- Review the staged order items.
        SELECT
            order_item_id,
            order_id,
            product_id,
            quantity,
            line_unit_price,
            unit_price,
            product_name
        FROM memory.stg_items
        ORDER BY order_item_id;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Start a transaction for atomicity
        BEGIN TRANSACTION;

        -- Merge valid staged order items into silver.order_items
        MERGE INTO silver.order_items AS t
        USING (
            SELECT
                i.order_item_id,
                i.order_id,
                i.product_id,
                i.product_name,
                i.subcategory_code,
                i.subcategory,
                i.category,
                i.quantity,
                i.unit_price,
                i.quantity * i.unit_price AS line_total,
                i.updated_date
            FROM memory.stg_items AS i
            -- Ensure referenced order and product exist
            INNER JOIN silver.orders AS o
                ON i.order_id = o.order_id
            INNER JOIN silver.products AS p
                ON i.product_id = p.product_id
            -- Only process positive, non-null quantity and price
            WHERE i.quantity IS NOT NULL
              AND i.quantity > 0
              AND i.unit_price IS NOT NULL
        ) AS s
            ON t.order_item_id = s.order_item_id
        WHEN MATCHED THEN UPDATE SET
            order_id = s.order_id,
            product_id = s.product_id,
            product_name = s.product_name,
            subcategory_code = s.subcategory_code,
            subcategory = s.subcategory,
            category = s.category,
            quantity = s.quantity,
            unit_price = s.unit_price,
            line_total = s.line_total,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (
            order_item_id, order_id, product_id, product_name, subcategory_code,
            subcategory, category, quantity, unit_price, line_total, updated_date
        ) VALUES (
            s.order_item_id, s.order_id, s.product_id, s.product_name,
            s.subcategory_code, s.subcategory, s.category, s.quantity,
            s.unit_price, s.line_total, s.updated_date
        );

        -- Remove any quarantined rows that were successfully loaded into Silver
        DELETE FROM quarantine.order_items
        WHERE order_item_id IN (SELECT order_item_id FROM memory.stg_items);

        -- Insert non-conforming rows into quarantine with reasons
        INSERT INTO quarantine.order_items
        SELECT
            i.order_item_id,
            i.order_id,
            i.product_id,
            i.quantity,
            i.line_unit_price,
            i.updated_date,
            CASE
                WHEN i.quantity IS NULL OR i.quantity <= 0 THEN 'Quantity must be positive'
                WHEN o.order_id IS NULL THEN 'Unknown order'
                WHEN p.product_id IS NULL THEN 'Unknown product'
                WHEN i.unit_price IS NULL THEN 'Missing unit_price'
                ELSE 'Invalid order item'
            END AS rejection_reason,
            DATE '{run_date}' AS _load_date
        FROM memory.stg_items AS i
        LEFT JOIN silver.orders AS o
            ON i.order_id = o.order_id
        LEFT JOIN silver.products AS p
            ON i.product_id = p.product_id
        WHERE i.quantity IS NULL
           OR i.quantity <= 0
           OR o.order_id IS NULL
           OR p.product_id IS NULL
           OR i.unit_price IS NULL;

        -- Log the commit message for auditing
        CALL sales_lake.set_commit_message(
            'admin',
            'Silver order_items MERGE {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        SELECT 'bronze.order_items ' || '{run_date}' AS source, count(*) AS row_count
        FROM bronze.order_items WHERE _load_date = DATE '{run_date}'
        UNION ALL
        SELECT 'silver.order_items' AS table_name, count(*) AS row_count
        FROM silver.order_items
        UNION ALL
        SELECT 'quarantine.order_items', count(*) FROM quarantine.order_items;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT rejection_reason, count(*) AS rows
        FROM quarantine.order_items
        GROUP BY rejection_reason
        ORDER BY rows DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 10. Sales detail (ready for Gold)

    One row per valid order line, joined to the customer and order. This table is rebuilt each run from current Silver (Or use MERGE instead of `CREATE OR REPLACE`).
    """)
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        BEGIN TRANSACTION;

        CREATE OR REPLACE TABLE silver.sales_detail AS
        SELECT
            i.order_id,
            o.order_date,
            o.status,
            o.customer_id,
            c.customer_name,
            c.city,
            c.country,
            i.order_item_id,
            i.product_id,
            i.product_name,
            i.subcategory_code,
            i.subcategory,
            i.category,
            i.quantity,
            i.unit_price,
            i.line_total
        FROM silver.order_items AS i
        INNER JOIN silver.orders AS o
            ON i.order_id = o.order_id
        INNER JOIN silver.customers AS c
            ON o.customer_id = c.customer_id;

        CALL sales_lake.set_commit_message(
            'admin',
            'Silver sales_detail {run_date}'
        );

        COMMIT;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM silver.sales_detail ORDER BY order_id, order_item_id;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### 12. Quality checks

    These counts should be **0**. If one is not zero, Silver still has a problem.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Silver data quality checks: duplicates, invalid values, and missing references.
        -- Silver layer data quality summary.
        SELECT
            -- Customer IDs appearing more than once.
            (
                SELECT count(*)
                FROM (
                    SELECT customer_id
                    FROM silver.customers
                    GROUP BY customer_id
                    HAVING count(*) > 1
                ) d
            ) AS duplicate_customers,

            -- Missing or negative product prices.
            (
                SELECT count(*)
                FROM silver.products
                WHERE unit_price IS NULL OR unit_price < 0
            ) AS bad_product_prices,

            -- Orders with no matching customer.
            (
                SELECT count(*)
                FROM silver.orders o
                LEFT JOIN silver.customers c
                    ON o.customer_id = c.customer_id
                WHERE c.customer_id IS NULL
            ) AS orders_without_customer,

            -- Order items with no matching order.
            (
                SELECT count(*)
                FROM silver.order_items i
                LEFT JOIN silver.orders o
                    ON i.order_id = o.order_id
                WHERE o.order_id IS NULL
            ) AS items_without_order,

            -- Order items with no matching product.
            (
                SELECT count(*)
                FROM silver.order_items i
                LEFT JOIN silver.products p
                    ON i.product_id = p.product_id
                WHERE p.product_id IS NULL
            ) AS items_without_product,

            -- Invalid quantities.
            (
                SELECT count(*)
                FROM silver.order_items
                WHERE quantity <= 0
            ) AS non_positive_qty;
        """
    )
    return


@app.cell
def _(mo, run_date):
    _df = mo.sql(
        f"""
        -- Row counts for each table, before and after cleaning/quarantine, for data validation
        -- Bronze customers loaded 
        SELECT 'bronze.customers ' || '{run_date}' AS source, count(*) AS rows
        FROM bronze.customers WHERE _load_date = DATE '{run_date}'

        UNION ALL
        -- Rows count in silver customers after merge/deduplication
        SELECT 'silver.customers', count(*) FROM silver.customers

        UNION ALL
        -- Bronze products loaded 
        SELECT 'bronze.products ' || '{run_date}', count(*)
        FROM bronze.products WHERE _load_date = DATE '{run_date}'

        UNION ALL
        -- Rows count in silver products after cleaning
        SELECT 'silver.products', count(*) FROM silver.products

        UNION ALL
        -- Invalid product rows quarantined
        SELECT 'quarantine.products', count(*) FROM quarantine.products

        UNION ALL
        -- Bronze orders loaded 
        SELECT 'bronze.orders ' || '{run_date}', count(*)
        FROM bronze.orders WHERE _load_date = DATE '{run_date}'

        UNION ALL
        -- All silver orders after cleaning and deduplication
        SELECT 'silver.orders', count(*) FROM silver.orders

        UNION ALL
        -- Orders quarantined for data quality issues
        SELECT 'quarantine.orders', count(*) FROM quarantine.orders

        UNION ALL
        -- Bronze order items loaded
        SELECT 'bronze.order_items ' || '{run_date}', count(*)
        FROM bronze.order_items WHERE _load_date = DATE '{run_date}'

        UNION ALL
        -- Rows count in cleaned/validated silver order_items
        SELECT 'silver.order_items', count(*) FROM silver.order_items

        UNION ALL
        -- Quarantined order_items (e.g. invalid product/order/pricing)
        SELECT 'quarantine.order_items', count(*) FROM quarantine.order_items

        UNION ALL
        -- Final detail rows published for gold metrics
        SELECT 'silver.sales_detail', count(*) FROM silver.sales_detail;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Releasing the lakehouse catalog with DETACH DATABASE ensures all file handles are closed and the catalog can safely be used in another notebook.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Release the lakehouse catalog so it can be used in another notebook
        USE memory;
        -- Detaching sales_lake releases its catalog and associated file handles.
        DETACH DATABASE IF EXISTS sales_lake;
        SHOW DATABASES;
        """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Summary

    - Processed only Bronze rows for the selected `run_date`.
    - Cleaned data types, codes, dates, and statuses using SQL.
    - Removed duplicates by keeping the latest record for each business key (`updated_date`).
    - Used `MERGE INTO` to insert new and update existing records.
    - Sent invalid products, orders, and items to the quarantine tables with reasons.
    - Created and published `silver.sales_detail` for Gold analytics.

    **Key takeaway:** Silver enforces data quality and supports incremental updates with MERGE. Quarantine keeps track of rejected records.

    Next steps: Run `03_gold.py` with the same `run_date`. After verifying for 17 Sep, change `run_date` to `2026-09-18` in notebooks 01–03 (no need to rerun setup). You should see updates like Mouse changing to `ELEC_ACC` and orders moving from Pending to Completed.
    """)
    return


if __name__ == "__main__":
    app.run()
