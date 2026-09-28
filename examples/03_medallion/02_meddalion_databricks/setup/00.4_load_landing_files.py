# Databricks notebook source
# MAGIC %md
# MAGIC # 00.4 - Helper: Load Raw CSV Extract Files to Unity Catalog Volume
# MAGIC 
# MAGIC This helper notebook populates the Unity Catalog Volume:
# MAGIC `/Volumes/<catalog_name>/bronze/landing_zone/`
# MAGIC 
# MAGIC with the 4 daily batches of raw CSV extracts (`2026-09-17`, `2026-09-18`, `2026-09-19`, `2026-09-20`).
# MAGIC 
# MAGIC ### Two Supported Ingestion Modes:
# MAGIC 1. **Automatic Copy from Cloned Repository**: If this workspace was created via Databricks Repos / Git Folders, the script copies files directly from `landing_zone/sales_data/`.
# MAGIC 2. **Self-Contained Embedded Dataset**: If imported as individual notebooks without the full Git folder, this notebook contains the complete, exact CSV extract datasets embedded in Python and writes them directly to the Volume in seconds!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Configure Catalog and Volume Widgets

# COMMAND ----------

dbutils.widgets.text("catalog_name", "sales_lake", "Catalog Name")
dbutils.widgets.text("volume_path", "", "Target Volume Path (leave blank for default)")

catalog_name = dbutils.widgets.get("catalog_name")
custom_volume_path = dbutils.widgets.get("volume_path").strip()

# Dynamically derive volume_path if not explicitly provided
if custom_volume_path:
    volume_path = custom_volume_path
else:
    volume_path = f"/Volumes/{catalog_name}/bronze/landing_zone"

print("==================================================")
print(f"Catalog Name: {catalog_name}")
print(f"Target Volume: {volume_path}")
print("==================================================")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Ensure Target Volume Exists in Unity Catalog

# COMMAND ----------

# Idempotently ensure the catalog, bronze schema, and Volume exist
spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.bronze")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog_name}.bronze.landing_zone")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Populate CSV Files into Volume

# COMMAND ----------

import os
import shutil

# Check common repository locations for existing source files
repo_source_dirs = [
    os.path.abspath(os.path.join(os.getcwd(), "..", "..", "landing_zone", "sales_data")),
    os.path.abspath(os.path.join(os.getcwd(), "..", "landing_zone", "sales_data")),
    os.path.abspath(os.path.join(os.getcwd(), "landing_zone", "sales_data")),
    "/Workspace/Repos/" + os.getcwd().split("/Workspace/Repos/")[-1].split("/")[0] + "/landing_zone/sales_data" if "/Workspace/Repos/" in os.getcwd() else None
]

found_source = None
for s_dir in repo_source_dirs:
    if s_dir and os.path.exists(s_dir) and os.path.exists(os.path.join(s_dir, "2026-09-17")):
        found_source = s_dir
        break

dates = ["2026-09-17", "2026-09-18", "2026-09-19", "2026-09-20"]
files = ["customers.csv", "products.csv", "product_category.csv", "orders.csv", "order_items.csv"]

if found_source:
    print(f"Found source CSV extracts in repository folder: {found_source}")
    print("Copying files to Unity Catalog Volume...")
    for d in dates:
        dest_dir = os.path.join(volume_path, d)
        os.makedirs(dest_dir, exist_ok=True)
        src_date_dir = os.path.join(found_source, d)
        for f in files:
            src_f = os.path.join(src_date_dir, f)
            dest_f = os.path.join(dest_dir, f)
            if os.path.exists(src_f):
                shutil.copyfile(src_f, dest_f)
                print(f"  Copied: {d}/{f} -> {dest_f}")
    print("\nFile copy completed successfully from repository.")
else:
    print("Repository folder not found. Writing complete embedded datasets directly into Volume...")
    DATASETS = {
        "2026-09-17": {
            "customers.csv": """customer_id,customer_name,email,city,country,updated_date
1,  ali hassan  ,Ali@Example.COM,Doha,Qatar,2026-09-17 10:00:00
2,SARA AHMED,,Al Rayyan,QA,2026-09-17 11:00:00
2,Sara Ahmed,sara@example.com,Al Rayyan,QAT,2026-09-17 12:00:00
3,Omar Saleh,omar@example.com,Al Wakrah,qatar,2026-09-17 09:00:00
4,Fatima Al-Thani,fatima.althani@example.com, Lusail ,Qatar,2026-09-17 15:30:00
5,mohammed khalid,mohammed.k@example.com,doha,QAT,2026-09-17 08:45:00
6,Noor Abdullah,noor.abdullah@example.com,Al Khor,Qatar,2026-09-17 11:20:00
7,Hassan Ibrahim,hassan.ibrahim@example.com,Umm Salal,QA,2026-09-17 14:10:00
8, Layla Mahmoud ,layla.mahmoud@example.com,Al Daayen,Qatar,2026-09-17 09:05:00
9,Khalid Al-Kuwari,khalid.k@example.com,Dubai,United Arab Emirates,2026-09-17 16:00:00
10,Reem Al-Sulaiti,reem.s@example.com,Al Shamal,,2026-09-17 13:15:00
11,khalid rahman,khalid.rahman,Al-Wakrah,Qatar,2026-09-17 10:30:00
12,Maryam Al-Bader,maryam.b@example.com,Doha,QATAR,2026-09-17 17:00:00
13,Ahmed Al-Marri,ahmed.marri@example.com,Riyadh,Saudi Arabia,2026-09-17 12:40:00
14,Hessa Al-Dosari,hessa.d@example.com,Al Rayyan,Qatar,2026-09-17 18:20:00
15,Tariq Aziz,tariq.aziz@example.com,Dohaa,Qa,2026-09-17 19:10:00
""",
            "products.csv": """product_id,product_name,subcategory_code,unit_price,updated_date
101,Laptop Pro 15,ELEC_COMP,"1,500.00",2026-09-17 08:00:00
102,Wireless Mouse,,25.00,2026-09-17 08:00:00
103,Mechanical Keyboard,ELEC_ACC,75.00,2026-09-17 08:00:00
104,Standing Desk,FURN_DSK,bad_price,2026-09-17 08:00:00
105,Ergonomic Chair,FURN_CHR,350.00,2026-09-17 08:00:00
106,  27-inch 4K Monitor  ,ELEC_COMP,400.00,2026-09-17 08:00:00
107,USB-C Hub Multiport,ELEC_ACC,45.00,2026-09-17 08:00:00
108,Noise Cancelling Headphones,ELEC_AUD,199.00,2026-09-17 08:00:00
109,Bluetooth Speaker,ELEC_AUD,59.00,2026-09-17 08:00:00
110,SAMSUNG GALAXY S25,elec_mob,999.00,2026-09-17 08:00:00
111,iPhone 16 Pro,ELEC_MOB,1199.00,2026-09-17 08:00:00
112,Leather Notebook A5,OFF_NOTE,15.00,2026-09-17 08:00:00
113,Gel Pen Set (10 pcs),OFF_STAT,8.50,2026-09-17 08:00:00
114,Water Bottle 1L,HOME_KIT,22.00,2026-09-17 08:00:00
115,Yoga Mat Non-Slip,FIT_ACC,-25.00,2026-09-17 08:00:00
118,Generic Gift Card,XXXX,50.00,2026-09-17 08:00:00
""",
            "product_category.csv": """subcategory_code,subcategory,category,updated_date
ELEC_COMP,Laptops,electronics,2026-09-17 07:00:00
ELEC_COMP,Computers,ELECTRONICS,2026-09-17 08:00:00
ELEC_ACC,Accessories,Electronics,2026-09-17 08:00:00
ELEC_AUD,Audio,Electronics,2026-09-17 08:00:00
ELEC_MOB,Mobile Phones,Electronics,2026-09-17 08:00:00
FURN_DSK,Desks,Furniture,2026-09-17 08:00:00
FURN_CHR,Chairs,Furniture,2026-09-17 08:00:00
OFF_NOTE,Notebooks,Office Supplies,2026-09-17 08:00:00
OFF_STAT,Stationery,Office Supplies,2026-09-17 08:00:00
HOME_KIT,Kitchenware,Home & Kitchen,2026-09-17 08:00:00
FIT_ACC,Fitness Accessories,Sports & Fitness,2026-09-17 08:00:00
OTHER,Other,Other,2026-09-17 08:00:00
""",
            "orders.csv": """order_id,customer_id,order_date,status,updated_date
1001,1,2026-09-17,completed,2026-09-17 10:30:00
1002,2,2026-09-17,pending,2026-09-17 11:15:00
1003,99,2026-09-17,Completed,2026-09-17 11:45:00
1004,3,2099-01-01,completed,2026-09-17 12:00:00
1005,4,2026-09-17,Complete,2026-09-17 12:30:00
1006,5,2026-09-17,pending,2026-09-17 13:00:00
1007,6,2026-09-17,shiped,2026-09-17 13:45:00
1008,7,2026/09/17,Completed,2026-09-17 14:20:00
1009,8,2026-09-17,COMPLETED,2026-09-17 15:00:00
1010,9,2026-09-17,pending,2026-09-17 15:30:00
1011,10,2026-09-17,Shipped,2026-09-17 16:10:00
1012,11,2026-09-17,,2026-09-17 16:40:00
1013,12,2026-09-17,Cancelled,2026-09-17 17:15:00
1014,13,2026-09-17,Processing,2026-09-17 17:50:00
1015,14,2026-09-17,PENDING,2026-09-17 18:30:00
1016,15,2026-09-17,done,2026-09-17 19:20:00
1017,1,2026-09-17,pending,2026-09-17 20:00:00
1018,4,2026-09-17,Completed,2026-09-17 21:10:00
""",
            "order_items.csv": """order_item_id,order_id,product_id,quantity,unit_price,updated_date
1,1001,101,1,"1,500.00",2026-09-17 10:30:00
2,1001,102,1,25.00,2026-09-17 10:30:00
2,1001,102,2,25.00,2026-09-17 10:35:00
3,1001,103,1,75.00,2026-09-17 10:30:00
4,1002,106,1,400.00,2026-09-17 11:15:00
5,1002,999,1,50.00,2026-09-17 11:15:00
6,1003,107,-1,45.00,2026-09-17 11:45:00
7,1005,110,1,999.00,2026-09-17 12:30:00
8,1005,107,2,45.00,2026-09-17 12:30:00
9,1006,108,1,199.00,2026-09-17 13:00:00
10,1006,109,1,59.00,2026-09-17 13:00:00
11,1007,105,1,350.00,2026-09-17 13:45:00
12,1008,111,1,1199.00,2026-09-17 14:20:00
13,1008,103,1,75.00,2026-09-17 14:20:00
14,1009,108,2,199.00,2026-09-17 15:00:00
15,1009,114,3,22.00,2026-09-17 15:00:00
16,1010,101,1,"1,500.00",2026-09-17 15:30:00
17,1010,107,1,,2026-09-17 15:30:00
18,1011,106,2,400.00,2026-09-17 16:10:00
19,1011,112,5,15.00,2026-09-17 16:10:00
20,1011,113,3,8.50,2026-09-17 16:10:00
21,1012,110,1,999.00,2026-09-17 16:40:00
22,1013,101,1,"1,500.00",2026-09-17 17:15:00
23,1014,105,1,350.00,2026-09-17 17:50:00
24,1014,103,1,75.00,2026-09-17 17:50:00
25,1015,108,1,199.00,2026-09-17 18:30:00
26,1015,114,2,22.00,2026-09-17 18:30:00
27,1016,111,1,1199.00,2026-09-17 19:20:00
28,1017,106,1,400.00,2026-09-17 20:00:00
29,1017,104,1,299.00,2026-09-17 20:00:00
30,1004,102,1,25.00,2026-09-17 12:00:00
31,1018,110,1,999.00,2026-09-17 21:10:00
32,1018,103,1,75.00,2026-09-17 21:10:00
33,1018,107,1,45.00,2026-09-17 21:10:00
46,1018,114,0,22.00,2026-09-17 21:10:00
47,1018,118,1,50.00,2026-09-17 21:10:00
"""
        },
        "2026-09-18": {
            "customers.csv": """customer_id,customer_name,email,city,country,updated_date
2,Sara Ahmed,sara.ahmed@example.com,Lusail,Qatar,2026-09-18 09:30:00
5,Mohammed Khalid, mohammed.k@example.com ,Doha,Qatar,2026-09-18 10:15:00
11,Khalid Rahman,khalid.rahman@example.com,Al Wakrah,Qatar,2026-09-18 11:00:00
16,Nasser Al-Attiyah,nasser.a@example.com,,Qatar,2026-09-18 14:00:00
1,Ali Hassan,ali.hassan@example.com,Al Wakrah,Qatar,2026-09-18 16:30:00
""",
            "products.csv": """product_id,product_name,subcategory_code,unit_price,updated_date
101,Laptop Pro 15,ELEC_COMP,"1,399.00",2026-09-18 08:00:00
102,Wireless Mouse,ELEC_ACC,25.00,2026-09-18 08:00:00
116,HD Pro Webcam 1080p,ELEC_ACC,79.00,2026-09-18 08:00:00
""",
            "product_category.csv": """subcategory_code,subcategory,category,updated_date
ELEC_ACC,Accessories,Electronics,2026-09-18 08:00:00
ELEC_MOB,Mobile Phones,Electronics,2026-09-18 08:00:00
HOME_STAT,Stationery,Home Office,2026-09-18 08:00:00
""",
            "orders.csv": """order_id,customer_id,order_date,status,updated_date
1006,5,2026-09-17,Completed,2026-09-18 09:00:00
1010,9,2026-09-17,Completed,2026-09-18 10:30:00
1019,16,2026-09-18,Completed,2026-09-18 14:30:00
1020,2,2026-09-18,pending,2026-09-18 15:00:00
1021,11,2026-09-18,completed ,2026-09-18 16:00:00
""",
            "order_items.csv": """order_item_id,order_id,product_id,quantity,unit_price,updated_date
34,1019,101,1,"1,399.00",2026-09-18 14:30:00
35,1019,116,1,79.00,2026-09-18 14:30:00
36,1020,111,1,1199.00,2026-09-18 15:00:00
37,1020,102,1,25.00,2026-09-18 15:00:00
38,1021,106,1,400.00,2026-09-18 16:00:00
39,1021,103,1,75.00,2026-09-18 16:00:00
"""
        },
        "2026-09-19": {
            "customers.csv": """customer_id,customer_name,email,city,country,updated_date
16,Nasser Al-Attiyah,nasser.a@example.com,Doha,Qatar,2026-09-19 09:00:00
17,Salma Al-Kuwari,salma.k@example.com,Al Khor,Qatar,2026-09-19 11:30:00
""",
            "products.csv": """product_id,product_name,subcategory_code,unit_price,updated_date
104,Standing Desk,FURN_DSK,299.00,2026-09-19 08:00:00
115,Yoga Mat Non-Slip,FIT_ACC,25.00,2026-09-19 08:00:00
""",
            "product_category.csv": """subcategory_code,subcategory,category,updated_date
ELEC_AUD,Audio & Headphones,Electronics,2026-09-19 08:00:00
""",
            "orders.csv": """order_id,customer_id,order_date,status,updated_date
1015,14,2026-09-17,Completed,2026-09-19 10:00:00
1017,1,2026-09-17,Shipped,2026-09-19 11:00:00
1020,2,2026-09-18,Completed,2026-09-19 12:00:00
1022,17,2026-09-19,Completed,2026-09-19 13:00:00
""",
            "order_items.csv": """order_item_id,order_id,product_id,quantity,unit_price,updated_date
40,1022,104,1,299.00,2026-09-19 13:00:00
41,1022,105,1,350.00,2026-09-19 13:00:00
41,1022,105,2,350.00,2026-09-19 13:10:00
"""
        },
        "2026-09-20": {
            "customers.csv": """customer_id,customer_name,email,city,country,updated_date
4,Fatima Al-Thani,fatima.althani@example.com,Doha,Qatar,2026-09-20 10:00:00
12,Maryam Al-Bader,maryam.b@example.com,Doha,Qatar,2026-09-20 11:00:00
18,Bader Al-Mansoor,BADER.M@EXAMPLE.COM, Al Rayyan ,Qatar,2026-09-20 14:00:00
""",
            "products.csv": """product_id,product_name,subcategory_code,unit_price,updated_date
117,LED Desk Lamp,HOME_LGT,49.00,2026-09-20 08:00:00
""",
            "product_category.csv": """subcategory_code,subcategory,category,updated_date
HOME_LGT,Lighting,Home & Kitchen,2026-09-20 08:00:00
""",
            "orders.csv": """order_id,customer_id,order_date,status,updated_date
1023,18,2026-09-20,pending,2026-09-20 14:30:00
1024,99,2026-09-20,Completed,2026-09-20 15:00:00
1025,8,20-09-2026,Completed,2026-09-20 16:00:00
""",
            "order_items.csv": """order_item_id,order_id,product_id,quantity,unit_price,updated_date
42,1024,101,1,"1,399.00",2026-09-20 15:00:00
43,1023,117,2,49.00,2026-09-20 14:30:00
44,1023,116,1,79.00,2026-09-20 14:30:00
45,1025,115,1,25.00,2026-09-20 16:00:00
"""
        }
    }

    for d, d_files in DATASETS.items():
        dest_dir = os.path.join(volume_path, d)
        os.makedirs(dest_dir, exist_ok=True)
        for fname, content in d_files.items():
            dest_file = os.path.join(dest_dir, fname)
            with open(dest_file, "w", encoding="utf-8") as fp:
                fp.write(content.strip() + "\n")
            print(f"  Wrote: {d}/{fname} ({len(content)} bytes)")
    print("\nStandalone dataset written to Unity Catalog Volume.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Verify Files in Unity Catalog Volume

# COMMAND ----------

# Display date subdirectories in Volume
display(dbutils.fs.ls(volume_path))

# COMMAND ----------

# Display CSV extract files inside Day 1 folder
display(dbutils.fs.ls(f"{volume_path}/2026-09-17"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary & Next Step
# MAGIC - Raw daily CSV extracts for all 4 dates (`2026-09-17` to `2026-09-20`) are now available in Unity Catalog Volume `${volume_path}`.
# MAGIC - Proceed to [`01_bronze.sql`](../pipeline/01_bronze.sql) to run the Bronze ingestion pipeline.
