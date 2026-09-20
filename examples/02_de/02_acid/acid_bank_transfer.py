import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # ACID Transaction with a Bank Transfer

    This notebook demonstrates **Atomicity, Consistency, Isolation, and Durability (ACID)** using a transfer of 200 between a Savings and a Current account in DuckDB.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 1. Create the accounts table and insert test data

    The total accounts balance is 1500: 1000 in Savings and 500 in Current.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        DROP TABLE IF EXISTS accounts;

        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            customer_name VARCHAR,
            account_type VARCHAR,
            balance DECIMAL(10, 2)
        );

        INSERT INTO accounts (account_id, customer_name, account_type, balance)
        VALUES
            (1, 'Ahmed', 'Savings', 1000.00),
            (2, 'Ahmed', 'Current', 500.00);
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT account_type, balance
        FROM accounts
        UNION ALL
        SELECT 'Total', SUM(balance)
        FROM accounts;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Transfer without a transaction: an exception leaves the database inconsistent

    Doing the transfer **without** wrapping the two updates in a transaction. Outside an explicit transaction, DuckDB commits each statement as soon as it succeeds.

    The withdrawal from Savings commits immediately. The deposit into Current then fails (nonexistent column), so the money never arrives - it simply disappears. This leaves the database inconsistent.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        -- Step 1: The withdrawal commits immediately outside a transaction.
        UPDATE accounts
        SET balance = balance - 200
        WHERE account_id = 1;

        -- Step 2: Simulate the failed deposit with a predicate that matches no row.
        -- The withdrawal remains applied, so the customer's total is now inconsistent.
        UPDATE accounts
        SET balance = balance + 200
        WHERE account_id = 2
          AND invalid_column = 1;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT account_type, balance
        FROM accounts
        UNION ALL
        SELECT 'Total', SUM(balance)
        FROM accounts;
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    - Real-world effect: the customer balance dropped from 1500 to 1300.
    - 😢 Customer: I moved 200 into my Current account, but it just vanished!'
    - 😀 Bank: now owes the customer 200. An unearned gain caused by the missing update.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Reset the test data

    Restore the original balances before demonstrating an explicit transaction.
    """)
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        UPDATE accounts
        SET balance = CASE
            WHEN account_id = 1 THEN 1000.00
            WHEN account_id = 2 THEN 500.00
        END;
        """
    )
    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT account_type, balance
        FROM accounts
        UNION ALL
        SELECT 'Total', SUM(balance)
        FROM accounts;
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Transfer with a transaction

    The withdrawal and deposit are executed inside one transaction. The explicit `ROLLBACK` demonstrates atomicity: neither change remains committed.
    """)
    return


@app.cell
def _():
    # Why a Python cell instead of a `sql` cell?
    # DuckDB SQL has no try/except support - if one statement fails, execution just stops and
    # the error propagates with no way to catch it and clean up afterward.
    # Python's try/except lets us catch that error and run ROLLBACK ourselves.
    import duckdb

    try:
        # Start a transaction: changes below are temporary until COMMIT runs.
        duckdb.sql("BEGIN TRANSACTION;")

        # Step 1: withdraw 200 from account 1 (Savings).
        duckdb.sql("""
            UPDATE accounts
            SET balance = balance - 200
            WHERE account_id = 1;
        """)

        # Step 2: deposit 200 into account 2 (Current).
        # `invalid_column` doesn't exist, so this line raises an error on purpose.
        duckdb.sql("""
            UPDATE accounts
            SET balance = balance + 200
            WHERE account_id = 2 AND invalid_column = 1;
        """)

        # Only reached if both updates above succeeded.
        duckdb.sql("COMMIT;")
        print("Transfer committed successfully.")
    except Exception as e:
        # Step 2 raised, so undo Step 1 too - the transfer must be all-or-nothing.
        duckdb.sql("ROLLBACK;")
        print(f"🤦Transaction failed, rolled back ↩️: {e}")

    return


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT account_type, balance
        FROM accounts
        UNION ALL
        SELECT 'Total', SUM(balance)
        FROM accounts
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## ACID properties illustrated

    - **Atomicity:** All-or-nothing. The withdrawal and deposit are treated as a single unit, so a mid-way failure prevents a partial update - `ROLLBACK` undoes both, leaving no half-finished transfer.
    - **Consistency:** The total accounts balance remains 1500 after the transfer
    - **Isolation:** Uncommitted changes are hidden from other transactions.
    - **Durability:** Committed changes persist after the transaction completes.
    """)
    return


if __name__ == "__main__":
    app.run()
