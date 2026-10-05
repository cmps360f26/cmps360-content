# 📊 Statistics for Data Insights: Qatar Real-World Applications

This repository contains **three educational Jupyter notebooks** designed for data analysts, students, and practitioners. Each notebook illustrates foundational statistical principles from **Chapter 3: Statistics for Data Insights** using practical, beginner-friendly examples contextualized for **Qatar**.

---

## 📁 Notebook Overview

| Notebook | Topic | Qatar Domain & Scenario | Key Statistical Concepts |
| :--- | :--- | :--- | :--- |
| [`01_central_tendency_qatar.ipynb`](file:///c:/_cmps360-content/examples/04_stats/01_central_tendency_qatar.ipynb) | **Central Tendency & Attributes** | **Residential Rental Market**<br>*(Al Sadd, Lusail, West Bay, The Pearl, Al Wakrah)* | • Nominal, Ordinal, Interval, Ratio<br>• Arithmetic Mean ($\bar{x}$)<br>• Median (50th Percentile)<br>• Mode<br>• Outlier sensitivity experiment |
| [`02_dispersion_and_distribution_qatar.ipynb`](file:///c:/_cmps360-content/examples/04_stats/02_dispersion_and_distribution_qatar.ipynb) | **Dispersion & Distribution Shape** | **Climate & Energy Grid Demand**<br>*(Doha Temperature & Kahramaa Cooling MW)* | • Range<br>• Quartiles ($Q_1, Q_3$) & IQR<br>• Variance ($S^2$) & Std Dev ($S$)<br>• Skewness & Kurtosis<br>• Automated `df.describe()` |
| [`03_relationships_and_correlation_qatar.ipynb`](file:///c:/_cmps360-content/examples/04_stats/03_relationships_and_correlation_qatar.ipynb) | **Relationships & Correlation** | **Aviation & Passenger Services**<br>*(Hamad International Airport - HIA)* | • Covariance matrix (`.cov()`)<br>• Pearson correlation ($r$)<br>• Spearman rank correlation ($\rho$)<br>• Kendall's Tau ($\tau$)<br>• Ordinal rank mapping<br>• Correlation $\neq$ Causation |

---

## 🇶🇦 Real-World Qatar Contexts

1. **Notebook 1 — Qatar Rental Market**:
   * Demonstrates why the **Median** is preferred over the **Mean** when evaluating housing costs across Doha and Lusail. Adding just two ultra-luxury penthouses (75,000 QAR and 95,000 QAR) surges the Mean by **+88%**, while the Median remains representative of everyday living costs.
2. **Notebook 2 — Qatar Climate & Energy Grid (Kahramaa)**:
   * Explores why knowing only the average temperature (~30°C) is insufficient for infrastructure planning. Using dispersion (standard deviation and IQR) helps Kahramaa engineers size cooling reserve margins for summer extremes (>45°C) and supports occupational health regulations during midday working hours.
3. **Notebook 3 — Hamad International Airport (HIA) Operations**:
   * Examines operational relationships between transit passenger volume, baggage delivery delays, and customer satisfaction ratings. Demonstrates how to map categorical survey tiers (`Poor`, `Average`, `Good`, `Excellent`) into numeric ranks and apply **Spearman** and **Kendall** correlation.

---

## 🚀 Environment & Execution

The notebooks are pre-executed with all output tables and Matplotlib/Seaborn visualizations rendered.

To run or modify the notebooks locally, ensure you have Python 3.10+ installed with the following libraries:

```bash
pip install pandas numpy scipy matplotlib seaborn statsmodels
```

To run a notebook interactively:
```bash
jupyter lab
# or open directly in VS Code / Cursor
```

To re-run and rebuild all notebooks automatically:
```bash
python build_all_notebooks.py
```
