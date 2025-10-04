"""
Run this script once to initialize the database tables for MedBuddy.
Usage:
    python3 init_db.py
"""
from app import create_db_and_tables

if __name__ == "__main__":
    print("Initializing database tables...")
    create_db_and_tables()
    print("Database tables created.")
