-- ==============================================================================
-- AIRLINE RESERVATION & FLEET MANAGEMENT SYSTEM (AeroReserve)
-- Database: airline_db
-- Normalized Relational Schema (3NF) for DBMS Project
-- Assessments: 8, 9, 10
-- ==============================================================================

DROP DATABASE IF EXISTS airline_db;
CREATE DATABASE airline_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE airline_db;

-- ------------------------------------------------------------------------------
-- 1. Airports Table
-- ------------------------------------------------------------------------------
CREATE TABLE airports (
    airport_code VARCHAR(3) PRIMARY KEY,
    airport_name VARCHAR(120) NOT NULL,
    city VARCHAR(60) NOT NULL,
    country VARCHAR(60) NOT NULL,
    timezone VARCHAR(40) NOT NULL DEFAULT 'UTC+05:30'
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. Airlines Table
-- ------------------------------------------------------------------------------
CREATE TABLE airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_code VARCHAR(5) NOT NULL UNIQUE,
    airline_name VARCHAR(100) NOT NULL,
    country VARCHAR(60) NOT NULL,
    status ENUM('ACTIVE', 'SUSPENDED') NOT NULL DEFAULT 'ACTIVE'
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. Aircrafts Table
-- ------------------------------------------------------------------------------
CREATE TABLE aircrafts (
    aircraft_id INT AUTO_INCREMENT PRIMARY KEY,
    model VARCHAR(60) NOT NULL,
    airline_id INT NOT NULL,
    total_seats INT NOT NULL,
    economy_seats INT NOT NULL,
    business_seats INT NOT NULL,
    first_seats INT NOT NULL,
    FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 4. Flights Table
-- ------------------------------------------------------------------------------
CREATE TABLE flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_number VARCHAR(15) NOT NULL UNIQUE,
    airline_id INT NOT NULL,
    aircraft_id INT NOT NULL,
    origin_code VARCHAR(3) NOT NULL,
    destination_code VARCHAR(3) NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    duration_mins INT NOT NULL,
    base_fare DECIMAL(10, 2) NOT NULL,
    status ENUM('SCHEDULED', 'ON_TIME', 'BOARDING', 'DELAYED', 'DEPARTED', 'CANCELLED') NOT NULL DEFAULT 'SCHEDULED',
    FOREIGN KEY (airline_id) REFERENCES airlines(airline_id) ON DELETE RESTRICT,
    FOREIGN KEY (aircraft_id) REFERENCES aircrafts(aircraft_id) ON DELETE RESTRICT,
    FOREIGN KEY (origin_code) REFERENCES airports(airport_code) ON DELETE RESTRICT,
    FOREIGN KEY (destination_code) REFERENCES airports(airport_code) ON DELETE RESTRICT,
    CONSTRAINT chk_flight_airports CHECK (origin_code <> destination_code),
    CONSTRAINT chk_flight_times CHECK (arrival_time > departure_time)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 5. Passengers Table
-- ------------------------------------------------------------------------------
CREATE TABLE passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    passport_number VARCHAR(30) NOT NULL UNIQUE,
    date_of_birth DATE NOT NULL,
    gender ENUM('MALE', 'FEMALE', 'OTHER') NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 6. Users Table (Authentication & RBAC)
-- ------------------------------------------------------------------------------
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'STAFF', 'PASSENGER') NOT NULL DEFAULT 'PASSENGER',
    passenger_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 7. Aircraft Seats Table
-- ------------------------------------------------------------------------------
CREATE TABLE seats (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    aircraft_id INT NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    seat_class ENUM('ECONOMY', 'BUSINESS', 'FIRST') NOT NULL DEFAULT 'ECONOMY',
    seat_type ENUM('WINDOW', 'AISLE', 'MIDDLE') NOT NULL DEFAULT 'AISLE',
    FOREIGN KEY (aircraft_id) REFERENCES aircrafts(aircraft_id) ON DELETE CASCADE,
    UNIQUE KEY uq_aircraft_seat (aircraft_id, seat_number)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 8. Bookings Table
-- ------------------------------------------------------------------------------
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    user_id INT NULL,
    passenger_id INT NOT NULL,
    flight_id INT NOT NULL,
    seat_number VARCHAR(5) NOT NULL,
    travel_class ENUM('ECONOMY', 'BUSINESS', 'FIRST') NOT NULL DEFAULT 'ECONOMY',
    booking_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('CONFIRMED', 'CANCELLED', 'CHECKED_IN', 'COMPLETED') NOT NULL DEFAULT 'CONFIRMED',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 9. Payments Table
-- ------------------------------------------------------------------------------
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    transaction_id VARCHAR(50) NOT NULL UNIQUE,
    payment_method ENUM('CREDIT_CARD', 'DEBIT_CARD', 'UPI', 'NET_BANKING', 'WALLET') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('SUCCESS', 'FAILED', 'REFUNDED') NOT NULL DEFAULT 'SUCCESS',
    payment_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 10. Audit Logs Table (For Database Operations Verification)
-- ------------------------------------------------------------------------------
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NULL,
    details TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- Indexes for High Performance & Query Optimization
-- ------------------------------------------------------------------------------
CREATE INDEX idx_flights_route ON flights(origin_code, destination_code, departure_time);
CREATE INDEX idx_bookings_pnr ON bookings(pnr);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_bookings_flight ON bookings(flight_id);
CREATE INDEX idx_passengers_email ON passengers(email);
