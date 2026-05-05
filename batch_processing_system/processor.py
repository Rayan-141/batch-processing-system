import pandas as pd
import sqlite3
from datetime import datetime
import os
import random

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'batch_data.db')

def add_random_raw_data(conn, target_date):
    """Always adds 5-15 new random transactions to simulate new data arrival."""
    cursor = conn.cursor()
    print(f"Injecting new simulated data for {target_date}...")
    categories = ['Groceries', 'Electronics', 'Clothing', 'Utilities', 'Entertainment']
    statuses = ['COMPLETED', 'COMPLETED', 'COMPLETED', 'FAILED']
    
    num_tx = random.randint(50, 120) # High volume transaction count
    for _ in range(num_tx):
        amount = round(random.uniform(5000.0, 25000.0), 2) # High value transactions
        category = random.choice(categories)
        status = random.choice(statuses)
        cursor.execute(
            "INSERT INTO raw_data (transaction_date, amount, category, status) VALUES (?, ?, ?, ?)",
            (target_date, amount, category, status)
        )
    conn.commit()
    print(f"Added {num_tx} new transactions to raw storage for {target_date}.")

def process_daily_data(target_date: str):
    """
    Reads data from SQLite, aggregates it using Pandas, and saves the report.
    Automatically generates raw data if none exists to ensure dynamic results.
    """
    print(f"[{datetime.now()}] Starting batch process for date: {target_date}")
    
    conn = sqlite3.connect(DB_NAME)
    
    # NEW: Inject fresh data every time to ensure dynamic results
    add_random_raw_data(conn, target_date)
    
    # 1. EXTRACT
    query = f"SELECT * FROM raw_data WHERE transaction_date = '{target_date}' AND status = 'COMPLETED'"
    
    # Using chunksize simulates handling large data efficiently
    print("Extracting data...")
    chunks = pd.read_sql_query(query, conn, chunksize=1000)
    
    total_amount = 0.0
    transaction_count = 0
    
    # 2. TRANSFORM
    print("Transforming and Aggregating data...")
    for df_chunk in chunks:
        if not df_chunk.empty:
            total_amount += df_chunk['amount'].sum()
            transaction_count += len(df_chunk)
            
    if transaction_count == 0:
        print(f"No COMPLETED data found for {target_date}.")
        conn.close()
        return

    # 3. LOAD
    print("Loading aggregated report into database...")
    report_data = {
        'report_date': [target_date],
        'total_amount': [total_amount],
        'transaction_count': [transaction_count],
        'processed_at': [datetime.now().isoformat()]
    }
    
    report_df = pd.DataFrame(report_data)
    # Check if report already exists to ensure idempotency
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM daily_reports WHERE report_date = '{target_date}'")
    conn.commit()
    
    report_df.to_sql('daily_reports', conn, if_exists='append', index=False)
    conn.close()
    
    print(f"[{datetime.now()}] Batch process completed successfully for {target_date}.")
    print(f"Report Summary -> Total Amount: ₹{total_amount:.2f} | Transactions: {transaction_count}")

if __name__ == "__main__":
    # Test script locally with today's date
    today = datetime.now().strftime('%Y-%m-%d')
    process_daily_data(today)
