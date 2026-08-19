import sqlite3
import random
import datetime
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
db_name = os.path.join(PROJECT_ROOT, "shop_oltp_p1.db")

def generate_db():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            patient_id TEXT,
            department TEXT,
            vital_sign_reading REAL,
            status TEXT,
            order_date TEXT
        )
    ''')
    cursor.execute("DELETE FROM orders") # ensure empty if run again
    
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "David", "Eve", "Frank"]
    last_names = ["Smith", "Doe", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    departments = ["cardiology", "oncology", "neurology", "pediatrics", "emergency"]
    
    start_date = datetime.datetime(2026, 1, 1)
    
    rows = []
    
    for i in range(1, 4001):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        pid = f"PID-{random.randint(10000, 99999)}"
        dept = random.choice(departments)
        vital = round(random.uniform(30.0, 120.0), 2)
        status = "COMPLETED"
        r_days = random.randint(0, 365)
        dt = start_date + datetime.timedelta(days=r_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        order_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Inject anomalies (~10% total over the different fields)
        anomaly_chance = random.random()
        if anomaly_chance < 0.033:
            # Null patient ID
            pid = None
        elif anomaly_chance < 0.066:
            # Messy whitespace and casing for department
            scrambled_casing = "".join(random.choice([k.upper(), k.lower()]) for k in dept)
            spaces = "   " * random.randint(1, 4)
            dept = f" {spaces} {scrambled_casing} {spaces} "
        elif anomaly_chance < 0.10:
            # Negative vital reading
            vital = -abs(vital)
        
        rows.append((name, pid, dept, vital, status, order_date))
    
    cursor.executemany('''
        INSERT INTO orders (patient_name, patient_id, department, vital_sign_reading, status, order_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', rows)
    
    conn.commit()
    conn.close()
    print(f"Generated {len(rows)} records in {db_name}")

if __name__ == "__main__":
    generate_db()
