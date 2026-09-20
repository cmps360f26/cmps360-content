import marimo

__generated_with = "0.24.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo


    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # SQL Basics with DuckDB

    Simple SQL queries for exploring the JSON datasets in `quran-data`.

    ## Datasets

    - `surah.json`: Surah details and revelation place.
    - `ayah.json`: Verse text and word counts.
    - `juz.json`: Juz divisions and verse counts.
    - `sajda.json`: Prostration verses.
    - `matching-ayah.json`: Nested verse similarity matches.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Running SQL with marimo

    Each query below is a SQL cell backed by DuckDB. The JSON files are queried directly, and query results are displayed below each cell.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Question 1: Surahs and Verses by Revelation Place

    Count total surahs and total verses for Makkah vs Madinah, including each place's percentage of the total.

    **SQL Concepts:** `WITH`, `GROUP BY`, `COUNT`, `SUM`, window functions.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Count surahs and verses, then calculate each place's percentage of the total.
        WITH surah_stats AS (
            SELECT
                revelation_place,
                COUNT(*) AS total_surahs,
                SUM(verses_count) AS total_verses
            FROM 'quran-data/surah.json'
            GROUP BY revelation_place
        )
        SELECT
            revelation_place,
            total_surahs,
            ROUND(100.0 * total_surahs / SUM(total_surahs) OVER (), 2) AS surah_percentage,
            total_verses,
            ROUND(100.0 * total_verses / SUM(total_verses) OVER (), 2) AS verse_percentage
        FROM surah_stats
        ORDER BY total_surahs DESC;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Question 2: Surahs with Prostration Verses (Sajdah)

    List Sajdah verses with their Surah names and Arabic text.

    **SQL Concepts:** `JOIN`, `ON`, `ORDER BY`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            s.sajdah_number,
            s.verse_key,
            s.sajdah_type,
            su.name_arabic AS surah_name,
            su.name_english AS surah_name_english,
            a.text AS verse_text
        FROM 'quran-data/sajda.json' AS s
        JOIN 'quran-data/ayah.json' AS a
            ON s.verse_key = a.verse_key
        JOIN 'quran-data/surah.json' AS su
            ON a.surah_number = su.id
        ORDER BY s.sajdah_number;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Question 3: Top 5 Longest Juz by Verse Count

    Find the 5 Juz with the most verses, including the names and text of their starting and ending ayahs.

    **SQL Concepts:** `SELECT`, `split_part`, `JOIN`, `ORDER BY`, `LIMIT`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            juz_number,
            verses_count,
            first_verse_key,
            last_verse_key
        FROM 'quran-data/juz.json'
        ORDER BY verses_count DESC
        LIMIT 5;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            j.juz_number,
            j.verses_count,
            split_part(j.first_verse_key, ':', 1)::INT AS start_surah,
            start_s.name_arabic AS start_surah_name,
            split_part(j.first_verse_key, ':', 2)::INT AS start_aya,
            start_a.text AS start_aya_text,
            split_part(j.last_verse_key, ':', 1)::INT AS end_surah,
            end_s.name_arabic AS end_surah_name,
            split_part(j.last_verse_key, ':', 2)::INT AS end_aya,
            end_a.text AS end_aya_text
        FROM 'quran-data/juz.json' AS j
        JOIN 'quran-data/ayah.json' AS start_a
            ON j.first_verse_key = start_a.verse_key
        JOIN 'quran-data/ayah.json' AS end_a
            ON j.last_verse_key = end_a.verse_key
        JOIN 'quran-data/surah.json' AS start_s
            ON start_a.surah_number = start_s.id
        JOIN 'quran-data/surah.json' AS end_s
            ON end_a.surah_number = end_s.id
        ORDER BY j.verses_count DESC
        LIMIT 5;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        COPY (
            SELECT
                j.juz_number,
                j.verses_count,
                split_part(j.first_verse_key, ':', 1)::INT AS start_surah,
                start_s.name_arabic AS start_surah_name,
                split_part(j.first_verse_key, ':', 2)::INT AS start_aya,
                start_a.text AS start_aya_text,
                split_part(j.last_verse_key, ':', 1)::INT AS end_surah,
                end_s.name_arabic AS end_surah_name,
                split_part(j.last_verse_key, ':', 2)::INT AS end_aya,
                end_a.text AS end_aya_text
            FROM 'quran-data/juz.json' AS j
            JOIN 'quran-data/ayah.json' AS start_a
                ON j.first_verse_key = start_a.verse_key
            JOIN 'quran-data/ayah.json' AS end_a
                ON j.last_verse_key = end_a.verse_key
            JOIN 'quran-data/surah.json' AS start_s
                ON start_a.surah_number = start_s.id
            JOIN 'quran-data/surah.json' AS end_s
                ON end_a.surah_number = end_s.id
            ORDER BY j.verses_count DESC
            LIMIT 5
        ) TO 'quran-data/top_juz.parquet' (FORMAT PARQUET);
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT * FROM 'quran-data/top_juz.parquet';
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Question 4: Top 5 Surahs by Total Word Count

    Find the 5 largest Surahs by total word count.

    **SQL Concepts:** `JOIN`, `SUM`, `GROUP BY ALL`, `ORDER BY`, `LIMIT`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            su.name_arabic AS surah_name,
            su.name_english AS surah_name_english,
            su.revelation_place,
            SUM(a.words_count) AS total_words
        FROM 'quran-data/surah.json' AS su
        JOIN 'quran-data/ayah.json' AS a
            ON su.id = a.surah_number
        GROUP BY ALL
        ORDER BY total_words DESC
        LIMIT 5;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### Question 5: Longest Verses

    Find the 5 verses with the most words and characters.

    **SQL Concepts:** `SELECT`, `length`, `AS`, `ORDER BY`, `LIMIT`.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT
            verse_key,
            words_count,
            length(text) AS character_count,
            text
        FROM 'quran-data/ayah.json'
        ORDER BY words_count DESC
        LIMIT 5;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        COPY (
            SELECT
                revelation_place,
                AVG(verses_count) AS avg_verse_count,
                COUNT(*) AS surah_count
            FROM 'quran-data/surah.json'
            GROUP BY revelation_place
            ORDER BY surah_count DESC
        ) TO 'quran-data/summary_by_revelation_place.parquet' (FORMAT parquet);
        """
    )
    return


if __name__ == "__main__":
    app.run()
