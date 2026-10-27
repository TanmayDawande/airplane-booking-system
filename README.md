# SkyReserve - Airline Reservation System

**DBMS Laboratory Project | Assessments 8, 9 and 10 | Academic Term 2026**

SkyReserve is a MySQL-backed airline reservation application. It supports flight
search, an interactive cabin seat map, passenger booking, payment records,
booking cancellation, reports and a trigger-based audit trail. The Flask app
and MySQL Workbench use the same database, so every row created by the website
can be inspected directly in Workbench.

---

## 1. Quick start

### Step 1 - Install the Python packages

```bash
pip install -r requirements.txt
```

### Step 2 - Create the database in MySQL Workbench

1. Open **MySQL Workbench**.
2. Connect to the local MySQL server on **localhost:3306** as `root`.
3. Open `database/airline_db.sql`.
4. Execute the whole file (lightning icon, or `Ctrl+Shift+Enter`).
5. Refresh the **SCHEMAS** panel and select `airline_db`.

The script creates:

- the `airline_db` schema
- 10 normalized tables with foreign keys and indexes
- the demo data (current bookings/passengers included)
- 8 triggers, 2 stored procedures and 4 views
- the application user `airline_app` with password `airline123`

The demo flights are dated **31 October 2026**, so they remain upcoming for the
29 October live presentation. The migration kept the current passengers and
bookings; two cancelled SQLite test bookings whose passenger rows had already
been deleted were skipped because MySQL enforces foreign keys.

> **Warning:** `airline_db.sql` starts with `DROP DATABASE IF EXISTS airline_db`.
> Running it again resets the database to the demo data. Do not run it while the
> app is in the middle of a demonstration.

### Step 3 - Start the application

```bash
python app.py
```

Open **http://127.0.0.1:5000**.

### Demo accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `password123` |
| Staff | `staff_flight` | `password123` |
| Passenger | `tanmay` | `password123` |
| Passenger | `aditi` | `password123` |

The login screen also has a **Create account** option for a new passenger.

---

## 2. Using MySQL Workbench

The website does not write to a SQLite file. It writes to the MySQL schema
`airline_db`. To inspect the live data:

1. Open MySQL Workbench and connect to `localhost:3306`.
2. Double-click **`airline_db`** in the SCHEMAS panel.
3. Open a new query tab and run any of these:

```sql
SELECT * FROM flights;
SELECT * FROM passengers ORDER BY passenger_id DESC;
SELECT * FROM bookings ORDER BY booking_id DESC;
SELECT * FROM payments ORDER BY payment_id DESC;
SELECT * FROM audit_logs ORDER BY log_id DESC;
```

`database/demo_queries.sql` contains the full set of assessment queries
(joins, `GROUP BY`, `HAVING`, subqueries, occupancy, views and procedures).
Open that file and run statements one at a time with `Ctrl+Enter`.

**Important:** opening a `.sql` file only shows SQL text. It does not show live
table data by itself. You must be connected to `airline_db` and execute a
`SELECT` statement.

### Verify the timezone in Workbench

```sql
SELECT NOW() AS current_time_ist, @@session.time_zone AS session_timezone;
```

The app sets `time_zone = '+05:30'` on every connection, so all generated
`booking_date`, `payment_time`, `created_at` and `audit_logs.timestamp` values
are stored in **IST (Asia/Kolkata)**.

---

## 3. Project structure

```text
airplaneSystem2/
|-- app.py                         # Flask routes, page routes and JSON APIs
|-- models.py                      # SQL data access and business rules
|-- database.py                    # MySQL connection, transactions, SQL studio
|-- timeutils.py                   # IST parsing and display helpers
|-- config.py                      # MySQL and Flask configuration
|-- requirements.txt
|-- database/
|   |-- airline_db.sql             # ONE file to run in MySQL Workbench
|   `-- demo_queries.sql           # Workbench queries for the three assessments
|-- public/static/
|   |-- css/style.css
|   `-- js/app.js
|-- templates/
|   |-- base.html                  # Header, IST clock, database status
|   |-- login.html                 # Sign in / create account
|   |-- index.html                 # Search and featured departures
|   |-- flights.html               # Filters and results
|   |-- booking.html               # Seat map, passenger form, payment
|   |-- ticket.html                # Boarding pass and transaction proof
|   |-- my_bookings.html           # PNR lookup, seat change, cancellation
|   |-- admin.html                 # CRUD and audit log
|   |-- reports.html               # Joins, HAVING, subquery, occupancy
|   |-- db_studio.html             # In-app SQL console
|   `-- assessment_guide.html      # Video cue cards
`-- README.md
```

---

## 4. What to show in each assessment video

The three videos must be different. The full cue cards are on `/guide`.

### Assessment 8 - front end and basic connectivity

- Introduce **SkyReserve** and its purpose.
- Show the home page, search form, flights page, seat map and Admin page.
- Click the **MySQL** badge and show `localhost:3306`, `airline_db` and the
  number of tables.
- Sign in as `admin`, open **Admin -> Add passenger**, submit a new passenger,
  and show the returned passenger ID and timestamp.
- Verify the row in Workbench with:
  `SELECT * FROM passengers ORDER BY passenger_id DESC LIMIT 5;`

### Assessment 9 - database operations and back end

- Show the back-end code: `app.py` route -> `models.py` parameterized SQL ->
  `database.py` PyMySQL connection.
- On Admin, **INSERT** a new flight `AI-999`; **UPDATE** its fare/status;
  **DELETE** it. Verify each step in Workbench.
- On Reports, show the five-table INNER JOIN, `GROUP BY + HAVING`, the nested
  subquery and the occupancy calculation.
- Show the **Audit log** tab to prove that triggers record the operations.

### Assessment 10 - complete workflow

- Sign in (show a wrong password first, then `tanmay` / `password123`).
- Search BOM -> DEL, choose a flight and an open seat.
- Show an invalid input or occupied-seat error, then enter valid details.
- Confirm the booking. Show the boarding pass and PNR.
- Verify the booking + payment rows in Workbench using the generated PNR.
- Cancel the booking and verify that the status becomes `CANCELLED`, the payment
  becomes `REFUNDED`, and the seat is available again.
- Finish with one report and a conclusion.

### Recording checklist

- Both teammates appear and explain their own contribution.
- Face and screen are visible together.
- Three separate videos, named with the team and assessment number.
- Actual application execution only; no slides or screenshots.
- Instructor has view permission to all three Drive links.
- Test the application again on 29.10 before the live verification.

---

## 5. Configuration

The defaults in `config.py` are:

```python
DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'airline_app'
DB_PASSWORD = 'airline123'
DB_NAME = 'airline_db'
```

You can override them with environment variables without editing the file:

```powershell
$env:DB_USER = 'root'
$env:DB_PASSWORD = 'your-mysql-password'
python app.py
```

The app refuses to start if it cannot connect to MySQL, and prints the exact
setup file to run.

---

## 6. Troubleshooting

**`Access denied for user 'airline_app'`**

The setup SQL was not executed, or the app user was not created. Run
`database/airline_db.sql` again as root.

**Workbench says "No database selected"**

Double-click `airline_db` in the SCHEMAS panel, or run `USE airline_db;`.

**The page shows old data after running the setup file**

The setup file recreates the database. Run it again and refresh Workbench.

**The app shows a UTC time**

Check that the app was restarted after the configuration changes, and run:

```sql
SELECT NOW(), @@session.time_zone;
```

The app connection sets `+05:30`; Workbench uses your local session. All new
rows should match the IST clock in the website header.
