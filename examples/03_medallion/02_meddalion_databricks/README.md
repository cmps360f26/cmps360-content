# CMPS 360: Retail Sales Medallion Lakehouse on Databricks

**Medallion Architecture (Bronze &rarr; Silver &rarr; Gold)** data pipeline on **Databricks Free Edition**, built with **Databricks SQL**, **Delta Lake**, and **Unity Catalog**.

This project processes retail sales transactions across GCC markets (Qatar, UAE, Saudi Arabia), handles dirty raw extracts, isolates invalid records in the **Quarantine** area, and populates an analytical **Kimball Star Schema**.

## Quick Setup: Databricks Free Edition

### 1. Get a Free Databricks Account
1. Go to [Databricks Free Edition](https://www.databricks.com/learn/free-edition).
2. Sign up for **Databricks Free Edition** (free forever, no credit card required).
3. Activate your account using the email link and sign in.

### 2. Import the Project into Databricks

Choose either method below:

#### Method A: Git Integration (Recommended)
1. In the left sidebar, click **Workspace** &rarr; **Git Folders** (or **Repos**).
2. Click **Add Git Folder** (or **Add Repo**).
3. Paste the URL of your Git repository and click **Create**. All notebooks and data folders will sync immediately.

#### Method B: Direct Import
1. In the left sidebar, click **Workspace** &rarr; **Users** &rarr; `your_email`.
2. Click **Import** (top right or folder menu).
3. Drag and drop the `02_meddalion_databricks` folder and click **Import**.

---

## Running the Pipeline

You can run the entire solution with the automated runner or step-by-step through individual notebooks.

### Option 1: Automated Fast Track (Recommended)

1. Open [`run_pipeline.py`](./run_pipeline.py).
2. Check the widgets at the top:
   - `target_date`: `ALL`
   - `init_catalog`: Set to **`true`** for the first run (creates all tables and loads data).
3. Click **Run All** (top right).
4. The notebook will automatically:
   - Initialize the catalog, schemas, and Volume.
   - Populate the raw CSV extracts into the Volume.
   - Process `2026-09-17` &rarr; `2026-09-18` &rarr; `2026-09-19` &rarr; `2026-09-20` through Bronze &rarr; Silver &rarr; Gold.
   - Display a status summary table from `bronze.pipeline_runs`.
5. Open [`analysis/04_answer_questions.sql`](./analysis/04_answer_questions.sql) to view the business analytics!

---

### Option 2: Step-by-Step Interactive Lab

To understand each Medallion transition, run the notebooks in this order:

#### Step 1: Initialize Schemas & Data (Run Once)
Run each notebook once using the **Run All** button:
1. [`setup/00_setup.sql`](./setup/00_setup.sql) &mdash; Creates catalog `sales_lake`, schemas (`bronze`, `silver`, `gold`, `quarantine`), volume `landing_zone`, and `pipeline_runs`.
2. [`setup/00.1_bronze_schema.sql`](./setup/00.1_bronze_schema.sql) &mdash; Defines the 5 Bronze tables with permissive `STRING` columns.
3. [`setup/00.2_silver_schema.sql`](./setup/00.2_silver_schema.sql) &mdash; Defines the 5 Silver tables and 3 Quarantine tables.
4. [`setup/00.3_gold_schema.sql`](./setup/00.3_gold_schema.sql) &mdash; Defines the Kimball Star Schema tables.
5. [`setup/00.4_load_landing_files.py`](./setup/00.4_load_landing_files.py) &mdash; Writes the raw CSV extracts into `/Volumes/sales_lake/bronze/landing_zone/`.

#### Step 2: Day 1 Initial Batch Load (`2026-09-17`)
Set widget `run_date = "2026-09-17"` (default) in each notebook:
1. [`pipeline/01_bronze.sql`](./pipeline/01_bronze.sql) &mdash; Ingests Day 1 CSVs into Bronze Delta tables with audit columns.
2. [`pipeline/02_silver.sql`](./pipeline/02_silver.sql) &mdash; Cleanses, standardizes, deduplicates (`QUALIFY row_number() = 1`), merges into Silver, and isolates invalid prices/orders to Quarantine.
3. [`pipeline/03_gold.sql`](./pipeline/03_gold.sql) &mdash; Generates contiguous calendar (`sequence` + `explode`) and merges dimensions and `fact_sales`.

#### Step 3: Practice Incremental Loading (`2026-09-18` .. `2026-09-20`)
To simulate daily production updates, change `run_date` and re-run notebooks `01_bronze.sql` &rarr; `02_silver.sql` &rarr; `03_gold.sql`:
- **`2026-09-18`**: Customer 2 moves to Lusail (SCD Type 1 update); Mouse 102 subcategory is resolved; Orders 1006 and 1010 transition from `Pending` &rarr; `Completed`.
- **`2026-09-19`**: Desk 104 & Yoga Mat 115 prices corrected &rarr; released from Quarantine into Silver; Orders 1015, 1017, and 1020 completed; **Self-healing retry releases Item 29 (Desk) into Silver and Gold**!
- **`2026-09-20`**: New category `HOME_LGT` (Lighting) introduced; LED Desk Lamp 117 added; Customer 12 country cleaned; Order 1025 with day-first date format (`20-09-2026`) parsed and fulfilled.

> **Note**: Do **not** re-run `setup/` notebooks between dates, or you will reset the lakehouse!

#### Step 4: Run Business Analytics
Open and execute [`analysis/04_answer_questions.sql`](./analysis/04_answer_questions.sql) to query the Star Schema:
- **Q1**: Realized revenue and fulfilled volume (`status IN ('Completed', 'Shipped')`).
- **Q2**: Daily sales and order trends via `dim_date`.
- **Q3**: Top-performing products by gross revenue.
- **Q4**: Category & subcategory revenue roll-up.
- **Q5**: Top spenders and customer lifetime value.
- **Q6**: Geographic sales distribution across Qatar, UAE, and Saudi Arabia.
- **Q7**: Full operational pipeline across all statuses (including Pending and Cancelled).
- **Q8**: Pipeline batch execution history from `bronze.pipeline_runs`.

---

## Verification & Quality Gates

Confirm your lakehouse state in Databricks SQL:

1. **Silver Quality Gates**:
   In `02_silver.sql`, the validation query checks 6 rules. **All counts must be `0`**:
   ```sql
   -- duplicate_customers: 0 | bad_product_prices: 0 | orders_without_customer: 0
   -- items_without_order: 0  | items_without_product: 0 | non_positive_qty: 0
   ```

2. **Quarantine Inspection**:
   ```sql
   SELECT rejection_reason, count(*) AS bad_records
   FROM sales_lake.quarantine.order_items
   GROUP BY rejection_reason;
   ```

3. **Gold Star Schema Counts**:
   ```sql
   SELECT 'fact_sales' AS tbl, count(*) AS total_rows FROM sales_lake.gold.fact_sales
   UNION ALL
   SELECT 'dim_customer', count(*) FROM sales_lake.gold.dim_customer
   UNION ALL
   SELECT 'dim_product', count(*) FROM sales_lake.gold.dim_product
   UNION ALL
   SELECT 'dim_status', count(*) FROM sales_lake.gold.dim_status
   UNION ALL
   SELECT 'dim_date', count(*) FROM sales_lake.gold.dim_date;
   ```

---

## FAQ

- **Q: "Permission Denied: Cannot create catalog sales_lake"**  
  **A**: If your Free Edition workspace restricts creating top-level catalogs, set the `catalog_name` widget at the top of the notebooks to `workspace` or `main`. All schemas and tables will be created under that catalog.
- **Q: "Path does not exist in Volume"**  
  **A**: Run [`setup/00.4_load_landing_files.py`](./setup/00.4_load_landing_files.py). It automatically writes the complete CSV extract dataset directly into the Volume in seconds.
