import hashlib
import random
import string
import re
from datetime import datetime
from database import db

# ------------------------------------------------------------------------------
# Security & Hashing Helpers
# ------------------------------------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_pnr():
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=5))
    return f"AER{suffix}"

def generate_txn_id():
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f"TXN_{suffix}"

# ------------------------------------------------------------------------------
# User & Authentication Model
# ------------------------------------------------------------------------------
class UserModel:
    @staticmethod
    def authenticate(username, password):
        pwd_hash = hash_password(password)
        query = "SELECT user_id, username, role, passenger_id FROM users WHERE username = %s AND password_hash = %s"
        return db.execute_query(query, (username, pwd_hash), fetch='one')

    @staticmethod
    def register(username, password, first_name, last_name, email, phone, passport_number, dob, gender, role='PASSENGER'):
        # Check existing user
        existing_user = db.execute_query("SELECT user_id FROM users WHERE username = %s", (username,), fetch='one')
        if existing_user:
            raise ValueError(f"Username '{username}' already exists.")

        # Check existing passenger email
        existing_email = db.execute_query("SELECT passenger_id FROM passengers WHERE email = %s", (email,), fetch='one')
        if existing_email:
            passenger_id = existing_email['passenger_id']
        else:
            passenger_query = """
                INSERT INTO passengers (first_name, last_name, email, phone, passport_number, date_of_birth, gender)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            passenger_id = db.execute_query(
                passenger_query,
                (first_name, last_name, email, phone, passport_number, dob, gender),
                commit=True
            )

        # Create user account
        user_query = "INSERT INTO users (username, password_hash, role, passenger_id) VALUES (%s, %s, %s, %s)"
        user_id = db.execute_query(user_query, (username, hash_password(password), role, passenger_id), commit=True)
        return {"user_id": user_id, "username": username, "role": role, "passenger_id": passenger_id}

    @staticmethod
    def get_by_id(user_id):
        query = """
            SELECT u.user_id, u.username, u.role, u.passenger_id,
                   p.first_name, p.last_name, p.email, p.phone, p.passport_number
            FROM users u
            LEFT JOIN passengers p ON u.passenger_id = p.passenger_id
            WHERE u.user_id = %s
        """
        return db.execute_query(query, (user_id,), fetch='one')

# ------------------------------------------------------------------------------
# Passenger Model (Assessment 8 & 9 CRUD)
# ------------------------------------------------------------------------------
class PassengerModel:
    @staticmethod
    def create(first_name, last_name, email, phone, passport_number, dob, gender):
        # Validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email format.")
        if len(phone) < 8:
            raise ValueError("Invalid phone number format.")
        if not passport_number or len(passport_number.strip()) < 4:
            raise ValueError("Invalid passport/ID number.")

        query = """
            INSERT INTO passengers (first_name, last_name, email, phone, passport_number, date_of_birth, gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        pid = db.execute_query(query, (first_name, last_name, email, phone, passport_number, dob, gender), commit=True)
        return PassengerModel.get_by_id(pid)

    @staticmethod
    def get_by_id(passenger_id):
        return db.execute_query("SELECT * FROM passengers WHERE passenger_id = %s", (passenger_id,), fetch='one')

    @staticmethod
    def get_all(limit=50):
        return db.execute_query("SELECT * FROM passengers ORDER BY passenger_id DESC LIMIT %s", (limit,))

    @staticmethod
    def search(term):
        term_param = f"%{term}%"
        query = """
            SELECT * FROM passengers 
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR passport_number LIKE %s
            ORDER BY passenger_id DESC LIMIT 50
        """
        return db.execute_query(query, (term_param, term_param, term_param, term_param))

    @staticmethod
    def update(passenger_id, first_name, last_name, email, phone, passport_number):
        query = """
            UPDATE passengers 
            SET first_name = %s, last_name = %s, email = %s, phone = %s, passport_number = %s
            WHERE passenger_id = %s
        """
        db.execute_query(query, (first_name, last_name, email, phone, passport_number, passenger_id), commit=True)
        return PassengerModel.get_by_id(passenger_id)

    @staticmethod
    def delete(passenger_id):
        # Check if active bookings exist
        bookings = db.execute_query("SELECT COUNT(*) AS c FROM bookings WHERE passenger_id = %s AND status = 'CONFIRMED'", (passenger_id,), fetch='one')
        if bookings and bookings['c'] > 0:
            raise ValueError("Cannot delete passenger with active confirmed bookings.")
        return db.execute_query("DELETE FROM passengers WHERE passenger_id = %s", (passenger_id,), commit=True)

# ------------------------------------------------------------------------------
# Flight Model (Search, Schedules, Seat Map)
# ------------------------------------------------------------------------------
class FlightModel:
    @staticmethod
    def search(origin=None, destination=None, travel_date=None, travel_class='ECONOMY', max_price=None):
        query = """
            SELECT 
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
                f.duration_mins, f.base_fare, f.status,
                al.airline_id, al.airline_code, al.airline_name,
                ac.aircraft_id, ac.model AS aircraft_model, ac.total_seats,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport, orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport, dest.city AS dest_city,
                (ac.total_seats - (
                    SELECT COUNT(*) FROM bookings b WHERE b.flight_id = f.flight_id AND b.status = 'CONFIRMED'
                )) AS available_seats
            FROM flights f
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            WHERE 1=1
        """
        params = []

        if origin:
            query += " AND f.origin_code = %s"
            params.append(origin)

        if destination:
            query += " AND f.destination_code = %s"
            params.append(destination)

        if travel_date:
            # Match date part of departure_time
            query += " AND DATE(f.departure_time) = DATE(%s)"
            params.append(travel_date)

        if max_price:
            query += " AND f.base_fare <= %s"
            params.append(float(max_price))

        query += " ORDER BY f.departure_time ASC"
        return db.execute_query(query, tuple(params))

    @staticmethod
    def get_by_id(flight_id):
        query = """
            SELECT 
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
                f.duration_mins, f.base_fare, f.status,
                al.airline_id, al.airline_code, al.airline_name,
                ac.aircraft_id, ac.model AS aircraft_model, ac.total_seats,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport, orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport, dest.city AS dest_city,
                (ac.total_seats - (
                    SELECT COUNT(*) FROM bookings b WHERE b.flight_id = f.flight_id AND b.status = 'CONFIRMED'
                )) AS available_seats
            FROM flights f
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            WHERE f.flight_id = %s
        """
        return db.execute_query(query, (flight_id,), fetch='one')

    @staticmethod
    def get_seat_rows(flight_id):
        """
        Generates realistic 24-row cabin layout (A B C | Aisle | D E F)
        with First, Business, and Economy classes and Exit Rows.
        """
        import re
        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            return []

        # Get all defined seats for this aircraft
        seats_query = "SELECT * FROM seats WHERE aircraft_id = %s"
        aircraft_seats = db.execute_query(seats_query, (flight['aircraft_id'],))

        # Get currently booked seats for this flight
        booked_query = "SELECT seat_number FROM bookings WHERE flight_id = %s AND status = 'CONFIRMED'"
        booked_rows = db.execute_query(booked_query, (flight_id,))
        booked_seat_numbers = set(r['seat_number'] for r in booked_rows)

        def parse_seat(s):
            m = re.match(r'(\d+)([A-Z])', s['seat_number'])
            r = int(m.group(1)) if m else 0
            c = m.group(2) if m else ''
            return r, c

        # If aircraft has no pre-populated seats, generate standard 24 rows
        if not aircraft_seats:
            aircraft_seats = []
            for r in range(1, 25):
                s_class = 'FIRST' if r <= 2 else ('BUSINESS' if r <= 5 else 'ECONOMY')
                for l in ['A', 'B', 'C', 'D', 'E', 'F']:
                    s_type = 'WINDOW' if l in ('A', 'F') else ('AISLE' if l in ('C', 'D') else 'MIDDLE')
                    aircraft_seats.append({
                        "seat_number": f"{r}{l}",
                        "seat_class": s_class,
                        "seat_type": s_type
                    })

        # Attach booking status and row/col info
        for s in aircraft_seats:
            s['is_booked'] = (s['seat_number'] in booked_seat_numbers)
            r, c = parse_seat(s)
            s['row_num'] = r
            s['col_letter'] = c

        # Group by row
        rows_dict = {}
        for s in aircraft_seats:
            r = s['row_num']
            if r not in rows_dict:
                rows_dict[r] = {
                    "row_num": r,
                    "seat_class": s['seat_class'],
                    "is_exit_row": (r in (11, 12)),
                    "left_seats": [],
                    "right_seats": []
                }
            if s['col_letter'] in ('A', 'B', 'C'):
                rows_dict[r]['left_seats'].append(s)
            else:
                rows_dict[r]['right_seats'].append(s)

        # Sort by row number and seat letters
        sorted_rows = []
        for r in sorted(rows_dict.keys()):
            rows_dict[r]['left_seats'].sort(key=lambda s: s['col_letter'])
            rows_dict[r]['right_seats'].sort(key=lambda s: s['col_letter'])
            sorted_rows.append(rows_dict[r])

        return sorted_rows

    @staticmethod
    def get_seat_map(flight_id):
        """
        Returns properly sorted flat list of seats.
        """
        rows = FlightModel.get_seat_rows(flight_id)
        flat = []
        for r in rows:
            flat.extend(r['left_seats'])
            flat.extend(r['right_seats'])
        return flat

    @staticmethod
    def create(flight_number, airline_id, aircraft_id, origin, destination, dep_time, arr_time, duration, fare, status='SCHEDULED'):
        query = """
            INSERT INTO flights (flight_number, airline_id, aircraft_id, origin_code, destination_code, departure_time, arrival_time, duration_mins, base_fare, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        fid = db.execute_query(query, (flight_number, airline_id, aircraft_id, origin, destination, dep_time, arr_time, duration, fare, status), commit=True)
        return FlightModel.get_by_id(fid)

    @staticmethod
    def update(flight_id, base_fare, status, dep_time=None, arr_time=None):
        if dep_time and arr_time:
            query = "UPDATE flights SET base_fare = %s, status = %s, departure_time = %s, arrival_time = %s WHERE flight_id = %s"
            db.execute_query(query, (base_fare, status, dep_time, arr_time, flight_id), commit=True)
        else:
            query = "UPDATE flights SET base_fare = %s, status = %s WHERE flight_id = %s"
            db.execute_query(query, (base_fare, status, flight_id), commit=True)
        return FlightModel.get_by_id(flight_id)

    @staticmethod
    def delete(flight_id):
        # Check active bookings
        bookings = db.execute_query("SELECT COUNT(*) AS c FROM bookings WHERE flight_id = %s AND status = 'CONFIRMED'", (flight_id,), fetch='one')
        if bookings and bookings['c'] > 0:
            raise ValueError(f"Cannot delete flight with {bookings['c']} active bookings.")
        return db.execute_query("DELETE FROM flights WHERE flight_id = %s", (flight_id,), commit=True)

# ------------------------------------------------------------------------------
# Booking & Payment Model (Assessment 10 End-to-End Workflow & Transactions)
# ------------------------------------------------------------------------------
class BookingModel:
    @staticmethod
    def create_booking_flow(flight_id, passenger_data, seat_number, travel_class='ECONOMY', payment_method='UPI', user_id=None):
        """
        ACID Transaction:
        1. Verifies seat availability
        2. Retrieves or inserts passenger
        3. Calculates total fare based on travel class
        4. Inserts booking record with unique PNR
        5. Inserts payment transaction
        """
        # 1. Verify flight exists
        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            raise ValueError("Flight not found.")

        # 2. Check seat availability for this flight
        seat_check = db.execute_query(
            "SELECT booking_id FROM bookings WHERE flight_id = %s AND seat_number = %s AND status = 'CONFIRMED'",
            (flight_id, seat_number),
            fetch='one'
        )
        if seat_check:
            raise ValueError(f"Seat {seat_number} is already booked on this flight. Please choose another seat.")

        # 3. Passenger lookup or create
        email = passenger_data.get('email', '').strip()
        passenger = db.execute_query("SELECT * FROM passengers WHERE email = %s", (email,), fetch='one')
        if not passenger:
            passenger = PassengerModel.create(
                first_name=passenger_data.get('first_name'),
                last_name=passenger_data.get('last_name'),
                email=email,
                phone=passenger_data.get('phone'),
                passport_number=passenger_data.get('passport_number'),
                dob=passenger_data.get('date_of_birth', '2000-01-01'),
                gender=passenger_data.get('gender', 'MALE')
            )
        passenger_id = passenger['passenger_id']

        # 4. Calculate Fare
        base_fare = float(flight['base_fare'])
        class_multiplier = 1.0
        if travel_class == 'BUSINESS':
            class_multiplier = 2.0
        elif travel_class == 'FIRST':
            class_multiplier = 3.5
        total_fare = round(base_fare * class_multiplier + 350.0, 2) # Base * multiplier + taxes/fees

        # 5. Generate PNR & Transaction ID
        pnr = generate_pnr()
        txn_id = generate_txn_id()

        # 6. Execute atomic transaction
        tx_steps = [
            (
                """
                INSERT INTO bookings (pnr, user_id, passenger_id, flight_id, seat_number, travel_class, total_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                """,
                (pnr, user_id, passenger_id, flight_id, seat_number, travel_class, total_fare),
                'new_booking_id'
            ),
            (
                """
                INSERT INTO payments (booking_id, transaction_id, payment_method, amount, payment_status)
                VALUES (%s, %s, %s, %s, 'SUCCESS')
                """,
                ('$new_booking_id', txn_id, payment_method, total_fare)
            )
        ]

        tx_result = db.execute_transaction(tx_steps)
        return BookingModel.get_by_pnr(pnr)

    @staticmethod
    def get_by_pnr(pnr):
        query = """
            SELECT 
                b.booking_id, b.pnr, b.booking_date, b.travel_class, b.seat_number,
                b.total_amount, b.status AS booking_status,
                p.passenger_id, CONCAT(p.first_name, ' ', p.last_name) AS passenger_name,
                p.first_name, p.last_name, p.email, p.phone, p.passport_number,
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time, f.duration_mins, f.status AS flight_status,
                al.airline_code, al.airline_name,
                ac.model AS aircraft_model,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport, orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport, dest.city AS dest_city,
                pay.payment_id, pay.transaction_id, pay.payment_method, pay.payment_status, pay.payment_time
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            WHERE b.pnr = %s
        """
        # Handle SQLite || concatenation if sqlite is used
        if db.engine == 'sqlite':
            query = query.replace("CONCAT(p.first_name, ' ', p.last_name)", "(p.first_name || ' ' || p.last_name)")

        return db.execute_query(query, (pnr,), fetch='one')

    @staticmethod
    def get_by_user(user_id):
        query = """
            SELECT 
                b.booking_id, b.pnr, b.booking_date, b.travel_class, b.seat_number,
                b.total_amount, b.status AS booking_status,
                f.flight_number, f.departure_time, f.arrival_time,
                al.airline_name, al.airline_code,
                orig.city AS origin_city, dest.city AS dest_city
            FROM bookings b
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            WHERE b.user_id = %s
            ORDER BY b.booking_id DESC
        """
        return db.execute_query(query, (user_id,))

    @staticmethod
    def get_all(limit=100):
        query = """
            SELECT 
                b.booking_id, b.pnr, b.booking_date, b.travel_class, b.seat_number,
                b.total_amount, b.status AS booking_status,
                p.first_name, p.last_name, p.email,
                f.flight_number, al.airline_code,
                orig.city AS origin_city, dest.city AS dest_city,
                pay.payment_method, pay.payment_status
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            ORDER BY b.booking_id DESC
            LIMIT %s
        """
        return db.execute_query(query, (limit,))

    @staticmethod
    def cancel(pnr):
        booking = BookingModel.get_by_pnr(pnr)
        if not booking:
            raise ValueError("Booking with given PNR not found.")
        if booking['booking_status'] == 'CANCELLED':
            raise ValueError("Booking is already cancelled.")

        tx_steps = [
            ("UPDATE bookings SET status = 'CANCELLED' WHERE pnr = %s", (pnr,)),
            ("UPDATE payments SET payment_status = 'REFUNDED' WHERE booking_id = %s", (booking['booking_id'],))
        ]
        db.execute_transaction(tx_steps)
        return BookingModel.get_by_pnr(pnr)

    @staticmethod
    def update_seat(pnr, new_seat):
        booking = BookingModel.get_by_pnr(pnr)
        if not booking:
            raise ValueError("Booking not found.")
        if booking['booking_status'] != 'CONFIRMED':
            raise ValueError("Only confirmed bookings can change seats.")

        # Check if new seat is already occupied
        seat_check = db.execute_query(
            "SELECT booking_id FROM bookings WHERE flight_id = %s AND seat_number = %s AND status = 'CONFIRMED' AND pnr <> %s",
            (booking['flight_id'], new_seat, pnr),
            fetch='one'
        )
        if seat_check:
            raise ValueError(f"Seat {new_seat} is already occupied on flight {booking['flight_number']}.")

        db.execute_query("UPDATE bookings SET seat_number = %s WHERE pnr = %s", (new_seat, pnr), commit=True)
        return BookingModel.get_by_pnr(pnr)

# ------------------------------------------------------------------------------
# Reports & Analytical Queries Model (Assessment 9 & 10)
# ------------------------------------------------------------------------------
class ReportsModel:
    @staticmethod
    def get_revenue_by_airline():
        """
        GROUP BY & AGGREGATION: Total revenue, confirmed bookings, average fare by airline
        """
        query = """
            SELECT 
                al.airline_code,
                al.airline_name,
                COUNT(DISTINCT f.flight_id) AS scheduled_flights,
                COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) AS confirmed_bookings,
                COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE 0 END), 0) AS total_revenue,
                COALESCE(ROUND(AVG(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE NULL END), 2), 0) AS average_ticket_fare
            FROM airlines al
            LEFT JOIN flights f ON al.airline_id = f.airline_id
            LEFT JOIN bookings b ON f.flight_id = b.flight_id
            GROUP BY al.airline_id, al.airline_code, al.airline_name
            ORDER BY total_revenue DESC
        """
        return db.execute_query(query)

    @staticmethod
    def get_busiest_airports():
        """
        Ranking airports by total departures and arrivals
        """
        query = """
            SELECT 
                a.airport_code,
                a.airport_name,
                a.city,
                COUNT(DISTINCT f_dep.flight_id) AS total_departures,
                COUNT(DISTINCT f_arr.flight_id) AS total_arrivals,
                (COUNT(DISTINCT f_dep.flight_id) + COUNT(DISTINCT f_arr.flight_id)) AS total_traffic
            FROM airports a
            LEFT JOIN flights f_dep ON a.airport_code = f_dep.origin_code
            LEFT JOIN flights f_arr ON a.airport_code = f_arr.destination_code
            GROUP BY a.airport_code, a.airport_name, a.city
            ORDER BY total_traffic DESC
        """
        return db.execute_query(query)

    @staticmethod
    def get_occupancy_report():
        """
        Mathematical aggregations: Flight seat capacity, booked, available, occupancy percentage
        """
        query = """
            SELECT 
                f.flight_number,
                al.airline_name,
                orig.city AS origin_city,
                dest.city AS dest_city,
                ac.model AS aircraft_model,
                ac.total_seats,
                COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) AS booked_seats,
                (ac.total_seats - COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END)) AS available_seats,
                ROUND((COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) * 100.0 / ac.total_seats), 2) AS occupancy_pct,
                COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE 0 END), 0) AS flight_revenue
            FROM flights f
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            LEFT JOIN bookings b ON f.flight_id = b.flight_id
            GROUP BY f.flight_id, f.flight_number, al.airline_name, orig.city, dest.city, ac.model, ac.total_seats
            ORDER BY booked_seats DESC
        """
        return db.execute_query(query)

    @staticmethod
    def get_high_value_passengers():
        """
        NESTED SUBQUERY: Passengers whose total booking spend exceeds the overall average booking value
        """
        query = """
            SELECT 
                p.passenger_id,
                CONCAT(p.first_name, ' ', p.last_name) AS full_name,
                p.email,
                p.phone,
                b.pnr,
                b.total_amount,
                b.travel_class
            FROM passengers p
            JOIN bookings b ON p.passenger_id = b.passenger_id
            WHERE b.status = 'CONFIRMED' 
              AND b.total_amount > (
                  SELECT AVG(total_amount) 
                  FROM bookings 
                  WHERE status = 'CONFIRMED'
              )
            ORDER BY b.total_amount DESC
        """
        if db.engine == 'sqlite':
            query = query.replace("CONCAT(p.first_name, ' ', p.last_name)", "(p.first_name || ' ' || p.last_name)")
        return db.execute_query(query)

    @staticmethod
    def get_audit_logs(limit=50):
        return db.execute_query("SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT %s", (limit,))

    @staticmethod
    def get_system_summary():
        airports_count = db.execute_query("SELECT COUNT(*) AS c FROM airports", fetch='one')['c']
        airlines_count = db.execute_query("SELECT COUNT(*) AS c FROM airlines", fetch='one')['c']
        flights_count = db.execute_query("SELECT COUNT(*) AS c FROM flights", fetch='one')['c']
        passengers_count = db.execute_query("SELECT COUNT(*) AS c FROM passengers", fetch='one')['c']
        bookings_count = db.execute_query("SELECT COUNT(*) AS c FROM bookings", fetch='one')['c']
        total_revenue = db.execute_query("SELECT COALESCE(SUM(total_amount), 0) AS s FROM bookings WHERE status = 'CONFIRMED'", fetch='one')['s']

        return {
            "airports": airports_count,
            "airlines": airlines_count,
            "flights": flights_count,
            "passengers": passengers_count,
            "bookings": bookings_count,
            "total_revenue": total_revenue,
            "engine": db.engine
        }
