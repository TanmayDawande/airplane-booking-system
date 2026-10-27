import hashlib
import hmac
import random
import re
import string
from datetime import date, datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from database import db

# ------------------------------------------------------------------------------
# Security & ID helpers
# ------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a new password. Werkzeug stores a random salt with the hash."""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(stored_hash: str, password: str) -> bool:
    """Support both new Werkzeug hashes and legacy SHA-256 seed hashes."""
    if not stored_hash:
        return False
    if stored_hash.startswith(('pbkdf2:', 'scrypt:')):
        return check_password_hash(stored_hash, password)
    legacy = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hmac.compare_digest(stored_hash, legacy)


def generate_pnr() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=5))
    return f'AER{suffix}'


def generate_txn_id() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f'TXN_{suffix}'


# ------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------
class UserModel:
    @staticmethod
    def authenticate(username: str, password: str):
        user = db.execute_query(
            """
            SELECT user_id, username, password_hash, role, passenger_id
            FROM users
            WHERE username = %s
            """,
            (username,),
            fetch='one',
        )
        if not user or not verify_password(user['password_hash'], password):
            return None
        user.pop('password_hash', None)
        return user

    @staticmethod
    def register(username, password, first_name, last_name, email, phone,
                 passport_number, dob, gender, role='PASSENGER'):
        # Public self-registration can only create a passenger account. Admin
        # and staff accounts are seeded in database/airline_db.sql.
        if not username or not password:
            raise ValueError('Username and password are required.')
        if len(password) < 6:
            raise ValueError('Password must be at least 6 characters long.')

        existing_user = db.execute_query(
            "SELECT user_id FROM users WHERE username = %s",
            (username,),
            fetch='one',
        )
        if existing_user:
            raise ValueError(f"Username '{username}' already exists.")

        details = PassengerModel.validate_details(
            first_name, last_name, email, phone, passport_number, dob, gender
        )

        existing_passenger = db.execute_query(
            "SELECT passenger_id FROM passengers WHERE email = %s OR passport_number = %s",
            (details['email'], details['passport_number']),
            fetch='one',
        )

        steps = []
        if existing_passenger:
            passenger_ref = existing_passenger['passenger_id']
        else:
            steps.append((
                """
                INSERT INTO passengers
                    (first_name, last_name, email, phone, passport_number, date_of_birth, gender)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    details['first_name'], details['last_name'], details['email'],
                    details['phone'], details['passport_number'],
                    details['date_of_birth'], details['gender'],
                ),
                'new_passenger_id',
            ))
            passenger_ref = '$new_passenger_id'

        steps.append((
            """
            INSERT INTO users (username, password_hash, role, passenger_id)
            VALUES (%s, %s, 'PASSENGER', %s)
            """,
            (username.strip(), hash_password(password), passenger_ref),
            'new_user_id',
        ))

        result = db.execute_transaction(steps)
        passenger_id = result['last_ids'].get(
            'new_passenger_id', existing_passenger['passenger_id'] if existing_passenger else None
        )
        return {
            "user_id": result['last_ids']['new_user_id'],
            "username": username.strip(),
            "role": 'PASSENGER',
            "passenger_id": passenger_id,
        }

    @staticmethod
    def get_by_id(user_id):
        return db.execute_query(
            """
            SELECT u.user_id, u.username, u.role, u.passenger_id,
                   p.first_name, p.last_name, p.email, p.phone, p.passport_number,
                   p.date_of_birth, p.gender, u.created_at
            FROM users u
            LEFT JOIN passengers p ON u.passenger_id = p.passenger_id
            WHERE u.user_id = %s
            """,
            (user_id,),
            fetch='one',
        )


# ------------------------------------------------------------------------------
# Passengers (Assessment 8 insertion / retrieval, Assessment 9 CRUD)
# ------------------------------------------------------------------------------
class PassengerModel:
    @staticmethod
    def validate_details(first_name, last_name, email, phone, passport_number, dob, gender):
        first_name = (first_name or '').strip()
        last_name = (last_name or '').strip()
        email = (email or '').strip().lower()
        phone = (phone or '').strip()
        passport_number = (passport_number or '').strip().upper()
        gender = (gender or 'MALE').strip().upper()
        if isinstance(dob, (date, datetime)):
            dob = dob.strftime('%Y-%m-%d')
        else:
            dob = (dob or '').strip()

        if not first_name or not last_name:
            raise ValueError('First name and last name are required.')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            raise ValueError('Enter a valid email address, for example name@example.com.')
        if len(re.sub(r'\D', '', phone)) < 8:
            raise ValueError('Enter a valid phone number with at least 8 digits.')
        if len(passport_number) < 4:
            raise ValueError('Enter a valid passport or ID number (at least 4 characters).')
        try:
            datetime.strptime(dob, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date of birth must be a valid date in YYYY-MM-DD format.')
        if gender not in ('MALE', 'FEMALE', 'OTHER'):
            raise ValueError('Gender must be MALE, FEMALE or OTHER.')

        return {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "passport_number": passport_number,
            "date_of_birth": dob,
            "gender": gender,
        }

    @staticmethod
    def create(first_name, last_name, email, phone, passport_number, dob, gender):
        details = PassengerModel.validate_details(
            first_name, last_name, email, phone, passport_number, dob, gender
        )

        duplicate = db.execute_query(
            """
            SELECT passenger_id, email, passport_number
            FROM passengers
            WHERE email = %s OR passport_number = %s
            """,
            (details['email'], details['passport_number']),
            fetch='one',
        )
        if duplicate:
            if duplicate['email'] == details['email']:
                raise ValueError('A passenger with this email already exists.')
            raise ValueError('A passenger with this passport/ID already exists.')

        passenger_id = db.execute_query(
            """
            INSERT INTO passengers
                (first_name, last_name, email, phone, passport_number, date_of_birth, gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                details['first_name'], details['last_name'], details['email'],
                details['phone'], details['passport_number'],
                details['date_of_birth'], details['gender'],
            ),
            commit=True,
        )
        return PassengerModel.get_by_id(passenger_id)

    @staticmethod
    def get_by_id(passenger_id):
        return db.execute_query(
            "SELECT * FROM passengers WHERE passenger_id = %s",
            (passenger_id,),
            fetch='one',
        )

    @staticmethod
    def get_all(limit=50):
        return db.execute_query(
            "SELECT * FROM passengers ORDER BY passenger_id DESC LIMIT %s",
            (int(limit),),
        )

    @staticmethod
    def search(term):
        term = (term or '').strip()
        if not term:
            return PassengerModel.get_all()
        pattern = f'%{term}%'
        return db.execute_query(
            """
            SELECT * FROM passengers
            WHERE first_name LIKE %s OR last_name LIKE %s
               OR email LIKE %s OR passport_number LIKE %s OR phone LIKE %s
            ORDER BY passenger_id DESC
            LIMIT 50
            """,
            (pattern, pattern, pattern, pattern, pattern),
        )

    @staticmethod
    def update(passenger_id, first_name, last_name, email, phone, passport_number):
        current = PassengerModel.get_by_id(passenger_id)
        if not current:
            raise ValueError('Passenger not found.')

        details = PassengerModel.validate_details(
            first_name, last_name, email, phone, passport_number,
            current['date_of_birth'], current['gender'],
        )

        duplicate = db.execute_query(
            """
            SELECT passenger_id, email, passport_number
            FROM passengers
            WHERE (email = %s OR passport_number = %s)
              AND passenger_id <> %s
            """,
            (details['email'], details['passport_number'], passenger_id),
            fetch='one',
        )
        if duplicate:
            if duplicate['email'] == details['email']:
                raise ValueError('Another passenger already uses this email.')
            raise ValueError('Another passenger already uses this passport/ID.')

        db.execute_query(
            """
            UPDATE passengers
            SET first_name = %s, last_name = %s, email = %s,
                phone = %s, passport_number = %s
            WHERE passenger_id = %s
            """,
            (
                details['first_name'], details['last_name'], details['email'],
                details['phone'], details['passport_number'], passenger_id,
            ),
            commit=True,
        )
        return PassengerModel.get_by_id(passenger_id)

    @staticmethod
    def delete(passenger_id):
        bookings = db.execute_query(
            "SELECT COUNT(*) AS c FROM bookings WHERE passenger_id = %s",
            (passenger_id,),
            fetch='one',
        )
        if bookings and bookings['c'] > 0:
            raise ValueError(
                'Cannot delete a passenger with booking history. '
                'Keep the record for audit and reporting purposes.'
            )
        return db.execute_query(
            "DELETE FROM passengers WHERE passenger_id = %s",
            (passenger_id,),
            commit=True,
        )


# ------------------------------------------------------------------------------
# Flights
# ------------------------------------------------------------------------------
class FlightModel:
    CLASS_MULTIPLIERS = {'ECONOMY': 1.0, 'BUSINESS': 2.0, 'FIRST': 3.5}
    VALID_STATUSES = ('SCHEDULED', 'ON_TIME', 'BOARDING', 'DELAYED', 'DEPARTED', 'CANCELLED')

    @staticmethod
    def search(origin=None, destination=None, travel_date=None,
               travel_class='ECONOMY', max_price=None, upcoming_only=False):
        travel_class = (travel_class or 'ECONOMY').upper()
        if travel_class not in FlightModel.CLASS_MULTIPLIERS:
            travel_class = 'ECONOMY'

        query = """
            SELECT
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
                f.duration_mins, f.base_fare, f.status,
                CASE %s
                    WHEN 'BUSINESS' THEN ROUND(f.base_fare * 2.0, 2)
                    WHEN 'FIRST' THEN ROUND(f.base_fare * 3.5, 2)
                    ELSE f.base_fare
                END AS cabin_fare,
                al.airline_id, al.airline_code, al.airline_name,
                ac.aircraft_id, ac.model AS aircraft_model, ac.total_seats,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport,
                orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport,
                dest.city AS dest_city,
                (ac.total_seats - (
                    SELECT COUNT(*) FROM bookings b
                    WHERE b.flight_id = f.flight_id AND b.status = 'CONFIRMED'
                )) AS available_seats
            FROM flights f
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            WHERE 1 = 1
        """
        params = [travel_class]

        if origin:
            query += " AND f.origin_code = %s"
            params.append(origin)
        if destination:
            query += " AND f.destination_code = %s"
            params.append(destination)
        if travel_date:
            query += " AND DATE(f.departure_time) = DATE(%s)"
            params.append(travel_date)
        if max_price:
            query += " AND (f.base_fare * %s) <= %s"
            params.extend([FlightModel.CLASS_MULTIPLIERS[travel_class], float(max_price)])
        if upcoming_only:
            query += " AND f.departure_time >= NOW()"

        query += " ORDER BY f.departure_time ASC"
        return db.execute_query(query, tuple(params))

    @staticmethod
    def get_default_travel_date():
        row = db.execute_query(
            "SELECT DATE(MIN(departure_time)) AS first_date FROM flights WHERE departure_time >= NOW()",
            fetch='one',
        )
        if row and row['first_date']:
            return str(row['first_date'])
        return (date.today() + timedelta(days=1)).isoformat()

    @staticmethod
    def get_by_id(flight_id):
        return db.execute_query(
            """
            SELECT
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
                f.duration_mins, f.base_fare, f.base_fare AS cabin_fare, f.status,
                al.airline_id, al.airline_code, al.airline_name,
                ac.aircraft_id, ac.model AS aircraft_model, ac.total_seats,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport,
                orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport,
                dest.city AS dest_city,
                (ac.total_seats - (
                    SELECT COUNT(*) FROM bookings b
                    WHERE b.flight_id = f.flight_id AND b.status = 'CONFIRMED'
                )) AS available_seats
            FROM flights f
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            WHERE f.flight_id = %s
            """,
            (flight_id,),
            fetch='one',
        )

    @staticmethod
    def get_seat_rows(flight_id):
        """Return the 24-row cabin layout with occupied seats marked."""
        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            return []

        aircraft_seats = db.execute_query(
            "SELECT * FROM seats WHERE aircraft_id = %s ORDER BY seat_id",
            (flight['aircraft_id'],),
        )
        booked = db.execute_query(
            "SELECT seat_number FROM bookings WHERE flight_id = %s AND status = 'CONFIRMED'",
            (flight_id,),
        )
        booked_numbers = {row['seat_number'] for row in booked}

        if not aircraft_seats:
            aircraft_seats = []
            for row in range(1, 25):
                seat_class = 'FIRST' if row <= 2 else ('BUSINESS' if row <= 5 else 'ECONOMY')
                for letter in ('A', 'B', 'C', 'D', 'E', 'F'):
                    seat_type = (
                        'WINDOW' if letter in ('A', 'F')
                        else 'AISLE' if letter in ('C', 'D')
                        else 'MIDDLE'
                    )
                    aircraft_seats.append({
                        "seat_number": f'{row}{letter}',
                        "seat_class": seat_class,
                        "seat_type": seat_type,
                    })

        rows = {}
        for seat in aircraft_seats:
            match = re.match(r'(\d+)([A-Z])', seat['seat_number'])
            row_num = int(match.group(1)) if match else 0
            col = match.group(2) if match else ''
            seat['is_booked'] = seat['seat_number'] in booked_numbers
            seat['row_num'] = row_num
            seat['col_letter'] = col

            if row_num not in rows:
                rows[row_num] = {
                    "row_num": row_num,
                    "seat_class": seat['seat_class'],
                    "is_exit_row": row_num in (11, 12),
                    "left_seats": [],
                    "right_seats": [],
                }
            if col in ('A', 'B', 'C'):
                rows[row_num]['left_seats'].append(seat)
            else:
                rows[row_num]['right_seats'].append(seat)

        result = []
        for row_num in sorted(rows):
            rows[row_num]['left_seats'].sort(key=lambda item: item['col_letter'])
            rows[row_num]['right_seats'].sort(key=lambda item: item['col_letter'])
            result.append(rows[row_num])
        return result

    @staticmethod
    def get_seat_map(flight_id):
        flat = []
        for row in FlightModel.get_seat_rows(flight_id):
            flat.extend(row['left_seats'])
            flat.extend(row['right_seats'])
        return flat

    @staticmethod
    def create(flight_number, airline_id, aircraft_id, origin, destination,
               dep_time, arr_time, duration, fare, status='SCHEDULED'):
        flight_number = (flight_number or '').strip().upper()
        status = (status or 'SCHEDULED').upper()
        if not flight_number:
            raise ValueError('Flight number is required.')
        if not dep_time or not arr_time:
            raise ValueError('Departure and arrival times are required.')
        existing = db.execute_query(
            "SELECT flight_id FROM flights WHERE flight_number = %s",
            (flight_number,),
            fetch='one',
        )
        if existing:
            raise ValueError(f'Flight {flight_number} already exists.')
        if origin == destination:
            raise ValueError('Origin and destination must be different.')
        try:
            dep_dt = datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')
            arr_dt = datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            raise ValueError('Use a valid departure and arrival date and time.')
        if arr_dt <= dep_dt:
            raise ValueError('Arrival time must be after departure time.')
        if status not in FlightModel.VALID_STATUSES:
            raise ValueError('Invalid flight status.')
        try:
            fare = float(fare)
        except (TypeError, ValueError):
            raise ValueError('Base fare is required.')
        if fare <= 0:
            raise ValueError('Base fare must be greater than zero.')

        flight_id = db.execute_query(
            """
            INSERT INTO flights
                (flight_number, airline_id, aircraft_id, origin_code, destination_code,
                 departure_time, arrival_time, duration_mins, base_fare, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                flight_number, int(airline_id), int(aircraft_id), origin, destination,
                dep_time, arr_time, int(duration), float(fare), status,
            ),
            commit=True,
        )
        return FlightModel.get_by_id(flight_id)

    @staticmethod
    def update(flight_id, base_fare, status, dep_time=None, arr_time=None):
        if not FlightModel.get_by_id(flight_id):
            raise ValueError('Flight not found.')
        status = (status or '').upper()
        try:
            base_fare = float(base_fare)
        except (TypeError, ValueError):
            raise ValueError('Base fare is required.')
        if status not in FlightModel.VALID_STATUSES:
            raise ValueError('Invalid flight status.')
        if base_fare <= 0:
            raise ValueError('Base fare must be greater than zero.')

        if dep_time and arr_time:
            if datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') <= datetime.strptime(
                    dep_time, '%Y-%m-%d %H:%M:%S'):
                raise ValueError('Arrival time must be after departure time.')
            db.execute_query(
                """
                UPDATE flights
                SET base_fare = %s, status = %s, departure_time = %s, arrival_time = %s
                WHERE flight_id = %s
                """,
                (float(base_fare), status, dep_time, arr_time, flight_id),
                commit=True,
            )
        else:
            db.execute_query(
                "UPDATE flights SET base_fare = %s, status = %s WHERE flight_id = %s",
                (float(base_fare), status, flight_id),
                commit=True,
            )
        return FlightModel.get_by_id(flight_id)

    @staticmethod
    def delete(flight_id):
        bookings = db.execute_query(
            "SELECT COUNT(*) AS c FROM bookings WHERE flight_id = %s",
            (flight_id,),
            fetch='one',
        )
        if bookings and bookings['c'] > 0:
            raise ValueError(
                'Cannot delete a flight with booking history. '
                'Cancel the bookings or keep the flight for audit purposes.'
            )
        return db.execute_query(
            "DELETE FROM flights WHERE flight_id = %s", (flight_id,), commit=True
        )


# ------------------------------------------------------------------------------
# Booking and payment transaction
# ------------------------------------------------------------------------------
class BookingModel:
    TAXES = 350.0

    @staticmethod
    def create_booking_flow(flight_id, passenger_data, seat_number,
                            travel_class='ECONOMY', payment_method='UPI', user_id=None):
        try:
            flight_id = int(flight_id)
        except (TypeError, ValueError):
            raise ValueError('Please choose a flight before booking.')
        if payment_method not in ('CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING', 'WALLET'):
            raise ValueError('Please choose a valid payment method.')
        if not isinstance(passenger_data, dict):
            raise ValueError('Passenger details are missing.')

        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            raise ValueError('Flight not found.')
        if flight['status'] == 'CANCELLED':
            raise ValueError('This flight has been cancelled.')

        seat_number = (seat_number or '').strip().upper()
        if not seat_number:
            raise ValueError('Please select a seat.')

        seat = db.execute_query(
            "SELECT * FROM seats WHERE aircraft_id = %s AND seat_number = %s",
            (flight['aircraft_id'], seat_number),
            fetch='one',
        )
        if not seat:
            raise ValueError(f'Seat {seat_number} does not exist on this aircraft.')

        # The seat's own cabin class decides the fare. This prevents a user from
        # sending a cheaper class in the request than the seat they selected.
        travel_class = seat['seat_class']

        occupied = db.execute_query(
            """
            SELECT booking_id FROM bookings
            WHERE flight_id = %s AND seat_number = %s AND status = 'CONFIRMED'
            """,
            (flight['flight_id'], seat_number),
            fetch='one',
        )
        if occupied:
            raise ValueError(f'Seat {seat_number} is already booked on this flight.')

        email = (passenger_data.get('email') or '').strip().lower()
        if not email:
            raise ValueError('Passenger email is required.')

        passenger = db.execute_query(
            "SELECT * FROM passengers WHERE email = %s", (email,), fetch='one'
        )
        if not passenger:
            passenger = PassengerModel.create(
                first_name=passenger_data.get('first_name'),
                last_name=passenger_data.get('last_name'),
                email=email,
                phone=passenger_data.get('phone'),
                passport_number=passenger_data.get('passport_number'),
                dob=passenger_data.get('date_of_birth'),
                gender=passenger_data.get('gender', 'MALE'),
            )

        multiplier = FlightModel.CLASS_MULTIPLIERS.get(travel_class, 1.0)
        total_fare = round(float(flight['base_fare']) * multiplier + BookingModel.TAXES, 2)

        pnr = None
        for _ in range(10):
            candidate = generate_pnr()
            exists = db.execute_query(
                "SELECT 1 AS found FROM bookings WHERE pnr = %s",
                (candidate,),
                fetch='one',
            )
            if not exists:
                pnr = candidate
                break
        if not pnr:
            raise RuntimeError('Could not generate a unique PNR. Please try again.')

        transaction_id = generate_txn_id()
        steps = [
            (
                """
                INSERT INTO bookings
                    (pnr, user_id, passenger_id, flight_id, seat_number,
                     travel_class, total_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                """,
                (
                    pnr, user_id, passenger['passenger_id'], flight['flight_id'],
                    seat_number, travel_class, total_fare,
                ),
                'new_booking_id',
            ),
            (
                """
                INSERT INTO payments
                    (booking_id, transaction_id, payment_method, amount, payment_status)
                VALUES (%s, %s, %s, %s, 'SUCCESS')
                """,
                ('$new_booking_id', transaction_id, payment_method, total_fare),
            ),
        ]
        db.execute_transaction(steps)
        return BookingModel.get_by_pnr(pnr)

    @staticmethod
    def get_by_pnr(pnr):
        return db.execute_query(
            """
            SELECT
                b.booking_id, b.pnr, b.booking_date, b.travel_class, b.seat_number,
                b.total_amount, b.status AS booking_status,
                p.passenger_id, CONCAT(p.first_name, ' ', p.last_name) AS passenger_name,
                p.first_name, p.last_name, p.email, p.phone, p.passport_number,
                f.flight_id, f.flight_number, f.departure_time, f.arrival_time,
                f.duration_mins, f.status AS flight_status,
                al.airline_code, al.airline_name,
                ac.aircraft_id, ac.model AS aircraft_model,
                orig.airport_code AS origin_code, orig.airport_name AS origin_airport,
                orig.city AS origin_city,
                dest.airport_code AS destination_code, dest.airport_name AS dest_airport,
                dest.city AS dest_city,
                pay.payment_id, pay.transaction_id, pay.payment_method,
                pay.payment_status, pay.payment_time
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            LEFT JOIN payments pay ON b.booking_id = pay.booking_id
            WHERE b.pnr = %s
            """,
            (pnr,),
            fetch='one',
        )

    @staticmethod
    def get_by_user(user_id):
        return db.execute_query(
            """
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
            """,
            (user_id,),
        )

    @staticmethod
    def get_all(limit=100):
        return db.execute_query(
            """
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
            """,
            (int(limit),),
        )

    @staticmethod
    def cancel(pnr):
        booking = BookingModel.get_by_pnr(pnr)
        if not booking:
            raise ValueError('Booking with this PNR was not found.')
        if booking['booking_status'] == 'CANCELLED':
            raise ValueError('This booking is already cancelled.')

        db.execute_transaction([
            ("UPDATE bookings SET status = 'CANCELLED' WHERE pnr = %s", (pnr,)),
            (
                "UPDATE payments SET payment_status = 'REFUNDED' WHERE booking_id = %s",
                (booking['booking_id'],),
            ),
        ])
        return BookingModel.get_by_pnr(pnr)

    @staticmethod
    def update_seat(pnr, new_seat):
        booking = BookingModel.get_by_pnr(pnr)
        if not booking:
            raise ValueError('Booking not found.')
        if booking['booking_status'] != 'CONFIRMED':
            raise ValueError('Only confirmed bookings can change seats.')

        new_seat = (new_seat or '').strip().upper()
        seat = db.execute_query(
            "SELECT * FROM seats WHERE aircraft_id = %s AND seat_number = %s",
            (booking['aircraft_id'], new_seat),
            fetch='one',
        )
        if not seat:
            raise ValueError(f'Seat {new_seat} does not exist on this aircraft.')
        if seat['seat_class'] != booking['travel_class']:
            raise ValueError(
                f'Seat {new_seat} is in {seat["seat_class"]}, '
                f'but this booking is {booking["travel_class"]}.'
            )

        occupied = db.execute_query(
            """
            SELECT booking_id FROM bookings
            WHERE flight_id = %s AND seat_number = %s
              AND status = 'CONFIRMED' AND pnr <> %s
            """,
            (booking['flight_id'], new_seat, pnr),
            fetch='one',
        )
        if occupied:
            raise ValueError(f'Seat {new_seat} is already occupied.')

        db.execute_query(
            "UPDATE bookings SET seat_number = %s WHERE pnr = %s",
            (new_seat, pnr),
            commit=True,
        )
        return BookingModel.get_by_pnr(pnr)


# ------------------------------------------------------------------------------
# Reports and analytical queries
# ------------------------------------------------------------------------------
class ReportsModel:
    @staticmethod
    def get_revenue_by_airline():
        return db.execute_query(
            """
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
        )

    @staticmethod
    def get_revenue_by_airline_having(min_revenue=5000):
        return db.execute_query(
            """
            SELECT
                al.airline_name,
                COUNT(b.booking_id) AS total_bookings,
                SUM(b.total_amount) AS gross_revenue,
                ROUND(AVG(b.total_amount), 2) AS average_fare
            FROM airlines al
            JOIN flights f ON al.airline_id = f.airline_id
            JOIN bookings b ON f.flight_id = b.flight_id
            WHERE b.status = 'CONFIRMED'
            GROUP BY al.airline_id, al.airline_name
            HAVING gross_revenue > %s
            ORDER BY gross_revenue DESC
            """,
            (float(min_revenue),),
        )

    @staticmethod
    def get_busiest_airports():
        return db.execute_query(
            """
            SELECT
                a.airport_code, a.airport_name, a.city,
                COUNT(DISTINCT f_dep.flight_id) AS total_departures,
                COUNT(DISTINCT f_arr.flight_id) AS total_arrivals,
                (COUNT(DISTINCT f_dep.flight_id) + COUNT(DISTINCT f_arr.flight_id)) AS total_traffic
            FROM airports a
            LEFT JOIN flights f_dep ON a.airport_code = f_dep.origin_code
            LEFT JOIN flights f_arr ON a.airport_code = f_arr.destination_code
            GROUP BY a.airport_code, a.airport_name, a.city
            ORDER BY total_traffic DESC
            """
        )

    @staticmethod
    def get_occupancy_report():
        return db.execute_query(
            """
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
            GROUP BY f.flight_id, f.flight_number, al.airline_name,
                     orig.city, dest.city, ac.model, ac.total_seats
            ORDER BY booked_seats DESC
            """
        )

    @staticmethod
    def get_high_value_passengers():
        return db.execute_query(
            """
            SELECT
                p.passenger_id,
                CONCAT(p.first_name, ' ', p.last_name) AS full_name,
                p.email, p.phone, b.pnr, b.total_amount, b.travel_class
            FROM passengers p
            JOIN bookings b ON p.passenger_id = b.passenger_id
            WHERE b.status = 'CONFIRMED'
              AND b.total_amount > (
                  SELECT AVG(total_amount) FROM bookings WHERE status = 'CONFIRMED'
              )
            ORDER BY b.total_amount DESC
            """
        )

    @staticmethod
    def get_full_itinerary(limit=25):
        """Five-table INNER JOIN used in the Assessment 9 demonstration."""
        return db.execute_query(
            """
            SELECT
                b.pnr,
                CONCAT(p.first_name, ' ', p.last_name) AS passenger_name,
                al.airline_name,
                f.flight_number,
                orig.city AS origin_city,
                dest.city AS dest_city,
                f.departure_time,
                b.seat_number,
                b.travel_class,
                b.total_amount,
                b.status AS booking_status,
                b.booking_date
            FROM bookings b
            JOIN passengers p ON b.passenger_id = p.passenger_id
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airlines al ON f.airline_id = al.airline_id
            JOIN airports orig ON f.origin_code = orig.airport_code
            JOIN airports dest ON f.destination_code = dest.airport_code
            ORDER BY b.booking_id DESC
            LIMIT %s
            """,
            (int(limit),),
        )

    @staticmethod
    def get_audit_logs(limit=50):
        return db.execute_query(
            "SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT %s",
            (int(limit),),
        )

    @staticmethod
    def get_system_summary():
        airports = db.execute_query(
            "SELECT COUNT(*) AS c FROM airports", fetch='one'
        )['c']
        airlines = db.execute_query(
            "SELECT COUNT(*) AS c FROM airlines", fetch='one'
        )['c']
        flights = db.execute_query(
            "SELECT COUNT(*) AS c FROM flights", fetch='one'
        )['c']
        passengers = db.execute_query(
            "SELECT COUNT(*) AS c FROM passengers", fetch='one'
        )['c']
        bookings = db.execute_query(
            "SELECT COUNT(*) AS c FROM bookings", fetch='one'
        )['c']
        revenue = db.execute_query(
            "SELECT COALESCE(SUM(total_amount), 0) AS s FROM bookings WHERE status = 'CONFIRMED'",
            fetch='one',
        )['s']
        return {
            "airports": airports,
            "airlines": airlines,
            "flights": flights,
            "passengers": passengers,
            "bookings": bookings,
            "total_revenue": revenue,
            "engine": db.engine,
        }
