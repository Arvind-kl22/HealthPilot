"""
Database Schema Setup Script for HealthPilot

- Creates the database if it does not exist
- Executes all .sql files in the database/ folder (schema.sql, ambulance_schema.sql)
- Only schema and table definitions are applied (no sample data)
"""
import os
import mysql.connector

DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "healthpilot"),
}

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")

# Ensure database exists
CREATE_DB_SQL = "CREATE DATABASE IF NOT EXISTS healthpilot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
USE_DB_SQL = "USE healthpilot;"


def run_sql_file(cursor, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)


def main():
    # Connect without database to create it if needed
    conn = mysql.connector.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
    )
    cursor = conn.cursor()
    try:
        cursor.execute(CREATE_DB_SQL)
        cursor.execute(USE_DB_SQL)
        # Run all .sql files in database folder
        for fname in ["schema.sql", "ambulance_schema.sql"]:
            fpath = os.path.join(DB_DIR, fname)
            if os.path.exists(fpath):
                print(f"Applying {fname} ...")
                run_sql_file(cursor, fpath)
        conn.commit()
        print("Database schema updated successfully.")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
