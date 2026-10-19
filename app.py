import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import db
from models import UserModel, PassengerModel, FlightModel, BookingModel, ReportsModel
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ------------------------------------------------------------------------------
# Context Processors (Injects DB status & current user to all templates)
# ------------------------------------------------------------------------------
@app.context_processor
def inject_global_vars():
    user = None
    if 'user_id' in session:
        user = UserModel.get_by_id(session['user_id'])
    
    db_info = {
        "engine": db.engine.upper(),
        "database": db.database if db.engine == 'mysql' else 'airline_db.sqlite3',
        "host": f"{db.host}:{db.port}" if db.engine == 'mysql' else 'Local File'
    }
    return dict(current_user=user, db_info=db_info)

# ------------------------------------------------------------------------------
# Frontend Page Routes
# ------------------------------------------------------------------------------
@app.route('/')
def index():
    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    stats = ReportsModel.get_system_summary()
    featured_flights = FlightModel.search()[:6]
    return render_template('index.html', airports=airports, stats=stats, featured_flights=featured_flights)

@app.route('/flights')
def flights_page():
    origin = request.args.get('origin', '')
    dest = request.args.get('destination', '')
    travel_date = request.args.get('date', '')
    travel_class = request.args.get('class', 'ECONOMY')
    max_price = request.args.get('max_price', '')

    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    results = FlightModel.search(origin=origin, destination=dest, travel_date=travel_date, travel_class=travel_class, max_price=max_price)
    return render_template('flights.html', flights=results, airports=airports, origin=origin, dest=dest, travel_date=travel_date, travel_class=travel_class, max_price=max_price)

@app.route('/book/<int:flight_id>')
def booking_page(flight_id):
    flight = FlightModel.get_by_id(flight_id)
    if not flight:
        return redirect(url_for('flights_page'))
    seat_rows = FlightModel.get_seat_rows(flight_id)
    return render_template('booking.html', flight=flight, seat_rows=seat_rows)

@app.route('/ticket/<pnr>')
def ticket_page(pnr):
    booking = BookingModel.get_by_pnr(pnr)
    if not booking:
        return render_template('ticket.html', booking=None, error=f"PNR '{pnr}' not found.")
    return render_template('ticket.html', booking=booking, error=None)

@app.route('/my-bookings')
def my_bookings_page():
    pnr_query = request.args.get('pnr', '').strip().upper()
    searched_booking = None
    if pnr_query:
        searched_booking = BookingModel.get_by_pnr(pnr_query)

    user_bookings = []
    if 'user_id' in session:
        user_bookings = BookingModel.get_by_user(session['user_id'])

    recent_bookings = BookingModel.get_all(limit=10)
    return render_template('my_bookings.html', searched_booking=searched_booking, user_bookings=user_bookings, recent_bookings=recent_bookings, pnr_query=pnr_query)

@app.route('/admin')
def admin_page():
    # Allow viewing admin dashboard for presentation convenience
    flights = FlightModel.search()
    airlines = db.execute_query("SELECT * FROM airlines ORDER BY airline_name ASC")
    aircrafts = db.execute_query("SELECT * FROM aircrafts ORDER BY model ASC")
    airports = db.execute_query("SELECT * FROM airports ORDER BY city ASC")
    passengers = PassengerModel.get_all(limit=50)
    bookings = BookingModel.get_all(limit=50)
    audit_logs = ReportsModel.get_audit_logs(limit=25)
    return render_template('admin.html', flights=flights, airlines=airlines, aircrafts=aircrafts, airports=airports, passengers=passengers, bookings=bookings, audit_logs=audit_logs)

@app.route('/reports')
def reports_page():
    rev_by_airline = ReportsModel.get_revenue_by_airline()
    busiest_airports = ReportsModel.get_busiest_airports()
    occupancy = ReportsModel.get_occupancy_report()
    high_value_pax = ReportsModel.get_high_value_passengers()
    audit_logs = ReportsModel.get_audit_logs(limit=30)
    summary = ReportsModel.get_system_summary()
    return render_template('reports.html', rev_by_airline=rev_by_airline, busiest_airports=busiest_airports, occupancy=occupancy, high_value_pax=high_value_pax, audit_logs=audit_logs, summary=summary)

@app.route('/db-studio')
def db_studio_page():
    tables = db.get_tables()
    return render_template('db_studio.html', tables=tables)

@app.route('/guide')
def guide_page():
    return render_template('assessment_guide.html')

# ------------------------------------------------------------------------------
# Authentication APIs
# ------------------------------------------------------------------------------
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = UserModel.authenticate(username, password)
    if not user:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    return jsonify({"success": True, "user": user})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    try:
        user = UserModel.register(
            username=data.get('username'),
            password=data.get('password'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            phone=data.get('phone'),
            passport_number=data.get('passport_number'),
            dob=data.get('dob', '2000-01-01'),
            gender=data.get('gender', 'MALE'),
            role=data.get('role', 'PASSENGER')
        )
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({"success": True, "user": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/auth/current')
def api_current_user():
    if 'user_id' in session:
        user = UserModel.get_by_id(session['user_id'])
        return jsonify({"authenticated": True, "user": user})
    return jsonify({"authenticated": False, "user": None})

# ------------------------------------------------------------------------------
# Flight APIs (Assessment 8, 9 CRUD)
# ------------------------------------------------------------------------------
@app.route('/api/flights', methods=['GET', 'POST'])
def api_flights():
    if request.method == 'GET':
        flights = FlightModel.search(
            origin=request.args.get('origin'),
            destination=request.args.get('destination'),
            travel_date=request.args.get('date'),
            travel_class=request.args.get('class', 'ECONOMY'),
            max_price=request.args.get('max_price')
        )
        return jsonify({"success": True, "data": flights})
    else: # POST: Create new flight (Assessment 9 INSERT)
        data = request.get_json() or {}
        try:
            new_flight = FlightModel.create(
                flight_number=data['flight_number'],
                airline_id=int(data['airline_id']),
                aircraft_id=int(data['aircraft_id']),
                origin=data['origin_code'],
                destination=data['destination_code'],
                dep_time=data['departure_time'],
                arr_time=data['arrival_time'],
                duration=int(data.get('duration_mins') or data.get('duration_minutes', 120)),
                fare=float(data['base_fare']),
                status=data.get('status', 'SCHEDULED')
            )
            return jsonify({"success": True, "data": new_flight, "message": f"Flight {new_flight['flight_number']} scheduled successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/flights/<int:flight_id>', methods=['GET', 'PUT', 'DELETE'])
def api_flight_detail(flight_id):
    if request.method == 'GET':
        flight = FlightModel.get_by_id(flight_id)
        if not flight:
            return jsonify({"success": False, "error": "Flight not found"}), 404
        return jsonify({"success": True, "data": flight})
    elif request.method == 'PUT': # Assessment 9 UPDATE
        data = request.get_json() or {}
        try:
            updated = FlightModel.update(
                flight_id=flight_id,
                base_fare=float(data.get('base_fare')),
                status=data.get('status'),
                dep_time=data.get('departure_time'),
                arr_time=data.get('arrival_time')
            )
            return jsonify({"success": True, "data": updated, "message": f"Flight {updated['flight_number']} updated successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    elif request.method == 'DELETE': # Assessment 9 DELETE
        try:
            FlightModel.delete(flight_id)
            return jsonify({"success": True, "message": f"Flight #{flight_id} deleted successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/flights/<int:flight_id>/seats')
def api_flight_seats(flight_id):
    seats = FlightModel.get_seat_map(flight_id)
    return jsonify({"success": True, "data": seats})

# ------------------------------------------------------------------------------
# Passenger APIs (Assessment 8 Insertion & Retrieval, Assessment 9 CRUD)
# ------------------------------------------------------------------------------
@app.route('/api/passengers', methods=['GET', 'POST'])
def api_passengers():
    if request.method == 'GET':
        search = request.args.get('q', '').strip()
        if search:
            res = PassengerModel.search(search)
        else:
            res = PassengerModel.get_all(limit=int(request.args.get('limit', 50)))
        return jsonify({"success": True, "data": res})
    else: # POST: Assessment 8 Insert a new passenger record
        data = request.get_json() or {}
        try:
            new_pax = PassengerModel.create(
                first_name=data.get('first_name', '').strip(),
                last_name=data.get('last_name', '').strip(),
                email=data.get('email', '').strip(),
                phone=data.get('phone', '').strip(),
                passport_number=data.get('passport_number', '').strip(),
                dob=data.get('date_of_birth', '2000-01-01'),
                gender=data.get('gender', 'MALE')
            )
            return jsonify({
                "success": True,
                "data": new_pax,
                "message": f"Passenger {new_pax['first_name']} {new_pax['last_name']} added successfully (ID: {new_pax['passenger_id']})."
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/passengers/<int:passenger_id>', methods=['GET', 'PUT', 'DELETE'])
def api_passenger_detail(passenger_id):
    if request.method == 'GET': # Assessment 8 Retrieve newly inserted record
        pax = PassengerModel.get_by_id(passenger_id)
        if not pax:
            return jsonify({"success": False, "error": "Passenger not found"}), 404
        return jsonify({"success": True, "data": pax})
    elif request.method == 'PUT': # Assessment 9 UPDATE
        data = request.get_json() or {}
        try:
            updated = PassengerModel.update(
                passenger_id=passenger_id,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                email=data.get('email'),
                phone=data.get('phone'),
                passport_number=data.get('passport_number')
            )
            return jsonify({"success": True, "data": updated, "message": "Passenger updated successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    elif request.method == 'DELETE': # Assessment 9 DELETE
        try:
            PassengerModel.delete(passenger_id)
            return jsonify({"success": True, "message": f"Passenger #{passenger_id} deleted successfully."})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

# ------------------------------------------------------------------------------
# Booking & Transaction Workflow APIs (Assessment 10)
# ------------------------------------------------------------------------------
@app.route('/api/bookings', methods=['POST'])
def api_create_booking():
    data = request.get_json() or {}
    flight_id = data.get('flight_id')
    seat_number = data.get('seat_number')
    travel_class = data.get('travel_class', 'ECONOMY')
    payment_method = data.get('payment_method', 'UPI')
    passenger_data = data.get('passenger', {})
    user_id = session.get('user_id')

    try:
        booking = BookingModel.create_booking_flow(
            flight_id=int(flight_id),
            passenger_data=passenger_data,
            seat_number=seat_number,
            travel_class=travel_class,
            payment_method=payment_method,
            user_id=user_id
        )
        return jsonify({
            "success": True,
            "data": booking,
            "pnr": booking['pnr'],
            "message": f"Booking confirmed! PNR: {booking['pnr']}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/bookings/<pnr>', methods=['GET'])
def api_get_booking(pnr):
    booking = BookingModel.get_by_pnr(pnr)
    if not booking:
        return jsonify({"success": False, "error": "Booking not found"}), 404
    return jsonify({"success": True, "data": booking})

@app.route('/api/bookings/<pnr>/cancel', methods=['POST'])
def api_cancel_booking(pnr):
    try:
        res = BookingModel.cancel(pnr)
        return jsonify({
            "success": True,
            "data": res,
            "message": f"Booking {pnr} has been successfully cancelled and refund initiated."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/bookings/<pnr>/change-seat', methods=['POST'])
def api_change_seat(pnr):
    data = request.get_json() or {}
    new_seat = data.get('seat_number', '').strip().upper()
    try:
        res = BookingModel.update_seat(pnr, new_seat)
        return jsonify({
            "success": True,
            "data": res,
            "message": f"Seat for booking {pnr} changed to {new_seat} successfully."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ------------------------------------------------------------------------------
# Reports & Analytics APIs (Assessment 9 & 10)
# ------------------------------------------------------------------------------
@app.route('/api/reports/revenue-by-airline')
def api_rep_revenue():
    return jsonify({"success": True, "data": ReportsModel.get_revenue_by_airline()})

@app.route('/api/reports/occupancy')
def api_rep_occupancy():
    return jsonify({"success": True, "data": ReportsModel.get_occupancy_report()})

@app.route('/api/reports/busiest-airports')
def api_rep_airports():
    return jsonify({"success": True, "data": ReportsModel.get_busiest_airports()})

@app.route('/api/reports/high-value-passengers')
def api_rep_high_value():
    return jsonify({"success": True, "data": ReportsModel.get_high_value_passengers()})

# ------------------------------------------------------------------------------
# Database Studio & Connection Management APIs
# ------------------------------------------------------------------------------
@app.route('/api/db/status')
def api_db_status():
    test = db.test_connection()
    tables = db.get_tables()
    return jsonify({
        "status": test,
        "engine": db.engine,
        "database": db.database if db.engine == 'mysql' else 'airline_db.sqlite3',
        "host": db.host if db.engine == 'mysql' else 'Local File',
        "port": db.port if db.engine == 'mysql' else None,
        "user": db.user if db.engine == 'mysql' else None,
        "tables_count": len(tables)
    })

@app.route('/api/db/tables')
def api_db_tables():
    tables = db.get_tables()
    return jsonify({"success": True, "data": tables})

@app.route('/api/db/table/<table_name>')
def api_db_table_data(table_name):
    schema = db.get_table_schema(table_name)
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    rows = db.get_table_data(table_name, limit, offset)
    return jsonify({
        "success": True,
        "table": table_name,
        "schema": schema,
        "rows": rows,
        "count": len(rows)
    })

@app.route('/api/db/query', methods=['POST'])
def api_db_query():
    data = request.get_json() or {}
    sql = data.get('query', '')
    if not sql:
        return jsonify({"success": False, "error": "Query cannot be empty"}), 400
    res = db.run_raw_sql(sql)
    return jsonify(res)

@app.route('/api/db/configure', methods=['POST'])
def api_db_configure():
    data = request.get_json() or {}
    engine = data.get('engine', 'sqlite').lower()
    host = data.get('host', 'localhost')
    port = data.get('port', 3306)
    user = data.get('user', 'root')
    password = data.get('password', '')
    dbname = data.get('database', 'airline_db')

    # Test before switching
    test = db.test_connection(host=host, port=port, user=user, password=password, database=dbname, engine=engine)
    if not test['success']:
        return jsonify({"success": False, "error": f"Failed to connect: {test.get('error')}"}), 400

    db.set_config(engine=engine, host=host, port=port, user=user, password=password, database=dbname)
    return jsonify({"success": True, "message": f"Database switched to {engine.upper()} successfully!", "details": test})

# ------------------------------------------------------------------------------
# Server Entrypoint
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    print(f"[*] Starting AeroReserve Airline Reservation System on http://127.0.0.1:{config.PORT}")
    app.run(host='127.0.0.1', port=config.PORT, debug=config.DEBUG)
