# 📊 Statistics for Data Insights: Qatar Real-World Applications

This repository contains **four interactive, beginner-friendly Jupyter notebooks** designed for undergraduate Data Analytics students (CMPS 360). Each notebook covers foundational statistical measures from **Lecture 5: Statistics for Data Insights** (Dr. Abdelkarim Erradi, CSE@QU) using realistic datasets contextualized in **Qatar**.

All datasets are stored as accessible CSV files in the [`data/`](file:///c:/_cmps360-content/examples/04_stats/data) directory.

---

## 📁 Notebook Directory & Curriculum Mapping

| # | Notebook | Statistical Topic | Lecture Slides | Qatar Real-World Scenario | CSV Dataset | Key Statistical Measures |
| :-: | :--- | :--- | :-: | :--- | :--- | :--- |
| **01** | [`01_measures_of_central_tendency.ipynb`](file:///c:/_cmps360-content/examples/04_stats/01_measures_of_central_tendency.ipynb) | **Measures of Central Tendency** | Slides 18–24 | • Qatar Trainee Exams<br>• Doha & Lusail Property Rents<br>• Retail Payment Channels | [`data/trainee_scores.csv`](file:///c:/_cmps360-content/examples/04_stats/data/trainee_scores.csv)<br>[`data/qatar_rents.csv`](file:///c:/_cmps360-content/examples/04_stats/data/qatar_rents.csv)<br>[`data/payment_methods.csv`](file:///c:/_cmps360-content/examples/04_stats/data/payment_methods.csv) | • Mean ($\bar{x}$), Median ($M$), Mode ($Mo$)<br>• Hand verification ($n=5$)<br>• Outlier sensitivity & robustness<br>• Center Gap Test ($|\bar{x} - M| / M$)<br>• `df.describe()` & `groupby('zone')` |
| **02** | [`02_measures_of_dispersion.ipynb`](file:///c:/_cmps360-content/examples/04_stats/02_measures_of_dispersion.ipynb) | **Measures of Dispersion** | Slides 25–32 | • Qatar E-Commerce Delivery Logistics<br>• Express vs. Standard Fleet Risk | [`data/delivery_times.csv`](file:///c:/_cmps360-content/examples/04_stats/data/delivery_times.csv) | • Range, Variance ($s^2$ with $n-1$), Std Dev ($s$)<br>• Quartiles ($Q_1, Q_2, Q_3$) & IQR<br>• 68–95–99.7 Empirical Rule<br>• $z$-Scores ($z = (x-\bar{x})/s$)<br>• Coefficient of Variation ($CV = s/\bar{x}$)<br>• Commitments in tails ($p_{95}, p_{99}$) |
| **03** | [`03_measures_of_distribution_shape.ipynb`](file:///c:/_cmps360-content/examples/04_stats/03_measures_of_distribution_shape.ipynb) | **Measures of Distribution Shape** | Slides 33–39 | • Qatar Mall Transactions (Villaggio, Vendôme, Mall of Qatar)<br>• Luxury Purchases & Outlier Governance | [`data/customer_orders.csv`](file:///c:/_cmps360-content/examples/04_stats/data/customer_orders.csv) | • Symmetric vs. Right- vs. Left-Skewed<br>• Fisher-Pearson Skewness ($g_1$)<br>• Log transformation ($\log(1+x)$)<br>• Excess Kurtosis ($g_2$, tail weight)<br>• $z$-Score screen ($|z| > 3$)<br>• Tukey's IQR Fences ($Q_3 + 1.5\cdot\text{IQR}$)<br>• Boxplots & 5-Step Outlier Workflow |
| **04** | [`04_relationships_between_variables.ipynb`](file:///c:/_cmps360-content/examples/04_stats/04_relationships_between_variables.ipynb) | **Analysis of Relationships Between Variables** | Slides 40–46 | • Hamad International Airport (HIA) Hub Operations<br>• Passenger Flows, Baggage Delays, Satisfaction Surveys | [`data/hia_operations.csv`](file:///c:/_cmps360-content/examples/04_stats/data/hia_operations.csv) | • **Pearson Correlation ($r$) & Spearman Rank ($\rho$) ONLY**<br>• Hand verification of Spearman formula ($n=5$, slide 44)<br>• Pearson linear $r$ & determination $r^2$ (% variance explained)<br>• Linearity, normality & outlier checks (when to switch to Spearman)<br>• Ordinal survey rank mapping (`Poor` $\to$ 1, `Excellent` $\to$ 4)<br>• Scatter regression plots & comparison heatmaps<br>• Correlation $\neq$ Causation & confounder checks |

---

## 🗃️ Datasets in `data/`

All datasets are kept compact, realistic, and directly inspectable in Excel, VS Code, or Python:

1. **[`data/trainee_scores.csv`](file:///c:/_cmps360-content/examples/04_stats/data/trainee_scores.csv)** (10 rows):
   * Columns: `trainee_id`, `name`, `gender`, `speaking_score`, `math_score`, `track`.
   * Replicates Dr. Erradi's five-trainee worked example (Omar, Layla, Noura, Khalid, Yousef) where students can calculate and verify every statistic by hand.
2. **[`data/qatar_rents.csv`](file:///c:/_cmps360-content/examples/04_stats/data/qatar_rents.csv)** (20 rows):
   * Columns: `property_id`, `zone`, `property_type`, `bedrooms`, `monthly_rent_qar`.
   * 18 standard residential rentals (5,000 to 17,000 QAR/month) across Al Sadd, Al Wakrah, West Bay, Lusail, and The Pearl, plus 2 ultra-luxury penthouses (75,000 and 95,000 QAR/month) illustrating the outlier sensitivity of the Mean vs. Median.
3. **[`data/payment_methods.csv`](file:///c:/_cmps360-content/examples/04_stats/data/payment_methods.csv)** (200 rows):
   * Columns: `order_id`, `customer_zone`, `payment_method`, `channel`, `order_amount_qar`.
   * Exactly matches Lecture Slide 22 payment distribution: 96 Card (48%), 62 Cash (31%), 30 Wallet (15%), and 12 Bank Transfer (6%).
4. **[`data/delivery_times.csv`](file:///c:/_cmps360-content/examples/04_stats/data/delivery_times.csv)** (40 rows):
   * Columns: `order_id`, `service_type`, `delivery_time_minutes`, `delivery_time_days`, `package_weight_kg`, `shipping_fee_qar`, `destination_zone`.
   * Compares Express Delivery ($s \approx 3.7$ min) vs. Standard Delivery ($s \approx 22.0$ min) around the identical mean (~50.0 min), demonstrating why spread matters for operational risk and why customer promises live at $p_{95}$.
5. **[`data/customer_orders.csv`](file:///c:/_cmps360-content/examples/04_stats/data/customer_orders.csv)** (80 rows):
   * Columns: `order_id`, `mall_branch`, `category`, `items_count`, `order_amount_qar`.
   * Captures right-skewed mall purchases (median 245 QAR, positive skewness $g_1 > 4$, heavy kurtosis $g_2 > 20$), with VIP luxury purchases demonstrating Tukey's IQR fences and outlier handling without silent deletion.
6. **[`data/hia_operations.csv`](file:///c:/_cmps360-content/examples/04_stats/data/hia_operations.csv)** (30 rows):
   * Columns: `day`, `concourse`, `transit_passengers_thousands`, `ground_staff_on_duty`, `baggage_wait_minutes`, `on_time_departure_pct`, `service_speed_rating`, `passenger_satisfaction_rating`.
   * Continuous operational metrics for Pearson linear correlation ($r$ and $r^2$), combined with ordinal survey ratings (`Poor` $\to$ `Excellent`, `Low` $\to$ `Very High`) for Spearman rank correlation ($\rho$).

---

## 🇶🇦 Real-World Analytical Case Studies

### 1. Qatar Rental Market: Mean vs. Median
Adding just two luxury penthouses (75,000 QAR and 95,000 QAR) surges the arithmetic mean rent by **+65.6%** (from 10,139 QAR to 16,785 QAR), positioning the mean above 90% of the listings. The median increases by only **+7.9%** (from 9,500 QAR to 10,250 QAR), preserving the true cost of everyday residential living in Doha.

### 2. Qatar Logistics: Commitments Live in the Tails
Advertising an "average 3-day delivery" leads to roughly **45% late deliveries** because the mean sits in the middle of outcomes. Sizing customer Service Level Agreements (SLAs) at the **95th percentile ($p_{95} = 7$ days)** provides an honest, dependable guarantee that survives traffic peaks and bad weather.

### 3. Luxury Mall Spending: Outlier Governance
Flagging high-value purchases (> 7,000 QAR at Place Vendôme) using $1.5 \cdot \text{IQR}$ fences identifies candidate extremes. However, silently deleting them would erase **34% of recorded store revenue**! The Five-Step Procedure (*Flag $\to$ Trace $\to$ Classify $\to$ Act $\to$ Document*) guides analysts to keep genuine VIP transactions and report robust statistics (Median + IQR).

### 4. Hamad International Airport (HIA): Correlation vs. Causation
Baggage wait times and flight on-time departure rates share a strong negative correlation ($r = -0.86, r^2 = 0.74$). However, correlation does not mechanically prove causation; peak flight arrival banks naturally stress both ramp baggage crews and boarding gates. Subgroup analysis by concourse and safe phrasing (*"was associated with"*, *"in this 30-day sample"*) ensure credible reporting.

---

## 🚀 Environment & Execution

All notebooks are pre-executed with fully rendered tables, markdown explanations, and Seaborn/Matplotlib visualizations.

### Recommended Environment:
* Python 3.10+
* Packages:
  ```bash
  pip install pandas numpy matplotlib seaborn scipy
  ```

### Running Interactively:
Open the folder in VS Code, Cursor, or start Jupyter Lab:
```bash
jupyter lab
```

---

## 📚 Section Recap: The Complete 9-Step Descriptive Workflow

From **Lecture Slide 46**, follow this systematic workflow on every new dataset:
1. **Completeness**: `df.isna().sum()` $\to$ report sample size $n$ and missing counts first.
2. **Centre**: `mean()`, `median()`, `mode()` $\to$ if Center Gap $> 10\%$, report the Median.
3. **Spread**: `std()`, `IQR`, `CV` $\to$ if $CV > 1.0$, use Median & IQR rather than $\bar{x} \pm s$.
4. **Shape**: `skew()`, `kurtosis()` $\to$ if $|g_1| > 1.0$, transform via $\log(1+x)$ or report percentiles.
5. **Extremes**: Screen with $1.5 \cdot \text{IQR}$ fences and $|z| > 3$ $\to$ apply *Flag, Trace, Classify, Act, Document*.
6. **Promises**: Calculate `quantile([0.90, 0.95, 0.99])` $\to$ commitments live at $p_{95}$, not the mean.
7. **Relationships**: Compute `corr()`, Spearman $\rho$, and $r^2$ $\to$ always attach a scatter plot.
8. **Subgroups**: `df.groupby().agg()` $\to$ check whether associations hold within subgroups.
9. **Claim**: Quote findings with safe language: *"was associated with"*, sample size $n$, and time frame.
