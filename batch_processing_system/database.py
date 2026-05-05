import sqlite3
import random
from datetime import datetime, timedelta

DB_NAME = 'batch_data.db'

def init_db():
    print("Initializing Database...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create raw_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT,
            amount REAL,
            category TEXT,
            status TEXT
        )
    ''')
    
    # Create daily_reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT,
            total_amount REAL,
            transaction_count INTEGER,
            processed_at TEXT
        )
    ''')

    # Create scheduled_jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT,
            schedule_time TEXT,
            status TEXT,
            next_run TEXT
        )
    ''')

    # Create job_logs table for monitoring
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT,
            start_time TEXT,
            end_time TEXT,
            duration TEXT,
            status TEXT,
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,
            logs TEXT
        )
    ''')
    
    conn.commit()

    # Initial Scheduled Jobs
    cursor.execute("SELECT COUNT(*) FROM scheduled_jobs")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO scheduled_jobs (job_name, schedule_time, status, next_run) VALUES (?, ?, ?, ?)",
                      ('Nightly Aggregation', '02:00 AM', 'Active', '2026-05-05T02:00:00'))
        cursor.execute("INSERT INTO scheduled_jobs (job_name, schedule_time, status, next_run) VALUES (?, ?, ?, ?)",
                      ('Hourly Sensor Check', 'Every 1 Hour', 'Paused', 'N/A'))
        conn.commit()
    
    # Initial Logs
    cursor.execute("SELECT COUNT(*) FROM job_logs")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO job_logs (job_name, start_time, end_time, duration, status, retry_count, logs) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Nightly Aggregation', '2026-05-04T02:00:00', '2026-05-04T02:05:22', '5m 22s', 'Success', 0, 'Starting job...\nExtracting 1200 rows...\nAggregating...\nSaved report.'))
        conn.commit()
    
    # Check if we need to insert dummy data
    cursor.execute("SELECT COUNT(*) FROM raw_data")
    if cursor.fetchone()[0] == 0:
        print("Inserting dummy data for the past 3 days...")
        categories = ['Groceries', 'Electronics', 'Clothing', 'Utilities']
        statuses = ['COMPLETED', 'COMPLETED', 'COMPLETED', 'FAILED'] # 75% complete
        
        for i in range(3): # Generate data for 3 previous days
            date_str = (datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')
            for _ in range(100): # 100 transactions per day
                amount = round(random.uniform(10.0, 500.0), 2)
                category = random.choice(categories)
                status = random.choice(statuses)
                cursor.execute(
                    "INSERT INTO raw_data (transaction_date, amount, category, status) VALUES (?, ?, ?, ?)",
                    (date_str, amount, category, status)
                )
        conn.commit()
        print("Dummy data inserted.")
    
    conn.close()
    print("Database ready.")

if __name__ == "__main__":
    init_db()
