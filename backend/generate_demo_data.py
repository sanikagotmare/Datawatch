"""
DataWatch Demo Data Generator
==============================
Generates realistic messy datasets for demonstrating DataWatch features.

Usage:
    cd backend
    python generate_demo_data.py

Generates 4 CSV files in ../sample-data/:
  1. sales_data.csv         - Sales records with missing values, negatives, outliers
  2. customer_data.csv      - Customer records with PII fields and duplicates
  3. inventory_data.csv     - Inventory with type issues and zero-variance columns
  4. hr_data.csv            - HR records with schema drift from previous version

Each file is designed to trigger specific DataWatch detection features.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import random

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save(df: pd.DataFrame, filename: str, description: str):
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False)
    print(f"✓ {filename:<30} {len(df):>5} rows  {len(df.columns):>3} cols  — {description}")


# ─── 1. SALES DATA ───────────────────────────────────────────────────────────
def generate_sales():
    """
    Triggers: missing values, negative amounts, outlier, duplicates, PII (email, phone)
    """
    n = 120
    products  = ["Laptop", "Mouse", "Keyboard", "Monitor", "USB Hub", "Webcam", "Headset"]
    statuses  = ["delivered", "shipped", "pending", "cancelled"]
    dates     = [datetime(2024, 1, 1) + timedelta(days=i % 90) for i in range(n)]

    df = pd.DataFrame({
        "order_id":       range(1001, 1001 + n),
        "customer_id":    [f"CUST{str(i).zfill(4)}" for i in range(n)],
        "customer_email": [f"user{i}@example.com" for i in range(n)],
        "phone":          [f"+91-{random.randint(7000000000,9999999999)}" for _ in range(n)],
        "product":        [random.choice(products) for _ in range(n)],
        "amount":         np.random.normal(15000, 8000, n).round(2),
        "quantity":       np.random.randint(1, 10, n),
        "order_date":     [d.strftime("%Y-%m-%d") for d in dates],
        "status":         [random.choice(statuses) for _ in range(n)],
    })

    # Inject issues
    # Missing customer_ids (15%)
    missing_idx = random.sample(range(n), int(n * 0.15))
    df.loc[missing_idx, "customer_id"] = None

    # Missing emails (10%)
    df.loc[random.sample(range(n), int(n * 0.10)), "customer_email"] = None

    # Negative amounts (invalid refunds) — 5 rows
    df.loc[random.sample(range(n), 5), "amount"] = -abs(np.random.normal(5000, 2000, 5)).round(2)

    # Extreme outlier — 1 row (fraud-like)
    df.loc[random.randint(0, n-1), "amount"] = 9999999.0

    # Duplicate rows — copy 8 rows
    duplicates = df.iloc[random.sample(range(n), 8)].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    save(df, "sales_data.csv", "Missing values + negatives + outlier + duplicates + PII")


# ─── 2. CUSTOMER DATA ────────────────────────────────────────────────────────
def generate_customers():
    """
    Triggers: PII (email, phone, aadhaar, dob), missing values, low cardinality
    """
    n = 200
    cities    = ["Mumbai", "Delhi", "Bangalore", "Pune", "Chennai", "Hyderabad"]
    segments  = ["Premium", "Standard", "Basic"]   # low cardinality

    df = pd.DataFrame({
        "customer_id":    [f"C{str(i).zfill(5)}" for i in range(n)],
        "name":           [f"Customer {i}" for i in range(n)],
        "email":          [f"customer{i}@domain.com" for i in range(n)],
        "phone":          [f"98{random.randint(10000000,99999999)}" for _ in range(n)],
        "aadhaar":        [f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}" for _ in range(n)],
        "dob":            [f"19{random.randint(60,99)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}" for _ in range(n)],
        "city":           [random.choice(cities) for _ in range(n)],
        "segment":        [random.choice(segments) for _ in range(n)],
        "lifetime_value": np.random.exponential(50000, n).round(2),
        "active":         ["Yes"] * n,   # zero variance — all same value
    })

    # Inject issues
    df.loc[random.sample(range(n), 30), "email"]   = None
    df.loc[random.sample(range(n), 20), "phone"]   = None
    df.loc[random.sample(range(n), 25), "aadhaar"] = None

    # Duplicate rows
    duplicates = df.iloc[random.sample(range(n), 10)].copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    save(df, "customer_data.csv", "PII fields (email, phone, aadhaar, dob) + zero variance + duplicates")


# ─── 3. INVENTORY DATA ───────────────────────────────────────────────────────
def generate_inventory():
    """
    Triggers: type issues (numeric stored as string), missing values, outliers
    """
    n = 150
    categories = ["Electronics", "Accessories", "Peripherals", "Networking"]
    warehouses = ["WH-Mumbai", "WH-Delhi", "WH-Bangalore"]

    # Deliberately store numbers as strings with formatting issues
    prices  = [f"{random.uniform(100, 50000):.2f}" for _ in range(n)]
    # Inject type issues: some with commas, some with currency symbols
    for i in random.sample(range(n), 20):
        val = random.uniform(1000, 99999)
        prices[i] = f"₹{val:,.0f}"     # currency symbol breaks numeric parsing
    for i in random.sample(range(n), 15):
        prices[i] = f"{random.uniform(1000,9999):,.0f}"  # comma in number

    stock_qty = list(np.random.randint(0, 500, n).astype(str))
    # Inject string values in numeric column
    for i in random.sample(range(n), 10):
        stock_qty[i] = "N/A"
    for i in random.sample(range(n), 5):
        stock_qty[i] = "Out of Stock"

    df = pd.DataFrame({
        "sku":            [f"SKU-{str(i).zfill(6)}" for i in range(n)],
        "product_name":   [f"Product {i}" for i in range(n)],
        "category":       [random.choice(categories) for _ in range(n)],
        "warehouse":      [random.choice(warehouses) for _ in range(n)],
        "price":          prices,          # TYPE ISSUE: should be float
        "stock_quantity": stock_qty,       # TYPE ISSUE: should be int
        "reorder_point":  np.random.randint(10, 100, n),
        "last_updated":   [f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}" for _ in range(n)],
    })

    # Missing values
    df.loc[random.sample(range(n), 20), "price"]         = None
    df.loc[random.sample(range(n), 15), "stock_quantity"] = None

    # Outlier stock quantity
    df.loc[random.randint(0, n-1), "reorder_point"] = 9999

    save(df, "inventory_data.csv", "Type issues (prices as strings) + missing values + outlier")


# ─── 4. HR DATA (with schema drift from v1) ──────────────────────────────────
def generate_hr_v1():
    """Previous schema — no performance_rating column, has salary column."""
    n = 80
    depts = ["Engineering", "Sales", "HR", "Finance", "Marketing"]

    df = pd.DataFrame({
        "employee_id":  [f"EMP{str(i).zfill(4)}" for i in range(n)],
        "name":         [f"Employee {i}" for i in range(n)],
        "department":   [random.choice(depts) for _ in range(n)],
        "salary":       np.random.normal(75000, 25000, n).round(0),  # column exists
        "age":          np.random.randint(22, 60, n),
        "years_exp":    np.random.randint(0, 30, n),
        "join_date":    [f"20{random.randint(10,23):02d}-{random.randint(1,12):02d}-01" for _ in range(n)],
    })
    save(df, "hr_data_v1.csv", "Upload this FIRST to establish schema baseline")


def generate_hr_v2():
    """
    Current schema — salary renamed to compensation, new performance_rating column.
    Triggers schema drift when uploaded after v1.
    """
    n = 85
    depts = ["Engineering", "Sales", "HR", "Finance", "Marketing", "Operations"]

    df = pd.DataFrame({
        "employee_id":       [f"EMP{str(i).zfill(4)}" for i in range(n)],
        "name":              [f"Employee {i}" for i in range(n)],
        "department":        [random.choice(depts) for _ in range(n)],
        "compensation":      np.random.normal(80000, 28000, n).round(0),  # RENAMED from salary
        "age":               np.random.randint(22, 62, n),
        "years_exp":         np.random.randint(0, 35, n),
        "join_date":         [f"20{random.randint(10,24):02d}-{random.randint(1,12):02d}-01" for _ in range(n)],
        "performance_rating": [random.choice(["A","B","C","D"]) for _ in range(n)],  # NEW column
    })

    # Missing values
    df.loc[random.sample(range(n), 12), "compensation"]      = None
    df.loc[random.sample(range(n), 8),  "performance_rating"] = None

    # Outlier age
    df.loc[random.randint(0, n-1), "age"] = 142

    save(df, "hr_data_v2.csv", "Upload AFTER v1 — triggers schema drift (salary→compensation, new column)")


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔧 DataWatch Demo Data Generator")
    print("=" * 60)
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}\n")

    generate_sales()
    generate_customers()
    generate_inventory()
    generate_hr_v1()
    generate_hr_v2()

    print("\n" + "=" * 60)
    print("✅ All demo files generated!\n")
    print("DEMO FLOW:")
    print("  1. Upload sales_data.csv      → see anomalies + PII + outlier")
    print("  2. Upload customer_data.csv   → see PII detection + zero variance")
    print("  3. Upload inventory_data.csv  → see type issue detection")
    print("  4. Upload hr_data_v1.csv      → establishes schema baseline")
    print("  5. Upload hr_data_v2.csv      → triggers schema drift alert")
    print("  6. Go to Self-Healing → upload sales_data.csv → heal → download")
    print("  7. Create a Pipeline → click Run Now → see real anomaly counts")
    print("=" * 60)
