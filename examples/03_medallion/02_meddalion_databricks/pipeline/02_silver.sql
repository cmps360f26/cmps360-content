-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 02 - Silver Layer: Cleansing, Validation, and Delta MERGE
-- MAGIC 
-- MAGIC Welcome to the **Silver Layer Data Pipeline**!
-- MAGIC 
-- MAGIC In the Medallion Lakehouse Architecture:
-- MAGIC - **Bronze** holds raw extract strings as received.
-- MAGIC - **Silver** converts them into strongly typed, standardized, validated, and deduplicated business entities.
-- MAGIC - Invalid records that fail business rules are routed to the **Quarantine** schema with descriptive rejection reasons.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### Core Data Engineering Patterns:
-- MAGIC 
-- MAGIC 1. **Incremental Processing**:
-- MAGIC    - Only Bronze records for the current batch date (`_load_date = DATE '${run_date}'`) are read and processed, avoiding expensive full-table scans.
-- MAGIC 2. **Session Temporary Views (`TEMPORARY VIEW`)**:
-- MAGIC    - Lightweight, in-memory staging views perform cleaning, parsing, and lookups without persisting scratch tables to disk.
-- MAGIC 3. **Safe Type Casting (`try_cast`, `try_to_date`, `try_to_timestamp`)**:
-- MAGIC    - Standard SQL `CAST('bad_price' AS DECIMAL)` terminates with a runtime error.
-- MAGIC    - Safe conversion functions return `NULL` instead of aborting the query, allowing downstream validation logic to cleanly identify and quarantine invalid data.
-- MAGIC 4. **Latest-Wins Deduplication (`QUALIFY row_number() = 1`)**:
-- MAGIC    - Handles intraday and batch duplicate keys by picking the latest record ordered by `updated_date DESC`.
-- MAGIC    - The `QUALIFY` clause filters window functions directly without requiring an extra subquery!
-- MAGIC 5. **Delta Lake `MERGE INTO` (Upsert)**:
-- MAGIC    - `WHEN MATCHED THEN UPDATE`: Updates existing entities (e.g. customer address changes, order status transitions).
-- MAGIC    - `WHEN NOT MATCHED THEN INSERT`: Appends brand-new records.
-- MAGIC 6. **Quarantine Pattern & Self-Healing Pipelines**:
-- MAGIC    - Corrupt or invalid rows are captured in `quarantine` with an explicit `rejection_reason`.
-- MAGIC    - A dedicated **Quarantine Retry Step** checks if previously quarantined records can now be resolved because their missing dependencies (e.g. a product price) have been corrected in Silver!

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 0: Configure Execution Parameters

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";
CREATE WIDGET TEXT run_date DEFAULT "2026-09-17";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Product Category Cleansing & Deduplication
-- MAGIC 
-- MAGIC ### Business Rules:
-- MAGIC - Trim and uppercase `subcategory_code` (`elec_mob` &rarr; `ELEC_MOB`).
-- MAGIC - Standardize category names to Title Case (`electronics` / `electronic` &rarr; `Electronics`).
-- MAGIC - Map missing or empty category names to `'Other'`.
-- MAGIC - Deduplicate using latest `updated_date` (e.g., `ELEC_COMP` had `Laptops` at 07:00 and `Computers` at 08:00).
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `initcap(trim(category))`: Converts string to title case (e.g., `'HOME & KITCHEN'` &rarr; `'Home & Kitchen'`).
-- MAGIC - `QUALIFY row_number() OVER (...) = 1`: Databricks SQL feature that filters on window function results in the same SELECT statement, eliminating redundant CTEs or nested subqueries.

-- COMMAND ----------

-- 1.1 Clean and standardize raw category extracts for run_date
CREATE OR REPLACE TEMPORARY VIEW stg_category_cleaned AS
SELECT
    upper(trim(subcategory_code)) AS subcategory_code,
    trim(subcategory) AS subcategory,
    CASE
        WHEN lower(trim(category)) IN ('electronics', 'electronic') THEN 'Electronics'
        WHEN category IS NULL OR trim(category) = '' THEN 'Other'
        ELSE initcap(trim(category))
    END AS category,
    try_to_timestamp(trim(updated_date), 'yyyy-MM-dd HH:mm:ss') AS updated_date
FROM bronze.product_category
WHERE _load_date = DATE '${run_date}'
  AND subcategory_code IS NOT NULL
  AND trim(subcategory_code) <> '';

-- COMMAND ----------

-- 1.2 Latest-Wins Deduplication per subcategory_code
CREATE OR REPLACE TEMPORARY VIEW stg_category AS
SELECT
    subcategory_code,
    subcategory,
    category,
    updated_date
FROM stg_category_cleaned
QUALIFY row_number() OVER (
    PARTITION BY subcategory_code
    ORDER BY updated_date DESC
) = 1;

-- COMMAND ----------

-- 1.3 Upsert into silver.product_category using Delta Lake MERGE
MERGE INTO silver.product_category AS t
USING stg_category AS s
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

-- COMMAND ----------

-- Preview cleaned categories in Silver
SELECT * FROM silver.product_category ORDER BY subcategory_code;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Customers Cleansing, Standardization & Deduplication
-- MAGIC 
-- MAGIC ### Business Rules:
-- MAGIC - Trim and title-case customer names (`ali hassan` &rarr; `Ali Hassan`).
-- MAGIC - Lowercase email addresses; validate format (must contain `@` and `.`), otherwise store `NULL`.
-- MAGIC - Correct city typos (`Dohaa` &rarr; `Doha`); replace hyphens with spaces (`Al-Wakrah` &rarr; `Al Wakrah`).
-- MAGIC - Standardize country names to full official names (`QA` / `QAT` / `QATAR` &rarr; `Qatar`, `UAE` &rarr; `United Arab Emirates`, `KSA` &rarr; `Saudi Arabia`). If country is blank, leave as `NULL`.
-- MAGIC - Apply latest-wins deduplication per `customer_id`.
-- MAGIC - Update existing customer records in-place (SCD Type 1) via `MERGE INTO`.

-- COMMAND ----------

-- 2.1 Clean and standardize raw customer attributes
CREATE OR REPLACE TEMPORARY VIEW stg_customers_cleaned AS
SELECT
    try_cast(trim(customer_id) AS INT) AS customer_id,
    CASE
        WHEN customer_name IS NULL OR trim(customer_name) = '' THEN NULL
        ELSE initcap(trim(customer_name))
    END AS customer_name,
    CASE
        WHEN email IS NULL OR trim(email) = '' THEN NULL
        WHEN lower(trim(email)) LIKE '%@%.%' THEN lower(trim(email))
        ELSE NULL
    END AS email,
    CASE
        WHEN city IS NULL OR trim(city) = '' THEN NULL
        WHEN lower(trim(replace(city, '-', ' '))) IN ('doha', 'dohaa') THEN 'Doha'
        ELSE initcap(trim(replace(city, '-', ' ')))
    END AS city,
    CASE
        WHEN lower(trim(replace(city, '-', ' '))) IN ('doha', 'dohaa') THEN 'Qatar'
        WHEN country IS NULL OR trim(country) = '' THEN NULL
        WHEN upper(trim(country)) IN ('QATAR', 'QA', 'QAT') THEN 'Qatar'
        WHEN upper(trim(country)) IN ('UAE', 'UNITED ARAB EMIRATES', 'ARE') THEN 'United Arab Emirates'
        WHEN upper(trim(country)) IN ('KSA', 'SAUDI ARABIA', 'SA', 'SAU') THEN 'Saudi Arabia'
        ELSE initcap(trim(country))
    END AS country,
    try_to_timestamp(trim(updated_date), 'yyyy-MM-dd HH:mm:ss') AS updated_date
FROM bronze.customers
WHERE _load_date = DATE '${run_date}';

-- COMMAND ----------

-- 2.2 Latest-Wins Deduplication per customer_id
CREATE OR REPLACE TEMPORARY VIEW stg_customers AS
SELECT
    customer_id,
    customer_name,
    email,
    city,
    country,
    updated_date
FROM stg_customers_cleaned
WHERE customer_id IS NOT NULL
QUALIFY row_number() OVER (
    PARTITION BY customer_id
    ORDER BY updated_date DESC
) = 1;

-- COMMAND ----------

-- 2.3 Upsert into silver.customers using Delta Lake MERGE (SCD Type 1 Overwrite)
MERGE INTO silver.customers AS t
USING stg_customers AS s
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
    s.customer_id, s.customer_name, s.email, s.city, s.country, s.updated_date
);

-- COMMAND ----------

-- Preview cleaned customers in Silver
SELECT * FROM silver.customers ORDER BY customer_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Products Cleansing, Categorization & Quarantine Routing
-- MAGIC 
-- MAGIC ### Business Rules:
-- MAGIC - Clean integer `product_id`.
-- MAGIC - Clean prices: strip thousands commas (`1,500.00` &rarr; `1500.00`) and cast to `DECIMAL(10, 2)`.
-- MAGIC - Trim product names (preserves technical names like `iPhone 16 Pro` or `4K Monitor`).
-- MAGIC - Map missing or unknown `subcategory_code` to `'OTHER'`.
-- MAGIC - Enrich product record with `subcategory` and `category` from `silver.product_category`.
-- MAGIC - **Validation Gate**: Valid products require valid integer `product_id` and non-negative `unit_price >= 0`.
-- MAGIC - **Quarantine Routing**: Corrupt prices (`bad_price`, `-25.00`) or missing IDs are routed to `quarantine.products`.
-- MAGIC - **Quarantine Refresh**: When a product is re-extracted with a corrected price on a later day (e.g. Desk 104 on 19 Sep), it is promoted to Silver and deleted from Quarantine!

-- COMMAND ----------

-- 3.1 Clean raw products
CREATE OR REPLACE TEMPORARY VIEW stg_products_cleaned AS
SELECT
    try_cast(trim(product_id) AS INT) AS product_id,
    CASE
        WHEN product_name IS NULL OR trim(product_name) = '' THEN NULL
        ELSE trim(product_name)
    END AS product_name,
    CASE
        WHEN subcategory_code IS NULL OR trim(subcategory_code) = '' THEN 'OTHER'
        ELSE upper(trim(subcategory_code))
    END AS subcategory_code,
    try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2)) AS unit_price,
    try_to_timestamp(trim(updated_date), 'yyyy-MM-dd HH:mm:ss') AS updated_date
FROM bronze.products
WHERE _load_date = DATE '${run_date}';

-- COMMAND ----------

-- 3.2 Enrich with category lookup and deduplicate
CREATE OR REPLACE TEMPORARY VIEW stg_products AS
SELECT
    p.product_id,
    p.product_name,
    coalesce(c.subcategory_code, 'OTHER') AS subcategory_code,
    coalesce(c.subcategory, 'Other') AS subcategory,
    coalesce(c.category, 'Other') AS category,
    p.unit_price,
    p.updated_date
FROM stg_products_cleaned AS p
LEFT JOIN silver.product_category AS c
    ON p.subcategory_code = c.subcategory_code
QUALIFY row_number() OVER (
    PARTITION BY p.product_id
    ORDER BY p.updated_date DESC
) = 1;

-- COMMAND ----------

-- 3.3 Upsert valid products into silver.products
MERGE INTO silver.products AS t
USING (
    SELECT *
    FROM stg_products
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

-- COMMAND ----------

-- 3.4 Refresh quarantine for products evaluated in this batch
DELETE FROM quarantine.products
WHERE product_id IN (SELECT product_id FROM stg_products WHERE product_id IS NOT NULL);

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
    DATE '${run_date}' AS _load_date
FROM stg_products
WHERE product_id IS NULL
   OR unit_price IS NULL
   OR unit_price < 0;

-- COMMAND ----------

-- Inspect quarantined products
SELECT * FROM quarantine.products ORDER BY _load_date, product_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Orders Cleansing, Date Parsing & Quarantine Routing
-- MAGIC 
-- MAGIC ### Business Rules:
-- MAGIC - Parse multiple date formats safely: ISO (`yyyy-MM-dd`), slash (`yyyy/MM/dd`), and day-first (`dd-MM-yyyy`).
-- MAGIC - Standardize status aliases: `complete` / `completed` / `done` &rarr; `Completed`, `pending` &rarr; `Pending`, `shiped` &rarr; `Shipped`, `cancelled` &rarr; `Cancelled`.
-- MAGIC - **Validation Gate**:
-- MAGIC   - Must have valid `order_id` and parsed `order_date`.
-- MAGIC   - Future dates are rejected (`order_date <= DATE '${run_date}'`).
-- MAGIC   - Foreign key referential integrity: `customer_id` must exist in `silver.customers`.
-- MAGIC - **Quarantine Routing**: Future dates (`2099-01-01`), unknown customers (e.g. `customer_id = 99`), or unparseable dates are routed to `quarantine.orders`.

-- COMMAND ----------

-- 4.1 Clean and standardize order header attributes
CREATE OR REPLACE TEMPORARY VIEW stg_orders_cleaned AS
SELECT
    try_cast(trim(order_id) AS INT) AS order_id,
    try_cast(trim(customer_id) AS INT) AS customer_id,
    CAST(
        coalesce(
            try_to_date(trim(order_date), 'yyyy-MM-dd'),
            try_to_date(trim(order_date), 'yyyy/MM/dd'),
            try_to_date(trim(order_date), 'dd-MM-yyyy')
        ) AS DATE
    ) AS order_date,
    CASE
        WHEN status IS NULL OR trim(status) = '' THEN 'Unknown'
        WHEN lower(trim(status)) IN ('complete', 'completed', 'done') THEN 'Completed'
        WHEN lower(trim(status)) = 'pending' THEN 'Pending'
        WHEN lower(trim(status)) IN ('shipped', 'shiped') THEN 'Shipped'
        WHEN lower(trim(status)) IN ('cancelled', 'canceled') THEN 'Cancelled'
        WHEN lower(trim(status)) = 'processing' THEN 'Processing'
        ELSE initcap(trim(status))
    END AS status,
    try_to_timestamp(trim(updated_date), 'yyyy-MM-dd HH:mm:ss') AS updated_date
FROM bronze.orders
WHERE _load_date = DATE '${run_date}';

-- COMMAND ----------

-- 4.2 Latest-Wins Deduplication per order_id
CREATE OR REPLACE TEMPORARY VIEW stg_orders AS
SELECT
    order_id,
    customer_id,
    order_date,
    status,
    updated_date
FROM stg_orders_cleaned
QUALIFY row_number() OVER (
    PARTITION BY order_id
    ORDER BY updated_date DESC
) = 1;

-- COMMAND ----------

-- 4.3 Upsert valid orders into silver.orders
MERGE INTO silver.orders AS t
USING (
    SELECT o.*
    FROM stg_orders AS o
    INNER JOIN silver.customers AS c
        ON o.customer_id = c.customer_id
    WHERE o.order_id IS NOT NULL
      AND o.order_date IS NOT NULL
      AND o.order_date <= DATE '${run_date}'
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

-- COMMAND ----------

-- 4.4 Refresh quarantine for orders evaluated in this batch
DELETE FROM quarantine.orders
WHERE order_id IN (SELECT order_id FROM stg_orders WHERE order_id IS NOT NULL);

INSERT INTO quarantine.orders
SELECT
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status,
    o.updated_date,
    CASE
        WHEN o.order_id IS NULL THEN 'Invalid order_id'
        WHEN o.order_date IS NULL THEN 'Invalid order_date'
        WHEN o.order_date > DATE '${run_date}' THEN 'Future order_date'
        WHEN c.customer_id IS NULL THEN 'Unknown customer'
        ELSE 'Invalid order'
    END AS rejection_reason,
    DATE '${run_date}' AS _load_date
FROM stg_orders AS o
LEFT JOIN silver.customers AS c
    ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
   OR o.order_date IS NULL
   OR o.order_date > DATE '${run_date}'
   OR c.customer_id IS NULL;

-- COMMAND ----------

-- Inspect quarantined orders
SELECT * FROM quarantine.orders ORDER BY _load_date, order_id;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Order Items Cleansing, Enrichment & Quarantine Routing
-- MAGIC 
-- MAGIC ### Business Rules:
-- MAGIC - Clean IDs and parse quantity (`INT > 0`).
-- MAGIC - Strip thousands commas from price (`1,500.00` &rarr; `1500.00`).
-- MAGIC - **Price Fallback Enrichment**: If line unit price is blank/missing (e.g. item 17), fall back to current catalog price in `silver.products`.
-- MAGIC - **Line Total Calculation**: `line_total = quantity * unit_price`.
-- MAGIC - **Referential Integrity**: Order must exist in `silver.orders`, and Product must exist in `silver.products`.
-- MAGIC - **Quarantine**: Bad quantities (`<= 0`), missing prices, or orphan lines without matching order/product go to quarantine.

-- COMMAND ----------

-- 5.1 Clean raw order items
CREATE OR REPLACE TEMPORARY VIEW stg_items_cleaned AS
SELECT
    try_cast(trim(order_item_id) AS INT) AS order_item_id,
    try_cast(trim(order_id) AS INT) AS order_id,
    try_cast(trim(product_id) AS INT) AS product_id,
    try_cast(trim(quantity) AS INT) AS quantity,
    try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2)) AS line_unit_price,
    try_to_timestamp(trim(updated_date), 'yyyy-MM-dd HH:mm:ss') AS updated_date
FROM bronze.order_items
WHERE _load_date = DATE '${run_date}';

-- COMMAND ----------

-- 5.2 Enrich with product catalog and deduplicate per order_item_id
CREATE OR REPLACE TEMPORARY VIEW stg_items AS
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
FROM stg_items_cleaned AS i
LEFT JOIN silver.orders AS o
    ON i.order_id = o.order_id
LEFT JOIN silver.products AS p
    ON i.product_id = p.product_id
QUALIFY row_number() OVER (
    PARTITION BY i.order_item_id
    ORDER BY i.updated_date DESC
) = 1;

-- COMMAND ----------

-- 5.3 Upsert valid order items into silver.order_items
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
        CAST(i.quantity * i.unit_price AS DECIMAL(12, 2)) AS line_total,
        i.updated_date
    FROM stg_items AS i
    INNER JOIN silver.orders AS o
        ON i.order_id = o.order_id
    INNER JOIN silver.products AS p
        ON i.product_id = p.product_id
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

-- COMMAND ----------

-- 5.4 Refresh quarantine for order items evaluated in this batch
DELETE FROM quarantine.order_items
WHERE order_item_id IN (SELECT order_item_id FROM stg_items WHERE order_item_id IS NOT NULL);

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
    DATE '${run_date}' AS _load_date
FROM stg_items AS i
LEFT JOIN silver.orders AS o
    ON i.order_id = o.order_id
LEFT JOIN silver.products AS p
    ON i.product_id = p.product_id
WHERE i.quantity IS NULL
   OR i.quantity <= 0
   OR o.order_id IS NULL
   OR p.product_id IS NULL
   OR i.unit_price IS NULL;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5.5: Quarantine Retry (Self-Healing Pipeline Pattern)
-- MAGIC 
-- MAGIC ### Why is Quarantine Retry Needed?
-- MAGIC Consider this real-world sequence:
-- MAGIC 1. On **17 Sep**, Item 29 (purchasing Standing Desk 104) was quarantined because Desk 104 had `bad_price` and was not in `silver.products`.
-- MAGIC 2. On **19 Sep**, the product catalog sent a corrected price (`299.00`) for Desk 104, promoting it to `silver.products`.
-- MAGIC 3. **The Self-Healing Mechanism**: Upstream dimensions (products/orders) often get fixed *after* dependent transactions were already rejected. The query below re-evaluates previously quarantined order items. If their referenced order and product now exist in Silver, the item is automatically **promoted to Silver** and **removed from Quarantine**!

-- COMMAND ----------

-- Find previously quarantined order items whose referenced order and product now exist in Silver
CREATE OR REPLACE TEMPORARY VIEW stg_quarantine_items_resolved AS
SELECT
    q.order_item_id,
    q.order_id,
    q.product_id,
    p.product_name,
    p.subcategory_code,
    p.subcategory,
    p.category,
    q.quantity,
    coalesce(q.line_unit_price, p.unit_price) AS unit_price,
    CAST(q.quantity * coalesce(q.line_unit_price, p.unit_price) AS DECIMAL(12, 2)) AS line_total,
    coalesce(q.updated_date, current_timestamp()) AS updated_date
FROM quarantine.order_items q
INNER JOIN silver.orders o
    ON q.order_id = o.order_id
INNER JOIN silver.products p
    ON q.product_id = p.product_id
WHERE q.quantity IS NOT NULL
  AND q.quantity > 0
  AND coalesce(q.line_unit_price, p.unit_price) IS NOT NULL
  AND coalesce(q.line_unit_price, p.unit_price) >= 0;

-- 1. Merge resolved items into silver.order_items
MERGE INTO silver.order_items AS t
USING stg_quarantine_items_resolved AS s
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

-- 2. Delete resolved items from quarantine
DELETE FROM quarantine.order_items
WHERE order_item_id IN (SELECT order_item_id FROM stg_quarantine_items_resolved);

-- COMMAND ----------

-- Inspect current quarantine order items breakdown
SELECT rejection_reason, count(*) AS total_quarantined_lines
FROM quarantine.order_items
GROUP BY rejection_reason
ORDER BY total_quarantined_lines DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Silver Quality Gates & Validation Auditing
-- MAGIC 
-- MAGIC Automated data quality gate checks against the Silver layer.
-- MAGIC **All 6 checks must return 0.** If any count is > 0, invalid data has leaked into Silver!

-- COMMAND ----------

SELECT
    -- 1. Duplicate customer IDs
    (
        SELECT count(*)
        FROM (
            SELECT customer_id
            FROM silver.customers
            GROUP BY customer_id
            HAVING count(*) > 1
        )
    ) AS duplicate_customers,

    -- 2. Missing or negative product prices
    (
        SELECT count(*)
        FROM silver.products
        WHERE unit_price IS NULL OR unit_price < 0
    ) AS bad_product_prices,

    -- 3. Orphan orders without customers
    (
        SELECT count(*)
        FROM silver.orders o
        LEFT JOIN silver.customers c
            ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
    ) AS orders_without_customer,

    -- 4. Order items without valid orders
    (
        SELECT count(*)
        FROM silver.order_items i
        LEFT JOIN silver.orders o
            ON i.order_id = o.order_id
        WHERE o.order_id IS NULL
    ) AS items_without_order,

    -- 5. Order items without valid products
    (
        SELECT count(*)
        FROM silver.order_items i
        LEFT JOIN silver.products p
            ON i.product_id = p.product_id
        WHERE p.product_id IS NULL
    ) AS items_without_product,

    -- 6. Non-positive quantities
    (
        SELECT count(*)
        FROM silver.order_items
        WHERE quantity <= 0
    ) AS non_positive_qty;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 7: Pre- and Post-Cleansing Row Counts
-- MAGIC Audits the distribution of records across Bronze, Silver, and Quarantine.

-- COMMAND ----------

SELECT 'bronze.customers ' || '${run_date}' AS layer_table, count(*) AS total_rows
FROM bronze.customers WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'silver.customers', count(*) FROM silver.customers
UNION ALL
SELECT 'bronze.products ' || '${run_date}', count(*)
FROM bronze.products WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'silver.products', count(*) FROM silver.products
UNION ALL
SELECT 'quarantine.products', count(*) FROM quarantine.products
UNION ALL
SELECT 'bronze.orders ' || '${run_date}', count(*)
FROM bronze.orders WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'silver.orders', count(*) FROM silver.orders
UNION ALL
SELECT 'quarantine.orders', count(*) FROM quarantine.orders
UNION ALL
SELECT 'bronze.order_items ' || '${run_date}', count(*)
FROM bronze.order_items WHERE _load_date = DATE '${run_date}'
UNION ALL
SELECT 'silver.order_items', count(*) FROM silver.order_items
UNION ALL
SELECT 'quarantine.order_items', count(*) FROM quarantine.order_items;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Educational Takeaways
-- MAGIC 
-- MAGIC - Cleaned, standardized, typed, and deduplicated all batch records for `${run_date}`.
-- MAGIC - Applied Delta Lake `MERGE INTO` for in-place entity updates (SCD Type 1) and status transitions.
-- MAGIC - Routed corrupt, negative, or orphan records into `quarantine` tables without interrupting pipeline execution.
-- MAGIC - Implemented the **Quarantine Self-Healing Pattern**, automatically releasing previously blocked order items when products are corrected.
-- MAGIC - Verified all 6 Silver data quality gate checks passed with count = 0.
-- MAGIC 
-- MAGIC **Next Step**: Open [`03_gold.sql`](./03_gold.sql) with the same `run_date` to populate the Gold Star Schema dimensional model.
