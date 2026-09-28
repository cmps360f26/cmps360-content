-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 04 - Answering Business & Operational Questions with the Star Schema
-- MAGIC 
-- MAGIC Welcome to the **Analytics & Reporting** notebook of the Medallion Lakehouse!
-- MAGIC 
-- MAGIC In `03_gold.sql`, we modeled our curated data into an incremental **Kimball Star Schema**:
-- MAGIC - **`gold.fact_sales`**: Central fact table storing sales transactions at the order-item grain.
-- MAGIC - **`gold.dim_date`**: Calendar dimension for daily, weekly, and monthly time-series analytics.
-- MAGIC - **`gold.dim_customer`**: Customer profile and geographic market dimension.
-- MAGIC - **`gold.dim_product`**: Product catalog and merchandise category hierarchy.
-- MAGIC - **`gold.dim_status`**: Order fulfillment pipeline statuses.
-- MAGIC 
-- MAGIC ---
-- MAGIC 
-- MAGIC ### The Star Join Pattern in Dimensional Analytics
-- MAGIC In modern data warehouses, lakehouses, and BI tools (such as Power BI, Tableau, and Databricks Dashboards), analytical queries perform **Star Joins**:
-- MAGIC - The central fact table (`fact_sales`) supplies additive numerical measures (`quantity`, `unit_price`, `sales_amount`).
-- MAGIC - Surrounding dimension tables provide descriptive attributes to slice, filter, and group the metrics.
-- MAGIC 
-- MAGIC > **Key Business Rule: Realized Revenue**
-- MAGIC > In retail analytics, gross realized revenue includes **only fulfilled orders** (`status IN ('Completed', 'Shipped')`). Orders that are `Pending`, `Processing`, or `Cancelled` represent pipeline or lost sales and are excluded from revenue KPIs.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 0: Configure Catalog Context

-- COMMAND ----------

CREATE WIDGET TEXT catalog_name DEFAULT "sales_lake";

-- COMMAND ----------

USE CATALOG IDENTIFIER(:catalog_name);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 1: Fulfilled Sales & Total Realized Revenue
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC What is our total realized revenue, total order volume, and number of fulfilled order line items across the business?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_status`, filtering for `s.status IN ('Completed', 'Shipped')`.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `COUNT(*)`: Counts the total number of fulfilled transactional line items.
-- MAGIC - `COUNT(DISTINCT f.order_id)`: Counts unique orders rather than lines (since an order may contain multiple items).
-- MAGIC - `SUM(f.quantity)`: Sums total individual units sold.
-- MAGIC - `ROUND(SUM(f.sales_amount), 2)`: Sums gross revenue, rounding to standard two decimal currency precision.

-- COMMAND ----------

SELECT
    COUNT(*) AS fulfilled_order_lines,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_sales_amount
FROM gold.fact_sales f
JOIN gold.dim_status s
    ON f.status = s.status
WHERE s.status IN ('Completed', 'Shipped');

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 2: Daily Sales Trend
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC How are order volumes, unit sales, and revenue trending across calendar dates and weeks?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_date` on `date`. Slices metrics by precomputed calendar attributes (`date`, `day_name`, `week`).
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `t.day_name` and `t.week`: Slices performance using precomputed attributes from `dim_date`, avoiding runtime `date_format()` calculations.
-- MAGIC - `GROUP BY t.date, t.day_name, t.week`: Aggregates metrics at the daily grain.
-- MAGIC - `ORDER BY t.date`: Displays chronological time-series progression.

-- COMMAND ----------

SELECT
    t.date,
    t.day_name,
    t.week,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM gold.fact_sales f
JOIN gold.dim_date t
    ON f.date = t.date
WHERE f.status IN ('Completed', 'Shipped')
GROUP BY t.date, t.day_name, t.week
ORDER BY t.date;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 3: Product Performance Ranking
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC Which individual products generate the highest revenue, and how many units were sold?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_product` on `product_id`. Slices metrics by product name and merchandise category.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `ORDER BY revenue DESC`: Ranks top-grossing products at the top.
-- MAGIC - Demonstrates how surrogate/business keys (`product_id`) connect atomic transaction rows to human-readable merchandise descriptions.

-- COMMAND ----------

SELECT
    p.product_id,
    p.product_name,
    p.subcategory,
    p.category,
    SUM(f.quantity) AS units_sold,
    COUNT(DISTINCT f.order_id) AS orders_count,
    ROUND(SUM(f.sales_amount), 2) AS revenue
FROM gold.fact_sales f
JOIN gold.dim_product p
    ON f.product_id = p.product_id
WHERE f.status IN ('Completed', 'Shipped')
GROUP BY p.product_id, p.product_name, p.subcategory, p.category
ORDER BY revenue DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 4: Sales by Category & Subcategory (Hierarchical Roll-Up)
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC What is the revenue contribution of each merchandise category and subcategory?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Demonstrates a **dimensional hierarchy roll-up**:
-- MAGIC `fact_sales` &rarr; `dim_product.subcategory` &rarr; `dim_product.category`.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `GROUP BY p.category, p.subcategory`: Aggregates the atomic fact lines into two parent levels of the merchandise hierarchy simultaneously.

-- COMMAND ----------

SELECT
    p.category,
    p.subcategory,
    SUM(f.quantity) AS units_sold,
    COUNT(DISTINCT f.order_id) AS orders_count,
    ROUND(SUM(f.sales_amount), 2) AS revenue
FROM gold.fact_sales f
JOIN gold.dim_product p
    ON f.product_id = p.product_id
WHERE f.status IN ('Completed', 'Shipped')
GROUP BY p.category, p.subcategory
ORDER BY revenue DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 5: Customer Summary & Top Spenders (Customer Lifetime Value)
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC Who are our highest-value customers by total spend, order count, and purchase volume?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_customer` on `customer_id` to evaluate customer lifetime value (CLV) and purchasing habits.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `COUNT(DISTINCT f.order_id)`: Measures repeat purchase frequency per customer.
-- MAGIC - `ORDER BY total_spent DESC`: Identifies VIP customers.

-- COMMAND ----------

SELECT
    c.customer_id,
    c.customer_name,
    c.city,
    c.country,
    COUNT(DISTINCT f.order_id) AS orders_count,
    SUM(f.quantity) AS units_purchased,
    ROUND(SUM(f.sales_amount), 2) AS total_spent
FROM gold.fact_sales f
JOIN gold.dim_customer c
    ON f.customer_id = c.customer_id
WHERE f.status IN ('Completed', 'Shipped')
GROUP BY c.customer_id, c.customer_name, c.city, c.country
ORDER BY total_spent DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 6: Sales by City & Geographic Distribution
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC Which geographic markets drive our sales volume and unique customer reach across the GCC?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_customer` on `customer_id` and aggregates by geographic market attributes (`city`, `country`).
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - `COUNT(DISTINCT f.customer_id)`: Calculates unique customer penetration per city.
-- MAGIC - `ROUND(SUM(f.sales_amount), 2)`: Evaluates total regional purchasing power.

-- COMMAND ----------

SELECT
    c.city,
    c.country,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    ROUND(SUM(f.sales_amount), 2) AS total_sales
FROM gold.fact_sales f
JOIN gold.dim_customer c
    ON f.customer_id = c.customer_id
WHERE f.status IN ('Completed', 'Shipped')
GROUP BY c.city, c.country
ORDER BY total_sales DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 7: Order Pipeline Breakdown by Status (Operational View)
-- MAGIC 
-- MAGIC ### Business Context:
-- MAGIC How many orders and what total monetary value exist across all stages of the fulfillment lifecycle?
-- MAGIC 
-- MAGIC ### Star Schema Pattern:
-- MAGIC Joins `fact_sales` with `dim_status` **without filtering** to provide complete operational visibility across `Pending`, `Processing`, `Completed`, `Shipped`, and `Cancelled` orders.
-- MAGIC 
-- MAGIC ### SQL Features Explained:
-- MAGIC - Omission of `WHERE status = 'Completed'` allows comparing fulfilled revenue against pending pipeline value and lost revenue from cancellations.

-- COMMAND ----------

SELECT
    s.status,
    COUNT(DISTINCT f.order_id) AS order_count,
    ROUND(SUM(f.sales_amount), 2) AS pipeline_value
FROM gold.fact_sales f
JOIN gold.dim_status s
    ON f.status = s.status
GROUP BY s.status
ORDER BY order_count DESC;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Question 8: Pipeline Execution & Ingestion Status (Audit Observability)
-- MAGIC 
-- MAGIC ### Operational Context:
-- MAGIC Which batch extract dates have been successfully processed through the medallion layers into the Gold Star Schema?
-- MAGIC 
-- MAGIC ### State Tracking Pattern:
-- MAGIC Queries `bronze.pipeline_runs` to inspect batch execution state and completion timestamps.

-- COMMAND ----------

SELECT
    run_date,
    status,
    processed_at
FROM bronze.pipeline_runs
ORDER BY run_date;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Summary & Key Educational Takeaways
-- MAGIC 
-- MAGIC - **Star Joins**: Sliced analytical metrics by joining `gold.fact_sales` directly with dimensions (`dim_date`, `dim_customer`, `dim_product`, `dim_status`).
-- MAGIC - **Realized vs. Pipeline Metrics**:
-- MAGIC   - Business revenue questions (Q1&ndash;Q6) isolate fulfilled orders (`status IN ('Completed', 'Shipped')`).
-- MAGIC   - Operational questions (Q7) examine the entire pipeline including pending and cancelled orders.
-- MAGIC - **Dimensional Hierarchies**: Evaluated hierarchical roll-up from products to subcategories and categories (Q4).
-- MAGIC - **Audit Observability**: Verified chronological batch progression using `bronze.pipeline_runs` (Q8).
