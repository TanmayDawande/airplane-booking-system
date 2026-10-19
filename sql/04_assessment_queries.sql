-- ==============================================================================
-- AIRLINE RESERVATION & FLEET MANAGEMENT SYSTEM (AeroReserve)
-- Assessment Demonstration SQL Queries Script
-- Specifically prepared for Assessments 8, 9, and 10 Presentation & Verification
-- ==============================================================================

USE airline_db;

-- ==============================================================================
-- ASSESSMENT 8: Front-End Design & Basic Database Connectivity Verification
-- ==============================================================================

-- 1. Proof of Database Connectivity & Table Listing
SHOW TABLES;

-- 2. Verify Schema Integrity of Key Tables
DESCRIBE passengers;
DESCRIBE flights;
DESCRIBE bookings;

-- 3. Enter a new record via Front-End (e.g., Passenger Registration)
-- Front-end executes parameterized INSERT:
-- INSERT INTO passengers (first_name, last_name, email, phone, passport_number, date_of_birth, gender)
-- VALUES ('Vikram', 'Malhotra', 'vikram.m@example.com', '+91-9811223344', 'X7766554', '1999-07-12', 'MALE');

-- 4. Retrieve the newly inserted record to verify storage
SELECT passenger_id, first_name, last_name, email, phone, passport_number, created_at
FROM passengers
ORDER BY passenger_id DESC
LIMIT 5;

-- 5. Verify direct table record matches front-end view
SELECT * FROM passengers WHERE email = 'vikram.m@example.com';


-- ==============================================================================
-- ASSESSMENT 9: Database Operations & Back-End Implementation Verification
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- A. CRUD OPERATIONS
-- ------------------------------------------------------------------------------

-- [SELECT] Filtered selection with pattern matching & status
SELECT flight_id, flight_number, origin_code, destination_code, departure_time, base_fare, status
FROM flights
WHERE status IN ('SCHEDULED', 'ON_TIME') 
  AND base_fare <= 10000.00
ORDER BY departure_time ASC;

-- [INSERT] Operational flight scheduling
INSERT INTO flights (flight_number, airline_id, aircraft_id, origin_code, destination_code, departure_time, arrival_time, duration_mins, base_fare, status)
VALUES ('AI-999', 1, 1, 'DEL', 'CCU', '2026-10-29 14:00:00', '2026-10-29 16:15:00', 135, 4700.00, 'SCHEDULED');

-- Verify insertion
SELECT * FROM flights WHERE flight_number = 'AI-999';

-- [UPDATE] Reschedule flight or modify base fare through the application
UPDATE flights 
SET base_fare = 4950.00, status = 'DELAYED'
WHERE flight_number = 'AI-999';

-- Verify update reflected in database
SELECT flight_id, flight_number, base_fare, status 
FROM flights 
WHERE flight_number = 'AI-999';

-- [DELETE] Remove test/cancelled flight from database
DELETE FROM flights WHERE flight_number = 'AI-999';

-- Verify deletion (must return 0 rows)
SELECT * FROM flights WHERE flight_number = 'AI-999';


-- ------------------------------------------------------------------------------
-- B. ADVANCED SQL QUERIES (Joins, Aggregation, Subqueries)
-- ------------------------------------------------------------------------------

-- QUERY 1: 5-Table INNER JOIN (Comprehensive Passenger Flight Schedule)
-- Demonstrates multi-table relational normalization navigation
SELECT 
    b.pnr AS [PNR Code],
    CONCAT(p.first_name, ' ', p.last_name) AS [Passenger Name],
    al.airline_name AS [Airline],
    f.flight_number AS [Flight No],
    orig.city AS [Origin City],
    dest.city AS [Destination City],
    f.departure_time AS [Departure],
    b.seat_number AS [Seat],
    b.travel_class AS [Class],
    b.total_amount AS [Fare (INR)],
    b.status AS [Booking Status]
FROM bookings b
JOIN passengers p ON b.passenger_id = p.passenger_id
JOIN flights f ON b.flight_id = f.flight_id
JOIN airlines al ON f.airline_id = al.airline_id
JOIN airports orig ON f.origin_code = orig.airport_code
JOIN airports dest ON f.destination_code = dest.airport_code
ORDER BY b.booking_date DESC;

-- QUERY 2: AGGREGATION & GROUP BY with HAVING (Airline Revenue Analysis)
-- Calculates total confirmed bookings, aggregate revenue, and average ticket yield
SELECT 
    al.airline_name AS Airline,
    COUNT(b.booking_id) AS Total_Confirmed_Bookings,
    SUM(b.total_amount) AS Gross_Revenue,
    ROUND(AVG(b.total_amount), 2) AS Average_Ticket_Price,
    MAX(b.total_amount) AS Highest_Fare_Sold
FROM airlines al
JOIN flights f ON al.airline_id = f.airline_id
JOIN bookings b ON f.flight_id = b.flight_id
WHERE b.status = 'CONFIRMED'
GROUP BY al.airline_id, al.airline_name
HAVING Gross_Revenue > 5000.00
ORDER BY Gross_Revenue DESC;

-- QUERY 3: NESTED SUBQUERY (High-Value Passengers Above Average Booking Value)
-- Demonstrates correlated subquery / scalar subquery filtering
SELECT 
    p.passenger_id,
    CONCAT(p.first_name, ' ', p.last_name) AS Full_Name,
    p.email,
    b.pnr,
    b.total_amount
FROM passengers p
JOIN bookings b ON p.passenger_id = b.passenger_id
WHERE b.total_amount > (
    SELECT AVG(total_amount) 
    FROM bookings 
    WHERE status = 'CONFIRMED'
)
ORDER BY b.total_amount DESC;

-- QUERY 4: SEAT OCCUPANCY PERCENTAGE BY FLIGHT (Mathematical Aggregation)
SELECT 
    f.flight_number,
    al.airline_code,
    ac.model,
    ac.total_seats,
    COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) AS Booked_Seats,
    (ac.total_seats - COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END)) AS Remaining_Seats,
    ROUND((COUNT(CASE WHEN b.status = 'CONFIRMED' THEN b.booking_id END) * 100.0 / ac.total_seats), 2) AS Occupancy_Rate_Pct
FROM flights f
JOIN airlines al ON f.airline_id = al.airline_id
JOIN aircrafts ac ON f.aircraft_id = ac.aircraft_id
LEFT JOIN bookings b ON f.flight_id = b.flight_id
GROUP BY f.flight_id, f.flight_number, al.airline_code, ac.model, ac.total_seats
ORDER BY Occupancy_Rate_Pct DESC;


-- ==============================================================================
-- ASSESSMENT 10: Complete Workflow & Transaction Validation
-- ==============================================================================

-- 1. Full Transactional Booking Execution (Atomicity: Insert Booking + Payment)
START TRANSACTION;

-- Step A: Insert Booking
INSERT INTO bookings (pnr, user_id, passenger_id, flight_id, seat_number, travel_class, total_amount, status)
VALUES ('AERO999Z', 3, 1, 101, '11A', 'ECONOMY', 5400.00, 'CONFIRMED');

-- Step B: Retrieve Last Generated ID & Insert Payment Record
INSERT INTO payments (booking_id, transaction_id, payment_method, amount, payment_status)
VALUES (LAST_INSERT_ID(), 'TXN_AERO_DEMO_10_VAL', 'UPI', 5400.00, 'SUCCESS');

COMMIT;

-- 2. Verify complete transaction record in database
SELECT 
    b.pnr, b.seat_number, b.travel_class, b.status AS booking_status,
    pay.transaction_id, pay.payment_method, pay.amount, pay.payment_status
FROM bookings b
JOIN payments pay ON b.booking_id = pay.booking_id
WHERE b.pnr = 'AERO999Z';

-- 3. Verify Automatic Audit Log Trigger execution
SELECT * FROM audit_logs ORDER BY log_id DESC LIMIT 5;

-- 4. Rollback demonstration in case of payment failure
START TRANSACTION;
INSERT INTO bookings (pnr, user_id, passenger_id, flight_id, seat_number, travel_class, total_amount, status)
VALUES ('AEROFAIL01', 3, 1, 101, '11B', 'ECONOMY', 5400.00, 'CONFIRMED');
-- Simulated payment failure -> Rollback
ROLLBACK;

-- Verify failed booking was NOT inserted
SELECT * FROM bookings WHERE pnr = 'AEROFAIL01';
