"""
Script to construct and execute all 3 educational Jupyter notebooks
demonstrating Key Statistics for Data Insights in a Qatar context.
Reference: Chapter 3 - Statistics for Data Insights.
"""

import os
import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

WORKSPACE = r"c:\_cmps360-content\examples\04_stats"
os.makedirs(WORKSPACE, exist_ok=True)

# -------------------------------------------------------------------------
# NOTEBOOK 1: CENTRAL TENDENCY & ATTRIBUTE TYPES
# -------------------------------------------------------------------------
def build_notebook_1():
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.14.2"}
    }
    cells = []
    
    # Header
    cells.append(nbf.v4.new_markdown_cell("""# 📊 Module 1: Measures of Central Tendency & Data Attributes
### Practical Insights from the Qatar Residential Rental Market

---

## 🎯 Learning Objectives
In this notebook, we examine the foundational statistical principles covered in **Chapter 3: Statistics for Data Insights**:
1. **Understanding Data Attributes**: Classifying variables as **Nominal**, **Ordinal**, **Interval**, and **Ratio**, as well as **Discrete** vs. **Continuous**.
2. **Measuring Central Tendency**: Calculating and interpreting the **Arithmetic Mean**, **Median**, and **Mode** using Python (`pandas`, `numpy`).
3. **Analyzing Outlier Sensitivity**: Demonstrating why the mean can be misleading when luxury outliers exist, and why the median provides a stable benchmark.
4. **Data Visualization**: Constructing visual summaries (Histograms, KDE plots, and Boxplots) to communicate central tendency to stakeholders.

---

## 🇶🇦 Real-World Qatar Context
The real estate market in Qatar includes diverse housing choices across municipalities:
* High-density, affordable family apartments in **Al Sadd**, **Al Mansoura**, and **Al Wakrah**.
* Modern smart-city high-rises in **Lusail City** (Marina and Fox Hills).
* High-end waterfront developments and luxury penthouses in **The Pearl-Qatar** and **West Bay Lagoon**.

For analysts working with property portals, government housing regulators, or corporate relocation agencies, knowing whether to report the **Mean** or the **Median** rent is critical for sound decision-making."""))

    # Section 1
    cells.append(nbf.v4.new_markdown_cell("""## 1. Understanding Attributes & Their Types

Before calculating summary statistics, an analyst must identify the scale of measurement for each attribute. As defined in Chapter 3:

* **Nominal**: Categorical labels without intrinsic order. (e.g., Doha Zone: `The Pearl`, `Lusail`, `West Bay`, `Al Sadd`, `Al Wakrah`). Mode is the only valid central tendency measure.
* **Ordinal**: Categorical labels with an inherent order or ranking, but unequal or unknown distances between ranks (e.g., Finish Grade: `Standard` < `Premium` < `Luxury` < `Ultra-Luxury`). Median and Mode are valid.
* **Numeric - Interval**: Ordered scale of equal intervals without an absolute true zero (e.g., Year Built, Temperature in °C). Differences are meaningful, but ratios are not.
* **Numeric - Ratio**: Ordered scale with an absolute zero point (e.g., Monthly Rent in QAR, Unit Area in $\\text{m}^2$). Multiplication and division are meaningful.
* **Discrete vs. Continuous**:
  * *Discrete*: Countable finite integers (e.g., Number of Bedrooms: 1, 2, 3).
  * *Continuous*: Infinite measurable real values (e.g., Monthly Rent in QAR, Area in $\\text{m}^2$).

Let's create a representative sample of residential rental listings across Qatar."""))

    # Code 1
    cells.append(nbf.v4.new_code_cell("""# Step 1: Import core data analysis libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configure visual styling
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

# Create realistic rental dataset for Qatar
rental_data = {
    "property_id": [f"QTR-{i:03d}" for i in range(101, 116)],
    "zone": [
        "Al Sadd", "Al Wakrah", "Al Mansoura", "Al Sadd", "Old Airport",
        "Lusail", "Lusail", "West Bay", "The Pearl", "Lusail",
        "Al Sadd", "The Pearl", "West Bay", "Al Wakrah", "The Pearl"
    ],  # Nominal attribute
    "finish_grade": [
        "Standard", "Standard", "Standard", "Premium", "Standard",
        "Premium", "Premium", "Luxury", "Luxury", "Premium",
        "Standard", "Luxury", "Luxury", "Standard", "Ultra-Luxury"
    ],  # Ordinal attribute
    "bedrooms": [2, 2, 1, 3, 2, 2, 3, 3, 2, 1, 2, 3, 4, 3, 3],  # Discrete Ratio
    "area_sqm": [110, 115, 75, 160, 105, 125, 175, 190, 145, 80, 112, 185, 240, 150, 210],  # Continuous Ratio
    "monthly_rent_qar": [
        6500, 5500, 4800, 8500, 5200, 
        9000, 11500, 13000, 12500, 7500, 
        6800, 14000, 18000, 6000, 16500
    ]  # Continuous Ratio (Qatari Riyals)
}

# Construct DataFrame
df_rentals = pd.DataFrame(rental_data)

# Preview first 6 properties
print("--- Qatar Rental Listings Sample ---")
df_rentals.head(6)"""))

    # Code 2
    cells.append(nbf.v4.new_code_cell("""# Step 2: Inspect column data types and verify attribute classifications
print("=== Dataset Summary and Data Types ===")
df_rentals.info()"""))

    # Section 2
    cells.append(nbf.v4.new_markdown_cell("""## 2. Measuring Central Tendency: Mean, Median, and Mode

Central tendency summarizes an entire dataset into a single, representative value located near the center of the distribution.

### Mathematical Definitions

1. **Arithmetic Mean ($\\bar{x}$)**:
   $$\\bar{x} = \\frac{1}{N} \\sum_{i=1}^{N} x_i$$
   The sum of all values divided by the total count. Sensitive to every value, including extreme outliers.

2. **Median (50th Percentile)**:
   The middle observation when data is sorted in ascending order:
   $$\\text{Position} = \\frac{N + 1}{2}$$
   If $N$ is even, it is the average of the two central numbers. It divides the distribution into two equal halves (50% below, 50% above). Highly robust to extreme values.

3. **Mode**:
   The value that appears most frequently in the sample. Applicable to numerical and categorical variables alike."""))

    # Code 3
    cells.append(nbf.v4.new_code_cell("""# Step 3: Compute central tendency for Monthly Rent (QAR)
mean_rent = df_rentals["monthly_rent_qar"].mean()
median_rent = df_rentals["monthly_rent_qar"].median()
mode_rent = df_rentals["monthly_rent_qar"].mode()[0]

# Compute mode for categorical and discrete attributes
mode_zone = df_rentals["zone"].mode()[0]
mode_bedrooms = df_rentals["bedrooms"].mode()[0]

# Print calculated statistics
print("=== Central Tendency Metrics: Qatar Residential Rent ===")
print(f"Mean Monthly Rent:   {mean_rent:,.2f} QAR")
print(f"Median Monthly Rent: {median_rent:,.2f} QAR")
print(f"Mode Monthly Rent:   {mode_rent:,.2f} QAR")
print("-" * 55)
print(f"Most Frequent Rental Zone (Mode):     {mode_zone}")
print(f"Most Frequent Bedroom Count (Mode):   {mode_bedrooms} Bedrooms")"""))

    # Section 3
    cells.append(nbf.v4.new_markdown_cell("""## 3. Practical Experiment: The Outlier Sensitivity Test

A common pitfall in real estate reporting is using the simple arithmetic mean when the market contains ultra-luxury properties.

Let's simulate what happens when **two ultra-luxury properties** (e.g., a beachfront villa in West Bay Lagoon at **75,000 QAR/month** and a triplex penthouse in The Pearl at **95,000 QAR/month**) are added to our 15 standard residential listings."""))

    # Code 4
    cells.append(nbf.v4.new_code_cell("""# Step 4: Add two ultra-luxury listings to test outlier resilience
luxury_outliers = pd.DataFrame({
    "property_id": ["QTR-901", "QTR-902"],
    "zone": ["The Pearl", "West Bay"],
    "finish_grade": ["Ultra-Luxury", "Ultra-Luxury"],
    "bedrooms": [5, 6],
    "area_sqm": [650, 850],
    "monthly_rent_qar": [75000, 95000]  # Extreme luxury values
})

# Concatenate original dataset with outliers
df_rentals_with_outliers = pd.concat([df_rentals, luxury_outliers], ignore_index=True)

# Re-calculate Mean and Median
mean_with_outliers = df_rentals_with_outliers["monthly_rent_qar"].mean()
median_with_outliers = df_rentals_with_outliers["monthly_rent_qar"].median()

# Construct comparison table
outlier_impact_df = pd.DataFrame({
    "Statistic": ["Mean Monthly Rent", "Median Monthly Rent"],
    "Original Data (15 units)": [f"{mean_rent:,.2f} QAR", f"{median_rent:,.2f} QAR"],
    "With 2 Luxury Outliers (17 units)": [f"{mean_with_outliers:,.2f} QAR", f"{median_with_outliers:,.2f} QAR"],
    "Absolute Change": [f"+{mean_with_outliers - mean_rent:,.2f} QAR", f"+{median_with_outliers - median_rent:,.2f} QAR"],
    "Percentage Shift": [
        f"{((mean_with_outliers - mean_rent) / mean_rent) * 100:+.1f}%",
        f"{((median_with_outliers - median_rent) / median_rent) * 100:+.1f}%"
    ]
})

print("=== Impact of High-End Outliers on Central Tendency ===")
outlier_impact_df"""))

    # Markdown Analysis
    cells.append(nbf.v4.new_markdown_cell("""### 💡 Key Analyst Observation
* The **Mean** increased from **~9,693 QAR** to **~18,229 QAR** — an **88% surge** caused by just two properties! If an expat or tenant uses the mean, they will overestimate typical housing expenses.
* The **Median** shifted modestly from **9,000 QAR** to **9,000 QAR / 11,500 QAR** (+27.8%), retaining its position in the middle of standard family listings.
* **Conclusion**: Whenever data is skewed or contains extreme luxury outliers, the **Median** is the superior indicator of typical market price."""))

    # Section 4: Visualizing
    cells.append(nbf.v4.new_markdown_cell("""## 4. Visualizing Central Tendency

Stakeholders understand statistical insights much faster through well-designed charts. Below, we plot:
1. **Histogram & KDE Curve**: Showing the density distribution of rents with vertical reference lines for Mean, Median, and Mode.
2. **Box Plot**: Showing the median line, quartiles, and the separated outlier points."""))

    # Code 5
    cells.append(nbf.v4.new_code_cell("""# Step 5: Visualizing Central Tendency
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Histogram + KDE for standard market listings
sns.histplot(
    data=df_rentals,
    x="monthly_rent_qar",
    kde=True,
    color="#1f77b4",
    bins=8,
    ax=axes[0]
)
axes[0].set_title("Distribution of Doha Rents (Standard Listings)", fontsize=13, fontweight="bold")
axes[0].set_xlabel("Monthly Rent (QAR)", fontsize=11)
axes[0].set_ylabel("Property Count", fontsize=11)

# Add reference lines for Mean, Median, Mode
axes[0].axvline(mean_rent, color="#d62728", linestyle="--", linewidth=2.2, label=f"Mean: {mean_rent:,.0f} QAR")
axes[0].axvline(median_rent, color="#2ca02c", linestyle="-", linewidth=2.2, label=f"Median: {median_rent:,.0f} QAR")
axes[0].axvline(mode_rent, color="#ff7f0e", linestyle=":", linewidth=2.2, label=f"Mode: {mode_rent:,.0f} QAR")
axes[0].legend(loc="upper right", frameon=True)

# Plot 2: Boxplot of expanded dataset showing luxury outliers
sns.boxplot(
    data=df_rentals_with_outliers,
    x="monthly_rent_qar",
    color="#aec7e8",
    fliersize=8,
    ax=axes[1]
)
axes[1].set_title("Boxplot with Luxury Penthouses (Showing Outliers)", fontsize=13, fontweight="bold")
axes[1].set_xlabel("Monthly Rent (QAR)", fontsize=11)

# Annotate Mean vs Median on the boxplot
axes[1].axvline(median_with_outliers, color="#2ca02c", linestyle="-", linewidth=2, label=f"Median: {median_with_outliers:,.0f} QAR")
axes[1].axvline(mean_with_outliers, color="#d62728", linestyle="--", linewidth=2, label=f"Mean: {mean_with_outliers:,.0f} QAR")
axes[1].legend(loc="upper right", frameon=True)

plt.tight_layout()
plt.show()"""))

    # Section 5: Grouped
    cells.append(nbf.v4.new_markdown_cell("""## 5. Segmented Central Tendency: Breakdown by Qatar Zone

In professional reporting, breaking metrics down by municipal sub-markets gives clearer actionable insights."""))

    # Code 6
    cells.append(nbf.v4.new_code_cell("""# Step 6: Group rental data by zone to compute localized central tendency
zone_breakdown = df_rentals.groupby("zone")["monthly_rent_qar"].agg(
    Listing_Count="count",
    Mean_Rent_QAR="mean",
    Median_Rent_QAR="median"
).reset_index()

# Sort by median rent in descending order
zone_breakdown = zone_breakdown.sort_values(by="Median_Rent_QAR", ascending=False)

# Format currency values
zone_breakdown["Mean_Rent_QAR"] = zone_breakdown["Mean_Rent_QAR"].map("{:,.0f} QAR".format)
zone_breakdown["Median_Rent_QAR"] = zone_breakdown["Median_Rent_QAR"].map("{:,.0f} QAR".format)

print("=== Rental Market Comparison Across Qatar Zones ===")
zone_breakdown"""))

    # Section 6: Summary Table
    cells.append(nbf.v4.new_markdown_cell("""## 6. Summary & Data Analyst Reference Guide

| Metric | Mathematical Formula | When to Use | Outlier Sensitivity | Qatar Practical Example |
| :--- | :--- | :--- | :--- | :--- |
| **Mean** | $\\bar{x} = \\frac{1}{N}\\sum x_i$ | Symmetrical, bell-shaped data without heavy tails | **High** | Average daily electricity consumption in a standardized gated compound |
| **Median** | Value at $\\frac{N+1}{2}$ | Skewed data, monetary metrics, salaries, property prices | **Low (Robust)** | Official Qatar housing market reports & median household income |
| **Mode** | $\\arg\\max f(x)$ | Categorical variables, most common configuration | **None** | Most popular apartment layout (e.g. 2-bedroom) or preferred telecom bundle |

### 📌 Practice Tip for Data Analysts
When preparing dashboards or reports for government authorities (like the Planning and Statistics Authority - PSA) or corporate executives in Qatar:
1. Always pair the **Mean** with the **Median**.
2. If the Mean is substantially higher than the Median, explain that high-value outliers are skewing the distribution.
3. Use the **Mode** to identify the most common customer choice or inventory segment."""))

    nb.cells = cells
    return nb

# -------------------------------------------------------------------------
# NOTEBOOK 2: DISPERSION & DISTRIBUTION SHAPE
# -------------------------------------------------------------------------
def build_notebook_2():
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.14.2"}
    }
    cells = []

    # Title & Introduction
    cells.append(nbf.v4.new_markdown_cell("""# 📈 Module 2: Measuring Dispersion & Distribution Shape
### Practical Insights from Qatar Climate & Energy Analytics

---

## 🎯 Learning Objectives
In this notebook, we explore the essential dispersion metrics and distribution shape characteristics covered in **Chapter 3: Statistics for Data Insights**:
1. **Understanding Dispersion**: Why central tendency alone is insufficient to understand variability and operational risk.
2. **Core Dispersion Metrics**: Computing the **Range**, **Interquartile Range (IQR)**, **Variance**, and **Standard Deviation** with Python.
3. **Distribution Shape Analysis**: Interpreting **Skewness** (symmetry) and **Kurtosis** (tailedness / outlier risk).
4. **Data Visualization**: Creating Boxplots and Distribution plots with Standard Deviation intervals to support capacity planning.

---

## 🇶🇦 Real-World Qatar Context
Qatar experiences distinct climatic variations across the year:
* **Mild Winter & Spring (December to April)**: Temperatures range between 15°C and 26°C with pleasant weather.
* **Intense Summer (June to September)**: Daytime temperatures routinely surpass 42°C to 48°C accompanied by high humidity.

Because cooling accounts for up to **60-70% of peak electricity demand**, the Qatar General Electricity and Water Corporation (**Kahramaa**) and cooling service providers (such as Qatar Cool) cannot rely solely on the *average* temperature. They must analyze the **dispersion** (variance, standard deviation, and peak extremes) to guarantee grid stability and avoid blackouts."""))

    # Section 1
    cells.append(nbf.v4.new_markdown_cell("""## 1. Why Central Tendency is Not Enough

Consider two hypothetical energy zones in Qatar that both report an average daily electricity load of **500 Megawatts (MW)**:
* **Zone A (Stable Industrial Load)**: Daily load consistently hovers between 480 MW and 520 MW.
* **Zone B (Residential & Tourist District)**: Daily load swings between 200 MW in winter and 800 MW during peak July heat.

Both zones share the exact same mean (500 MW), but Zone B has vastly higher **variability (dispersion)**, requiring massive backup generation and emergency reserve margins.

Let's generate a realistic dataset representing 365 days of weather and energy load in Doha."""))

    # Code 1
    cells.append(nbf.v4.new_code_cell("""# Step 1: Import core statistical and plotting libraries
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns

# Set visual aesthetic
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["figure.dpi"] = 120

# Set seed for reproducible results
np.random.seed(42)

# Generate 365 daily observations modeling Doha's climate and Kahramaa cooling demand
n_days = 365
days_of_year = np.arange(1, n_days + 1)

# Model temperature seasonality: cosine wave peaking in mid-summer (day ~200, late July)
# Mean temp ~30°C, amplitude ~13°C (winter ~17°C, summer ~43°C) + daily random variation
temp_trend = 30.0 - 13.0 * np.cos(2 * np.pi * (days_of_year - 20) / 365)
daily_temp_c = temp_trend + np.random.normal(loc=0, scale=2.5, size=n_days)
daily_temp_c = np.clip(daily_temp_c, 12.0, 48.5)

# Electricity cooling demand (MW) strongly correlates with temperature above 22°C
base_load_mw = 250.0
cooling_demand_mw = base_load_mw + np.maximum(0, daily_temp_c - 20.0) * 22.0 + np.random.normal(0, 15.0, n_days)

# Assign seasons based on day of year
def assign_season(day):
    if day < 80 or day >= 355:
        return "Winter"
    elif day < 172:
        return "Spring"
    elif day < 265:
        return "Summer"
    else:
        return "Autumn"

seasons = [assign_season(d) for d in days_of_year]

# Create DataFrame
df_climate = pd.DataFrame({
    "day_of_year": days_of_year,
    "season": seasons,
    "temperature_c": np.round(daily_temp_c, 1),
    "cooling_load_mw": np.round(cooling_demand_mw, 1)
})

# Display sample rows across seasons
print("--- Qatar Climate & Cooling Energy Sample ---")
df_climate.sample(6, random_state=12).sort_index()"""))

    # Section 2
    cells.append(nbf.v4.new_markdown_cell("""## 2. Measuring Dispersion: Range, IQR, Variance, and Standard Deviation

As outlined in Chapter 3, dispersion quantifies the spread of observations around the central value.

### A. Range
$$\\text{Range} = \\text{Max} - \\text{Min}$$
* Simplest metric of total spread.
* **Limitation**: Highly sensitive to the two most extreme points and ignores the distribution of data between them.

### B. Quartiles & Interquartile Range (IQR)
Quartiles divide sorted data into four equal quarters:
* **$Q_1$ (25th percentile)**: 25% of observations fall below this value.
* **$Q_2$ (50th percentile / Median)**: 50% of observations fall below this value.
* **$Q_3$ (75th percentile)**: 75% of observations fall below this value.

$$\\text{IQR} = Q_3 - Q_1$$
* Measures the spread of the central 50% of observations (the midspread).
* **Advantage**: Resilient against extreme values. Used to establish Tukey's box plot fences:
  $$\\text{Lower Fence} = Q_1 - 1.5 \\times \\text{IQR}, \\quad \\text{Upper Fence} = Q_3 + 1.5 \\times \\text{IQR}$$

### C. Variance ($S^2$)
$$\\text{Variance} = \\frac{1}{N - 1} \\sum_{i=1}^{N} (x_i - \\bar{x})^2$$
* Average of squared deviations from the mean.
* **Limitation**: The unit is squared (°C² or MW²), making it hard to interpret intuitively.

### D. Standard Deviation ($S$ or $\\sigma$)
$$S = \\sqrt{\\text{Variance}} = \\sqrt{\\frac{1}{N - 1} \\sum_{i=1}^{N} (x_i - \\bar{x})^2}$$
* The square root of the variance.
* **Key Advantage**: Restores the original unit of measurement (°C or MW). Directly shows how much typical observations deviate from the mean.

Let's compute all four dispersion metrics for Doha's daily temperature."""))

    # Code 2
    cells.append(nbf.v4.new_code_cell("""# Step 2: Compute dispersion metrics for temperature_c
temp_min = df_climate["temperature_c"].min()
temp_max = df_climate["temperature_c"].max()
temp_range = temp_max - temp_min

# Quartiles and IQR
q1 = df_climate["temperature_c"].quantile(0.25)
q3 = df_climate["temperature_c"].quantile(0.75)
iqr = q3 - q1

# Variance and Standard Deviation
temp_var = df_climate["temperature_c"].var()
temp_std = df_climate["temperature_c"].std()
temp_mean = df_climate["temperature_c"].mean()

# Display formatted results
print("=== Doha Temperature Dispersion Analysis ===")
print(f"Minimum Temperature:       {temp_min:.1f} °C")
print(f"Maximum Temperature:       {temp_max:.1f} °C")
print(f"Range:                     {temp_range:.1f} °C")
print("-" * 45)
print(f"1st Quartile (Q1 - 25%):    {q1:.1f} °C")
print(f"3rd Quartile (Q3 - 75%):    {q3:.1f} °C")
print(f"Interquartile Range (IQR): {iqr:.1f} °C")
print("-" * 45)
print(f"Variance:                  {temp_var:.2f} (°C)²")
print(f"Standard Deviation (std):  {temp_std:.2f} °C")
print(f"Mean Temperature:          {temp_mean:.2f} °C")"""))

    # Section 3
    cells.append(nbf.v4.new_markdown_cell("""### Automated Five-Number Summary: `df.describe()`
In pandas, the `.describe()` function computes count, mean, standard deviation, minimum, 25%, 50%, 75%, and maximum in a single command, as shown in Chapter 3."""))

    # Code 3
    cells.append(nbf.v4.new_code_cell("""# Step 3: Use describe() for full summary statistics of both metrics
print("=== Descriptive Summary: Temperature & Cooling Load ===")
df_climate[["temperature_c", "cooling_load_mw"]].describe()"""))

    # Section 4: Skewness and Kurtosis
    cells.append(nbf.v4.new_markdown_cell("""## 3. Understanding Distribution Shape: Skewness & Kurtosis

Dispersion tells us how wide the spread is; **Skewness** and **Kurtosis** describe the *shape* and *symmetry* of the distribution.

### A. Skewness (Symmetry)
Measures the asymmetry of the data distribution around the mean:
* **Symmetric ($Skew \\approx 0$)**: Bell-shaped; Mean $\\approx$ Median $\\approx$ Mode.
* **Positive / Right-Skewed ($Skew > 0$)**: Longer right tail. A few unusually high values pull the mean upward: Mean > Median > Mode.
* **Negative / Left-Skewed ($Skew < 0$)**: Longer left tail. A few unusually low values pull the mean downward: Mean < Median < Mode.

### B. Kurtosis (Tailedness & Outlier Propensity)
Measures the thickness of tails relative to a normal distribution:
* **Mesokurtic ($Kurtosis \\approx 0$ excess)**: Normal distribution tail profile.
* **Leptokurtic ($Kurtosis > 0$ excess)**: Heavy-tailed, sharper peak. More frequent extreme outliers (higher risk).
* **Platykurtic ($Kurtosis < 0$ excess)**: Thin-tailed, flatter peak. Fewer extreme outliers.

Let's compute and interpret skewness and kurtosis for both columns."""))

    # Code 4
    cells.append(nbf.v4.new_code_cell("""# Step 4: Calculate Skewness and Kurtosis using pandas
temp_skew = df_climate["temperature_c"].skew()
temp_kurt = df_climate["temperature_c"].kurtosis()

load_skew = df_climate["cooling_load_mw"].skew()
load_kurt = df_climate["cooling_load_mw"].kurtosis()

shape_df = pd.DataFrame({
    "Variable": ["Daily Temperature (°C)", "Cooling Load (MW)"],
    "Skewness": [f"{temp_skew:.3f}", f"{load_skew:.3f}"],
    "Skewness Interpretation": [
        "Slightly Left-Skewed" if temp_skew < -0.2 else ("Slightly Right-Skewed" if temp_skew > 0.2 else "Approximately Symmetric"),
        "Right-Skewed (Summer Peak Load)" if load_skew > 0.2 else "Symmetric"
    ],
    "Excess Kurtosis": [f"{temp_kurt:.3f}", f"{load_kurt:.3f}"],
    "Kurtosis Shape": [
        "Platykurtic (Flatter Peak, spread out)" if temp_kurt < -0.5 else "Mesokurtic",
        "Platykurtic" if load_kurt < -0.5 else ("Leptokurtic" if load_kurt > 0.5 else "Mesokurtic")
    ]
})

print("=== Distribution Shape Analysis ===")
shape_df"""))

    # Section 5: Visualizing Dispersion
    cells.append(nbf.v4.new_markdown_cell("""## 4. Visualizing Dispersion & Distribution Shape

To make dispersion intuitive for energy operations engineers, we present:
1. **Histogram & Standard Deviation Bands**: Showing the mean $\\pm 1\\sigma$ (covering ~68% of days) and $\\pm 2\\sigma$ (covering ~95% of days).
2. **Annotated Box Plot**: Explicitly visualizing Min, $Q_1$, Median, $Q_3$, Max, and the Interquartile Range.
3. **Seasonal Boxplots**: Showing how dispersion changes drastically across Qatar's four seasons."""))

    # Code 5
    cells.append(nbf.v4.new_code_cell("""# Step 5: Multi-panel visualization of dispersion
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Panel 1: Histogram with Mean & Standard Deviation Bands
sns.histplot(df_climate["temperature_c"], kde=True, color="#2b5c8f", bins=20, ax=axes[0])
axes[0].set_title("Doha Daily Temperature (°C)\\nwith Std Dev Bands", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Temperature (°C)")
axes[0].set_ylabel("Frequency (Days)")

# Vertical lines for Mean and Standard Deviation intervals
axes[0].axvline(temp_mean, color="red", linestyle="--", linewidth=2, label=f"Mean: {temp_mean:.1f}°C")
axes[0].axvline(temp_mean - temp_std, color="orange", linestyle=":", linewidth=1.8, label=f"±1 StdDev: [{temp_mean-temp_std:.1f}, {temp_mean+temp_std:.1f}]")
axes[0].axvline(temp_mean + temp_std, color="orange", linestyle=":", linewidth=1.8)
axes[0].legend(loc="upper left", frameon=True, fontsize=9)

# Panel 2: Boxplot with labeled Quartiles & IQR
sns.boxplot(y=df_climate["temperature_c"], color="#79b473", width=0.35, ax=axes[1])
axes[1].set_title("Boxplot Decomposition\\n(Quartiles & IQR)", fontsize=12, fontweight="bold")
axes[1].set_ylabel("Daily Temperature (°C)")

# Annotate boxplot milestones
axes[1].text(0.22, temp_max, f"Max: {temp_max:.1f}°C", verticalalignment="center", fontweight="bold")
axes[1].text(0.22, q3, f"Q3 (75%): {q3:.1f}°C", verticalalignment="center")
axes[1].text(0.22, df_climate['temperature_c'].median(), f"Median: {df_climate['temperature_c'].median():.1f}°C", verticalalignment="center", color="blue", fontweight="bold")
axes[1].text(0.22, q1, f"Q1 (25%): {q1:.1f}°C", verticalalignment="center")
axes[1].text(0.22, temp_min, f"Min: {temp_min:.1f}°C", verticalalignment="center", fontweight="bold")
axes[1].text(-0.35, (q1 + q3) / 2, f"IQR = {iqr:.1f}°C\\n(Middle 50%)", color="darkgreen", fontweight="bold", ha="center")

# Panel 3: Seasonal Dispersion Comparison
season_order = ["Winter", "Spring", "Summer", "Autumn"]
sns.boxplot(data=df_climate, x="season", y="temperature_c", order=season_order, palette="Set2", ax=axes[2])
axes[2].set_title("Seasonal Temperature Dispersion\\n(Qatar Seasons)", fontsize=12, fontweight="bold")
axes[2].set_xlabel("Season")
axes[2].set_ylabel("Temperature (°C)")

plt.tight_layout()
plt.show()"""))

    # Section 6: Seasonal Metrics
    cells.append(nbf.v4.new_markdown_cell("""## 5. Seasonal Variability Analysis: Winter vs. Summer

Breaking down dispersion by season reveals how operational uncertainty shifts across the year."""))

    # Code 6
    cells.append(nbf.v4.new_code_cell("""# Step 6: Compute dispersion metrics grouped by Season
seasonal_dispersion = df_climate.groupby("season")["temperature_c"].agg(
    Days="count",
    Mean_Temp="mean",
    Std_Dev="std",
    IQR=lambda x: x.quantile(0.75) - x.quantile(0.25),
    Min="min",
    Max="max",
    Range=lambda x: x.max() - x.min()
).loc[season_order].reset_index()

print("=== Seasonal Dispersion Metrics for Doha Climate ===")
seasonal_dispersion.round(2)"""))

    # Section 7: Analyst Insights
    cells.append(nbf.v4.new_markdown_cell("""## 6. Practical Data Analyst Insights for Qatar

### ⚡ Practical Applications in Infrastructure & Public Policy:
1. **Cooling Infrastructure Dimensioning**:
   * Peak summer cooling demand reaches over **800 MW** with a standard deviation of **~125 MW**. Sizing power stations solely for the mean demand (~470 MW) would result in widespread summer brownouts.
   * Standard deviation and upper quartiles ($Q_3$) determine the **spinning reserve capacity** required by Kahramaa.
2. **Occupational Health & Labour Regulations**:
   * Qatar's Ministry of Labour enforces outdoor work bans during summer afternoons (10:00 AM – 3:30 PM from June 1 to September 15).
   * Dispersion analysis of temperature and wet-bulb globe temperature (WBGT) directly supports occupational safety thresholds.
3. **Summary Comparison Guide**:

| Metric | Formula | Interpretation | Sensitivity to Extremes |
| :--- | :--- | :--- | :--- |
| **Range** | $\\text{Max} - \\text{Min}$ | Full span of observations | **Extreme** (determined solely by min and max) |
| **IQR** | $Q_3 - Q_1$ | Spread of typical middle 50% | **Low / Robust** (ignores outer tails) |
| **Variance** | $\\frac{1}{N-1}\\sum(x_i - \\bar{x})^2$ | Mean squared deviation | **High** (squared units) |
| **Standard Deviation** | $\\sqrt{\\text{Variance}}$ | Average distance from mean in original units | **Moderate-High** (intuitive and actionable) |"""))

    nb.cells = cells
    return nb

# -------------------------------------------------------------------------
# NOTEBOOK 3: RELATIONSHIPS & CORRELATION
# -------------------------------------------------------------------------
def build_notebook_3():
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.14.2"}
    }
    cells = []

    # Title & Introduction
    cells.append(nbf.v4.new_markdown_cell("""# 🔗 Module 3: Understanding Relationships: Covariance & Correlation
### Practical Insights from Qatar Aviation & Hospitality Services

---

## 🎯 Learning Objectives
In this notebook, we explore how data analysts measure relationships between variables, referencing **Chapter 3: Statistics for Data Insights**:
1. **Covariance**: Computing the degree of co-variation between variables and recognizing its scale-dependency limitation.
2. **Correlation Coefficients**: Standardizing covariance into normalized metrics ($-1$ to $+1$) using three core methods:
   * **Pearson Correlation ($r$)**: Parametric measure for linear relationships between continuous numeric variables.
   * **Spearman Rank Correlation ($\\rho$)**: Non-parametric measure for monotonic relationships, ideal for skewed data and outliers.
   * **Kendall’s Tau ($\\tau$)**: Non-parametric measure based on concordant and discordant pairs, ideal for small sample sizes and tied ordinal ranks.
3. **Ordinal Mapping**: Converting survey rating scales (e.g. `Poor`, `Average`, `Good`, `Excellent`) into numeric ranks for statistical correlation.
4. **Data Visualization**: Creating Scatter plots with trendlines and Correlation Heatmaps for executive reporting.

---

## 🇶🇦 Real-World Qatar Context
**Hamad International Airport (HIA)** and **Qatar Airways** represent world-class standards in global aviation and tourism. 

Airport operations and customer experience teams continuously evaluate operational dynamics:
* Does higher passenger transit volume increase baggage delivery wait times?
* How strongly does baggage delivery delay impact passenger satisfaction?
* How do customer satisfaction ratings correlate with on-time flight performance?

Understanding these relationships through the correct correlation method allows managers to allocate ground staff efficiently and protect high customer satisfaction ratings."""))

    # Section 1
    cells.append(nbf.v4.new_markdown_cell("""## 1. Creating the Operational Dataset

Let's build a realistic dataset representing 15 operational shifts at Hamad International Airport (HIA):
* **`flight_arrivals`**: Number of scheduled wide-body flight arrivals during the shift (Discrete numeric).
* **`transit_passengers_thousands`**: Number of connecting passengers in thousands (Continuous numeric).
* **`ground_staff_on_duty`**: Number of ground handling personnel deployed (Discrete numeric).
* **`baggage_wait_minutes`**: Average wait time for first baggage on carousel in minutes (Continuous numeric).
* **`on_time_departure_pct`**: Percentage of flights departing on schedule (Continuous numeric).
* **`service_speed_rating`**: Customer survey rating for check-in / transit speed (`Poor`, `Average`, `Good`, `Excellent`) (Ordinal).
* **`overall_satisfaction`**: Passenger experience satisfaction (`Low`, `Medium`, `High`, `Very High`) (Ordinal)."""))

    # Code 1
    cells.append(nbf.v4.new_code_cell("""# Step 1: Import core data analysis and visualization libraries
import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns

# Visual formatting
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 120

# Create realistic Qatar airport operations dataset (15 operational shifts)
hia_operations_data = {
    "shift_id": [f"HIA-S{i:02d}" for i in range(1, 16)],
    "transit_passengers_thousands": [18.5, 24.0, 14.2, 32.5, 28.0, 16.0, 22.5, 35.0, 12.0, 26.5, 30.0, 19.0, 21.0, 34.0, 15.5],
    "ground_staff_on_duty":        [45,   52,   40,   60,   55,   42,   50,   62,   38,   56,   58,   46,   48,   64,   42],
    "baggage_wait_minutes":        [22,   28,   18,   38,   34,   20,   27,   42,   16,   32,   36,   24,   26,   40,   19],
    "on_time_departure_pct":       [94.2, 88.5, 96.0, 81.0, 85.2, 95.0, 89.1, 78.4, 97.5, 84.0, 82.5, 92.0, 90.3, 79.5, 95.8],
    "service_speed_rating": [
        "Good", "Average", "Good", "Poor", "Average",
        "Good", "Average", "Poor", "Excellent", "Average",
        "Poor", "Good", "Average", "Poor", "Excellent"
    ],  # Ordinal
    "overall_satisfaction": [
        "High", "Medium", "High", "Low", "Medium",
        "High", "Medium", "Low", "Very High", "Medium",
        "Low", "High", "Medium", "Low", "Very High"
    ]   # Ordinal
}

df_hia = pd.DataFrame(hia_operations_data)

print("--- Hamad International Airport (HIA) Operations Sample ---")
df_hia.head(6)"""))

    # Section 2
    cells.append(nbf.v4.new_markdown_cell("""## 2. Covariance: Concept, Computation, and Limitations

### Mathematical Definition
Covariance measures the joint variability of two random variables:

$$\\text{Cov}(X, Y) = \\frac{1}{N - 1} \\sum_{i=1}^{N} (x_i - \\bar{x})(y_i - \\bar{y})$$

* **Positive Covariance ($>0$)**: When $X$ is above its mean, $Y$ also tends to be above its mean (they move in the same direction).
* **Negative Covariance ($<0$)**: When $X$ increases, $Y$ tends to decrease (they move in opposite directions).
* **Zero Covariance ($=0$)**: No linear co-movement.

### ⚠️ The Problem with Covariance
As emphasized in Chapter 3:
> *"The problem with covariance is that it does not provide effective conclusions because its range is $-\\infty$ to $+\\infty$, which is not normalized."*

Because covariance is measured in the product of the original units (e.g., $\\text{passengers} \\times \\text{minutes}$), a massive covariance number does **not** necessarily mean a stronger relationship than a small number.

Let's compute the covariance matrix using pandas `.cov()`."""))

    # Code 2
    cells.append(nbf.v4.new_code_cell("""# Step 2: Compute covariance matrix for continuous numeric metrics
numeric_cols = [
    "transit_passengers_thousands",
    "ground_staff_on_duty",
    "baggage_wait_minutes",
    "on_time_departure_pct"
]

cov_matrix = df_hia[numeric_cols].cov()

print("=== Covariance Matrix (HIA Operations) ===")
cov_matrix.round(2)"""))

    # Section 3: Correlation Coefficients
    cells.append(nbf.v4.new_markdown_cell("""## 3. Correlation Coefficients: Normalized Association

To overcome the unit-dependency of covariance, we normalize it by dividing by the product of both variables' standard deviations. This produces the **Correlation Coefficient ($r$)**, bounded strictly between **$-1.0$** and **$+1.0$**:

$$r = \\frac{\\text{Cov}(X, Y)}{\\sigma_X \\cdot \\sigma_Y}$$

* **$+1.0$**: Perfect positive linear relationship.
* **$0.0$**: No linear association.
* **$-1.0$**: Perfect negative linear relationship.

As detailed in Chapter 3, pandas supports three distinct correlation methods via `.corr(method=...)`:
1. **`pearson`**: Standard linear correlation coefficient.
2. **`spearman`**: Rank correlation for monotonic associations; robust to outliers.
3. **`kendall`**: Kendall's Tau coefficient for small datasets and tied ordinal rankings.

---

### A. Pearson Correlation (Linear Continuous Variables)
Let's compute the Pearson correlation matrix for our continuous operational variables."""))

    # Code 3
    cells.append(nbf.v4.new_code_cell("""# Step 3: Compute Pearson correlation matrix
pearson_corr = df_hia[numeric_cols].corr(method="pearson")

print("=== Pearson Correlation Matrix (Continuous Metrics) ===")
pearson_corr.round(3)"""))

    # Section 4: Ordinal Mapping
    cells.append(nbf.v4.new_markdown_cell("""## 4. Rank Correlation for Ordinal Survey Data: Spearman & Kendall

In customer experience analytics, survey responses are often collected as **Ordinal** categories (e.g., `Poor`, `Average`, `Good`, `Excellent`). 

Following the exact methodology demonstrated on **page 14 of Chapter 3**:
1. We define an **ordinal rank mapping dictionary**.
2. We map the text responses to numerical ranks.
3. We compute **Spearman** and **Kendall** correlation coefficients."""))

    # Code 4
    cells.append(nbf.v4.new_code_cell("""# Step 4: Define ordinal mapping dictionaries (referencing Chapter 3, page 14)
speed_rank_map = {"Poor": 1, "Average": 2, "Good": 3, "Excellent": 4}
satisfaction_rank_map = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}

# Map categorical text into numeric ranks
df_hia["speed_rank"] = df_hia["service_speed_rating"].map(speed_rank_map)
df_hia["satisfaction_rank"] = df_hia["overall_satisfaction"].map(satisfaction_rank_map)

# Compute Spearman's Rank Correlation
spearman_corr = df_hia[["speed_rank", "satisfaction_rank"]].corr(method="spearman")

# Compute Kendall's Tau Correlation
kendall_corr = df_hia[["speed_rank", "satisfaction_rank"]].corr(method="kendall")

print("=== Spearman Rank Correlation ===")
print(spearman_corr.round(4))
print("\\n=== Kendall's Tau Rank Correlation ===")
print(kendall_corr.round(4))"""))

    # Markdown comparison
    cells.append(nbf.v4.new_markdown_cell("""### 💡 Interpreting Spearman vs. Kendall
* **Spearman Correlation ($\\rho \\approx 0.98$)**: Indicates a near-perfect monotonic relationship. When service speed rank improves, passenger satisfaction rank almost always improves.
* **Kendall's Tau ($\\tau \\approx 0.95$)**: Measures the probability of concordant vs. discordant pairs. It is slightly more conservative than Spearman and is mathematically preferred when handling many tied ranks in customer satisfaction scales."""))

    # Section 5: Visualizing
    cells.append(nbf.v4.new_markdown_cell("""## 5. Visualizing Relationships: Scatter Plots & Heatmaps

Visualizing relationships helps stakeholders see the direction, strength, and dispersion of associations at a glance:
1. **Scatter Plot with Linear Regression Line**: Demonstrating the strong inverse relationship between Baggage Wait Time and On-Time Performance.
2. **Correlation Heatmap**: Visualizing all pairwise correlations with color intensity and numerical annotations."""))

    # Code 5
    cells.append(nbf.v4.new_code_cell("""# Step 5: Construct relationship visualizations
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Plot 1: Scatter plot with regression line (Baggage Wait vs On-Time Performance)
sns.regplot(
    data=df_hia,
    x="baggage_wait_minutes",
    y="on_time_departure_pct",
    color="#c0392b",
    scatter_kws={"s": 65, "alpha": 0.8},
    line_kws={"color": "#2c3e50", "linewidth": 2},
    ax=axes[0]
)
axes[0].set_title("Baggage Wait Time vs. On-Time Departure %\\n(Strong Negative Correlation)", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Baggage Wait Time (Minutes)", fontsize=11)
axes[0].set_ylabel("On-Time Departure Rate (%)", fontsize=11)

# Annotate correlation coefficient on plot
r_val = pearson_corr.loc["baggage_wait_minutes", "on_time_departure_pct"]
axes[0].text(0.05, 0.15, f"Pearson r = {r_val:.2f}", transform=axes[0].transAxes,
             fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="gray", alpha=0.9))

# Plot 2: Annotated Heatmap of the Pearson Correlation Matrix
sns.heatmap(
    pearson_corr,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    vmin=-1.0,
    vmax=1.0,
    linewidths=1.0,
    cbar_kws={"label": "Correlation Coefficient"},
    ax=axes[1]
)
axes[1].set_title("HIA Operational Metrics Correlation Heatmap", fontsize=12, fontweight="bold")

plt.tight_layout()
plt.show()"""))

    # Section 6: Correlation vs Causation & Guide
    cells.append(nbf.v4.new_markdown_cell("""## 6. Crucial Rule: Correlation vs. Causation & Selection Guide

### ⚠️ Correlation Does NOT Imply Causation!
Finding a high positive correlation between **Transit Passengers** and **Baggage Wait Time** ($r \\approx +0.99$) shows they move together, but passenger count alone does not mechanically delay bags. The real cause is **carousel conveyor capacity bottlenecks** and **staff allocation constraints** during peak flight arrival banks.

Always look for underlying confounding or lurking variables before recommending policy changes.

---

### 📋 Method Selection Guide for Data Analysts

| Correlation Method | Applicable Data Type | Assumptions | Best Practical Use Case in Qatar |
| :--- | :--- | :--- | :--- |
| **Pearson ($r$)** | Continuous Numeric | Linear relationship, normally distributed data, no extreme outliers | Evaluating Kahramaa power load vs ambient temperature |
| **Spearman ($\\rho$)** | Continuous or Ordinal | Monotonic relationship (not necessarily linear); tolerant to outliers | Logistics turnaround time vs parcel volume with seasonal spikes |
| **Kendall’s Tau ($\\tau$)** | Ordinal Rankings | Concordance-based; small samples; robust with tied ranks | Passenger satisfaction surveys, airline cabin service ratings |"""))

    nb.cells = cells
    return nb

# -------------------------------------------------------------------------
# EXECUTE & SAVE ALL NOTEBOOKS
# -------------------------------------------------------------------------
def generate_and_execute_all():
    notebooks = [
        ("01_central_tendency_qatar.ipynb", build_notebook_1()),
        ("02_dispersion_and_distribution_qatar.ipynb", build_notebook_2()),
        ("03_relationships_and_correlation_qatar.ipynb", build_notebook_3())
    ]
    
    ep = ExecutePreprocessor(timeout=120, kernel_name="python3")
    
    for filename, nb in notebooks:
        filepath = os.path.join(WORKSPACE, filename)
        print(f"Executing and saving: {filename}...")
        try:
            ep.preprocess(nb, {"metadata": {"path": WORKSPACE}})
            print(f"  Execution succeeded for {filename}!")
        except Exception as e:
            print(f"  Execution error in {filename}: {e}")
            raise e
            
        with open(filepath, "w", encoding="utf-8") as f:
            nbf.write(nb, f)
        print(f"  Successfully written to: {filepath}\n")

if __name__ == "__main__":
    generate_and_execute_all()
