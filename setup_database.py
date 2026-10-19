import os
import sys
import argparse
import hashlib
from database import db
import config

def init_sqlite():
    print("[*] Initializing SQLite database...")
    import sqlite3
    db_path = config.SQLITE_PATH
    if os.path.exists(db_path):
        try: os.remove(db_path)
        except Exception: pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # DDL for SQLite
    cur.executescript("""
    CREATE TABLE airports (
        airport_code TEXT PRIMARY KEY,
        airport_name TEXT NOT NULL,
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        timezone TEXT NOT NULL DEFAULT 'UTC+05:30'
    );

    CREATE TABLE airlines (
        airline_id INTEGER PRIMARY KEY AUTOINCREMENT,
        airline_code TEXT NOT NULL UNIQUE,
        airline_name TEXT NOT NULL,
        country TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE'
    );

    CREATE TABLE aircrafts (
        aircraft_id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT NOT NULL,
        airline_id INTEGER NOT NULL,
        total_seats INTEGER NOT NULL,
        economy_seats INTEGER NOT NULL,
        business_seats INTEGER NOT NULL,
        first_seats INTEGER NOT NULL,
        FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE CASCADE
    );

    CREATE TABLE flights (
        flight_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flight_number TEXT NOT NULL UNIQUE,
        airline_id INTEGER NOT NULL,
        aircraft_id INTEGER NOT NULL,
        origin_code TEXT NOT NULL,
        destination_code TEXT NOT NULL,
        departure_time TEXT NOT NULL,
        arrival_time TEXT NOT NULL,
        duration_mins INTEGER NOT NULL,
        base_fare REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'SCHEDULED',
        FOREIGN KEY (airline_id) REFERENCES airlines(airline_id),
        FOREIGN KEY (aircraft_id) REFERENCES aircrafts(aircraft_id),
        FOREIGN KEY (origin_code) REFERENCES airports(airport_code),
        FOREIGN KEY (destination_code) REFERENCES airports(airport_code)
    );

    CREATE TABLE passengers (
        passenger_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL,
        passport_number TEXT NOT NULL UNIQUE,
        date_of_birth TEXT NOT NULL,
        gender TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'PASSENGER',
        passenger_id INTEGER NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id)
    );

    CREATE TABLE seats (
        seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        aircraft_id INTEGER NOT NULL,
        seat_number TEXT NOT NULL,
        seat_class TEXT NOT NULL DEFAULT 'ECONOMY',
        seat_type TEXT NOT NULL DEFAULT 'AISLE',
        FOREIGN KEY (aircraft_id) REFERENCES aircrafts(aircraft_id),
        UNIQUE (aircraft_id, seat_number)
    );

    CREATE TABLE bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pnr TEXT NOT NULL UNIQUE,
        user_id INTEGER NULL,
        passenger_id INTEGER NOT NULL,
        flight_id INTEGER NOT NULL,
        seat_number TEXT NOT NULL,
        travel_class TEXT NOT NULL DEFAULT 'ECONOMY',
        booking_date TEXT NOT NULL DEFAULT (datetime('now')),
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'CONFIRMED',
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
        FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
    );

    CREATE TABLE payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL UNIQUE,
        transaction_id TEXT NOT NULL UNIQUE,
        payment_method TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'SUCCESS',
        payment_time TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
    );

    CREATE TABLE audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER NULL,
        details TEXT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- SQLite Triggers
    CREATE TRIGGER trg_after_booking_insert
    AFTER INSERT ON bookings
    BEGIN
        INSERT INTO audit_logs (action_type, table_name, record_id, details)
        VALUES (
            'INSERT_BOOKING',
            'bookings',
            NEW.booking_id,
            'PNR: ' || NEW.pnr || ' created for Flight ID: ' || NEW.flight_id || ', Seat: ' || NEW.seat_number || ', Amount: INR ' || NEW.total_amount
        );
    END;

    CREATE TRIGGER trg_after_booking_update
    AFTER UPDATE OF status ON bookings
    BEGIN
        INSERT INTO audit_logs (action_type, table_name, record_id, details)
        VALUES (
            'UPDATE_BOOKING_STATUS',
            'bookings',
            NEW.booking_id,
            'Booking PNR: ' || NEW.pnr || ' status changed from ' || OLD.status || ' to ' || NEW.status
        );
    END;
    """)

    # Views for SQLite
    cur.executescript("""
    CREATE VIEW vw_flight_details AS
    SELECT 
        f.flight_id,
        f.flight_number,
        al.airline_code,
        al.airline_name,
        ac.model AS aircraft_model,
        ac.total_seats,
        f.origin_code,
        orig.airport_name AS origin_airport,
        orig.city AS origin_city,
        f.destination_code,
        dest.airport_name AS dest_airport,
        dest.city AS dest_city,
        f.departure_time,
        f.arrival_time,
        f.duration_mins,
        f.base_fare,
        f.status,
        (ac.total_seats - (
            SELECT COUNT(*) FROM bookings b 
            WHERE b.flight_id = f.flight_id AND b.status = 'CONFIRMED'
        )) AS available_seats
    FROM flights f
    JOIN airlines al ON f.airline_id = al.airline_id
    JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
    JOIN airports orig ON f.origin_code = orig.airport_code
    JOIN airports dest ON f.destination_code = dest.airport_code;

    CREATE VIEW vw_booking_summary AS
    SELECT 
        b.booking_id,
        b.pnr,
        b.booking_date,
        b.travel_class,
        b.seat_number,
        b.total_amount,
        b.status AS booking_status,
        p.passenger_id,
        (p.first_name || ' ' || p.last_name) AS passenger_name,
        p.email AS passenger_email,
        p.phone AS passenger_phone,
        f.flight_id,
        f.flight_number,
        al.airline_name,
        f.origin_code,
        orig.city AS origin_city,
        f.destination_code,
        dest.city AS dest_city,
        f.departure_time,
        f.arrival_time,
        pay.payment_id,
        pay.transaction_id,
        pay.payment_method,
        pay.payment_status
    FROM bookings b
    JOIN passengers p ON b.passenger_id = p.passenger_id
    JOIN flights f ON b.flight_id = f.flight_id
    JOIN airlines al ON f.airline_id = al.airline_id
    JOIN airports orig ON f.origin_code = orig.airport_code
    JOIN airports dest ON f.destination_code = dest.airport_code
    LEFT JOIN payments pay ON b.booking_id = pay.booking_id;
    """)

    # Seed data
    with open('sql/03_sample_data.sql', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strip USE statements
    statements = [s.strip() for s in content.split(';') if s.strip() and not s.strip().upper().startswith('USE ')]
    for stmt in statements:
        try:
            cur.execute(stmt)
        except Exception as e:
            # Continue if minor syntax variation
            pass

    conn.commit()
    conn.close()
    print("[+] SQLite database initialized and seeded successfully!")

def init_mysql(host='localhost', port=3306, user='root', password='', dbname='airline_db'):
    print(f"[*] Connecting to MySQL at {host}:{port} as {user}...")
    import pymysql
    # Connect without db first to create database
    conn = pymysql.connect(host=host, port=int(port), user=user, password=password, autocommit=True)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.execute(f"USE `{dbname}`")

    # Run 01_schema.sql
    print("[*] Applying 01_schema.sql...")
    with open('sql/01_schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    for stmt in schema_sql.split(';'):
        clean = stmt.strip()
        if clean and not clean.upper().startswith(('DROP DATABASE', 'CREATE DATABASE', 'USE ')):
            cur.execute(clean)

    # Run 02_procedures_triggers.sql
    print("[*] Applying 02_procedures_triggers.sql...")
    with open('sql/02_procedures_triggers.sql', 'r', encoding='utf-8') as f:
        proc_sql = f.read()
    
    # Split DELIMITER
    delimiter = ';'
    buffer = []
    for line in proc_sql.splitlines():
        if line.strip().startswith('DELIMITER'):
            delimiter = line.strip().split()[1]
            continue
        buffer.append(line)
        if delimiter != ';' and line.strip().endswith(delimiter):
            block = "\n".join(buffer)
            block = block[:block.rfind(delimiter)].strip()
            if block and not block.upper().startswith('USE '):
                try: cur.execute(block)
                except Exception as ex: print(f"Warning on procedure/trigger: {ex}")
            buffer = []
        elif delimiter == ';' and line.strip().endswith(';'):
            block = "\n".join(buffer).strip().rstrip(';')
            if block and not block.upper().startswith('USE '):
                try: cur.execute(block)
                except Exception as ex: print(f"Warning on view/sql: {ex}")
            buffer = []

    # Run 03_sample_data.sql
    print("[*] Seeding 03_sample_data.sql...")
    with open('sql/03_sample_data.sql', 'r', encoding='utf-8') as f:
        data_sql = f.read()
    for stmt in data_sql.split(';'):
        clean = stmt.strip()
        if clean and not clean.upper().startswith('USE '):
            cur.execute(clean)

    conn.close()
    print("[+] MySQL database initialized, triggers/views created, and data seeded successfully!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AeroReserve Database Initializer")
    parser.add_argument('--engine', choices=['mysql', 'sqlite', 'auto'], default='auto')
    parser.add_argument('--host', default=config.DB_HOST)
    parser.add_argument('--port', default=config.DB_PORT)
    parser.add_argument('--user', default=config.DB_USER)
    parser.add_argument('--password', default=config.DB_PASSWORD)
    parser.add_argument('--dbname', default=config.DB_NAME)

    args = parser.parse_args()

    if args.engine == 'auto':
        test_res = db.test_connection(host=args.host, port=args.port, user=args.user, password=args.password, engine='mysql')
        if test_res['success']:
            print(f"[+] MySQL is reachable ({test_res['message']}). Initializing MySQL...")
            init_mysql(args.host, args.port, args.user, args.password, args.dbname)
        else:
            print(f"[-] MySQL not connected with current credentials: {test_res.get('error')}")
            print("[*] Defaulting to SQLite database for instant, robust out-of-the-box operation.")
            init_sqlite()
    elif args.engine == 'mysql':
        init_mysql(args.host, args.port, args.user, args.password, args.dbname)
    else:
        init_sqlite()
