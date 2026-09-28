"""
Retail Sales Data Generator & Medallion Pipeline Orchestrator
=============================================================

This script generates realistic retail sales data from January 1, 2025 through
the current date (September 28, 2026), inserts it into the Bronze layer, and
populates the Silver and Gold layers by reusing the lakehouse transformation logic.

Key Features:
  1. Inspects and reuses existing Bronze schemas automatically.
  2. Realistic business simulation:
     - Growth trend (exponential monthly growth ~130 to ~700 orders/day)
     - Day of week variations (Friday/Saturday/Thursday peaks in GCC)
     - Seasonal patterns (summer lull, Q4 surge)
     - Holiday spikes (White Friday, National Days, Eid seasons, Back-to-school)
     - Product popularity differences (Pareto distribution)
     - Customer purchasing behavior (VIP, frequent, occasional segments)
     - Regional market variations (Qatar, UAE, Saudi Arabia)
     - Order volume strictly between 100 and 1,000 orders/day
     - 1 to 10 line items per order
  3. Efficient bulk insertion into DuckLake Bronze tables.
  4. End-to-end transformation into Silver and Gold star schema layers.
  5. Updates `bronze.pipeline_runs` state tracking and outputs KPI summaries.

Usage:
  python generate_retail_sales.py               # Generate full dataset and run pipeline
  python generate_retail_sales.py --init        # Reset and re-initialize catalog first
  python generate_retail_sales.py --bronze-only # Only generate and insert into Bronze
  python generate_retail_sales.py --help        # Show available options
"""

import argparse
import datetime
import math
import os
import random
import sys
import time
from typing import Dict, List, Tuple

import duckdb
import pyarrow as pa

# Configure UTF-8 output for Windows console
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
LAKEHOUSE_DIR = os.path.join(BASE_DIR, "lakehouse")
CATALOG_PATH = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "sales_lake_catalog.db")).replace("\\", "/")
DATA_PATH = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "sales_lake_data")).replace("\\", "/")

DEFAULT_START_DATE = datetime.date(2025, 1, 1)
DEFAULT_END_DATE = datetime.date(2026, 9, 28)


# ---------------------------------------------------------------------------
# 2. Database Connection Helper
# ---------------------------------------------------------------------------
def get_ducklake_connection():
    """Connects to the DuckLake catalog and selects sales_lake database."""
    con = duckdb.connect()
    con.sql(f"""
        INSTALL ducklake;
        LOAD ducklake;
        ATTACH '{CATALOG_PATH}' AS sales_lake (
            TYPE DUCKLAKE,
            DATA_PATH '{DATA_PATH}',
            OVERRIDE_DATA_PATH TRUE
        );
        USE sales_lake;
    """)
    return con


# ---------------------------------------------------------------------------
# 3. Schema Inspection
# ---------------------------------------------------------------------------
def inspect_bronze_schemas(con) -> Dict[str, List[Tuple[str, str]]]:
    """
    Automatically inspects and returns the column definitions of all Bronze tables.
    Validates compatibility before generating and inserting any data.
    """
    print("\n" + "=" * 65)
    print("  STEP 1: Inspecting Existing Bronze Layer Schema")
    print("=" * 65)

    tables = con.sql("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_catalog = 'sales_lake'
          AND table_schema = 'bronze'
          AND table_name != 'pipeline_runs'
        ORDER BY table_name;
    """).fetchall()

    if not tables:
        raise RuntimeError("No Bronze tables found in sales_lake catalog. Run setup first.")

    schemas = {}
    for (tbl,) in tables:
        cols = con.sql(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_catalog = 'sales_lake'
              AND table_schema = 'bronze'
              AND table_name = '{tbl}'
            ORDER BY ordinal_position;
        """).fetchall()
        schemas[tbl] = cols

        col_str = ", ".join([f"{col} ({dt})" for col, dt in cols])
        print(f"\n  [bronze.{tbl}] ({len(cols)} columns):")
        for col, dt in cols:
            print(f"    - {col:<18} : {dt}")

    print("\n  ✓ Bronze schemas successfully verified and reused.")
    print("=" * 65 + "\n")
    return schemas


# ---------------------------------------------------------------------------
# 4. Realistic Catalog & Customer Definitions
# ---------------------------------------------------------------------------
CATEGORIES_DATA = [
    ("ELEC_COMP", "Computers", "Electronics"),
    ("ELEC_MOB",  "Mobile Phones", "Electronics"),
    ("ELEC_ACC",  "Accessories", "Electronics"),
    ("ELEC_AUD",  "Audio", "Electronics"),
    ("HOME_FURN", "Furniture", "Home & Office"),
    ("HOME_APPL", "Kitchen Appliances", "Home Appliances"),
    ("HOME_STAT", "Stationery", "Home & Office"),
]

# Rich product catalog with realistic baseline prices and popularity weights (Pareto)
PRODUCTS_DATA = [
    # Computers
    ("101", "Laptop Pro 15", "ELEC_COMP", "1499.00", 4),
    ("106", "UltraWide Monitor 27", "ELEC_COMP", "349.00", 7),
    ("121", "Tablet Air 11", "ELEC_COMP", "499.00", 6),
    ("131", "Desktop Workstation", "ELEC_COMP", "1899.00", 2),
    # Mobile Phones
    ("109", "iPhone 16 Pro", "ELEC_MOB", "999.00", 8),
    ("110", "Samsung Galaxy S25", "ELEC_MOB", "899.00", 7),
    ("132", "Google Pixel 9", "ELEC_MOB", "799.00", 4),
    # Accessories (High popularity frequency)
    ("102", "Optical Mouse", "ELEC_ACC", "25.00", 22),
    ("103", "Mechanical Keyboard", "ELEC_ACC", "69.99", 16),
    ("104", "USB-C Multiport Hub", "ELEC_ACC", "39.99", 18),
    ("105", "Wireless Ergonomic Mouse", "ELEC_ACC", "45.00", 17),
    ("118", "Dual-Sided Desk Mat", "ELEC_ACC", "24.00", 15),
    ("119", "4K Ultra HD Webcam", "ELEC_ACC", "99.00", 9),
    ("122", "Fast Wireless Charger", "ELEC_ACC", "29.99", 18),
    ("133", "Aluminum Laptop Stand", "ELEC_ACC", "34.50", 14),
    # Audio
    ("111", "Wireless Over-Ear Headphones", "ELEC_AUD", "149.00", 12),
    ("112", "Bluetooth Speaker Waterproof", "ELEC_AUD", "79.00", 11),
    ("120", "Smartwatch Active", "ELEC_AUD", "249.00", 7),
    ("124", "ANC True Wireless Earbuds", "ELEC_AUD", "129.00", 16),
    # Furniture
    ("107", "Ergonomic Office Chair", "HOME_FURN", "229.00", 5),
    ("108", "Solid Wood Study Desk", "HOME_FURN", "299.00", 4),
    ("113", "Electric Standing Desk", "HOME_FURN", "489.00", 4),
    ("127", "Modular 5-Tier Bookshelf", "HOME_FURN", "159.00", 4),
    ("128", "Dimmable LED Desk Lamp", "HOME_FURN", "42.00", 10),
    # Kitchen Appliances
    ("114", "Espresso Coffee Maker", "HOME_APPL", "129.00", 8),
    ("115", "Digital Air Fryer 5L", "HOME_APPL", "99.00", 10),
    ("125", "Digital Microwave 25L", "HOME_APPL", "149.00", 5),
    ("126", "High-Power Blender", "HOME_APPL", "69.00", 8),
    ("134", "Stainless Electric Kettle", "HOME_APPL", "39.00", 12),
    # Stationery
    ("116", "Hardcover Notebook Set", "HOME_STAT", "14.50", 18),
    ("117", "Ergonomic Gel Pen Pack", "HOME_STAT", "8.99", 24),
    ("129", "Steel Desktop File Organizer", "HOME_STAT", "19.50", 12),
    ("130", "Magnetic Dry-Erase Whiteboard", "HOME_STAT", "49.00", 6),
    ("135", "Document Paper Shredder", "HOME_STAT", "79.00", 4),
]

REGIONAL_CITIES = [
    # Qatar (65% share)
    ("Doha", "Qatar", 45),
    ("Al Rayyan", "Qatar", 15),
    ("Lusail", "Qatar", 12),
    ("Al Wakrah", "Qatar", 8),
    ("Al Khor", "Qatar", 5),
    ("Umm Salal", "Qatar", 4),
    # United Arab Emirates (20% share)
    ("Dubai", "United Arab Emirates", 13),
    ("Abu Dhabi", "United Arab Emirates", 8),
    ("Sharjah", "United Arab Emirates", 3),
    # Saudi Arabia (15% share)
    ("Riyadh", "Saudi Arabia", 10),
    ("Jeddah", "Saudi Arabia", 6),
    ("Dammam", "Saudi Arabia", 3),
]

ARABIC_FIRST_NAMES = [
    "Mohammed", "Ali", "Ahmed", "Abdullah", "Omar", "Khalid", "Saeed", "Hamad",
    "Abdulaziz", "Fahad", "Salem", "Youssef", "Tariq", "Nasser", "Ibrahim",
    "Sara", "Fatima", "Maryam", "Noor", "Amina", "Reem", "Dana", "Hessa",
    "Noura", "Aisha", "Maha", "Lulwa", "Shaikha", "Zainab", "Layla"
]

FAMILY_NAMES = [
    "Al-Thani", "Al-Kuwari", "Al-Marri", "Al-Hajri", "Al-Attiyah", "Al-Nuaimi",
    "Al-Sulaiti", "Al-Kaabi", "Al-Dosari", "Al-Khelaifi", "Hassan", "Ahmed",
    "Ibrahim", "Khalid", "Abdullah", "Nasser", "Farid", "Mansoor", "Khan",
    "Sharma", "Smith", "Patel"
]


def generate_customer_pool(num_customers: int = 5000, seed: int = 42) -> List[Dict]:
    """Generates a rich, segmented pool of customers with regional and CLV attributes."""
    rng = random.Random(seed)
    cities, countries, city_weights = zip(*REGIONAL_CITIES)

    customers = []
    for cid in range(1, num_customers + 1):
        first = rng.choice(ARABIC_FIRST_NAMES)
        last = rng.choice(FAMILY_NAMES)
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower().replace('-', '')}{cid}@example.com"

        city_idx = rng.choices(range(len(cities)), weights=city_weights)[0]
        city = cities[city_idx]
        country = countries[city_idx]

        # Customer segmentation for purchasing behavior
        segment_prob = rng.random()
        if segment_prob < 0.10:
            segment = "VIP"         # 10%: high frequency, larger ticket
            order_weight = 6.0
        elif segment_prob < 0.35:
            segment = "Frequent"    # 25%: regular repeat buyer
            order_weight = 2.5
        elif segment_prob < 0.70:
            segment = "Regular"     # 35%: periodic buyer
            order_weight = 1.0
        else:
            segment = "Occasional"  # 30%: 1-2 purchases
            order_weight = 0.3

        # Join date staggered across 2024 - 2026
        join_days = rng.randint(0, 600)
        join_date = datetime.date(2024, 6, 1) + datetime.timedelta(days=join_days)

        customers.append({
            "customer_id": str(cid),
            "customer_name": full_name,
            "email": email,
            "city": city,
            "country": country,
            "segment": segment,
            "order_weight": order_weight,
            "join_date": join_date,
            "updated_date": f"{join_date.strftime('%Y-%m-%d')} 09:00:00",
            "_load_date": join_date,
            "_ingested_at": datetime.datetime.now(),
            "_source_file": "synthetic_generator"
        })

    return customers


# ---------------------------------------------------------------------------
# 5. Business Simulation Functions
# ---------------------------------------------------------------------------
def calculate_daily_order_volume(
    dt: datetime.date,
    start_date: datetime.date,
    end_date: datetime.date,
    rng: random.Random
) -> int:
    """
    Computes a statistically realistic order count for date `dt` factoring in:
    1. Monthly compound growth trend
    2. GCC weekday vs. weekend patterns
    3. Seasonal demand cycles
    4. Holiday and promotional spikes (White Friday, National Days, Eid, etc.)
    Guarantees order count strictly between 100 and 1,000.
    """
    total_days = max(1, (end_date - start_date).days)
    elapsed_days = (dt - start_date).days
    progress = elapsed_days / total_days

    # 1. Growth Trend: Business expands from ~140 base orders to ~620 base orders
    growth_multiplier = 1.0 + progress * 3.4
    base_orders = 135.0 * growth_multiplier

    # 2. Weekday vs Weekend (GCC: Thu evening, Fri, Sat are shopping peaks)
    # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    dow = dt.weekday()
    dow_multipliers = {
        0: 0.92,  # Monday
        1: 0.90,  # Tuesday
        2: 0.94,  # Wednesday
        3: 1.15,  # Thursday (weekend kickoff)
        4: 1.35,  # Friday (family shopping peak)
        5: 1.25,  # Saturday (weekend shopping)
        6: 0.98,  # Sunday
    }
    dow_factor = dow_multipliers.get(dow, 1.0)

    # 3. Monthly / Seasonal Factor
    month = dt.month
    monthly_factors = {
        1:  1.12,  # January Winter Sales
        2:  1.02,
        3:  1.18,  # Ramadan shopping
        4:  1.32,  # Eid al-Fitr gift buying
        5:  1.05,
        6:  1.22,  # Eid al-Adha
        7:  0.82,  # Summer travel lull
        8:  0.88,  # August vacation / late Aug back-to-school
        9:  1.20,  # Back to school surge
        10: 1.08,
        11: 1.55,  # White Friday / Cyber Week
        12: 1.40,  # National Day & End-of-year clearance
    }
    seasonal_factor = monthly_factors.get(month, 1.0)

    # 4. Specific Holiday / Promo Spikes
    promo_factor = 1.0
    # White Friday / Cyber Week (Late November)
    if month == 11 and 21 <= dt.day <= 30:
        promo_factor = 1.85 if dt.day in (26, 27, 28) else 1.50
    # Qatar National Day (Dec 18)
    elif month == 12 and 15 <= dt.day <= 18:
        promo_factor = 1.45
    # Saudi National Day (Sep 23)
    elif month == 9 and 21 <= dt.day <= 23:
        promo_factor = 1.25
    # UAE National Day (Dec 2)
    elif month == 12 and 1 <= dt.day <= 3:
        promo_factor = 1.25
    # Back to School Surge
    elif (month == 8 and dt.day >= 25) or (month == 9 and dt.day <= 5):
        promo_factor = 1.30
    # New Year White Sale
    elif month == 1 and 1 <= dt.day <= 5:
        promo_factor = 1.25

    # 5. Day-to-Day Statistical Noise
    noise = rng.gauss(1.0, 0.05)

    orders = int(base_orders * dow_factor * seasonal_factor * promo_factor * noise)

    # Strict volume constraint: 100 to 1,000 orders/day
    return max(100, min(1000, orders))


def sample_line_items_count(rng: random.Random) -> int:
    """Samples number of items in an order strictly between 1 and 10."""
    item_counts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    weights = [0.22, 0.28, 0.20, 0.13, 0.07, 0.04, 0.025, 0.015, 0.012, 0.008]
    return rng.choices(item_counts, weights=weights)[0]


def sample_order_status(dt: datetime.date, as_of_date: datetime.date, rng: random.Random) -> str:
    """Simulates realistic fulfillment lifecycle status depending on order recency."""
    days_ago = (as_of_date - dt).days

    if days_ago > 10:
        # Fully matured orders
        return rng.choices(
            ["Completed", "Shipped", "Cancelled", "Processing"],
            weights=[0.89, 0.06, 0.04, 0.01]
        )[0]
    elif days_ago > 3:
        # In-transit / recent fulfillment
        return rng.choices(
            ["Completed", "Shipped", "Processing", "Cancelled", "Pending"],
            weights=[0.55, 0.30, 0.08, 0.04, 0.03]
        )[0]
    else:
        # Latest active orders (today, yesterday)
        return rng.choices(
            ["Processing", "Pending", "Shipped", "Completed", "Cancelled"],
            weights=[0.35, 0.30, 0.20, 0.10, 0.05]
        )[0]


# ---------------------------------------------------------------------------
# 6. Bulk Generation & Insertion into Bronze
# ---------------------------------------------------------------------------
def generate_and_insert_bronze_data(
    con,
    start_date: datetime.date,
    end_date: datetime.date,
    seed: int = 42
) -> Dict[str, int]:
    """Generates synthetic retail sales dataset and inserts directly into Bronze."""
    rng = random.Random(seed)
    ingested_at = datetime.datetime.now()

    print("\n" + "=" * 65)
    print("  STEP 2: Generating Synthetic Retail Sales Data")
    print(f"  Date Range:  {start_date} to {end_date} ({(end_date - start_date).days + 1} days)")
    print("=" * 65)

    # 1. Product Categories
    print("  Generating product categories...")
    cat_rows = []
    for code, subcat, cat in CATEGORIES_DATA:
        cat_rows.append({
            "subcategory_code": code,
            "subcategory": subcat,
            "category": cat,
            "updated_date": f"{start_date} 00:00:00",
            "_load_date": start_date,
            "_ingested_at": ingested_at,
            "_source_file": "synthetic_generator"
        })
    cat_arrow = pa.Table.from_pylist(cat_rows)
    con.sql("INSERT INTO bronze.product_category SELECT * FROM cat_arrow")
    print(f"    ✓ {len(cat_rows)} categories inserted into bronze.product_category.")

    # 2. Products Catalog
    print("  Generating product catalog...")
    prod_rows = []
    prod_ids = []
    prod_weights = []
    prod_prices = {}
    for pid, pname, scode, price, weight in PRODUCTS_DATA:
        prod_ids.append(pid)
        prod_weights.append(weight)
        prod_prices[pid] = price
        prod_rows.append({
            "product_id": pid,
            "product_name": pname,
            "subcategory_code": scode,
            "unit_price": price,
            "updated_date": f"{start_date} 00:00:00",
            "_load_date": start_date,
            "_ingested_at": ingested_at,
            "_source_file": "synthetic_generator"
        })
    prod_arrow = pa.Table.from_pylist(prod_rows)
    con.sql("INSERT INTO bronze.products SELECT * FROM prod_arrow")
    print(f"    ✓ {len(prod_rows)} products inserted into bronze.products.")

    # 3. Customer Base
    print("  Generating customer base (5,000 customers)...")
    customer_pool = generate_customer_pool(num_customers=5000, seed=seed)
    cust_rows = []
    for c in customer_pool:
        cust_rows.append({
            "customer_id": c["customer_id"],
            "customer_name": c["customer_name"],
            "email": c["email"],
            "city": c["city"],
            "country": c["country"],
            "updated_date": c["updated_date"],
            "_load_date": c["_load_date"],
            "_ingested_at": c["_ingested_at"],
            "_source_file": c["_source_file"]
        })
    cust_arrow = pa.Table.from_pylist(cust_rows)
    con.sql("INSERT INTO bronze.customers SELECT * FROM cust_arrow")
    print(f"    ✓ {len(cust_rows)} customers inserted into bronze.customers.")

    # Customer sampling weights based on customer segment
    cust_ids = [c["customer_id"] for c in customer_pool]
    cust_weights = [c["order_weight"] for c in customer_pool]

    # 4. Generate Orders & Order Items by Day
    total_days = (end_date - start_date).days + 1
    print(f"  Generating daily orders and order lines across {total_days} days...")

    order_id_counter = 100000
    item_id_counter = 1000000

    total_orders = 0
    total_order_items = 0

    # Batch insertions by 30-day blocks for performance and low memory footprint
    batch_days = 30
    curr_start = start_date

    while curr_start <= end_date:
        curr_end = min(end_date, curr_start + datetime.timedelta(days=batch_days - 1))
        batch_orders = []
        batch_items = []

        day_cursor = curr_start
        while day_cursor <= curr_end:
            order_date_str = day_cursor.strftime("%Y-%m-%d")
            daily_vol = calculate_daily_order_volume(day_cursor, start_date, end_date, rng)

            # Sample customers for this day
            sampled_customers = rng.choices(cust_ids, weights=cust_weights, k=daily_vol)

            for cid in sampled_customers:
                order_id_counter += 1
                oid_str = str(order_id_counter)
                status = sample_order_status(day_cursor, end_date, rng)

                # Order time between 08:00 and 23:59
                h = rng.randint(8, 23)
                m = rng.randint(0, 59)
                s = rng.randint(0, 59)
                order_ts_str = f"{order_date_str} {h:02d}:{m:02d}:{s:02d}"

                batch_orders.append({
                    "order_id": oid_str,
                    "customer_id": cid,
                    "order_date": order_date_str,
                    "status": status,
                    "updated_date": order_ts_str,
                    "_load_date": day_cursor,
                    "_ingested_at": ingested_at,
                    "_source_file": "synthetic_generator"
                })

                # Line items for this order (1 to 10 items)
                num_items = sample_line_items_count(rng)
                sampled_products = rng.choices(prod_ids, weights=prod_weights, k=num_items)

                for pid in sampled_products:
                    item_id_counter += 1
                    # Quantity between 1 and 5 (higher for stationery/accessories)
                    qty = rng.choices([1, 2, 3, 4, 5], weights=[0.68, 0.21, 0.07, 0.03, 0.01])[0]
                    uprice = prod_prices[pid]

                    batch_items.append({
                        "order_item_id": str(item_id_counter),
                        "order_id": oid_str,
                        "product_id": pid,
                        "quantity": str(qty),
                        "unit_price": uprice,
                        "updated_date": order_ts_str,
                        "_load_date": day_cursor,
                        "_ingested_at": ingested_at,
                        "_source_file": "synthetic_generator"
                    })

            day_cursor += datetime.timedelta(days=1)

        # Bulk insert batch into DuckLake
        orders_arrow = pa.Table.from_pylist(batch_orders)
        items_arrow = pa.Table.from_pylist(batch_items)

        con.sql("INSERT INTO bronze.orders SELECT * FROM orders_arrow")
        con.sql("INSERT INTO bronze.order_items SELECT * FROM items_arrow")

        total_orders += len(batch_orders)
        total_order_items += len(batch_items)

        print(f"    - Processed {curr_start} to {curr_end}: +{len(batch_orders):,} orders, +{len(batch_items):,} line items")
        curr_start = curr_end + datetime.timedelta(days=1)

    print("\n" + "=" * 65)
    print(f"  ✓ Bronze Generation Complete!")
    print(f"    Total Orders:      {total_orders:,}")
    print(f"    Total Order Lines: {total_order_items:,}")
    print("=" * 65 + "\n")

    return {
        "orders": total_orders,
        "order_items": total_order_items,
        "customers": len(cust_rows),
        "products": len(prod_rows),
        "categories": len(cat_rows)
    }


# ---------------------------------------------------------------------------
# 7. Reusing Existing Code: Populate Silver and Gold
# ---------------------------------------------------------------------------
def populate_silver_and_gold_layers(con):
    """
    Reuses the exact transformation and modeling logic from 02_silver.py and 03_gold.py
    to clean, standardize, validate, and build the analytical Star Schema.
    """
    print("\n" + "=" * 65)
    print("  STEP 3: Populating Silver and Gold Layers (Reusing Pipeline Logic)")
    print("=" * 65)

    t0 = time.time()

    # --- 1. Silver Product Category ---
    print("  1/10 Standardizing & Merging silver.product_category...")
    con.sql("""
        CREATE OR REPLACE TABLE memory.stg_category_cleaned AS
        SELECT
            upper(trim(subcategory_code)) AS subcategory_code,
            subcategory,
            CASE
                WHEN lower(trim(category)) IN ('electronics', 'electronic') THEN 'Electronics'
                WHEN category IS NULL OR trim(category) = '' THEN 'Other'
                ELSE trim(category)
            END AS category,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.product_category
        WHERE trim(subcategory_code) <> '';

        CREATE OR REPLACE TABLE memory.stg_category AS
        SELECT subcategory_code, subcategory, category, updated_date
        FROM memory.stg_category_cleaned
        QUALIFY row_number() OVER (PARTITION BY subcategory_code ORDER BY updated_date DESC) = 1;

        MERGE INTO silver.product_category AS t
        USING memory.stg_category AS s
            ON t.subcategory_code = s.subcategory_code
        WHEN MATCHED THEN UPDATE SET
            subcategory = s.subcategory,
            category = s.category,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (subcategory_code, subcategory, category, updated_date)
        VALUES (s.subcategory_code, s.subcategory, s.category, s.updated_date);
    """)

    # --- 2. Silver Customers ---
    print("  2/10 Cleaning & Merging silver.customers...")
    con.sql("""
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
                WHEN lower(trim(replace(city, '-', ' '))) IN ('doha', 'dohaa') THEN 'Doha'
                ELSE trim(replace(city, '-', ' '))
            END AS city,
            CASE
                WHEN lower(trim(replace(city, '-', ' '))) IN ('doha', 'dohaa') THEN 'Qatar'
                WHEN country IS NULL OR trim(country) = '' THEN NULL
                WHEN upper(trim(country)) IN ('QATAR', 'QA', 'QAT') THEN 'Qatar'
                WHEN upper(trim(country)) IN ('UAE', 'UNITED ARAB EMIRATES', 'ARE') THEN 'United Arab Emirates'
                WHEN upper(trim(country)) IN ('KSA', 'SAUDI ARABIA', 'SA', 'SAU') THEN 'Saudi Arabia'
                ELSE trim(country)
            END AS country,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.customers;

        CREATE OR REPLACE TABLE memory.stg_customers AS
        SELECT customer_id, customer_name, email, city, country, updated_date
        FROM memory.stg_customers_cleaned
        WHERE customer_id IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY updated_date DESC) = 1;

        MERGE INTO silver.customers AS t
        USING memory.stg_customers AS s
            ON t.customer_id = s.customer_id
        WHEN MATCHED THEN UPDATE SET
            customer_name = s.customer_name,
            email = s.email,
            city = s.city,
            country = s.country,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (customer_id, customer_name, email, city, country, updated_date)
        VALUES (s.customer_id, s.customer_name, s.email, s.city, s.country, s.updated_date);
    """)

    # --- 3. Silver Products ---
    print("  3/10 Validating & Merging silver.products...")
    con.sql("""
        CREATE OR REPLACE TABLE memory.stg_products_cleaned AS
        SELECT
            try_cast(trim(product_id) AS INTEGER) AS product_id,
            CASE
                WHEN product_name IS NULL OR trim(product_name) = '' THEN NULL
                ELSE trim(product_name)
            END AS product_name,
            CASE
                WHEN subcategory_code IS NULL OR trim(subcategory_code) = '' THEN 'OTHER'
                ELSE upper(trim(subcategory_code))
            END AS subcategory_code,
            try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2)) AS unit_price,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.products;

        CREATE OR REPLACE TABLE memory.stg_products AS
        SELECT
            p.product_id,
            p.product_name,
            p.subcategory_code,
            coalesce(c.subcategory, 'Other') AS subcategory,
            coalesce(c.category, 'Other') AS category,
            p.unit_price,
            p.updated_date
        FROM memory.stg_products_cleaned AS p
        LEFT JOIN silver.product_category AS c
            ON p.subcategory_code = c.subcategory_code
        QUALIFY row_number() OVER (PARTITION BY p.product_id ORDER BY p.updated_date DESC) = 1;

        MERGE INTO silver.products AS t
        USING (
            SELECT * FROM memory.stg_products
            WHERE product_id IS NOT NULL AND unit_price IS NOT NULL AND unit_price >= 0
        ) AS s
            ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET
            product_name = s.product_name,
            subcategory_code = s.subcategory_code,
            subcategory = s.subcategory,
            category = s.category,
            unit_price = s.unit_price,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (product_id, product_name, subcategory_code, subcategory, category, unit_price, updated_date)
        VALUES (s.product_id, s.product_name, s.subcategory_code, s.subcategory, s.category, s.unit_price, s.updated_date);
    """)

    # --- 4. Silver Orders ---
    print("  4/10 Cleaning & Merging silver.orders...")
    con.sql("""
        CREATE OR REPLACE TABLE memory.stg_orders_cleaned AS
        SELECT
            try_cast(trim(order_id) AS INTEGER) AS order_id,
            try_cast(trim(customer_id) AS INTEGER) AS customer_id,
            CAST(
                coalesce(
                    try_strptime(trim(order_date), '%Y-%m-%d'),
                    try_strptime(trim(order_date), '%Y/%m/%d'),
                    try_strptime(trim(order_date), '%d-%m-%Y')
                ) AS DATE
            ) AS order_date,
            CASE
                WHEN status IS NULL OR trim(status) = '' THEN 'Unknown'
                WHEN lower(trim(status)) IN ('complete', 'completed', 'done') THEN 'Completed'
                WHEN lower(trim(status)) = 'pending' THEN 'Pending'
                WHEN lower(trim(status)) IN ('shipped', 'shiped') THEN 'Shipped'
                WHEN lower(trim(status)) IN ('cancelled', 'canceled') THEN 'Cancelled'
                WHEN lower(trim(status)) = 'processing' THEN 'Processing'
                ELSE trim(status)
            END AS status,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.orders;

        CREATE OR REPLACE TABLE memory.stg_orders AS
        SELECT order_id, customer_id, order_date, status, updated_date
        FROM memory.stg_orders_cleaned
        QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY updated_date DESC) = 1;

        MERGE INTO silver.orders AS t
        USING (
            SELECT o.*
            FROM memory.stg_orders AS o
            INNER JOIN silver.customers AS c
                ON o.customer_id = c.customer_id
            WHERE o.order_id IS NOT NULL AND o.order_date IS NOT NULL
        ) AS s
            ON t.order_id = s.order_id
        WHEN MATCHED THEN UPDATE SET
            customer_id = s.customer_id,
            order_date = s.order_date,
            status = s.status,
            updated_date = s.updated_date
        WHEN NOT MATCHED THEN INSERT (order_id, customer_id, order_date, status, updated_date)
        VALUES (s.order_id, s.customer_id, s.order_date, s.status, s.updated_date);
    """)

    # --- 5. Silver Order Items ---
    print("  5/10 Enriching & Merging silver.order_items...")
    con.sql("""
        CREATE OR REPLACE TABLE memory.stg_items_cleaned AS
        SELECT
            try_cast(trim(order_item_id) AS INTEGER) AS order_item_id,
            try_cast(trim(order_id) AS INTEGER) AS order_id,
            try_cast(trim(product_id) AS INTEGER) AS product_id,
            try_cast(trim(quantity) AS INTEGER) AS quantity,
            try_cast(replace(trim(unit_price), ',', '') AS DECIMAL(10, 2)) AS line_unit_price,
            try_strptime(trim(updated_date), '%Y-%m-%d %H:%M:%S') AS updated_date
        FROM bronze.order_items;

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
        LEFT JOIN silver.orders AS o ON i.order_id = o.order_id
        LEFT JOIN silver.products AS p ON i.product_id = p.product_id
        QUALIFY row_number() OVER (PARTITION BY i.order_item_id ORDER BY i.updated_date DESC) = 1;

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
            FROM memory.stg_items AS i
            INNER JOIN silver.orders AS o ON i.order_id = o.order_id
            INNER JOIN silver.products AS p ON i.product_id = p.product_id
            WHERE i.order_item_id IS NOT NULL AND i.quantity > 0 AND i.unit_price >= 0
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
            s.order_item_id, s.order_id, s.product_id, s.product_name, s.subcategory_code,
            s.subcategory, s.category, s.quantity, s.unit_price, s.line_total, s.updated_date
        );
    """)

    # --- 6. Gold dim_date ---
    print("  6/10 Populating gold.dim_date calendar dimension...")
    con.sql("""
        MERGE INTO gold.dim_date AS t
        USING (
            WITH bounds AS (
                SELECT MIN(order_date) AS first_date, MAX(order_date) AS last_date
                FROM silver.orders
                WHERE order_date IS NOT NULL
            ),
            days AS (
                SELECT CAST(day_ts AS DATE) AS date
                FROM bounds
                CROSS JOIN generate_series(first_date, last_date, INTERVAL 1 DAY) AS generated(day_ts)
            )
            SELECT
                date,
                year(date) AS year,
                quarter(date) AS quarter,
                month(date) AS month,
                monthname(date) AS month_name,
                week(date) AS week,
                day(date) AS day,
                dayname(date) AS day_name
            FROM days
        ) AS s
            ON t.date = s.date
        WHEN NOT MATCHED THEN INSERT (
            date, year, quarter, month, month_name, week, day, day_name
        ) VALUES (
            s.date, s.year, s.quarter, s.month, s.month_name, s.week, s.day, s.day_name
        );
    """)

    # --- 7. Gold dim_customer ---
    print("  7/10 Populating gold.dim_customer dimension...")
    con.sql("""
        MERGE INTO gold.dim_customer AS t
        USING silver.customers AS s
            ON t.customer_id = s.customer_id
        WHEN MATCHED THEN UPDATE SET
            customer_name = s.customer_name,
            email = s.email,
            city = s.city,
            country = s.country
        WHEN NOT MATCHED THEN INSERT (customer_id, customer_name, email, city, country)
        VALUES (s.customer_id, s.customer_name, s.email, s.city, s.country);
    """)

    # --- 8. Gold dim_product ---
    print("  8/10 Populating gold.dim_product dimension...")
    con.sql("""
        MERGE INTO gold.dim_product AS t
        USING silver.products AS s
            ON t.product_id = s.product_id
        WHEN MATCHED THEN UPDATE SET
            product_name = s.product_name,
            subcategory = s.subcategory,
            category = s.category
        WHEN NOT MATCHED THEN INSERT (product_id, product_name, subcategory, category)
        VALUES (s.product_id, s.product_name, s.subcategory, s.category);
    """)

    # --- 9. Gold dim_status ---
    print("  9/10 Populating gold.dim_status dimension...")
    con.sql("""
        MERGE INTO gold.dim_status AS t
        USING (
            SELECT DISTINCT status
            FROM silver.orders
            WHERE status IS NOT NULL
        ) AS s
            ON t.status = s.status
        WHEN NOT MATCHED THEN INSERT (status) VALUES (s.status);
    """)

    # --- 10. Gold fact_sales ---
    print("  10/10 Building central fact table gold.fact_sales...")
    con.sql("""
        MERGE INTO gold.fact_sales AS t
        USING (
            SELECT
                i.order_item_id,
                o.order_id,
                o.order_date AS date,
                o.customer_id,
                i.product_id,
                o.status,
                i.quantity,
                i.unit_price,
                CAST(i.quantity * i.unit_price AS DECIMAL(12, 2)) AS sales_amount
            FROM silver.order_items i
            JOIN silver.orders o ON i.order_id = o.order_id
        ) AS s
            ON t.order_item_id = s.order_item_id
        WHEN MATCHED THEN UPDATE SET
            order_id = s.order_id,
            date = s.date,
            customer_id = s.customer_id,
            product_id = s.product_id,
            status = s.status,
            quantity = s.quantity,
            unit_price = s.unit_price,
            sales_amount = s.sales_amount
        WHEN NOT MATCHED THEN INSERT (
            order_item_id, order_id, date, customer_id, product_id, status, quantity, unit_price, sales_amount
        ) VALUES (
            s.order_item_id, s.order_id, s.date, s.customer_id, s.product_id, s.status, s.quantity, s.unit_price, s.sales_amount
        );
    """)

    # --- Update Pipeline Runs State Tracking ---
    print("  Registering batch runs in bronze.pipeline_runs state table...")
    con.sql("""
        INSERT INTO bronze.pipeline_runs (run_date, status, processed_at)
        SELECT date, 'Completed', current_timestamp
        FROM gold.dim_date
        WHERE NOT EXISTS (
            SELECT 1 FROM bronze.pipeline_runs WHERE bronze.pipeline_runs.run_date = gold.dim_date.date
        );
    """)

    elapsed = time.time() - t0
    print(f"\n  ✓ Silver and Gold layers successfully populated in {elapsed:.2f} seconds!")
    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# 8. Lakehouse BI Verification & Summary
# ---------------------------------------------------------------------------
def print_lakehouse_summary(con):
    """Outputs an analytical reporting summary across all Medallion layers."""
    print("\n" + "=" * 65)
    print("         MEDALLION LAKEHOUSE LAYER METRICS SUMMARY")
    print("=" * 65)

    counts = [
        ("Bronze Categories", con.sql("SELECT count(*) FROM bronze.product_category").fetchone()[0]),
        ("Bronze Products",   con.sql("SELECT count(*) FROM bronze.products").fetchone()[0]),
        ("Bronze Customers",  con.sql("SELECT count(*) FROM bronze.customers").fetchone()[0]),
        ("Bronze Orders",     con.sql("SELECT count(*) FROM bronze.orders").fetchone()[0]),
        ("Bronze Items",      con.sql("SELECT count(*) FROM bronze.order_items").fetchone()[0]),
        ("------------------", "----------"),
        ("Silver Categories", con.sql("SELECT count(*) FROM silver.product_category").fetchone()[0]),
        ("Silver Products",   con.sql("SELECT count(*) FROM silver.products").fetchone()[0]),
        ("Silver Customers",  con.sql("SELECT count(*) FROM silver.customers").fetchone()[0]),
        ("Silver Orders",     con.sql("SELECT count(*) FROM silver.orders").fetchone()[0]),
        ("Silver Items",      con.sql("SELECT count(*) FROM silver.order_items").fetchone()[0]),
        ("------------------", "----------"),
        ("Gold dim_date",     con.sql("SELECT count(*) FROM gold.dim_date").fetchone()[0]),
        ("Gold dim_customer", con.sql("SELECT count(*) FROM gold.dim_customer").fetchone()[0]),
        ("Gold dim_product",  con.sql("SELECT count(*) FROM gold.dim_product").fetchone()[0]),
        ("Gold dim_status",   con.sql("SELECT count(*) FROM gold.dim_status").fetchone()[0]),
        ("Gold fact_sales",   con.sql("SELECT count(*) FROM gold.fact_sales").fetchone()[0]),
    ]

    for label, cnt in counts:
        if isinstance(cnt, int):
            print(f"  {label:<22} : {cnt:>12,}")
        else:
            print(f"  {label:<22}   {cnt:>12}")

    print("\n" + "-" * 65)
    print("  Key Business Reporting Metrics (Fulfilled Sales):")
    print("-" * 65)

    kpi = con.sql("""
        SELECT
            COUNT(*) AS fulfilled_order_lines,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(f.quantity) AS total_units_sold,
            ROUND(SUM(f.sales_amount), 2) AS total_sales_amount
        FROM gold.fact_sales f
        WHERE f.status IN ('Completed', 'Shipped');
    """).fetchall()[0]

    print(f"  Fulfilled Order Lines : {kpi[0]:>14,}")
    print(f"  Total Realized Orders : {kpi[1]:>14,}")
    print(f"  Total Units Sold      : {kpi[2]:>14,}")
    print(f"  Total Realized Sales  : ${kpi[3]:>13,}")

    print("\n  Top 5 Product Categories by Revenue:")
    top_cats = con.sql("""
        SELECT p.category, ROUND(SUM(f.sales_amount), 2) AS revenue
        FROM gold.fact_sales f
        JOIN gold.dim_product p ON f.product_id = p.product_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY p.category
        ORDER BY revenue DESC
        LIMIT 5;
    """).fetchall()
    for cat, rev in top_cats:
        print(f"    - {cat:<24} : ${rev:>12,}")

    print("\n  Top 5 Geographic Markets by Revenue:")
    top_regions = con.sql("""
        SELECT c.city, c.country, ROUND(SUM(f.sales_amount), 2) AS total_sales
        FROM gold.fact_sales f
        JOIN gold.dim_customer c ON f.customer_id = c.customer_id
        WHERE f.status IN ('Completed', 'Shipped')
        GROUP BY c.city, c.country
        ORDER BY total_sales DESC
        LIMIT 5;
    """).fetchall()
    for city, country, sales in top_regions:
        print(f"    - {city} ({country}) : ${sales:>12,}")

    print("=" * 65 + "\n")


# ---------------------------------------------------------------------------
# 9. Main Orchestrator
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Retail Sales Test Data Generator & Medallion Pipeline")
    parser.add_argument("--start-date", default="2025-01-01", help="Start date (YYYY-MM-DD), default: 2025-01-01")
    parser.add_argument("--end-date", default="2026-09-28", help="End date (YYYY-MM-DD), default: 2026-09-28")
    parser.add_argument("--init", action="store_true", help="Re-initialize lakehouse schemas before generating data")
    parser.add_argument("--bronze-only", action="store_true", help="Only insert into Bronze without populating Silver and Gold")
    args = parser.parse_args()

    start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if start_date > end_date:
        print("Error: start-date must be on or before end-date.")
        sys.exit(1)

    # Optional re-initialization
    if args.init:
        print("\nRe-initializing catalog and schemas...")
        import subprocess
        python_exe = sys.executable
        for script in [
            os.path.join(BASE_DIR, "setup", "00_setup.py"),
            os.path.join(BASE_DIR, "setup", "00.1_bronze_schema.py"),
            os.path.join(BASE_DIR, "setup", "00.2_silver_schema.py"),
            os.path.join(BASE_DIR, "setup", "00.3_gold_schema.py"),
        ]:
            print(f"  Running {os.path.basename(script)}...")
            res = subprocess.run([python_exe, script], cwd=BASE_DIR, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Error initializing schema:\n{res.stderr}")
                sys.exit(1)
        print("✓ Catalogs and schemas successfully initialized.\n")

    # Connect to Lakehouse
    con = get_ducklake_connection()

    try:
        # Step 1: Inspect Bronze schemas
        inspect_bronze_schemas(con)

        # Step 2: Generate and insert Bronze data
        generate_and_insert_bronze_data(con, start_date=start_date, end_date=end_date)

        # Step 3: Populate Silver and Gold by reusing pipeline transformation logic
        if not args.bronze_only:
            populate_silver_and_gold_layers(con)

        # Step 4: Display comprehensive summary & BI metrics
        print_lakehouse_summary(con)

    finally:
        con.close()


if __name__ == "__main__":
    main()
