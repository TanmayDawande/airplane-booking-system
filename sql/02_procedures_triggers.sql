-- ==============================================================================
-- AIRLINE RESERVATION & FLEET MANAGEMENT SYSTEM
-- Triggers, Stored Procedures, and Analytical Views
-- For Assessment 9 & 10 Verification
-- ==============================================================================

USE airline_db;

DELIMITER $$

-- ------------------------------------------------------------------------------
-- TRIGGER 1: trg_after_booking_insert
-- Automatically records an audit log when a new booking is created
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_after_booking_insert$$
CREATE TRIGGER trg_after_booking_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES (
        'INSERT_BOOKING',
        'bookings',
        NEW.booking_id,
        CONCAT('PNR: ', NEW.pnr, ' created for Flight ID: ', NEW.flight_id, ', Seat: ', NEW.seat_number, ', Amount: INR ', NEW.total_amount)
    );
END$$

-- ------------------------------------------------------------------------------
-- TRIGGER 2: trg_after_booking_update
-- Automatically records status changes or seat updates in audit_logs
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_after_booking_update$$
CREATE TRIGGER trg_after_booking_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_logs (action_type, table_name, record_id, details)
        VALUES (
            'UPDATE_BOOKING_STATUS',
            'bookings',
            NEW.booking_id,
            CONCAT('Booking PNR: ', NEW.pnr, ' status changed from ', OLD.status, ' to ', NEW.status)
        );
    END IF;
    IF OLD.seat_number <> NEW.seat_number THEN
        INSERT INTO audit_logs (action_type, table_name, record_id, details)
        VALUES (
            'UPDATE_BOOKING_SEAT',
            'bookings',
            NEW.booking_id,
            CONCAT('Booking PNR: ', NEW.pnr, ' seat changed from ', OLD.seat_number, ' to ', NEW.seat_number)
        );
    END IF;
END$$

-- ------------------------------------------------------------------------------
-- TRIGGER 3: trg_after_flight_update
-- Logs schedule and flight status alterations
-- ------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_after_flight_update$$
CREATE TRIGGER trg_after_flight_update
AFTER UPDATE ON flights
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES (
        'UPDATE_FLIGHT',
        'flights',
        NEW.flight_id,
        CONCAT('Flight ', NEW.flight_number, ' status: ', OLD.status, ' -> ', NEW.status, ', Fare: ', OLD.base_fare, ' -> ', NEW.base_fare)
    );
END$$

-- ------------------------------------------------------------------------------
-- STORED PROCEDURE 1: sp_GetFlightOccupancy
-- Calculates total seats, booked seats, available seats, and revenue for a flight
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_GetFlightOccupancy$$
CREATE PROCEDURE sp_GetFlightOccupancy(IN p_flight_id INT)
BEGIN
    SELECT 
        f.flight_id,
        f.flight_number,
        al.airline_name,
        ac.model AS aircraft_model,
        ac.total_seats,
        COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) AS booked_seats,
        (ac.total_seats - COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END)) AS available_seats,
        ROUND((COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) / ac.total_seats) * 100, 2) AS occupancy_percentage,
        COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE 0 END), 0) AS total_revenue
    FROM flights f
    JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
    JOIN airlines al ON f.airline_id = al.airline_id
    LEFT JOIN bookings b ON f.flight_id = b.flight_id
    WHERE f.flight_id = p_flight_id
    GROUP BY f.flight_id, f.flight_number, al.airline_name, ac.model, ac.total_seats;
END$$

-- ------------------------------------------------------------------------------
-- STORED PROCEDURE 2: sp_CancelBooking
-- Transactional booking cancellation with refund calculation and status update
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_CancelBooking$$
CREATE PROCEDURE sp_CancelBooking(IN p_pnr VARCHAR(10), OUT p_message VARCHAR(100))
BEGIN
    DECLARE v_booking_id INT;
    DECLARE v_current_status VARCHAR(20);
    
    SELECT booking_id, status INTO v_booking_id, v_current_status
    FROM bookings WHERE pnr = p_pnr;
    
    IF v_booking_id IS NULL THEN
        SET p_message = 'ERROR: Booking with given PNR not found.';
    ELSEIF v_current_status = 'CANCELLED' THEN
        SET p_message = 'NOTICE: Booking is already cancelled.';
    ELSE
        START TRANSACTION;
        UPDATE bookings SET status = 'CANCELLED' WHERE booking_id = v_booking_id;
        UPDATE payments SET payment_status = 'REFUNDED' WHERE booking_id = v_booking_id;
        COMMIT;
        SET p_message = 'SUCCESS: Booking cancelled and refund processed.';
    END IF;
END$$

DELIMITER ;

-- ------------------------------------------------------------------------------
-- VIEW 1: vw_flight_details (Multi-table 5-way JOIN)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_flight_details AS
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

-- ------------------------------------------------------------------------------
-- VIEW 2: vw_booking_summary (Comprehensive 6-way JOIN)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_booking_summary AS
SELECT 
    b.booking_id,
    b.pnr,
    b.booking_date,
    b.travel_class,
    b.seat_number,
    b.total_amount,
    b.status AS booking_status,
    p.passenger_id,
    CONCAT(p.first_name, ' ', p.last_name) AS passenger_name,
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

-- ------------------------------------------------------------------------------
-- VIEW 3: vw_revenue_by_airline (Aggregation & Group By)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_revenue_by_airline AS
SELECT 
    al.airline_code,
    al.airline_name,
    COUNT(DISTINCT f.flight_id) AS scheduled_flights,
    COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) AS confirmed_bookings,
    COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE 0 END), 0) AS total_revenue,
    COALESCE(AVG(CASE WHEN b.status = 'CONFIRMED' THEN b.total_amount ELSE NULL END), 0) AS average_ticket_fare
FROM airlines al
LEFT JOIN flights f ON al.airline_id = f.airline_id
LEFT JOIN bookings b ON f.flight_id = b.flight_id
GROUP BY al.airline_id, al.airline_code, al.airline_name;

-- ------------------------------------------------------------------------------
-- VIEW 4: vw_busiest_airports (Aggregation & Ranking)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_busiest_airports AS
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
ORDER BY total_traffic DESC;
