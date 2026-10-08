# Data Visualization & Insight Communication: Practical Demonstrations

This repository contains eight hands-on Jupyter notebooks designed for undergraduate Data Analytics students (CMPS 360). Each notebook demonstrates a distinct analytical purpose using **Seaborn** (for publication-ready static charts) and **Plotly** (for interactive dashboard charts).

All examples align directly with the lecture **"Data Visualization & Insight Communication"** by **Dr. Abdelkarim Erradi (CSE@QU)**.

---

## The Eight Analytical Purposes at a Glance

| # | Notebook | Analytical Purpose | Core Question | Primary Chart | Alternatives Covered | Dataset (`data/`) |
|---|---|---|---|---|---|---|
| 1 | [01_trend_analysis.ipynb](01_trend_analysis.ipynb) | **Trend Analysis** | *How does it change over time?* | Line Chart (Seaborn & Plotly) | Area Chart, Column Chart (discrete quarters) | `qatar_monthly_visitors.csv` |
| 2 | [02_comparison_analysis.ipynb](02_comparison_analysis.ipynb) | **Comparison Analysis** | *How do categories differ?* | Bar Chart (single color, zero baseline) | Grouped Bar Chart, Cleveland Dot Plot | `qatar_retail_channels.csv` |
| 3 | [03_ranking_analysis.ipynb](03_ranking_analysis.ipynb) | **Ranking Analysis** | *What is highest or lowest?* | Sorted Horizontal Bar Chart | Top-N with 'Other' Bar, Lollipop Chart | `qatar_destinations_footfall.csv` |
| 4 | [04_part_to_whole_analysis.ipynb](04_part_to_whole_analysis.ipynb) | **Part-to-Whole Analysis** | *How does each part contribute?* | Stacked Bar Chart | 100% Stacked Bar, Donut Chart | `qatar_energy_generation.csv` |
| 5 | [05_distribution_analysis.ipynb](05_distribution_analysis.ipynb) | **Distribution Analysis** | *How are values spread out?* | Histogram with Median & Box Margin | Box Plot across groups, Violin & Strip Plot | `qatar_ecommerce_orders.csv` |
| 6 | [06_relationship_analysis.ipynb](06_relationship_analysis.ipynb) | **Relationship Analysis** | *How are variables related?* | Scatter Plot with OLS Trendline | Bubble Chart (3rd metric), Correlation Heatmap | `qatar_digital_marketing.csv` |
| 7 | [07_geographic_analysis.ipynb](07_geographic_analysis.ipynb) | **Geographic Analysis** | *Where does it happen?* | Choropleth Map (rates per 1k) | Symbol/Bubble Map, Sorted Regional Bar Chart | `gcc_ecommerce_rates.csv` |
| 8 | [08_target_deviation_analysis.ipynb](08_target_deviation_analysis.ipynb) | **Target Deviation Analysis** | *How do we compare with plan?* | Actual-vs-Target Bar with Markers | Variance Diverging Bar Chart, Bullet Gauge Chart | `qatar_zones_revenue_targets.csv` |

---

## Pedagogical Teaching Pattern

Every chart in every notebook follows a rigorous analytical workflow:

$$\text{Business Question} \longrightarrow \text{Chart Choice} \longrightarrow \text{Visualization} \longrightarrow \text{Interpretation} \longrightarrow \text{Actionable Implication}$$

### The 5-Step Insight Framework (Slides 42–44)
1. **Question:** What decision needs an answer? (e.g., *"Are we growing, and where?"*)
2. **Visualization:** Which chart geometry answers it? (e.g., monthly revenue line chart)
3. **Observation:** What does the chart show? (Descriptive, verifiable from chart alone, e.g., *"Revenue rose from 120k to 175k QAR"*)
4. **Insight:** What does the pattern mean? (Interpretive, compares pattern to expectation, e.g., *"Growth accelerated after May; the rate changed, not just the level"*)
5. **Implication:** Why does it matter, and what to do next? (Actionable, decision-oriented, e.g., *"Plan Q3 capacity on the higher baseline; verify pricing elasticity"*)

---

## Core Visual Design Principles (Slides 46–48)

1. **Honest Axes:** Always anchor bar charts at a zero baseline. Never truncate axes to manufacture drama.
2. **Intentional Colour:** Use a single color for single-metric bars. Rainbow palettes imply groupings that do not exist.
3. **Title States the Finding:** Avoid titles that merely name the axes (`"Revenue by Month"`). State the analytical takeaway (`"Revenue Rose 46% in H1 Driven by May–June"`).
4. **Rates Over Raw Counts:** In geographic maps, always map rates per capita or per 1,000 residents; raw counts merely map population.
5. **Median Over Mean for Skewed Data:** For asymmetric or long-tailed distributions, report median and IQR rather than an inflated arithmetic mean.
6. **Say What the Data Cannot Prove:** State correlation as an association; never claim causation from an observational scatter plot alone.

---

## Repository Structure

```text
05_visualization/
│
├── data/                                 # Small, realistic CSV datasets (Qatar & GCC contexts)
│   ├── qatar_monthly_visitors.csv        # 12-month visitor inflows and occupancy
│   ├── qatar_retail_channels.csv         # Omnichannel sales by customer segment
│   ├── qatar_destinations_footfall.csv   # Annual visitors across 8 Qatar destinations
│   ├── qatar_energy_generation.csv       # Quarterly electricity generation mix (GWh)
│   ├── qatar_ecommerce_orders.csv        # 450 customer orders (basket QAR & delivery min)
│   ├── qatar_digital_marketing.csv       # 16-week ad spend, revenue, conversions & ROAS
│   ├── gcc_ecommerce_rates.csv           # 6 GCC countries, capitals, rates per 1k
│   └── qatar_zones_revenue_targets.csv   # Q4 actuals vs targets across 5 Qatar zones
│
├── 01_trend_analysis.ipynb               # Notebook 1: Trend Analysis
├── 02_comparison_analysis.ipynb          # Notebook 2: Comparison Analysis
├── 03_ranking_analysis.ipynb             # Notebook 3: Ranking Analysis
├── 04_part_to_whole_analysis.ipynb       # Notebook 4: Part-to-Whole Analysis
├── 05_distribution_analysis.ipynb        # Notebook 5: Distribution Analysis
├── 06_relationship_analysis.ipynb        # Notebook 6: Relationship Analysis
├── 07_geographic_analysis.ipynb          # Notebook 7: Geographic Analysis
├── 08_target_deviation_analysis.ipynb    # Notebook 8: Target Deviation Analysis
│
├── build_all.py                          # Rebuilds all 8 notebooks
├── build_all_notebooks.py                # Source generation definitions
├── create_datasets.py                    # Re-creates all CSV data files
└── verify_notebooks.py                   # Automated verification test script
```

---

## How to Run

1. Open any notebook in **VS Code**, **JupyterLab**, or **Google Colab**.
2. Run cells sequentially:
   - Python 3.10+
   - `pandas`, `seaborn`, `matplotlib`, `plotly`, `statsmodels`
3. Complete the three hands-on practice exercises at the bottom of each notebook to reinforce learning.
