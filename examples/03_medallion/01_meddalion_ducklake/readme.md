# Medallion Lakehouse Pipeline

A DuckLake-based Medallion Architecture (Bronze → Silver → Gold) data pipeline for retail sales data.

## Quick Start: Running the Pipeline

### 1. Activate the Virtual Environment

In the terminal:

- **macOS / Linux:**
  ```bash
  source "$HOME/.venvs/py-env/bin/activate"
  ```

- **Windows:**
  ```powershell
  & "$HOME\.venvs\py-env\Scripts\Activate.ps1"
  ```

### 2. Navigate to the Pipeline Directory

```bash
cd 01_meddalion_ducklake
```

### 3. Execute the Pipeline

Run the automated orchestrator `run_pipeline.py`:

```bash
# 1. Initialize catalog and schemas (required on first run)
python run_pipeline.py --init

# 2. Process all pending dates chronologically
python run_pipeline.py

# 3. View pipeline execution status
python run_pipeline.py --status
```

#### Additional Commands

```bash
# Process a single specific date
python run_pipeline.py --date 2026-09-17

# Force re-run all dates (even if already completed)
python run_pipeline.py --rerun
```

## Project Layout

```text
01_meddalion_ducklake/
├── run_pipeline.py
├── setup/
│   ├── 00_setup.py
│   ├── 00.1_bronze_schema.py
│   ├── 00.2_silver_schema.py
│   └── 00.3_gold_schema.py
├── pipeline/
│   ├── 01_bronze.py
│   ├── 02_silver.py
│   └── 03_gold.py
└── analysis/
    └── 04_answer_questions.py
```

---

## Interactive / Notebook Workflow (Marimo)

The pipeline notebooks can also be run interactively via Marimo:

```bash
marimo edit setup/00_setup.py
```

### Execution Order:
1. **Setup & Schemas (`setup/`)**: `00_setup.py` → `00.1_bronze_schema.py` → `00.2_silver_schema.py` → `00.3_gold_schema.py`
2. **Bronze Layer (`pipeline/`)**: `01_bronze.py` (raw batch ingestion)
3. **Silver Layer (`pipeline/`)**: `02_silver.py` (data quality validation & cleansing)
4. **Gold Layer (`pipeline/`)**: `03_gold.py` (star schema facts & dimensions)
5. **Analytics (`analysis/`)**: `04_answer_questions.py` (business KPI queries)
