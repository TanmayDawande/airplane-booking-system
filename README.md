# Airline Reservation System (DBMS Project)
### Database Management Systems Laboratory Project
**Academic Term 2026** • Prepared for Assessments 8, 9, and 10 Demonstration & Live Verification

---

## 1. Project Overview & Architecture
The **Airline Reservation System** is a full-stack relational database application modeled in **3rd Normal Form (3NF)**. It manages flight schedules, aircraft seat inventories, passenger registrations, multi-class ticketing, financial transactions, and operational analytics.

### Technical Stack
- **Front-End**: Semantic HTML5, clean CSS (inspired by Google Flights & Skyscanner), vanilla JavaScript (fast, responsive, zero bulky framework dependencies).
- **Back-End**: Python 3.10+ with Flask RESTful APIs, parameterized SQL execution, and transactional consistency.
- **Database**:
  - **MySQL 8.0** (Supported on Port 3306 with MySQL Workbench)
  - **SQLite Dual-Engine** (Built-in zero-config embedded database fallback)
- **Database Objects**: 10 normalized tables, foreign key constraints, 2 triggers, 2 stored procedures, 4 analytical views, and indexes.

---

## 2. File & Directory Structure
```
g:\airplaneSystem2\
├── app.py                      # Flask web server & RESTful endpoints
├── database.py                 # Dual database connector (MySQL 8.0 + SQLite)
├── models.py                   # Data Access Layer & 3NF business logic
├── config.py                   # App configuration & credentials
├── setup_database.py           # Database initializer & schema seed tool
├── airline_db.sqlite3          # Pre-seeded SQLite database file
├── sql/
│   ├── 01_schema.sql           # DDL: 10 normalized tables with constraints
│   ├── 02_procedures_triggers.sql # Triggers, stored procedures, and views
│   ├── 03_sample_data.sql      # Seed data: airports, airlines, aircrafts, flights
│   └── 04_assessment_queries.sql  # SQL demonstration queries for video recordings
├── static/
│   ├── css/style.css           # Clean, modern stylesheet
│   └── js/app.js               # Interactive seat selection, modal dialogs & API requests
├── templates/
│   ├── base.html               # Base layout with navigation and DB status badge
│   ├── index.html              # Flight search & metric summary cards
│   ├── flights.html            # Flight listings with sidebar filters
│   ├── booking.html            # Booking wizard with interactive aircraft cabin seat map
│   ├── ticket.html             # Printable Boarding Pass & E-Ticket with verification box
│   ├── my_bookings.html        # PNR lookup, seat modification, and cancellation
│   ├── admin.html              # Full CRUD Portal (INSERT, SELECT, UPDATE, DELETE)
│   ├── reports.html            # Analytical SQL queries (JOINs, GROUP BY, subqueries)
│   ├── db_studio.html          # Built-in live Database Studio & SQL query runner
│   └── assessment_guide.html   # Teleprompter cue cards for Assessments 8, 9, and 10
└── README.md                   # Documentation & setup guide
```

---

## 3. How to Run the Application

### Running with SQLite (Immediate, Zero Configuration)
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser. All tables and sample data are pre-populated and ready to use.

### Running with MySQL 8.0
1. Set up the schema and seed data in your local MySQL instance:
   ```bash
   python setup_database.py --engine=mysql --user=root --password=YOUR_PASSWORD
   ```
2. Or in the running web application, click the **DB Status Badge** in the top header, select **MySQL**, enter your credentials, and click **Save & Connect**.

---

## 4. Assessment Video Recording Guide

### Assessment 8: Front-End Design & Basic Database Connectivity (~3 Minutes)
- **Introduction**: Introduce teammates and state project title and purpose.
- **Interface Walkthrough**: Show the home page, flight search controls, and scheduled flights table.
- **Database Connectivity**: Click the green **DB Status Badge** in the top navigation bar to show live engine status, host, and active table count.
- **Insert a Record**:
  - Click the **"A8 Proof"** button on the header.
  - Fill in passenger details (e.g., *Rohit Verma, rohit.verma@example.com, +91-9876543210, Passport: Z1234567*).
  - Click **"Execute INSERT & Retrieve"**.
- **Retrieve & Verify**:
  - Show the confirmation panel displaying the generated primary key (`passenger_id`) retrieved from the database.
  - Switch to **DB Studio** ([/db-studio](http://127.0.0.1:5000/db-studio)) and run:
    ```sql
    SELECT * FROM passengers WHERE email = 'rohit.verma@example.com';
    ```
    Verify that the row physically exists in the database table.

---

### Assessment 9: Database Operations & Back-End Implementation (~4 Minutes)
- **Back-End Architecture**: Explain that Flask routes handle API requests and execute parameterized SQL queries to prevent SQL injection and ensure transaction safety.
- **CRUD Operations**:
  - **INSERT**: On the **Admin CRUD** page ([/admin](http://127.0.0.1:5000/admin)), click **"Schedule Flight (INSERT)"**. Add flight `AI-999` (BOM &rarr; DEL, Fare: ₹5,200). Verify it appears in the table.
  - **SELECT**: Use the search and filter options on the Flights page.
  - **UPDATE**: On flight `AI-999`, click **Edit**. Update the fare to ₹5,600 and change status to `DELAYED`. Show the updated values in the table and verify via SQL:
    ```sql
    SELECT flight_number, base_fare, status FROM flights WHERE flight_number = 'AI-999';
    ```
  - **DELETE**: Click **Delete** on flight `AI-999`. Verify that it is removed from the table and querying the database returns 0 rows.
- **Important SQL Queries** (Available in **Reports** [/reports](http://127.0.0.1:5000/reports)):
  - **5-Table INNER JOIN**: Joining `bookings`, `passengers`, `flights`, `airlines`, and `airports`.
  - **GROUP BY with HAVING**: Calculating total bookings, gross revenue, and average ticket price by airline (`HAVING gross_revenue > 5000`).
  - **Nested Subquery**: Identifying high-value passengers whose booking exceeds the system average fare.
  - **Database Triggers**: View the `audit_logs` tab in the Admin portal to prove triggers automatically record insert and update events.

---

### Assessment 10: Complete Project Workflow & Functional Validation (~5 Minutes)
- **End-to-End Workflow**:
  1. From Home, search flights from **Mumbai (BOM)** to **New Delhi (DEL)**.
  2. Select Flight **AI-101**.
  3. **Interactive Cabin Seat Map**: View occupied seats (red) and pick an available seat (e.g., **11C**). Observe dynamic price updates.
  4. Fill in passenger details and select payment method (UPI / Card).
  5. Click **"Confirm & Pay"** to execute the atomic transaction.
- **Input Validation**: Show that submitting invalid input or selecting an already occupied seat is properly caught and blocked.
- **Output Generation**: Inspect the generated **Boarding Pass & E-Ticket** with unique PNR, seat 11C, departure time, and barcode. Click **Print Boarding Pass**.
- **ACID Transaction Verification**:
  - Inspect the *Database Transaction Verification* box on the boarding pass.
  - Run the query in DB Studio:
    ```sql
    SELECT b.pnr, b.seat_number, b.status, p.amount, p.payment_status 
    FROM bookings b JOIN payments p ON b.booking_id = p.booking_id 
    WHERE b.pnr = '<GENERATED_PNR>';
    ```
- **Cancellation & Seat Release**:
  - Go to **Manage PNR** ([/my-bookings](http://127.0.0.1:5000/my-bookings)), enter the PNR, and click **Cancel Booking**.
  - Verify that the status updates to `CANCELLED`, payment is marked `REFUNDED`, and the seat becomes immediately re-available on the flight seat map.

---

## 5. Sample Data for Demonstrations
- **Sample PNRs**: `AERO101A`, `AERO101B`, `AERO205C`, `AERO812D`, `AERO501E`
- **Active Flights**: `AI-101` (BOM-DEL), `AI-102` (DEL-BOM), `6E-205` (DEL-BLR), `UK-812` (BOM-BLR), `EK-501` (BOM-DXB)
- **Airports**: DEL (Delhi), BOM (Mumbai), BLR (Bengaluru), HYD (Hyderabad), DXB (Dubai), LHR (London), JFK (New York)
