import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            progress REAL DEFAULT 0.0,
            step TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def update_job_status(job_id, status=None, progress=None, step=None):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    try:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        if step:
            updates.append("step = ?")
            params.append(step)
            
        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        params.append(job_id)
        
        cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()