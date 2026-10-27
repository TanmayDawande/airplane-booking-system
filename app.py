import sys
from decimal import Decimal
from datetime import date, datetime, timedelta

from flask import (
    Flask, jsonify, redirect, render_template, request, session, url_for
)
from flask.json.provider import DefaultJSONProvider

import config
from database import db
from models import (
    UserModel, PassengerModel, FlightModel, BookingModel, ReportsModel
)
from timeutils import (
    format_date_ist, format_ist, format_json_ist, format_time_ist,
    now_ist, today_ist_iso,
)


class MySQLJSONProvider(DefaultJSONProvider):
    """Make MySQL datetime/Decimal values safe for JSON APIs."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return format_json_ist(obj)
        if isinstance(obj, date):
            return format_date_ist(obj)
        return super().default(obj)


app = Flask(__name__, static_folder='public/static')
app.json = MySQLJSONProvider(app)
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=8)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

app.add_template_filter(format_ist, 'ist')
app.add_template_filter(format_date_ist, 'ist_date')
app.add_template_filter(format_time_ist, 'ist_time')


# ------------------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------------------
def clean_datetime(value):
    """Accept HTML datetime-local values and normalize them for MySQL."""
    if not value:
        return None
    value = str(value).strip().replace('T', ' ')
    if len(value) == 16:
        value += ':00'
    return value


def safe_next(target):
    """Only allow redirects inside this application."""
    if not target:
        return None
    target = target.strip()
    if target.startswith('/') and not target.startswith('//'):
        return target
    return None


def login_session(user):
    session.permanent = True
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']


# ------------------------------------------------------------------------------
# Shared template values
# ------------------------------------------------------------------------------
@app.context_processor
def inject_global_vars():
    current_user = None
    if 'user_id' in session:
        current_user = UserModel.get_by_id(session['user_id'])

    db_info = {
        "engine": "MySQL",
        "database": db.database,
        "host": db.host,
        "port": db.port,
        "user": db.user,
        "timezone": f"{config.TIMEZONE_NAME} ({config.TIMEZONE_LABEL} UTC+05:30)",
    }
    return {
        "current_user": current_user,
        "db_info": db_info,
        "ist_now": now_ist(),
        "timezone_label": config.TIMEZONE_LABEL,
    }


# ------------------------------------------------------------------------------
# Public pages
# ------------------------------------------------------------------------------
@app.route('/')
def index():
    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    stats = ReportsModel.get_system_summary()
    featured_flights = FlightModel.search(upcoming_only=True)[:6]
    return render_template(
        'index.html',
        airports=airports,
        stats=stats,
        featured_flights=featured_flights,
        default_date=FlightModel.get_default_travel_date(),
    )


@app.route('/flights')
def flights_page():
    origin = request.args.get('origin', '')
    dest = request.args.get('destination', '')
    travel_date = request.args.get('date', '') or FlightModel.get_default_travel_date()
    travel_class = request.args.get('class', 'ECONOMY')
    max_price = request.args.get('max_price', '')

    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    results = FlightModel.search(
        origin=origin,
        destination=dest,
        travel_date=travel_date,
        travel_class=travel_class,
        max_price=max_price,
    )
    return render_template(
        'flights.html',
        flights=results,
        airports=airports,
        origin=origin,
        dest=dest,
        travel_date=travel_date,
        travel_class=travel_class,
        max_price=max_price,
        default_date=FlightModel.get_default_travel_date(),
    )


@app.route('/book/<int:flight_id>')
def booking_page(flight_id):
    flight = FlightModel.get_by_id(flight_id)
    if not flight:
        return redirect(url_for('flights_page'))
    seat_rows = FlightModel.get_seat_rows(flight_id)
    prefill = current_user() if 'user_id' in session else None
    return render_template(
        'booking.html',
        flight=flight,
        seat_rows=seat_rows,
        prefill=prefill,
        today=today_ist_iso(),
    )


def current_user():
    if 'user_id' in session:
        return UserModel.get_by_id(session['user_id'])
    return None


@app.route('/ticket/<pnr>')
def ticket_page(pnr):
    booking = BookingModel.get_by_pnr(pnr)
    if not booking:
        return render_template(
            'ticket.html',
            booking=None,
            error=f"PNR '{pnr}' was not found.",
        )
    return render_template('ticket.html', booking=booking, error=None)


@app.route('/my-bookings')
def my_bookings_page():
    pnr_query = request.args.get('pnr', '').strip().upper()
    searched_booking = BookingModel.get_by_pnr(pnr_query) if pnr_query else None

    user_id = session.get('user_id')
    if user_id:
        recent_bookings = BookingModel.get_by_user(user_id)
        booking_heading = 'Your bookings'
    else:
        recent_bookings = BookingModel.get_all(limit=10)
        booking_heading = 'Recent bookings'

    return render_template(
        'my_bookings.html',
        searched_booking=searched_booking,
        recent_bookings=recent_bookings,
        pnr_query=pnr_query,
        booking_heading=booking_heading,
    )


@app.route('/admin')
def admin_page():
    passenger_query = request.args.get('q', '').strip()
    flights = FlightModel.search()
    airlines = db.execute_query("SELECT * FROM airlines ORDER BY airline_name ASC")
    aircrafts = db.execute_query("SELECT * FROM aircrafts ORDER BY model ASC")
    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    passengers = (
        PassengerModel.search(passenger_query)
        if passenger_query else PassengerModel.get_all(limit=50)
    )
    bookings = BookingModel.get_all(limit=50)
    audit_logs = ReportsModel.get_audit_logs(limit=25)
    return render_template(
        'admin.html',
        flights=flights,
        airlines=airlines,
        aircrafts=aircrafts,
        airports=airports,
        passengers=passengers,
        bookings=bookings,
        audit_logs=audit_logs,
        passenger_query=passenger_query,
    )


@app.route('/reports')
def reports_page():
    rev_by_airline = ReportsModel.get_revenue_by_airline()
    revenue_having = ReportsModel.get_revenue_by_airline_having(5000)
    busiest_airports = ReportsModel.get_busiest_airports()
    occupancy = ReportsModel.get_occupancy_report()
    high_value_pax = ReportsModel.get_high_value_passengers()
    itinerary = ReportsModel.get_full_itinerary(limit=25)
    audit_logs = ReportsModel.get_audit_logs(limit=30)
    summary = ReportsModel.get_system_summary()
    return render_template(
        'reports.html',
        rev_by_airline=rev_by_airline,
        revenue_having=revenue_having,
        busiest_airports=busiest_airports,
        occupancy=occupancy,
        high_value_pax=high_value_pax,
        itinerary=itinerary,
        audit_logs=audit_logs,
        summary=summary,
    )


@app.route('/db-studio')
def db_studio_page():
    return render_template('db_studio.html', tables=db.get_tables())


@app.route('/guide')
def guide_page():
    return render_template('assessment_guide.html')


# ------------------------------------------------------------------------------
# Authentication pages
# ------------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('user_id'):
        return redirect(url_for('index'))

    next_url = safe_next(request.values.get('next')) or url_for('index')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = UserModel.authenticate(username, password)
        if user:
            login_session(user)
            return redirect(next_url)
        return render_template(
            'login.html',
            mode='login',
            error='Invalid username or password. Use the demo account shown below.',
            next_url=request.form.get('next', ''),
            username=username,
        ), 401

    return render_template(
        'login.html',
        mode='login',
        error=None,
        next_url=request.args.get('next', ''),
        username='',
    )


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        form = request.form
        try:
            user = UserModel.register(
                username=form.get('username', '').strip(),
                password=form.get('password', ''),
                first_name=form.get('first_name', ''),
                last_name=form.get('last_name', ''),
                email=form.get('email', ''),
                phone=form.get('phone', ''),
                passport_number=form.get('passport_number', ''),
                dob=form.get('date_of_birth', ''),
                gender=form.get('gender', 'MALE'),
            )
            login_session(user)
            return redirect(url_for('index'))
        except Exception as exc:
            return render_template(
                'login.html',
                mode='register',
                error=str(exc),
                next_url=request.form.get('next', ''),
                form=form,
            ), 400

    return render_template(
        'login.html',
        mode='register',
        error=None,
        next_url=request.args.get('next', ''),
        form={},
    )


@app.route('/logout')
def logout_page():
    session.clear()
    return redirect(url_for('index'))


# ------------------------------------------------------------------------------
# Authentication APIs
# ------------------------------------------------------------------------------
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    user = UserModel.authenticate(
        data.get('username', '').strip(),
        data.get('password', ''),
    )
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401
    login_session(user)
    return jsonify({"success": True, "user": user})


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    try:
        user = UserModel.register(
            username=data.get('username', '').strip(),
            password=data.get('password', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            passport_number=data.get('passport_number', ''),
            dob=data.get('date_of_birth') or data.get('dob', ''),
            gender=data.get('gender', 'MALE'),
        )
        login_session(user)
        return jsonify({"success": True, "user": user})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/auth/current')
def api_current_user():
    if 'user_id' in session:
        return jsonify({"authenticated": True, "user": UserModel.get_by_id(session['user_id'])})
    return jsonify({"authenticated": False, "user": None})


# ------------------------------------------------------------------------------
# Flight APIs (Assessment 8/9 CRUD)
# ------------------------------------------------------------------------------
@app.route('/api/flights', methods=['GET', 'POST'])
def api_flights():
    if request.method == 'GET':
        flights = FlightModel.search(
            origin=request.args.get('origin'),
            destination=request.args.get('destination'),
            travel_date=request.args.get('date'),
            travel_class=request.args.get('class', 'ECONOMY'),
            max_price=request.args.get('max_price'),
            upcoming_only=request.args.get('upcoming') == '1',
        )
        return jsonify({"success": True, "data": flights})

    data = request.get_json() or {}
    try:
        new_flight = FlightModel.create(
            flight_number=data.get('flight_number', ''),
            airline_id=int(data.get('airline_id')),
            aircraft_id=int(data.get('aircraft_id')),
            origin=data.get('origin_code', ''),
            destination=data.get('destination_code', ''),
            dep_time=clean_datetime(data.get('departure_time')),
            arr_time=clean_datetime(data.get('arrival_time')),
            duration=int(data.get('duration_mins') or data.get('duration_minutes', 120)),
            fare=float(data.get('base_fare')),
            status=data.get('status', 'SCHEDULED'),
        )
        return jsonify({
            "success": True,
            "data": new_flight,
            "message": f"Flight {new_flight['flight_number']} scheduled successfully.",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/flights/<int:flight_id>', methods=['GET', 'PUT', 'DELETE'])
def api_flight_detail(flight_id):
    if request.method == 'GET':
        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            return jsonify({"success": False, "error": "Flight not found"}), 404
        return jsonify({"success": True, "data": flight})

    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            updated = FlightModel.update(
                flight_id=flight_id,
                base_fare=float(data.get('base_fare')),
                status=data.get('status'),
                dep_time=clean_datetime(data.get('departure_time')),
                arr_time=clean_datetime(data.get('arrival_time')),
            )
            return jsonify({
                "success": True,
                "data": updated,
                "message": f"Flight {updated['flight_number']} updated successfully.",
            })
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

    try:
        FlightModel.delete(flight_id)
        return jsonify({"success": True, "message": f"Flight #{flight_id} deleted successfully."})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/flights/<int:flight_id>/seats')
def api_flight_seats(flight_id):
    return jsonify({"success": True, "data": FlightModel.get_seat_map(flight_id)})


# ------------------------------------------------------------------------------
# Passenger APIs (Assessment 8 insertion/retrieval, Assessment 9 CRUD)
# ------------------------------------------------------------------------------
@app.route('/api/passengers', methods=['GET', 'POST'])
def api_passengers():
    if request.method == 'GET':
        search = request.args.get('q', '').strip()
        rows = (
            PassengerModel.search(search)
            if search else PassengerModel.get_all(limit=int(request.args.get('limit', 50)))
        )
        return jsonify({"success": True, "data": rows})

    data = request.get_json() or {}
    try:
        new_pax = PassengerModel.create(
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            passport_number=data.get('passport_number', ''),
            dob=data.get('date_of_birth') or data.get('dob', ''),
            gender=data.get('gender', 'MALE'),
        )
        return jsonify({
            "success": True,
            "data": new_pax,
            "message": (
                f"Passenger {new_pax['first_name']} {new_pax['last_name']} "
                f"added successfully (ID: {new_pax['passenger_id']})."
            ),
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/passengers/<int:passenger_id>', methods=['GET', 'PUT', 'DELETE'])
def api_passenger_detail(passenger_id):
    if request.method == 'GET':
        pax = PassengerModel.get_by_id(passenger_id)
        if not pax:
            return jsonify({"success": False, "error": "Passenger not found"}), 404
        return jsonify({"success": True, "data": pax})

    if request.method == 'PUT':
        data = request.get_json() or {}
        try:
            updated = PassengerModel.update(
                passenger_id=passenger_id,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                email=data.get('email'),
                phone=data.get('phone'),
                passport_number=data.get('passport_number'),
            )
            return jsonify({"success": True, "data": updated, "message": "Passenger updated successfully."})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

    try:
        PassengerModel.delete(passenger_id)
        return jsonify({"success": True, "message": f"Passenger #{passenger_id} deleted successfully."})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


# ------------------------------------------------------------------------------
# Booking and payment workflow (Assessment 10)
# ------------------------------------------------------------------------------
@app.route('/api/bookings', methods=['POST'])
def api_create_booking():
    data = request.get_json() or {}
    try:
        booking = BookingModel.create_booking_flow(
            flight_id=int(data.get('flight_id')),
            passenger_data=data.get('passenger', {}),
            seat_number=data.get('seat_number'),
            travel_class=data.get('travel_class', 'ECONOMY'),
            payment_method=data.get('payment_method', 'UPI'),
            user_id=session.get('user_id'),
        )
        return jsonify({
            "success": True,
            "data": booking,
            "pnr": booking['pnr'],
            "message": f"Booking confirmed. PNR: {booking['pnr']}",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/bookings/<pnr>', methods=['GET'])
def api_get_booking(pnr):
    booking = BookingModel.get_by_pnr(pnr)
    if not booking:
        return jsonify({"success": False, "error": "Booking not found"}), 404
    return jsonify({"success": True, "data": booking})


@app.route('/api/bookings/<pnr>/cancel', methods=['POST'])
def api_cancel_booking(pnr):
    try:
        result = BookingModel.cancel(pnr)
        return jsonify({
            "success": True,
            "data": result,
            "message": f"Booking {pnr} cancelled and refund initiated.",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route('/api/bookings/<pnr>/change-seat', methods=['POST'])
def api_change_seat(pnr):
    data = request.get_json() or {}
    try:
        result = BookingModel.update_seat(pnr, data.get('seat_number', ''))
        return jsonify({
            "success": True,
            "data": result,
            "message": f"Seat for {pnr} changed to {result['seat_number']} successfully.",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


# ------------------------------------------------------------------------------
# Report APIs
# ------------------------------------------------------------------------------
@app.route('/api/reports/revenue-by-airline')
def api_rep_revenue():
    return jsonify({"success": True, "data": ReportsModel.get_revenue_by_airline()})


@app.route('/api/reports/revenue-having')
def api_rep_revenue_having():
    return jsonify({"success": True, "data": ReportsModel.get_revenue_by_airline_having()})


@app.route('/api/reports/occupancy')
def api_rep_occupancy():
    return jsonify({"success": True, "data": ReportsModel.get_occupancy_report()})


@app.route('/api/reports/busiest-airports')
def api_rep_airports():
    return jsonify({"success": True, "data": ReportsModel.get_busiest_airports()})


@app.route('/api/reports/high-value-passengers')
def api_rep_high_value():
    return jsonify({"success": True, "data": ReportsModel.get_high_value_passengers()})


@app.route('/api/reports/itinerary')
def api_rep_itinerary():
    return jsonify({"success": True, "data": ReportsModel.get_full_itinerary(limit=50)})


# ------------------------------------------------------------------------------
# SQL Studio and database status
# ------------------------------------------------------------------------------
@app.route('/api/db/status')
def api_db_status():
    test = db.test_connection()
    tables = db.get_tables()
    base_tables = [t for t in tables if t.get('type') == 'BASE TABLE']
    return jsonify({
        "status": test,
        "engine": db.engine,
        "database": db.database,
        "host": db.host,
        "port": db.port,
        "user": db.user,
        "timezone": config.TIMEZONE_NAME,
        "server_time": now_ist(),
        "tables_count": len(base_tables),
        "tables": tables,
    })


@app.route('/api/db/tables')
def api_db_tables():
    return jsonify({"success": True, "data": db.get_tables()})


@app.route('/api/db/table/<table_name>')
def api_db_table_data(table_name):
    limit = min(int(request.args.get('limit', 50)), 500)
    offset = max(int(request.args.get('offset', 0)), 0)
    rows = db.get_table_data(table_name, limit, offset)
    return jsonify({
        "success": True,
        "table": table_name,
        "schema": db.get_table_schema(table_name),
        "rows": rows,
        "count": len(rows),
    })


@app.route('/api/db/query', methods=['POST'])
def api_db_query():
    data = request.get_json() or {}
    sql = (data.get('query') or '').strip()
    if not sql:
        return jsonify({"success": False, "error": "Query cannot be empty."}), 400
    return jsonify(db.run_raw_sql(sql))


@app.route('/api/db/configure', methods=['POST'])
def api_db_configure():
    return jsonify({
        "success": False,
        "error": (
            "This project is MySQL-only. Run database/airline_db.sql in "
            "MySQL Workbench once, then start the app."
        ),
    }), 410


# ------------------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    status = db.test_connection()
    if not status['success']:
        print('\n[!] Could not connect to MySQL.')
        print(f"    Host: {db.host}:{db.port}  User: {db.user}  Database: {db.database}")
        print(f"    Error: {status.get('error')}")
        print('\n    Run database/airline_db.sql once in MySQL Workbench as root.')
        print('    Then start the app again: python app.py\n')
        sys.exit(1)

    print(f"[*] Connected to MySQL {status['version']} at {db.host}:{db.port}/{db.database}")
    print(f"[*] Server time zone: {status['time_zone']}  |  App timezone: {config.TIMEZONE_NAME}")
    print(f"[*] Starting SkyReserve at http://127.0.0.1:{config.PORT}")
    app.run(host='127.0.0.1', port=config.PORT, debug=config.DEBUG)
