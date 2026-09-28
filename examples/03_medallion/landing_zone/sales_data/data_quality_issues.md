# Data quality issues in the retail extracts

The CSVs under `data/YYYY-MM-DD/` are **intentionally dirty**. Use them to practice Silver-layer **cleaning**, **standardization**, **validation**, and **enrichment**. Bronze should store the files as received.

Extract folders:

| Folder | Role |
| --- | --- |
| `2026-09-17` | First (full) load |
| `2026-09-18` … `2026-09-20` | Incremental loads (new and changed rows only) |

Watermark column on **every** extract (including `order_items`): `updated_date`. Silver processes **one `run_date` at a time** and `MERGE`s the latest row per business key into Silver.

---

## Suggested Silver rules

These are the intended treatments. Your pipeline may implement them with SQL, DataFrames, or both.

### Cleaning

- Trim leading and trailing whitespace.
- Treat blank strings as null.
- Trim names and product names; lower-case emails. (DuckDB 1.5 has no `initcap()`, so the classroom notebook does not implement full title-case.)
- Parse numbers that use thousands separators (`1,500.00`) or non-numeric text (`bad_price`).
- Parse mixed date formats (`2026-09-17`, `2026/09/17`, `20-09-2026`).

### Standardization

- Country → ISO-like codes: Qatar / QA / QAT / Qa / QATAR → `QAT`; UAE / United Arab Emirates → `ARE`; KSA / Saudi Arabia → `SAU`.
- City: trim, replace hyphens with spaces (`Al-Wakrah` → `Al Wakrah`), title-case, fix obvious typos (`Dohaa` → `Doha`).
- Order status → a small set: `Completed`, `Pending`, `Shipped`, `Cancelled`, `Processing`. Map typos and aliases (`complete`, `COMPLETED`, `done`, `shiped`, trailing spaces).
- Category names: `electronics` / `ELECTRONICS` → `Electronics`.
- Subcategory codes: trim and upper-case (`elec_mob` → `ELEC_MOB`).

### Validation (quarantine invalid rows; do not drop them silently)

- Types and ranges: positive `unit_price` and `quantity`; valid integer IDs.
- Referential integrity: orders must reference a known customer; order items must reference a known order and product.
- Dates: reject future `order_date` values (for example `2099-01-01`).
- Emails: require a simple `local@domain` shape; blank or `khalid.rahman` is invalid.

### Enrichment

- Dimensions and facts: latest-wins on `updated_date` for `customer_id`, `product_id`, `subcategory_code`, `order_id`, and `order_item_id`.
- Products: join `product_category` on `subcategory_code`. If the code is blank or not in the lookup, use **`OTHER`**.
- Order items: prefer the line `unit_price` (price at sale time). If it is blank, fall back to the current catalog price. Compute `line_total = quantity * unit_price`.

Catch-all category row (first load):

```text
OTHER, Other, Other
```

### Classroom Silver pattern (used in `02_silver.py`)

Process **only** `_load_date = run_date`, then:

1. Clean today's Bronze rows into a memory staging table.
2. Keep the latest row per business key (`row_number()` on `updated_date`).
3. `MERGE INTO` Silver (insert new keys, update existing keys).
4. Insert invalid rows into `quarantine` with a reason.
5. Re-check `quarantine.order_items` after products/orders are updated, so a later price fix can release an older order line.

Do not `CREATE OR REPLACE` the Silver tables each day — that would wipe yesterday's data.

---

## `product_category`

| Issue | Where | Practice |
| --- | --- | --- |
| Duplicate `ELEC_COMP` (`Laptops` at 07:00, `Computers` at 08:00) | `2026-09-17` | Latest-wins; keep `Computers` |
| Inconsistent category casing (`electronics`, `ELECTRONICS`) | `2026-09-17` | Standardize to `Electronics` |
| `OTHER` catch-all row | `2026-09-17` | Use for missing or unknown product codes |
| Category casing corrected | `2026-09-18` (`ELEC_ACC`, `ELEC_MOB`) | Incremental merge |
| `HOME_STAT` name filled (`Stationery`) | `2026-09-18` | Incremental merge |
| `ELEC_AUD` renamed to `Audio & Headphones` | `2026-09-19` | Type-1 name change |
| New `HOME_LGT` (Lighting) | `2026-09-20` | Insert new lookup key |

---

## `customers`

| Issue | Where | Practice |
| --- | --- | --- |
| Duplicate `customer_id` 2 (blank email, then a complete later row) | `2026-09-17` | Latest-wins on `updated_date` |
| Leading/trailing spaces in names | ids 1, 8 on `2026-09-17` | Trim + `initcap` |
| Mixed name casing (`SARA AHMED`, `mohammed khalid`, `ali hassan`) | `2026-09-17` | `initcap` |
| Mixed-case email (`Ali@Example.COM`) | id 1 on `2026-09-17` | Lower-case |
| Invalid email (no `@`) | id 11 `khalid.rahman` on `2026-09-17` | Null or quarantine; later row on the 18th supplies a valid email |
| Blank email | id 2 (first version) on `2026-09-17` | Null; later duplicate fills it |
| Padded city (` Lusail `) | id 4 on `2026-09-17` | Trim |
| City casing (`doha`, `DOHA` via later rows) | ids 5, 15 | Title-case |
| Hyphenated city (`Al-Wakrah`) | id 11 on `2026-09-17` | `Al Wakrah` |
| Typo city (`Dohaa`) | id 15 on `2026-09-17` | Map to `Doha` |
| Inconsistent country labels (`Qatar`, `QA`, `QAT`, `qatar`, `QATAR`, `Qa`) | several rows | `Qatar` |
| Long country names (`United Arab Emirates`, `Saudi Arabia`) | ids 9, 13 | Keep as full names |
| Blank country | id 10 on `2026-09-17` | Null; do not invent a country |
| Blank city on a new customer | id 16 on `2026-09-18` | Null; filled on `2026-09-19` |
| Padded email | id 5 on `2026-09-18` | Trim |
| Upper-case email and padded city | id 18 on `2026-09-20` | Lower-case + trim |
| Late country cleanup (`QATAR` → `Qatar`) | id 12 on `2026-09-20` | Latest-wins |
| City change (Doha → Al Wakrah, Lusail → Doha) | ids 1 and 4 on later days | SCD Type 1 overwrite |

---

## `products`

| Issue | Where | Practice |
| --- | --- | --- |
| Blank `subcategory_code` | Mouse `102` on `2026-09-17` | Map to `OTHER`; code is filled `ELEC_ACC` on `2026-09-18` |
| Unknown `subcategory_code` `XXXX` | Gift Card `118` on `2026-09-17` | Map to `OTHER` (no matching lookup row) |
| Lower-case code `elec_mob` | `110` on `2026-09-17` | Upper-case before join |
| Padded product name | Monitor `106` on `2026-09-17` | Trim + `initcap` |
| Shouted product name | `SAMSUNG GALAXY S25` | `initcap` |
| Non-numeric price `bad_price` | Desk `104` on `2026-09-17` | Quarantine; corrected to `299.00` on `2026-09-19` |
| Negative catalog price | Yoga Mat `115` on `2026-09-17` | Quarantine; corrected to `25.00` on `2026-09-19` |
| Catalog price change | Laptop `101` `1500` → `1399` on `2026-09-18` | Latest catalog price; historical sales keep line price |
| New product | Webcam `116` on `2026-09-18`; Desk Lamp `117` on `2026-09-20` | Insert |
| Desk Lamp uses new `HOME_LGT` | `2026-09-20` | Join after the same-day category insert |

---

## `orders`

| Issue | Where | Practice |
| --- | --- | --- |
| Status aliases (`completed`, `Complete`, `COMPLETED`, `complete`, `PENDING`, `pending`) | `2026-09-17` | Map to `Completed` / `Pending` |
| Typo `shiped` | order `1007` on `2026-09-17` | Map to `Shipped` |
| Informal status `done` | order `1016` on `2026-09-17` | Map to `Completed` |
| Blank status | order `1012` on `2026-09-17` | Null or `Unknown`; optional quarantine |
| Trailing space in status (`completed `) | order `1021` on `2026-09-18` | Trim before mapping |
| Alternate slash date `2026/09/17` | order `1008` on `2026-09-17` | Parse to date |
| Day-first date `20-09-2026` | order `1025` on `2026-09-20` | Parse as 20 Sep 2026 |
| Future `order_date` `2099-01-01` | order `1004` | Quarantine |
| Unknown `customer_id` `99` | orders `1003`, `1024` | Quarantine (orphan fact) |
| Status changes over time | `1006`, `1010` pending → completed on `2026-09-18`; `1015`, `1017`, `1020` on `2026-09-19`; `1023` on `2026-09-20` | Latest-wins on `order_id` using `updated_date` |

Gold metrics should usually include `Completed` and `Shipped` only, not `Cancelled` or `Pending`.

---

## `order_items`

| Issue | Where | Practice |
| --- | --- | --- |
| Duplicate `order_item_id` | item `2` twice on `2026-09-17`; item `41` twice on `2026-09-19` | Keep the latest `updated_date` per `order_item_id` before MERGE |
| Unknown `product_id` `999` | item `5` on `2026-09-17` | Quarantine |
| Negative `quantity` | item `6` on `2026-09-17` | Quarantine |
| Zero `quantity` | item `46` on `2026-09-17` | Quarantine (`quantity` must be > 0) |
| Blank line `unit_price` | item `17` (USB-C Hub on order `1010`) | Coalesce to catalog `unit_price` |
| Thousands separator in price `"1,500.00"` | item `1` on `2026-09-17` | Parse to decimal `1500.00` |
| Line price ≠ current catalog | item `14` headphones `119` vs catalog `129`; item `16` laptop `1450` vs `1500`; item `19` bulk notebook `4.25` vs `4.50`; item `23` mouse `22` vs `25` | Keep the line price as the sale price |
| Line on a quarantined product | item `29` Desk while catalog is `bad_price`; items that reference Yoga Mat `115` before the 19th correction | Quarantine the line; after the product is corrected, re-check `quarantine.order_items` |
| Items for invalid orders | item `30` (future order `1004`); item `6` (unknown customer order `1003`); item `42` (order `1024`) | Fail the order-exists check |
| Gift Card uses unknown category code | item `47` product `118` | Product is valid; enrich category as `OTHER` |

---

## Incremental stories (latest-wins)

Use these when you load a later extract into Bronze and MERGE that `run_date` into Silver:

1. **Customer 2** moves from Al Rayyan to Lusail on 18 Sep.
2. **Customer 11** gets a valid email on 18 Sep.
3. **Customer 16** is created with a blank city on 18 Sep; city is Doha on 19 Sep.
4. **Mouse 102** missing subcategory is set to `ELEC_ACC` on 18 Sep.
5. **Desk 104** and **Yoga Mat 115** catalog prices become valid on 19 Sep — MERGE loads the products, and a quarantine retry releases their earlier order lines.
6. **Order 1006 / 1010 / 1015 / 1017 / 1020 / 1023** status progresses from pending/processing to completed or shipped.

After all four days, Silver should have one current row per customer, product, category, and order, plus only valid order lines.
