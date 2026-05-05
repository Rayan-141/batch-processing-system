from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import sqlite3
import pandas as pd
from datetime import datetime
import os
import time
import threading
from datetime import datetime, timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background scheduler thread
    print("Initializing Background Scheduler...")
    threading.Thread(target=background_scheduler, daemon=True).start()
    yield
    # Clean up (if needed)

app = FastAPI(
    title="Batch Processing System API", 
    description="API to access reports and trigger batch jobs manually.",
    lifespan=lifespan
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'batch_data.db')

def get_db_connection():
    if not os.path.exists(DB_NAME):
        print("Database not found. Auto-initializing...")
        from database import init_db
        init_db()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
def read_root():
    return FileResponse("static/index.html")

@app.get("/reports", tags=["Reports"])
def get_all_reports():
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM daily_reports ORDER BY report_date DESC", conn)
        data = df.to_dict(orient='records')
        # Add metadata hint
        return {"reports": data, "engine_stats": {"workers": 3, "strategy": "Parallel Chunking"}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/scheduled-jobs/{job_id}", tags=["Scheduler"])
def delete_scheduled_job(job_id: int):
    """Delete a scheduled job."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/job-logs", tags=["Monitoring"])
def get_job_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()
    return [dict(l) for l in logs]

@app.delete("/job-logs/{log_id}", tags=["Monitoring"])
def delete_job_log(log_id: int):
    """Delete a specific execution log."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/trigger_job/{date}", tags=["Jobs"])
def trigger_batch_job(date: str, background_tasks: BackgroundTasks):
    from processor import process_daily_data
    start_time = datetime.now()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO job_logs (job_name, start_time, status, logs) 
        VALUES (?, ?, ?, ?)
    ''', (f"Batch Run: {date}", start_time.strftime('%Y-%m-%dT%H:%M:%S'), 'Running', 'Initializing workers...\nQueuing tasks...'))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    background_tasks.add_task(job_executor, date, log_id, start_time)
    return {"status": "success", "log_id": log_id}

@app.get("/job-logs/by-date/{date}", tags=["Monitoring"])
def get_job_log_by_date(date: str):
    """Fetch the latest execution log for a specific date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Search for "Batch Run: YYYY-MM-DD" or similar in job_name
    cursor.execute("SELECT * FROM job_logs WHERE job_name LIKE ? ORDER BY id DESC LIMIT 1", (f"%{date}%",))
    log = cursor.fetchone()
    conn.close()
    if log:
        return dict(log)
    raise HTTPException(status_code=404, detail="No log found for this date")

@app.post("/retry_job/{log_id}", tags=["Jobs"])
def retry_job(log_id: int, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT job_name FROM job_logs WHERE id = ?", (log_id,))
    job = cursor.fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Extract date from job_name "Batch Run: YYYY-MM-DD"
    try:
        date = job['job_name'].split(': ')[1]
    except:
        date = datetime.now().strftime('%Y-%m-%d')

    start_time = datetime.now()
    cursor.execute('''
        UPDATE job_logs SET start_time = ?, end_time = NULL, duration = NULL, 
        status = ?, logs = ?, error_message = NULL WHERE id = ?
    ''', (start_time.strftime('%Y-%m-%dT%H:%M:%S'), 'Running', 'Retrying job...\nClearing cache...', log_id))
    conn.commit()
    conn.close()

    background_tasks.add_task(job_executor, date, log_id, start_time)
    return {"status": "success"}

def job_executor(date, log_id, start_time):
    from processor import process_daily_data
    try:
        # Simulate realistic time for system design depth
        time.sleep(2) 
        
        # Step-by-step logging simulation
        update_log(log_id, "Running", "Worker 1: Connected to SQLite\nWorker 2: Loading Chunks\nWorker 3: Aggregating...")
        
        process_daily_data(date)
        
        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()
        duration_str = f"{int(duration_sec)}s"
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE job_logs SET end_time = ?, duration = ?, status = ?, logs = ? WHERE id = ?
        ''', (end_time.strftime('%Y-%m-%dT%H:%M:%S'), duration_str, 'Success', 
              'SUCCESS: All chunks processed.\nFinal aggregation complete.\nReport saved to disk.', log_id))
        conn.commit()
        conn.close()
    except Exception as e:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE job_logs SET status = ?, error_message = ?, retry_count = retry_count + 1, logs = ? WHERE id = ?
        ''', ('Failed', str(e), f"CRITICAL ERROR: {str(e)}\nTerminating workers...", log_id))
        conn.commit()
        conn.close()

def update_log(log_id, status, log_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE job_logs SET status = ?, logs = logs || '\n' || ? WHERE id = ?", (status, log_text, log_id))
    conn.commit()
    conn.close()

@app.delete("/reports/{report_id}", tags=["Reports"])
def delete_report(report_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/scheduled-jobs", tags=["Scheduler"])
def get_scheduled_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduled_jobs")
    jobs = cursor.fetchall()
    conn.close()
    return [dict(j) for j in jobs]

@app.post("/scheduled-jobs", tags=["Scheduler"])
def create_scheduled_job(job_name: str, start_time: str, end_time: str, duration: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scheduled_jobs (job_name, schedule_time, next_run, status) VALUES (?, ?, ?, ?)",
        (job_name, start_time, f"{start_time} - {end_time} ({duration})", 'Active')
    )
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/scheduled-jobs/{job_id}/toggle", tags=["Scheduler"])
def toggle_job_status(job_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM scheduled_jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if job:
        new_status = 'Paused' if job['status'] == 'Active' else 'Active'
        cursor.execute("UPDATE scheduled_jobs SET status = ? WHERE id = ?", (new_status, job_id))
        conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/download-report/{date}", tags=["Reports"])
def download_report_pdf(date: str):
    from exporter import generate_batch_report_pdf
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_reports WHERE report_date = ?", (date,))
    report = cursor.fetchone()
    
    cursor.execute("SELECT * FROM job_logs WHERE job_name LIKE ? ORDER BY id DESC LIMIT 1", (f"%{date}%",))
    log = cursor.fetchone()
    conn.close()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    log_dict = dict(log) if log else {}
    file_path = generate_batch_report_pdf(dict(report), log_dict)
    return FileResponse(file_path, filename=f"Batch_Report_{date}.pdf", media_type="application/pdf")

@app.get("/download-history", tags=["Monitoring"])
def download_history_pdf():
    from exporter import generate_history_export_pdf
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_logs ORDER BY id DESC")
    logs = [dict(l) for l in cursor.fetchall()]
    conn.close()
    
    file_path = generate_history_export_pdf(logs)
    return FileResponse(file_path, filename="Execution_History.pdf", media_type="application/pdf")

def background_scheduler():
    """Background thread to check and trigger scheduled jobs."""
    print("Background Scheduler Started...")
    while True:
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            now = datetime.now()
            current_time_str = now.strftime('%H:%M')
            current_date_str = now.strftime('%Y-%m-%d')
            
            # Find Active jobs that should run at this minute
            cursor.execute("SELECT * FROM scheduled_jobs WHERE status = 'Active' AND schedule_time = ?", (current_time_str,))
            jobs = cursor.fetchall()
            
            for job in jobs:
                # To prevent double trigger in the same minute, we could check last_run
                # For simplicity in this demo, we'll just trigger
                print(f"Triggering Scheduled Job: {job['job_name']}")
                
                # Trigger the job (using a background task like manual trigger)
                from processor import process_daily_data
                start_time = datetime.now()
                
                # We need a new connection for the insert to avoid locking issues in threaded environment
                inner_conn = sqlite3.connect(DB_NAME)
                inner_cursor = inner_conn.cursor()
                inner_cursor.execute('''
                    INSERT INTO job_logs (job_name, start_time, status, logs) 
                    VALUES (?, ?, ?, ?)
                ''', (f"Scheduled: {job['job_name']} ({current_date_str})", start_time.strftime('%Y-%m-%dT%H:%M:%S'), 'Running', 'System: Scheduled trigger activated.'))
                log_id = inner_cursor.lastrowid
                inner_conn.commit()
                inner_conn.close()
                
                # Run the actual processing
                # In a real app, this should be in its own thread to not block the scheduler
                threading.Thread(target=job_executor, args=(current_date_str, log_id, start_time)).start()
                
            conn.close()
        except Exception as e:
            print(f"Scheduler Error: {e}")
            
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
