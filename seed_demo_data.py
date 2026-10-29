"""
Load demo data into the configured database (PostgreSQL, or the SQLite
fallback).  Safe to run more than once - it only inserts, never deletes.

    python seed_demo_data.py
"""
from db.db import get_connection
from db.seed import seed_demo_data


if __name__ == "__main__":
    conn = get_connection()
    try:
        result = seed_demo_data(conn)
    finally:
        conn.close()
    print(result["message"])
    for table, count in result["added"].items():
        print(f"  {table:<16} +{count}")
