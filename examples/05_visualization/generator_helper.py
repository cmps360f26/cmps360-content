import nbformat as nbf
import os
import sys

def make_notebook(title, purpose, objectives, scenario, data_code, preview_code, 
                  questions, sns_code, px_code, interpretation_md, 
                  insights_md, mistakes_md, ex1_md, ex2_md, ex2_code, 
                  ex3_md, ex3_code, challenge_md, takeaways_md):
    nb = nbf.v4.new_notebook()
    cells = []

    # 1. Notebook Title & Purpose
    title_md = f"""# {title}
### Primary Analytical Purpose: *{purpose}*

---
"""
    cells.append(nbf.v4.new_markdown_cell(title_md))

    # 2. Learning Objectives
    obj_md = f"""## 1. Learning Objectives

By completing this notebook, you will be able to:
"""
    for obj in objectives:
        obj_md += f"- **{obj[0]}**: {obj[1]}\n"
    obj_md += """
**The Analytical Workflow:**
$$\\text{Business Question} \\longrightarrow \\text{Analyze Data} \\longrightarrow \\text{Visualize Patterns} \\longrightarrow \\text{Interpret Visuals} \\longrightarrow \\text{Actionable Insight}$$
"""
    cells.append(nbf.v4.new_markdown_cell(obj_md))

    # 3. Business Scenario
    scen_md = f"""## 2. Business Scenario

{scenario}
"""
    cells.append(nbf.v4.new_markdown_cell(scen_md))

    # Standard Setup Cell
    setup_code = """# Standard imports for data analysis and visualization
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px

# Set Seaborn visual style
sns.set_theme(style="whitegrid")
"""
    cells.append(nbf.v4.new_code_cell(setup_code))

    # 4. Dataset Creation
    data_intro_md = """## 3. Dataset Creation

We generate a self-contained, realistic dataset directly in Pandas so you can run this notebook anywhere without external file downloads.
"""
    cells.append(nbf.v4.new_markdown_cell(data_intro_md))
    cells.append(nbf.v4.new_code_cell(data_code))

    # 5. Dataset Preview
    prev_md = """## 4. Dataset Preview

Before creating any charts, always inspect the structure, column data types, and first few rows of your DataFrame.
"""
    cells.append(nbf.v4.new_markdown_cell(prev_md))
    cells.append(nbf.v4.new_code_cell(preview_code))

    # 6. Analytical Question
    q_md = """## 5. Analytical Questions

As an analyst, we examine the data to answer specific business questions:
"""
    for q in questions:
        q_md += f"- **{q}**\n"
    cells.append(nbf.v4.new_markdown_cell(q_md))

    # 7. Seaborn Visualization
    sns_intro_md = """## 6. Seaborn Visualization (Static Publication Chart)

Seaborn creates clean, statistically-tuned static graphics ideal for reports, slide decks, and written documentation.
"""
    cells.append(nbf.v4.new_markdown_cell(sns_intro_md))
    cells.append(nbf.v4.new_code_cell(sns_code))

    # 8. Plotly Express Visualization
    px_intro_md = """## 7. Plotly Express Visualization (Interactive Web Chart)

Plotly Express creates responsive, interactive charts where you can hover over data points, zoom, pan, and isolate categories.
"""
    cells.append(nbf.v4.new_markdown_cell(px_intro_md))
    cells.append(nbf.v4.new_code_cell(px_code))

    # 9. Interpretation
    interp_section_md = f"""## 8. Interpretation

{interpretation_md}
"""
    cells.append(nbf.v4.new_markdown_cell(interp_section_md))

    # 10. Key Insights & Common Mistakes
    insights_section_md = f"""## 9. Key Insights & Recommended Business Actions

{insights_md}

---

### Common Analytical Mistake to Avoid
{mistakes_md}
"""
    cells.append(nbf.v4.new_markdown_cell(insights_section_md))

    # 11. Practice Exercises
    exercises_md = f"""## 10. Practice Exercises

Apply what you have learned by completing these three exercises.
"""
    cells.append(nbf.v4.new_markdown_cell(exercises_md))

    # Exercise 1 (Markdown interpretation)
    cells.append(nbf.v4.new_markdown_cell(f"""### Exercise 1: Chart Interpretation
{ex1_md}
"""))

    # Exercise 2 (Code modification)
    cells.append(nbf.v4.new_markdown_cell(f"""### Exercise 2: Modify Chart Settings
{ex2_md}
"""))
    cells.append(nbf.v4.new_code_cell(ex2_code))

    # Exercise 3 (Business calculation / question)
    cells.append(nbf.v4.new_markdown_cell(f"""### Exercise 3: Answer a Business Question
{ex3_md}
"""))
    cells.append(nbf.v4.new_code_cell(ex3_code))

    # 12. Challenge Activity
    chal_md = f"""## 11. Challenge Activity

{challenge_md}
"""
    cells.append(nbf.v4.new_markdown_cell(chal_md))
    cells.append(nbf.v4.new_code_cell("# Student Solution for Challenge Activity\n# Write your code below:\n"))

    # 13. Key Takeaways
    take_md = f"""## 12. Key Takeaways

{takeaways_md}
"""
    cells.append(nbf.v4.new_markdown_cell(take_md))

    nb.cells = cells
    return nb

print("make_notebook helper defined.")
