import nbformat as nbf
import os
import sys

def build_all():
    print("Building all 8 analytical Jupyter notebooks...")

    # Load notebook 1 generator from make_nb1.py
    import make_nb1
    nb1 = make_nb1.create_nb1()
    with open("01_trend_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb1, f)
    print("[OK] 01_trend_analysis.ipynb created.")

    import make_nb2
    nb2 = make_nb2.create_nb2()
    with open("02_comparison_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb2, f)
    print("[OK] 02_comparison_analysis.ipynb created.")

    import make_nb3
    nb3 = make_nb3.create_nb3()
    with open("03_ranking_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb3, f)
    print("[OK] 03_ranking_analysis.ipynb created.")

    import make_nb4
    nb4 = make_nb4.create_nb4()
    with open("04_part_to_whole_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb4, f)
    print("[OK] 04_part_to_whole_analysis.ipynb created.")

    import make_nb5
    nb5 = make_nb5.create_nb5()
    with open("05_distribution_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb5, f)
    print("[OK] 05_distribution_analysis.ipynb created.")

    import make_nb6
    nb6 = make_nb6.create_nb6()
    with open("06_relationship_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb6, f)
    print("[OK] 06_relationship_analysis.ipynb created.")

    import make_nb7
    nb7 = make_nb7.create_nb7()
    with open("07_geographic_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb7, f)
    print("[OK] 07_geographic_analysis.ipynb created.")

    import make_nb8
    nb8 = make_nb8.create_nb8()
    with open("08_target_deviation_analysis.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb8, f)
    print("[OK] 08_target_deviation_analysis.ipynb created.")

    print("\nAll 8 notebooks built successfully!")

if __name__ == "__main__":
    build_all()
