-- ==============================================================================
-- SkyReserve - Airline Reservation System (MySQL 8.0)
-- Complete database setup for MySQL Workbench
-- ==============================================================================
--
-- HOW TO USE THIS FILE
--   1. Open MySQL Workbench.
--   2. Connect to your local MySQL server (localhost:3306) as root.
--   3. Open this file with File > Open SQL Script.
--   4. Run the whole file with the lightning icon (or Ctrl+Shift+Enter).
--   5. Refresh SCHEMAS, select `airline_db`, and run:
--          SELECT * FROM flights;
--
-- The script creates:
--   * the airline_db schema
--   * 10 normalized tables, indexes, triggers, stored procedures and views
--   * the app user `airline_app` with password `airline123`
--   * the current demo data, with all generated timestamps in IST
--
-- New app timestamps are written in IST because the Flask connection sets
-- time_zone = '+05:30'. This script also sets it for the Workbench session.
-- ==============================================================================

SET NAMES utf8mb4;
SET time_zone = '+05:30';

DROP DATABASE IF EXISTS airline_db;
CREATE DATABASE airline_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE airline_db;

-- The Flask application uses this account. Change the password here and in
-- config.py / the DB_PASSWORD environment variable if required.
CREATE USER IF NOT EXISTS 'airline_app'@'localhost' IDENTIFIED BY 'airline123';
ALTER USER 'airline_app'@'localhost' IDENTIFIED BY 'airline123';
GRANT ALL PRIVILEGES ON airline_db.* TO 'airline_app'@'localhost';

-- Also allow the TCP host used by config.py (127.0.0.1). This matters on
-- MySQL servers with skip_name_resolve enabled.
CREATE USER IF NOT EXISTS 'airline_app'@'127.0.0.1' IDENTIFIED BY 'airline123';
ALTER USER 'airline_app'@'127.0.0.1' IDENTIFIED BY 'airline123';
GRANT ALL PRIVILEGES ON airline_db.* TO 'airline_app'@'127.0.0.1';

FLUSH PRIVILEGES;


-- ------------------------------------------------------------------------------

-- Tables and indexes

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


-- ------------------------------------------------------------------------------

-- Demo data

-- ------------------------------------------------------------------------------

INSERT INTO airports (airport_code, airport_name, city, country, timezone) VALUES
('DEL', 'Indira Gandhi International Airport', 'New Delhi', 'India', 'UTC+05:30'),
('BOM', 'Chhatrapati Shivaji Maharaj International Airport', 'Mumbai', 'India', 'UTC+05:30'),
('BLR', 'Kempegowda International Airport', 'Bengaluru', 'India', 'UTC+05:30'),
('HYD', 'Rajiv Gandhi International Airport', 'Hyderabad', 'India', 'UTC+05:30'),
('MAA', 'Chennai International Airport', 'Chennai', 'India', 'UTC+05:30'),
('CCU', 'Netaji Subhash Chandra Bose International Airport', 'Kolkata', 'India', 'UTC+05:30'),
('GOI', 'Dabolim Airport', 'Goa', 'India', 'UTC+05:30'),
('DXB', 'Dubai International Airport', 'Dubai', 'United Arab Emirates', 'UTC+04:00'),
('LHR', 'Heathrow Airport', 'London', 'United Kingdom', 'UTC+00:00'),
('JFK', 'John F. Kennedy International Airport', 'New York', 'United States', 'UTC-05:00');


INSERT INTO airlines (airline_id, airline_code, airline_name, country, status) VALUES
(1, 'AI', 'Air India', 'India', 'ACTIVE'),
(2, '6E', 'IndiGo Airlines', 'India', 'ACTIVE'),
(3, 'UK', 'Vistara', 'India', 'ACTIVE'),
(4, 'SG', 'SpiceJet', 'India', 'ACTIVE'),
(5, 'EK', 'Emirates', 'United Arab Emirates', 'ACTIVE'),
(6, 'BA', 'British Airways', 'United Kingdom', 'ACTIVE');


INSERT INTO aircrafts (aircraft_id, model, airline_id, total_seats, economy_seats, business_seats, first_seats) VALUES
(1, 'Boeing 777-300ER', 1, 342, 276, 54, 12),
(2, 'Airbus A320neo', 2, 186, 186, 0, 0),
(3, 'Boeing 787-9 Dreamliner', 3, 296, 240, 48, 8),
(4, 'Boeing 737-800', 4, 189, 177, 12, 0),
(5, 'Airbus A380-800', 5, 516, 426, 76, 14),
(6, 'Boeing 777-200LR', 6, 275, 219, 48, 8);


INSERT INTO seats (seat_id, aircraft_id, seat_number, seat_class, seat_type) VALUES
(64, 1, '1A', 'FIRST', 'WINDOW'),
(65, 1, '1B', 'FIRST', 'MIDDLE'),
(66, 1, '1C', 'FIRST', 'AISLE'),
(67, 1, '1D', 'FIRST', 'AISLE'),
(68, 1, '1E', 'FIRST', 'MIDDLE'),
(69, 1, '1F', 'FIRST', 'WINDOW'),
(70, 1, '2A', 'FIRST', 'WINDOW'),
(71, 1, '2B', 'FIRST', 'MIDDLE'),
(72, 1, '2C', 'FIRST', 'AISLE'),
(73, 1, '2D', 'FIRST', 'AISLE'),
(74, 1, '2E', 'FIRST', 'MIDDLE'),
(75, 1, '2F', 'FIRST', 'WINDOW'),
(76, 1, '3A', 'BUSINESS', 'WINDOW'),
(77, 1, '3B', 'BUSINESS', 'MIDDLE'),
(78, 1, '3C', 'BUSINESS', 'AISLE'),
(79, 1, '3D', 'BUSINESS', 'AISLE'),
(80, 1, '3E', 'BUSINESS', 'MIDDLE'),
(81, 1, '3F', 'BUSINESS', 'WINDOW'),
(82, 1, '4A', 'BUSINESS', 'WINDOW'),
(83, 1, '4B', 'BUSINESS', 'MIDDLE'),
(84, 1, '4C', 'BUSINESS', 'AISLE'),
(85, 1, '4D', 'BUSINESS', 'AISLE'),
(86, 1, '4E', 'BUSINESS', 'MIDDLE'),
(87, 1, '4F', 'BUSINESS', 'WINDOW'),
(88, 1, '5A', 'BUSINESS', 'WINDOW'),
(89, 1, '5B', 'BUSINESS', 'MIDDLE'),
(90, 1, '5C', 'BUSINESS', 'AISLE'),
(91, 1, '5D', 'BUSINESS', 'AISLE'),
(92, 1, '5E', 'BUSINESS', 'MIDDLE'),
(93, 1, '5F', 'BUSINESS', 'WINDOW'),
(94, 1, '6A', 'ECONOMY', 'WINDOW'),
(95, 1, '6B', 'ECONOMY', 'MIDDLE'),
(96, 1, '6C', 'ECONOMY', 'AISLE'),
(97, 1, '6D', 'ECONOMY', 'AISLE'),
(98, 1, '6E', 'ECONOMY', 'MIDDLE'),
(99, 1, '6F', 'ECONOMY', 'WINDOW'),
(100, 1, '7A', 'ECONOMY', 'WINDOW'),
(101, 1, '7B', 'ECONOMY', 'MIDDLE'),
(102, 1, '7C', 'ECONOMY', 'AISLE'),
(103, 1, '7D', 'ECONOMY', 'AISLE'),
(104, 1, '7E', 'ECONOMY', 'MIDDLE'),
(105, 1, '7F', 'ECONOMY', 'WINDOW'),
(106, 1, '8A', 'ECONOMY', 'WINDOW'),
(107, 1, '8B', 'ECONOMY', 'MIDDLE'),
(108, 1, '8C', 'ECONOMY', 'AISLE'),
(109, 1, '8D', 'ECONOMY', 'AISLE'),
(110, 1, '8E', 'ECONOMY', 'MIDDLE'),
(111, 1, '8F', 'ECONOMY', 'WINDOW'),
(112, 1, '9A', 'ECONOMY', 'WINDOW'),
(113, 1, '9B', 'ECONOMY', 'MIDDLE'),
(114, 1, '9C', 'ECONOMY', 'AISLE'),
(115, 1, '9D', 'ECONOMY', 'AISLE'),
(116, 1, '9E', 'ECONOMY', 'MIDDLE'),
(117, 1, '9F', 'ECONOMY', 'WINDOW'),
(118, 1, '10A', 'ECONOMY', 'WINDOW'),
(119, 1, '10B', 'ECONOMY', 'MIDDLE'),
(120, 1, '10C', 'ECONOMY', 'AISLE'),
(121, 1, '10D', 'ECONOMY', 'AISLE'),
(122, 1, '10E', 'ECONOMY', 'MIDDLE'),
(123, 1, '10F', 'ECONOMY', 'WINDOW'),
(124, 1, '11A', 'ECONOMY', 'WINDOW'),
(125, 1, '11B', 'ECONOMY', 'MIDDLE'),
(126, 1, '11C', 'ECONOMY', 'AISLE'),
(127, 1, '11D', 'ECONOMY', 'AISLE'),
(128, 1, '11E', 'ECONOMY', 'MIDDLE'),
(129, 1, '11F', 'ECONOMY', 'WINDOW'),
(130, 1, '12A', 'ECONOMY', 'WINDOW'),
(131, 1, '12B', 'ECONOMY', 'MIDDLE'),
(132, 1, '12C', 'ECONOMY', 'AISLE'),
(133, 1, '12D', 'ECONOMY', 'AISLE'),
(134, 1, '12E', 'ECONOMY', 'MIDDLE'),
(135, 1, '12F', 'ECONOMY', 'WINDOW'),
(136, 1, '13A', 'ECONOMY', 'WINDOW'),
(137, 1, '13B', 'ECONOMY', 'MIDDLE'),
(138, 1, '13C', 'ECONOMY', 'AISLE'),
(139, 1, '13D', 'ECONOMY', 'AISLE'),
(140, 1, '13E', 'ECONOMY', 'MIDDLE'),
(141, 1, '13F', 'ECONOMY', 'WINDOW'),
(142, 1, '14A', 'ECONOMY', 'WINDOW'),
(143, 1, '14B', 'ECONOMY', 'MIDDLE'),
(144, 1, '14C', 'ECONOMY', 'AISLE'),
(145, 1, '14D', 'ECONOMY', 'AISLE'),
(146, 1, '14E', 'ECONOMY', 'MIDDLE'),
(147, 1, '14F', 'ECONOMY', 'WINDOW'),
(148, 1, '15A', 'ECONOMY', 'WINDOW'),
(149, 1, '15B', 'ECONOMY', 'MIDDLE'),
(150, 1, '15C', 'ECONOMY', 'AISLE'),
(151, 1, '15D', 'ECONOMY', 'AISLE'),
(152, 1, '15E', 'ECONOMY', 'MIDDLE'),
(153, 1, '15F', 'ECONOMY', 'WINDOW'),
(154, 1, '16A', 'ECONOMY', 'WINDOW'),
(155, 1, '16B', 'ECONOMY', 'MIDDLE'),
(156, 1, '16C', 'ECONOMY', 'AISLE'),
(157, 1, '16D', 'ECONOMY', 'AISLE'),
(158, 1, '16E', 'ECONOMY', 'MIDDLE'),
(159, 1, '16F', 'ECONOMY', 'WINDOW'),
(160, 1, '17A', 'ECONOMY', 'WINDOW'),
(161, 1, '17B', 'ECONOMY', 'MIDDLE'),
(162, 1, '17C', 'ECONOMY', 'AISLE'),
(163, 1, '17D', 'ECONOMY', 'AISLE'),
(164, 1, '17E', 'ECONOMY', 'MIDDLE'),
(165, 1, '17F', 'ECONOMY', 'WINDOW'),
(166, 1, '18A', 'ECONOMY', 'WINDOW'),
(167, 1, '18B', 'ECONOMY', 'MIDDLE'),
(168, 1, '18C', 'ECONOMY', 'AISLE'),
(169, 1, '18D', 'ECONOMY', 'AISLE'),
(170, 1, '18E', 'ECONOMY', 'MIDDLE'),
(171, 1, '18F', 'ECONOMY', 'WINDOW'),
(172, 1, '19A', 'ECONOMY', 'WINDOW'),
(173, 1, '19B', 'ECONOMY', 'MIDDLE'),
(174, 1, '19C', 'ECONOMY', 'AISLE'),
(175, 1, '19D', 'ECONOMY', 'AISLE'),
(176, 1, '19E', 'ECONOMY', 'MIDDLE'),
(177, 1, '19F', 'ECONOMY', 'WINDOW'),
(178, 1, '20A', 'ECONOMY', 'WINDOW'),
(179, 1, '20B', 'ECONOMY', 'MIDDLE'),
(180, 1, '20C', 'ECONOMY', 'AISLE'),
(181, 1, '20D', 'ECONOMY', 'AISLE'),
(182, 1, '20E', 'ECONOMY', 'MIDDLE'),
(183, 1, '20F', 'ECONOMY', 'WINDOW'),
(184, 1, '21A', 'ECONOMY', 'WINDOW'),
(185, 1, '21B', 'ECONOMY', 'MIDDLE'),
(186, 1, '21C', 'ECONOMY', 'AISLE'),
(187, 1, '21D', 'ECONOMY', 'AISLE'),
(188, 1, '21E', 'ECONOMY', 'MIDDLE'),
(189, 1, '21F', 'ECONOMY', 'WINDOW'),
(190, 1, '22A', 'ECONOMY', 'WINDOW'),
(191, 1, '22B', 'ECONOMY', 'MIDDLE'),
(192, 1, '22C', 'ECONOMY', 'AISLE'),
(193, 1, '22D', 'ECONOMY', 'AISLE'),
(194, 1, '22E', 'ECONOMY', 'MIDDLE'),
(195, 1, '22F', 'ECONOMY', 'WINDOW'),
(196, 1, '23A', 'ECONOMY', 'WINDOW'),
(197, 1, '23B', 'ECONOMY', 'MIDDLE'),
(198, 1, '23C', 'ECONOMY', 'AISLE'),
(199, 1, '23D', 'ECONOMY', 'AISLE'),
(200, 1, '23E', 'ECONOMY', 'MIDDLE'),
(201, 1, '23F', 'ECONOMY', 'WINDOW'),
(202, 1, '24A', 'ECONOMY', 'WINDOW'),
(203, 1, '24B', 'ECONOMY', 'MIDDLE'),
(204, 1, '24C', 'ECONOMY', 'AISLE'),
(205, 1, '24D', 'ECONOMY', 'AISLE'),
(206, 1, '24E', 'ECONOMY', 'MIDDLE'),
(207, 1, '24F', 'ECONOMY', 'WINDOW'),
(208, 2, '1A', 'FIRST', 'WINDOW'),
(209, 2, '1B', 'FIRST', 'MIDDLE'),
(210, 2, '1C', 'FIRST', 'AISLE'),
(211, 2, '1D', 'FIRST', 'AISLE'),
(212, 2, '1E', 'FIRST', 'MIDDLE'),
(213, 2, '1F', 'FIRST', 'WINDOW'),
(214, 2, '2A', 'FIRST', 'WINDOW'),
(215, 2, '2B', 'FIRST', 'MIDDLE'),
(216, 2, '2C', 'FIRST', 'AISLE'),
(217, 2, '2D', 'FIRST', 'AISLE'),
(218, 2, '2E', 'FIRST', 'MIDDLE'),
(219, 2, '2F', 'FIRST', 'WINDOW'),
(220, 2, '3A', 'BUSINESS', 'WINDOW'),
(221, 2, '3B', 'BUSINESS', 'MIDDLE'),
(222, 2, '3C', 'BUSINESS', 'AISLE'),
(223, 2, '3D', 'BUSINESS', 'AISLE'),
(224, 2, '3E', 'BUSINESS', 'MIDDLE'),
(225, 2, '3F', 'BUSINESS', 'WINDOW'),
(226, 2, '4A', 'BUSINESS', 'WINDOW'),
(227, 2, '4B', 'BUSINESS', 'MIDDLE'),
(228, 2, '4C', 'BUSINESS', 'AISLE'),
(229, 2, '4D', 'BUSINESS', 'AISLE'),
(230, 2, '4E', 'BUSINESS', 'MIDDLE'),
(231, 2, '4F', 'BUSINESS', 'WINDOW'),
(232, 2, '5A', 'BUSINESS', 'WINDOW'),
(233, 2, '5B', 'BUSINESS', 'MIDDLE'),
(234, 2, '5C', 'BUSINESS', 'AISLE'),
(235, 2, '5D', 'BUSINESS', 'AISLE'),
(236, 2, '5E', 'BUSINESS', 'MIDDLE'),
(237, 2, '5F', 'BUSINESS', 'WINDOW'),
(238, 2, '6A', 'ECONOMY', 'WINDOW'),
(239, 2, '6B', 'ECONOMY', 'MIDDLE'),
(240, 2, '6C', 'ECONOMY', 'AISLE'),
(241, 2, '6D', 'ECONOMY', 'AISLE'),
(242, 2, '6E', 'ECONOMY', 'MIDDLE'),
(243, 2, '6F', 'ECONOMY', 'WINDOW'),
(244, 2, '7A', 'ECONOMY', 'WINDOW'),
(245, 2, '7B', 'ECONOMY', 'MIDDLE'),
(246, 2, '7C', 'ECONOMY', 'AISLE'),
(247, 2, '7D', 'ECONOMY', 'AISLE'),
(248, 2, '7E', 'ECONOMY', 'MIDDLE'),
(249, 2, '7F', 'ECONOMY', 'WINDOW'),
(250, 2, '8A', 'ECONOMY', 'WINDOW'),
(251, 2, '8B', 'ECONOMY', 'MIDDLE'),
(252, 2, '8C', 'ECONOMY', 'AISLE'),
(253, 2, '8D', 'ECONOMY', 'AISLE'),
(254, 2, '8E', 'ECONOMY', 'MIDDLE'),
(255, 2, '8F', 'ECONOMY', 'WINDOW'),
(256, 2, '9A', 'ECONOMY', 'WINDOW'),
(257, 2, '9B', 'ECONOMY', 'MIDDLE'),
(258, 2, '9C', 'ECONOMY', 'AISLE'),
(259, 2, '9D', 'ECONOMY', 'AISLE'),
(260, 2, '9E', 'ECONOMY', 'MIDDLE'),
(261, 2, '9F', 'ECONOMY', 'WINDOW'),
(262, 2, '10A', 'ECONOMY', 'WINDOW'),
(263, 2, '10B', 'ECONOMY', 'MIDDLE'),
(264, 2, '10C', 'ECONOMY', 'AISLE'),
(265, 2, '10D', 'ECONOMY', 'AISLE'),
(266, 2, '10E', 'ECONOMY', 'MIDDLE'),
(267, 2, '10F', 'ECONOMY', 'WINDOW'),
(268, 2, '11A', 'ECONOMY', 'WINDOW'),
(269, 2, '11B', 'ECONOMY', 'MIDDLE'),
(270, 2, '11C', 'ECONOMY', 'AISLE'),
(271, 2, '11D', 'ECONOMY', 'AISLE'),
(272, 2, '11E', 'ECONOMY', 'MIDDLE'),
(273, 2, '11F', 'ECONOMY', 'WINDOW'),
(274, 2, '12A', 'ECONOMY', 'WINDOW'),
(275, 2, '12B', 'ECONOMY', 'MIDDLE'),
(276, 2, '12C', 'ECONOMY', 'AISLE'),
(277, 2, '12D', 'ECONOMY', 'AISLE'),
(278, 2, '12E', 'ECONOMY', 'MIDDLE'),
(279, 2, '12F', 'ECONOMY', 'WINDOW'),
(280, 2, '13A', 'ECONOMY', 'WINDOW'),
(281, 2, '13B', 'ECONOMY', 'MIDDLE'),
(282, 2, '13C', 'ECONOMY', 'AISLE'),
(283, 2, '13D', 'ECONOMY', 'AISLE'),
(284, 2, '13E', 'ECONOMY', 'MIDDLE'),
(285, 2, '13F', 'ECONOMY', 'WINDOW'),
(286, 2, '14A', 'ECONOMY', 'WINDOW'),
(287, 2, '14B', 'ECONOMY', 'MIDDLE'),
(288, 2, '14C', 'ECONOMY', 'AISLE'),
(289, 2, '14D', 'ECONOMY', 'AISLE'),
(290, 2, '14E', 'ECONOMY', 'MIDDLE'),
(291, 2, '14F', 'ECONOMY', 'WINDOW'),
(292, 2, '15A', 'ECONOMY', 'WINDOW'),
(293, 2, '15B', 'ECONOMY', 'MIDDLE'),
(294, 2, '15C', 'ECONOMY', 'AISLE'),
(295, 2, '15D', 'ECONOMY', 'AISLE'),
(296, 2, '15E', 'ECONOMY', 'MIDDLE'),
(297, 2, '15F', 'ECONOMY', 'WINDOW'),
(298, 2, '16A', 'ECONOMY', 'WINDOW'),
(299, 2, '16B', 'ECONOMY', 'MIDDLE'),
(300, 2, '16C', 'ECONOMY', 'AISLE'),
(301, 2, '16D', 'ECONOMY', 'AISLE'),
(302, 2, '16E', 'ECONOMY', 'MIDDLE'),
(303, 2, '16F', 'ECONOMY', 'WINDOW'),
(304, 2, '17A', 'ECONOMY', 'WINDOW'),
(305, 2, '17B', 'ECONOMY', 'MIDDLE'),
(306, 2, '17C', 'ECONOMY', 'AISLE'),
(307, 2, '17D', 'ECONOMY', 'AISLE'),
(308, 2, '17E', 'ECONOMY', 'MIDDLE'),
(309, 2, '17F', 'ECONOMY', 'WINDOW'),
(310, 2, '18A', 'ECONOMY', 'WINDOW'),
(311, 2, '18B', 'ECONOMY', 'MIDDLE'),
(312, 2, '18C', 'ECONOMY', 'AISLE'),
(313, 2, '18D', 'ECONOMY', 'AISLE'),
(314, 2, '18E', 'ECONOMY', 'MIDDLE'),
(315, 2, '18F', 'ECONOMY', 'WINDOW'),
(316, 2, '19A', 'ECONOMY', 'WINDOW'),
(317, 2, '19B', 'ECONOMY', 'MIDDLE'),
(318, 2, '19C', 'ECONOMY', 'AISLE'),
(319, 2, '19D', 'ECONOMY', 'AISLE'),
(320, 2, '19E', 'ECONOMY', 'MIDDLE'),
(321, 2, '19F', 'ECONOMY', 'WINDOW'),
(322, 2, '20A', 'ECONOMY', 'WINDOW'),
(323, 2, '20B', 'ECONOMY', 'MIDDLE'),
(324, 2, '20C', 'ECONOMY', 'AISLE'),
(325, 2, '20D', 'ECONOMY', 'AISLE'),
(326, 2, '20E', 'ECONOMY', 'MIDDLE'),
(327, 2, '20F', 'ECONOMY', 'WINDOW'),
(328, 2, '21A', 'ECONOMY', 'WINDOW'),
(329, 2, '21B', 'ECONOMY', 'MIDDLE'),
(330, 2, '21C', 'ECONOMY', 'AISLE'),
(331, 2, '21D', 'ECONOMY', 'AISLE'),
(332, 2, '21E', 'ECONOMY', 'MIDDLE'),
(333, 2, '21F', 'ECONOMY', 'WINDOW'),
(334, 2, '22A', 'ECONOMY', 'WINDOW'),
(335, 2, '22B', 'ECONOMY', 'MIDDLE'),
(336, 2, '22C', 'ECONOMY', 'AISLE'),
(337, 2, '22D', 'ECONOMY', 'AISLE'),
(338, 2, '22E', 'ECONOMY', 'MIDDLE'),
(339, 2, '22F', 'ECONOMY', 'WINDOW'),
(340, 2, '23A', 'ECONOMY', 'WINDOW'),
(341, 2, '23B', 'ECONOMY', 'MIDDLE'),
(342, 2, '23C', 'ECONOMY', 'AISLE'),
(343, 2, '23D', 'ECONOMY', 'AISLE'),
(344, 2, '23E', 'ECONOMY', 'MIDDLE'),
(345, 2, '23F', 'ECONOMY', 'WINDOW'),
(346, 2, '24A', 'ECONOMY', 'WINDOW'),
(347, 2, '24B', 'ECONOMY', 'MIDDLE'),
(348, 2, '24C', 'ECONOMY', 'AISLE'),
(349, 2, '24D', 'ECONOMY', 'AISLE'),
(350, 2, '24E', 'ECONOMY', 'MIDDLE'),
(351, 2, '24F', 'ECONOMY', 'WINDOW'),
(352, 3, '1A', 'FIRST', 'WINDOW'),
(353, 3, '1B', 'FIRST', 'MIDDLE'),
(354, 3, '1C', 'FIRST', 'AISLE'),
(355, 3, '1D', 'FIRST', 'AISLE'),
(356, 3, '1E', 'FIRST', 'MIDDLE'),
(357, 3, '1F', 'FIRST', 'WINDOW'),
(358, 3, '2A', 'FIRST', 'WINDOW'),
(359, 3, '2B', 'FIRST', 'MIDDLE'),
(360, 3, '2C', 'FIRST', 'AISLE'),
(361, 3, '2D', 'FIRST', 'AISLE'),
(362, 3, '2E', 'FIRST', 'MIDDLE'),
(363, 3, '2F', 'FIRST', 'WINDOW'),
(364, 3, '3A', 'BUSINESS', 'WINDOW'),
(365, 3, '3B', 'BUSINESS', 'MIDDLE'),
(366, 3, '3C', 'BUSINESS', 'AISLE'),
(367, 3, '3D', 'BUSINESS', 'AISLE'),
(368, 3, '3E', 'BUSINESS', 'MIDDLE'),
(369, 3, '3F', 'BUSINESS', 'WINDOW'),
(370, 3, '4A', 'BUSINESS', 'WINDOW'),
(371, 3, '4B', 'BUSINESS', 'MIDDLE'),
(372, 3, '4C', 'BUSINESS', 'AISLE'),
(373, 3, '4D', 'BUSINESS', 'AISLE'),
(374, 3, '4E', 'BUSINESS', 'MIDDLE'),
(375, 3, '4F', 'BUSINESS', 'WINDOW'),
(376, 3, '5A', 'BUSINESS', 'WINDOW'),
(377, 3, '5B', 'BUSINESS', 'MIDDLE'),
(378, 3, '5C', 'BUSINESS', 'AISLE'),
(379, 3, '5D', 'BUSINESS', 'AISLE'),
(380, 3, '5E', 'BUSINESS', 'MIDDLE'),
(381, 3, '5F', 'BUSINESS', 'WINDOW'),
(382, 3, '6A', 'ECONOMY', 'WINDOW'),
(383, 3, '6B', 'ECONOMY', 'MIDDLE'),
(384, 3, '6C', 'ECONOMY', 'AISLE'),
(385, 3, '6D', 'ECONOMY', 'AISLE'),
(386, 3, '6E', 'ECONOMY', 'MIDDLE'),
(387, 3, '6F', 'ECONOMY', 'WINDOW'),
(388, 3, '7A', 'ECONOMY', 'WINDOW'),
(389, 3, '7B', 'ECONOMY', 'MIDDLE'),
(390, 3, '7C', 'ECONOMY', 'AISLE'),
(391, 3, '7D', 'ECONOMY', 'AISLE'),
(392, 3, '7E', 'ECONOMY', 'MIDDLE'),
(393, 3, '7F', 'ECONOMY', 'WINDOW'),
(394, 3, '8A', 'ECONOMY', 'WINDOW'),
(395, 3, '8B', 'ECONOMY', 'MIDDLE'),
(396, 3, '8C', 'ECONOMY', 'AISLE'),
(397, 3, '8D', 'ECONOMY', 'AISLE'),
(398, 3, '8E', 'ECONOMY', 'MIDDLE'),
(399, 3, '8F', 'ECONOMY', 'WINDOW'),
(400, 3, '9A', 'ECONOMY', 'WINDOW'),
(401, 3, '9B', 'ECONOMY', 'MIDDLE'),
(402, 3, '9C', 'ECONOMY', 'AISLE'),
(403, 3, '9D', 'ECONOMY', 'AISLE'),
(404, 3, '9E', 'ECONOMY', 'MIDDLE'),
(405, 3, '9F', 'ECONOMY', 'WINDOW'),
(406, 3, '10A', 'ECONOMY', 'WINDOW'),
(407, 3, '10B', 'ECONOMY', 'MIDDLE'),
(408, 3, '10C', 'ECONOMY', 'AISLE'),
(409, 3, '10D', 'ECONOMY', 'AISLE'),
(410, 3, '10E', 'ECONOMY', 'MIDDLE'),
(411, 3, '10F', 'ECONOMY', 'WINDOW'),
(412, 3, '11A', 'ECONOMY', 'WINDOW'),
(413, 3, '11B', 'ECONOMY', 'MIDDLE'),
(414, 3, '11C', 'ECONOMY', 'AISLE'),
(415, 3, '11D', 'ECONOMY', 'AISLE'),
(416, 3, '11E', 'ECONOMY', 'MIDDLE'),
(417, 3, '11F', 'ECONOMY', 'WINDOW'),
(418, 3, '12A', 'ECONOMY', 'WINDOW'),
(419, 3, '12B', 'ECONOMY', 'MIDDLE'),
(420, 3, '12C', 'ECONOMY', 'AISLE'),
(421, 3, '12D', 'ECONOMY', 'AISLE'),
(422, 3, '12E', 'ECONOMY', 'MIDDLE'),
(423, 3, '12F', 'ECONOMY', 'WINDOW'),
(424, 3, '13A', 'ECONOMY', 'WINDOW'),
(425, 3, '13B', 'ECONOMY', 'MIDDLE'),
(426, 3, '13C', 'ECONOMY', 'AISLE'),
(427, 3, '13D', 'ECONOMY', 'AISLE'),
(428, 3, '13E', 'ECONOMY', 'MIDDLE'),
(429, 3, '13F', 'ECONOMY', 'WINDOW'),
(430, 3, '14A', 'ECONOMY', 'WINDOW'),
(431, 3, '14B', 'ECONOMY', 'MIDDLE'),
(432, 3, '14C', 'ECONOMY', 'AISLE'),
(433, 3, '14D', 'ECONOMY', 'AISLE'),
(434, 3, '14E', 'ECONOMY', 'MIDDLE'),
(435, 3, '14F', 'ECONOMY', 'WINDOW'),
(436, 3, '15A', 'ECONOMY', 'WINDOW'),
(437, 3, '15B', 'ECONOMY', 'MIDDLE'),
(438, 3, '15C', 'ECONOMY', 'AISLE'),
(439, 3, '15D', 'ECONOMY', 'AISLE'),
(440, 3, '15E', 'ECONOMY', 'MIDDLE'),
(441, 3, '15F', 'ECONOMY', 'WINDOW'),
(442, 3, '16A', 'ECONOMY', 'WINDOW'),
(443, 3, '16B', 'ECONOMY', 'MIDDLE'),
(444, 3, '16C', 'ECONOMY', 'AISLE'),
(445, 3, '16D', 'ECONOMY', 'AISLE'),
(446, 3, '16E', 'ECONOMY', 'MIDDLE'),
(447, 3, '16F', 'ECONOMY', 'WINDOW'),
(448, 3, '17A', 'ECONOMY', 'WINDOW'),
(449, 3, '17B', 'ECONOMY', 'MIDDLE'),
(450, 3, '17C', 'ECONOMY', 'AISLE'),
(451, 3, '17D', 'ECONOMY', 'AISLE'),
(452, 3, '17E', 'ECONOMY', 'MIDDLE'),
(453, 3, '17F', 'ECONOMY', 'WINDOW'),
(454, 3, '18A', 'ECONOMY', 'WINDOW'),
(455, 3, '18B', 'ECONOMY', 'MIDDLE'),
(456, 3, '18C', 'ECONOMY', 'AISLE'),
(457, 3, '18D', 'ECONOMY', 'AISLE'),
(458, 3, '18E', 'ECONOMY', 'MIDDLE'),
(459, 3, '18F', 'ECONOMY', 'WINDOW'),
(460, 3, '19A', 'ECONOMY', 'WINDOW'),
(461, 3, '19B', 'ECONOMY', 'MIDDLE'),
(462, 3, '19C', 'ECONOMY', 'AISLE'),
(463, 3, '19D', 'ECONOMY', 'AISLE'),
(464, 3, '19E', 'ECONOMY', 'MIDDLE'),
(465, 3, '19F', 'ECONOMY', 'WINDOW'),
(466, 3, '20A', 'ECONOMY', 'WINDOW'),
(467, 3, '20B', 'ECONOMY', 'MIDDLE'),
(468, 3, '20C', 'ECONOMY', 'AISLE'),
(469, 3, '20D', 'ECONOMY', 'AISLE'),
(470, 3, '20E', 'ECONOMY', 'MIDDLE'),
(471, 3, '20F', 'ECONOMY', 'WINDOW'),
(472, 3, '21A', 'ECONOMY', 'WINDOW'),
(473, 3, '21B', 'ECONOMY', 'MIDDLE'),
(474, 3, '21C', 'ECONOMY', 'AISLE'),
(475, 3, '21D', 'ECONOMY', 'AISLE'),
(476, 3, '21E', 'ECONOMY', 'MIDDLE'),
(477, 3, '21F', 'ECONOMY', 'WINDOW'),
(478, 3, '22A', 'ECONOMY', 'WINDOW'),
(479, 3, '22B', 'ECONOMY', 'MIDDLE'),
(480, 3, '22C', 'ECONOMY', 'AISLE'),
(481, 3, '22D', 'ECONOMY', 'AISLE'),
(482, 3, '22E', 'ECONOMY', 'MIDDLE'),
(483, 3, '22F', 'ECONOMY', 'WINDOW'),
(484, 3, '23A', 'ECONOMY', 'WINDOW'),
(485, 3, '23B', 'ECONOMY', 'MIDDLE'),
(486, 3, '23C', 'ECONOMY', 'AISLE'),
(487, 3, '23D', 'ECONOMY', 'AISLE'),
(488, 3, '23E', 'ECONOMY', 'MIDDLE'),
(489, 3, '23F', 'ECONOMY', 'WINDOW'),
(490, 3, '24A', 'ECONOMY', 'WINDOW'),
(491, 3, '24B', 'ECONOMY', 'MIDDLE'),
(492, 3, '24C', 'ECONOMY', 'AISLE'),
(493, 3, '24D', 'ECONOMY', 'AISLE'),
(494, 3, '24E', 'ECONOMY', 'MIDDLE'),
(495, 3, '24F', 'ECONOMY', 'WINDOW'),
(496, 4, '1A', 'FIRST', 'WINDOW'),
(497, 4, '1B', 'FIRST', 'MIDDLE'),
(498, 4, '1C', 'FIRST', 'AISLE'),
(499, 4, '1D', 'FIRST', 'AISLE'),
(500, 4, '1E', 'FIRST', 'MIDDLE'),
(501, 4, '1F', 'FIRST', 'WINDOW'),
(502, 4, '2A', 'FIRST', 'WINDOW'),
(503, 4, '2B', 'FIRST', 'MIDDLE'),
(504, 4, '2C', 'FIRST', 'AISLE'),
(505, 4, '2D', 'FIRST', 'AISLE'),
(506, 4, '2E', 'FIRST', 'MIDDLE'),
(507, 4, '2F', 'FIRST', 'WINDOW'),
(508, 4, '3A', 'BUSINESS', 'WINDOW'),
(509, 4, '3B', 'BUSINESS', 'MIDDLE'),
(510, 4, '3C', 'BUSINESS', 'AISLE'),
(511, 4, '3D', 'BUSINESS', 'AISLE'),
(512, 4, '3E', 'BUSINESS', 'MIDDLE'),
(513, 4, '3F', 'BUSINESS', 'WINDOW'),
(514, 4, '4A', 'BUSINESS', 'WINDOW'),
(515, 4, '4B', 'BUSINESS', 'MIDDLE'),
(516, 4, '4C', 'BUSINESS', 'AISLE'),
(517, 4, '4D', 'BUSINESS', 'AISLE'),
(518, 4, '4E', 'BUSINESS', 'MIDDLE'),
(519, 4, '4F', 'BUSINESS', 'WINDOW'),
(520, 4, '5A', 'BUSINESS', 'WINDOW'),
(521, 4, '5B', 'BUSINESS', 'MIDDLE'),
(522, 4, '5C', 'BUSINESS', 'AISLE'),
(523, 4, '5D', 'BUSINESS', 'AISLE'),
(524, 4, '5E', 'BUSINESS', 'MIDDLE'),
(525, 4, '5F', 'BUSINESS', 'WINDOW'),
(526, 4, '6A', 'ECONOMY', 'WINDOW'),
(527, 4, '6B', 'ECONOMY', 'MIDDLE'),
(528, 4, '6C', 'ECONOMY', 'AISLE'),
(529, 4, '6D', 'ECONOMY', 'AISLE'),
(530, 4, '6E', 'ECONOMY', 'MIDDLE'),
(531, 4, '6F', 'ECONOMY', 'WINDOW'),
(532, 4, '7A', 'ECONOMY', 'WINDOW'),
(533, 4, '7B', 'ECONOMY', 'MIDDLE'),
(534, 4, '7C', 'ECONOMY', 'AISLE'),
(535, 4, '7D', 'ECONOMY', 'AISLE'),
(536, 4, '7E', 'ECONOMY', 'MIDDLE'),
(537, 4, '7F', 'ECONOMY', 'WINDOW'),
(538, 4, '8A', 'ECONOMY', 'WINDOW'),
(539, 4, '8B', 'ECONOMY', 'MIDDLE'),
(540, 4, '8C', 'ECONOMY', 'AISLE'),
(541, 4, '8D', 'ECONOMY', 'AISLE'),
(542, 4, '8E', 'ECONOMY', 'MIDDLE'),
(543, 4, '8F', 'ECONOMY', 'WINDOW'),
(544, 4, '9A', 'ECONOMY', 'WINDOW'),
(545, 4, '9B', 'ECONOMY', 'MIDDLE'),
(546, 4, '9C', 'ECONOMY', 'AISLE'),
(547, 4, '9D', 'ECONOMY', 'AISLE'),
(548, 4, '9E', 'ECONOMY', 'MIDDLE'),
(549, 4, '9F', 'ECONOMY', 'WINDOW'),
(550, 4, '10A', 'ECONOMY', 'WINDOW'),
(551, 4, '10B', 'ECONOMY', 'MIDDLE'),
(552, 4, '10C', 'ECONOMY', 'AISLE'),
(553, 4, '10D', 'ECONOMY', 'AISLE'),
(554, 4, '10E', 'ECONOMY', 'MIDDLE'),
(555, 4, '10F', 'ECONOMY', 'WINDOW'),
(556, 4, '11A', 'ECONOMY', 'WINDOW'),
(557, 4, '11B', 'ECONOMY', 'MIDDLE'),
(558, 4, '11C', 'ECONOMY', 'AISLE'),
(559, 4, '11D', 'ECONOMY', 'AISLE'),
(560, 4, '11E', 'ECONOMY', 'MIDDLE'),
(561, 4, '11F', 'ECONOMY', 'WINDOW'),
(562, 4, '12A', 'ECONOMY', 'WINDOW'),
(563, 4, '12B', 'ECONOMY', 'MIDDLE'),
(564, 4, '12C', 'ECONOMY', 'AISLE'),
(565, 4, '12D', 'ECONOMY', 'AISLE'),
(566, 4, '12E', 'ECONOMY', 'MIDDLE'),
(567, 4, '12F', 'ECONOMY', 'WINDOW'),
(568, 4, '13A', 'ECONOMY', 'WINDOW'),
(569, 4, '13B', 'ECONOMY', 'MIDDLE'),
(570, 4, '13C', 'ECONOMY', 'AISLE'),
(571, 4, '13D', 'ECONOMY', 'AISLE'),
(572, 4, '13E', 'ECONOMY', 'MIDDLE'),
(573, 4, '13F', 'ECONOMY', 'WINDOW'),
(574, 4, '14A', 'ECONOMY', 'WINDOW'),
(575, 4, '14B', 'ECONOMY', 'MIDDLE'),
(576, 4, '14C', 'ECONOMY', 'AISLE'),
(577, 4, '14D', 'ECONOMY', 'AISLE'),
(578, 4, '14E', 'ECONOMY', 'MIDDLE'),
(579, 4, '14F', 'ECONOMY', 'WINDOW'),
(580, 4, '15A', 'ECONOMY', 'WINDOW'),
(581, 4, '15B', 'ECONOMY', 'MIDDLE'),
(582, 4, '15C', 'ECONOMY', 'AISLE'),
(583, 4, '15D', 'ECONOMY', 'AISLE'),
(584, 4, '15E', 'ECONOMY', 'MIDDLE'),
(585, 4, '15F', 'ECONOMY', 'WINDOW'),
(586, 4, '16A', 'ECONOMY', 'WINDOW'),
(587, 4, '16B', 'ECONOMY', 'MIDDLE'),
(588, 4, '16C', 'ECONOMY', 'AISLE'),
(589, 4, '16D', 'ECONOMY', 'AISLE'),
(590, 4, '16E', 'ECONOMY', 'MIDDLE'),
(591, 4, '16F', 'ECONOMY', 'WINDOW'),
(592, 4, '17A', 'ECONOMY', 'WINDOW'),
(593, 4, '17B', 'ECONOMY', 'MIDDLE'),
(594, 4, '17C', 'ECONOMY', 'AISLE'),
(595, 4, '17D', 'ECONOMY', 'AISLE'),
(596, 4, '17E', 'ECONOMY', 'MIDDLE'),
(597, 4, '17F', 'ECONOMY', 'WINDOW'),
(598, 4, '18A', 'ECONOMY', 'WINDOW'),
(599, 4, '18B', 'ECONOMY', 'MIDDLE'),
(600, 4, '18C', 'ECONOMY', 'AISLE'),
(601, 4, '18D', 'ECONOMY', 'AISLE'),
(602, 4, '18E', 'ECONOMY', 'MIDDLE'),
(603, 4, '18F', 'ECONOMY', 'WINDOW'),
(604, 4, '19A', 'ECONOMY', 'WINDOW'),
(605, 4, '19B', 'ECONOMY', 'MIDDLE'),
(606, 4, '19C', 'ECONOMY', 'AISLE'),
(607, 4, '19D', 'ECONOMY', 'AISLE'),
(608, 4, '19E', 'ECONOMY', 'MIDDLE'),
(609, 4, '19F', 'ECONOMY', 'WINDOW'),
(610, 4, '20A', 'ECONOMY', 'WINDOW'),
(611, 4, '20B', 'ECONOMY', 'MIDDLE'),
(612, 4, '20C', 'ECONOMY', 'AISLE'),
(613, 4, '20D', 'ECONOMY', 'AISLE'),
(614, 4, '20E', 'ECONOMY', 'MIDDLE'),
(615, 4, '20F', 'ECONOMY', 'WINDOW'),
(616, 4, '21A', 'ECONOMY', 'WINDOW'),
(617, 4, '21B', 'ECONOMY', 'MIDDLE'),
(618, 4, '21C', 'ECONOMY', 'AISLE'),
(619, 4, '21D', 'ECONOMY', 'AISLE'),
(620, 4, '21E', 'ECONOMY', 'MIDDLE'),
(621, 4, '21F', 'ECONOMY', 'WINDOW'),
(622, 4, '22A', 'ECONOMY', 'WINDOW'),
(623, 4, '22B', 'ECONOMY', 'MIDDLE'),
(624, 4, '22C', 'ECONOMY', 'AISLE'),
(625, 4, '22D', 'ECONOMY', 'AISLE'),
(626, 4, '22E', 'ECONOMY', 'MIDDLE'),
(627, 4, '22F', 'ECONOMY', 'WINDOW'),
(628, 4, '23A', 'ECONOMY', 'WINDOW'),
(629, 4, '23B', 'ECONOMY', 'MIDDLE'),
(630, 4, '23C', 'ECONOMY', 'AISLE'),
(631, 4, '23D', 'ECONOMY', 'AISLE'),
(632, 4, '23E', 'ECONOMY', 'MIDDLE'),
(633, 4, '23F', 'ECONOMY', 'WINDOW'),
(634, 4, '24A', 'ECONOMY', 'WINDOW'),
(635, 4, '24B', 'ECONOMY', 'MIDDLE'),
(636, 4, '24C', 'ECONOMY', 'AISLE'),
(637, 4, '24D', 'ECONOMY', 'AISLE'),
(638, 4, '24E', 'ECONOMY', 'MIDDLE'),
(639, 4, '24F', 'ECONOMY', 'WINDOW'),
(640, 5, '1A', 'FIRST', 'WINDOW'),
(641, 5, '1B', 'FIRST', 'MIDDLE'),
(642, 5, '1C', 'FIRST', 'AISLE'),
(643, 5, '1D', 'FIRST', 'AISLE'),
(644, 5, '1E', 'FIRST', 'MIDDLE'),
(645, 5, '1F', 'FIRST', 'WINDOW'),
(646, 5, '2A', 'FIRST', 'WINDOW'),
(647, 5, '2B', 'FIRST', 'MIDDLE'),
(648, 5, '2C', 'FIRST', 'AISLE'),
(649, 5, '2D', 'FIRST', 'AISLE'),
(650, 5, '2E', 'FIRST', 'MIDDLE'),
(651, 5, '2F', 'FIRST', 'WINDOW'),
(652, 5, '3A', 'BUSINESS', 'WINDOW'),
(653, 5, '3B', 'BUSINESS', 'MIDDLE'),
(654, 5, '3C', 'BUSINESS', 'AISLE'),
(655, 5, '3D', 'BUSINESS', 'AISLE'),
(656, 5, '3E', 'BUSINESS', 'MIDDLE'),
(657, 5, '3F', 'BUSINESS', 'WINDOW'),
(658, 5, '4A', 'BUSINESS', 'WINDOW'),
(659, 5, '4B', 'BUSINESS', 'MIDDLE'),
(660, 5, '4C', 'BUSINESS', 'AISLE'),
(661, 5, '4D', 'BUSINESS', 'AISLE'),
(662, 5, '4E', 'BUSINESS', 'MIDDLE'),
(663, 5, '4F', 'BUSINESS', 'WINDOW'),
(664, 5, '5A', 'BUSINESS', 'WINDOW'),
(665, 5, '5B', 'BUSINESS', 'MIDDLE'),
(666, 5, '5C', 'BUSINESS', 'AISLE'),
(667, 5, '5D', 'BUSINESS', 'AISLE'),
(668, 5, '5E', 'BUSINESS', 'MIDDLE'),
(669, 5, '5F', 'BUSINESS', 'WINDOW'),
(670, 5, '6A', 'ECONOMY', 'WINDOW'),
(671, 5, '6B', 'ECONOMY', 'MIDDLE'),
(672, 5, '6C', 'ECONOMY', 'AISLE'),
(673, 5, '6D', 'ECONOMY', 'AISLE'),
(674, 5, '6E', 'ECONOMY', 'MIDDLE'),
(675, 5, '6F', 'ECONOMY', 'WINDOW'),
(676, 5, '7A', 'ECONOMY', 'WINDOW'),
(677, 5, '7B', 'ECONOMY', 'MIDDLE'),
(678, 5, '7C', 'ECONOMY', 'AISLE'),
(679, 5, '7D', 'ECONOMY', 'AISLE'),
(680, 5, '7E', 'ECONOMY', 'MIDDLE'),
(681, 5, '7F', 'ECONOMY', 'WINDOW'),
(682, 5, '8A', 'ECONOMY', 'WINDOW'),
(683, 5, '8B', 'ECONOMY', 'MIDDLE'),
(684, 5, '8C', 'ECONOMY', 'AISLE'),
(685, 5, '8D', 'ECONOMY', 'AISLE'),
(686, 5, '8E', 'ECONOMY', 'MIDDLE'),
(687, 5, '8F', 'ECONOMY', 'WINDOW'),
(688, 5, '9A', 'ECONOMY', 'WINDOW'),
(689, 5, '9B', 'ECONOMY', 'MIDDLE'),
(690, 5, '9C', 'ECONOMY', 'AISLE'),
(691, 5, '9D', 'ECONOMY', 'AISLE'),
(692, 5, '9E', 'ECONOMY', 'MIDDLE'),
(693, 5, '9F', 'ECONOMY', 'WINDOW'),
(694, 5, '10A', 'ECONOMY', 'WINDOW'),
(695, 5, '10B', 'ECONOMY', 'MIDDLE'),
(696, 5, '10C', 'ECONOMY', 'AISLE'),
(697, 5, '10D', 'ECONOMY', 'AISLE'),
(698, 5, '10E', 'ECONOMY', 'MIDDLE'),
(699, 5, '10F', 'ECONOMY', 'WINDOW'),
(700, 5, '11A', 'ECONOMY', 'WINDOW'),
(701, 5, '11B', 'ECONOMY', 'MIDDLE'),
(702, 5, '11C', 'ECONOMY', 'AISLE'),
(703, 5, '11D', 'ECONOMY', 'AISLE'),
(704, 5, '11E', 'ECONOMY', 'MIDDLE'),
(705, 5, '11F', 'ECONOMY', 'WINDOW'),
(706, 5, '12A', 'ECONOMY', 'WINDOW'),
(707, 5, '12B', 'ECONOMY', 'MIDDLE'),
(708, 5, '12C', 'ECONOMY', 'AISLE'),
(709, 5, '12D', 'ECONOMY', 'AISLE'),
(710, 5, '12E', 'ECONOMY', 'MIDDLE'),
(711, 5, '12F', 'ECONOMY', 'WINDOW'),
(712, 5, '13A', 'ECONOMY', 'WINDOW'),
(713, 5, '13B', 'ECONOMY', 'MIDDLE'),
(714, 5, '13C', 'ECONOMY', 'AISLE'),
(715, 5, '13D', 'ECONOMY', 'AISLE'),
(716, 5, '13E', 'ECONOMY', 'MIDDLE'),
(717, 5, '13F', 'ECONOMY', 'WINDOW'),
(718, 5, '14A', 'ECONOMY', 'WINDOW'),
(719, 5, '14B', 'ECONOMY', 'MIDDLE'),
(720, 5, '14C', 'ECONOMY', 'AISLE'),
(721, 5, '14D', 'ECONOMY', 'AISLE'),
(722, 5, '14E', 'ECONOMY', 'MIDDLE'),
(723, 5, '14F', 'ECONOMY', 'WINDOW'),
(724, 5, '15A', 'ECONOMY', 'WINDOW'),
(725, 5, '15B', 'ECONOMY', 'MIDDLE'),
(726, 5, '15C', 'ECONOMY', 'AISLE'),
(727, 5, '15D', 'ECONOMY', 'AISLE'),
(728, 5, '15E', 'ECONOMY', 'MIDDLE'),
(729, 5, '15F', 'ECONOMY', 'WINDOW'),
(730, 5, '16A', 'ECONOMY', 'WINDOW'),
(731, 5, '16B', 'ECONOMY', 'MIDDLE'),
(732, 5, '16C', 'ECONOMY', 'AISLE'),
(733, 5, '16D', 'ECONOMY', 'AISLE'),
(734, 5, '16E', 'ECONOMY', 'MIDDLE'),
(735, 5, '16F', 'ECONOMY', 'WINDOW'),
(736, 5, '17A', 'ECONOMY', 'WINDOW'),
(737, 5, '17B', 'ECONOMY', 'MIDDLE'),
(738, 5, '17C', 'ECONOMY', 'AISLE'),
(739, 5, '17D', 'ECONOMY', 'AISLE'),
(740, 5, '17E', 'ECONOMY', 'MIDDLE'),
(741, 5, '17F', 'ECONOMY', 'WINDOW'),
(742, 5, '18A', 'ECONOMY', 'WINDOW'),
(743, 5, '18B', 'ECONOMY', 'MIDDLE'),
(744, 5, '18C', 'ECONOMY', 'AISLE'),
(745, 5, '18D', 'ECONOMY', 'AISLE'),
(746, 5, '18E', 'ECONOMY', 'MIDDLE'),
(747, 5, '18F', 'ECONOMY', 'WINDOW'),
(748, 5, '19A', 'ECONOMY', 'WINDOW'),
(749, 5, '19B', 'ECONOMY', 'MIDDLE'),
(750, 5, '19C', 'ECONOMY', 'AISLE'),
(751, 5, '19D', 'ECONOMY', 'AISLE'),
(752, 5, '19E', 'ECONOMY', 'MIDDLE'),
(753, 5, '19F', 'ECONOMY', 'WINDOW'),
(754, 5, '20A', 'ECONOMY', 'WINDOW'),
(755, 5, '20B', 'ECONOMY', 'MIDDLE'),
(756, 5, '20C', 'ECONOMY', 'AISLE'),
(757, 5, '20D', 'ECONOMY', 'AISLE'),
(758, 5, '20E', 'ECONOMY', 'MIDDLE'),
(759, 5, '20F', 'ECONOMY', 'WINDOW'),
(760, 5, '21A', 'ECONOMY', 'WINDOW'),
(761, 5, '21B', 'ECONOMY', 'MIDDLE'),
(762, 5, '21C', 'ECONOMY', 'AISLE'),
(763, 5, '21D', 'ECONOMY', 'AISLE'),
(764, 5, '21E', 'ECONOMY', 'MIDDLE'),
(765, 5, '21F', 'ECONOMY', 'WINDOW'),
(766, 5, '22A', 'ECONOMY', 'WINDOW'),
(767, 5, '22B', 'ECONOMY', 'MIDDLE'),
(768, 5, '22C', 'ECONOMY', 'AISLE'),
(769, 5, '22D', 'ECONOMY', 'AISLE'),
(770, 5, '22E', 'ECONOMY', 'MIDDLE'),
(771, 5, '22F', 'ECONOMY', 'WINDOW'),
(772, 5, '23A', 'ECONOMY', 'WINDOW'),
(773, 5, '23B', 'ECONOMY', 'MIDDLE'),
(774, 5, '23C', 'ECONOMY', 'AISLE'),
(775, 5, '23D', 'ECONOMY', 'AISLE'),
(776, 5, '23E', 'ECONOMY', 'MIDDLE'),
(777, 5, '23F', 'ECONOMY', 'WINDOW'),
(778, 5, '24A', 'ECONOMY', 'WINDOW'),
(779, 5, '24B', 'ECONOMY', 'MIDDLE'),
(780, 5, '24C', 'ECONOMY', 'AISLE'),
(781, 5, '24D', 'ECONOMY', 'AISLE'),
(782, 5, '24E', 'ECONOMY', 'MIDDLE'),
(783, 5, '24F', 'ECONOMY', 'WINDOW'),
(784, 6, '1A', 'FIRST', 'WINDOW'),
(785, 6, '1B', 'FIRST', 'MIDDLE'),
(786, 6, '1C', 'FIRST', 'AISLE'),
(787, 6, '1D', 'FIRST', 'AISLE'),
(788, 6, '1E', 'FIRST', 'MIDDLE'),
(789, 6, '1F', 'FIRST', 'WINDOW'),
(790, 6, '2A', 'FIRST', 'WINDOW'),
(791, 6, '2B', 'FIRST', 'MIDDLE'),
(792, 6, '2C', 'FIRST', 'AISLE'),
(793, 6, '2D', 'FIRST', 'AISLE'),
(794, 6, '2E', 'FIRST', 'MIDDLE'),
(795, 6, '2F', 'FIRST', 'WINDOW'),
(796, 6, '3A', 'BUSINESS', 'WINDOW'),
(797, 6, '3B', 'BUSINESS', 'MIDDLE'),
(798, 6, '3C', 'BUSINESS', 'AISLE'),
(799, 6, '3D', 'BUSINESS', 'AISLE'),
(800, 6, '3E', 'BUSINESS', 'MIDDLE'),
(801, 6, '3F', 'BUSINESS', 'WINDOW'),
(802, 6, '4A', 'BUSINESS', 'WINDOW'),
(803, 6, '4B', 'BUSINESS', 'MIDDLE'),
(804, 6, '4C', 'BUSINESS', 'AISLE'),
(805, 6, '4D', 'BUSINESS', 'AISLE'),
(806, 6, '4E', 'BUSINESS', 'MIDDLE'),
(807, 6, '4F', 'BUSINESS', 'WINDOW'),
(808, 6, '5A', 'BUSINESS', 'WINDOW'),
(809, 6, '5B', 'BUSINESS', 'MIDDLE'),
(810, 6, '5C', 'BUSINESS', 'AISLE'),
(811, 6, '5D', 'BUSINESS', 'AISLE'),
(812, 6, '5E', 'BUSINESS', 'MIDDLE'),
(813, 6, '5F', 'BUSINESS', 'WINDOW'),
(814, 6, '6A', 'ECONOMY', 'WINDOW'),
(815, 6, '6B', 'ECONOMY', 'MIDDLE'),
(816, 6, '6C', 'ECONOMY', 'AISLE'),
(817, 6, '6D', 'ECONOMY', 'AISLE'),
(818, 6, '6E', 'ECONOMY', 'MIDDLE'),
(819, 6, '6F', 'ECONOMY', 'WINDOW'),
(820, 6, '7A', 'ECONOMY', 'WINDOW'),
(821, 6, '7B', 'ECONOMY', 'MIDDLE'),
(822, 6, '7C', 'ECONOMY', 'AISLE'),
(823, 6, '7D', 'ECONOMY', 'AISLE'),
(824, 6, '7E', 'ECONOMY', 'MIDDLE'),
(825, 6, '7F', 'ECONOMY', 'WINDOW'),
(826, 6, '8A', 'ECONOMY', 'WINDOW'),
(827, 6, '8B', 'ECONOMY', 'MIDDLE'),
(828, 6, '8C', 'ECONOMY', 'AISLE'),
(829, 6, '8D', 'ECONOMY', 'AISLE'),
(830, 6, '8E', 'ECONOMY', 'MIDDLE'),
(831, 6, '8F', 'ECONOMY', 'WINDOW'),
(832, 6, '9A', 'ECONOMY', 'WINDOW'),
(833, 6, '9B', 'ECONOMY', 'MIDDLE'),
(834, 6, '9C', 'ECONOMY', 'AISLE'),
(835, 6, '9D', 'ECONOMY', 'AISLE'),
(836, 6, '9E', 'ECONOMY', 'MIDDLE'),
(837, 6, '9F', 'ECONOMY', 'WINDOW'),
(838, 6, '10A', 'ECONOMY', 'WINDOW'),
(839, 6, '10B', 'ECONOMY', 'MIDDLE'),
(840, 6, '10C', 'ECONOMY', 'AISLE'),
(841, 6, '10D', 'ECONOMY', 'AISLE'),
(842, 6, '10E', 'ECONOMY', 'MIDDLE'),
(843, 6, '10F', 'ECONOMY', 'WINDOW'),
(844, 6, '11A', 'ECONOMY', 'WINDOW'),
(845, 6, '11B', 'ECONOMY', 'MIDDLE'),
(846, 6, '11C', 'ECONOMY', 'AISLE'),
(847, 6, '11D', 'ECONOMY', 'AISLE'),
(848, 6, '11E', 'ECONOMY', 'MIDDLE'),
(849, 6, '11F', 'ECONOMY', 'WINDOW'),
(850, 6, '12A', 'ECONOMY', 'WINDOW'),
(851, 6, '12B', 'ECONOMY', 'MIDDLE'),
(852, 6, '12C', 'ECONOMY', 'AISLE'),
(853, 6, '12D', 'ECONOMY', 'AISLE'),
(854, 6, '12E', 'ECONOMY', 'MIDDLE'),
(855, 6, '12F', 'ECONOMY', 'WINDOW'),
(856, 6, '13A', 'ECONOMY', 'WINDOW'),
(857, 6, '13B', 'ECONOMY', 'MIDDLE'),
(858, 6, '13C', 'ECONOMY', 'AISLE'),
(859, 6, '13D', 'ECONOMY', 'AISLE'),
(860, 6, '13E', 'ECONOMY', 'MIDDLE'),
(861, 6, '13F', 'ECONOMY', 'WINDOW'),
(862, 6, '14A', 'ECONOMY', 'WINDOW'),
(863, 6, '14B', 'ECONOMY', 'MIDDLE'),
(864, 6, '14C', 'ECONOMY', 'AISLE'),
(865, 6, '14D', 'ECONOMY', 'AISLE'),
(866, 6, '14E', 'ECONOMY', 'MIDDLE'),
(867, 6, '14F', 'ECONOMY', 'WINDOW'),
(868, 6, '15A', 'ECONOMY', 'WINDOW'),
(869, 6, '15B', 'ECONOMY', 'MIDDLE'),
(870, 6, '15C', 'ECONOMY', 'AISLE'),
(871, 6, '15D', 'ECONOMY', 'AISLE'),
(872, 6, '15E', 'ECONOMY', 'MIDDLE'),
(873, 6, '15F', 'ECONOMY', 'WINDOW'),
(874, 6, '16A', 'ECONOMY', 'WINDOW'),
(875, 6, '16B', 'ECONOMY', 'MIDDLE'),
(876, 6, '16C', 'ECONOMY', 'AISLE'),
(877, 6, '16D', 'ECONOMY', 'AISLE'),
(878, 6, '16E', 'ECONOMY', 'MIDDLE'),
(879, 6, '16F', 'ECONOMY', 'WINDOW'),
(880, 6, '17A', 'ECONOMY', 'WINDOW'),
(881, 6, '17B', 'ECONOMY', 'MIDDLE'),
(882, 6, '17C', 'ECONOMY', 'AISLE'),
(883, 6, '17D', 'ECONOMY', 'AISLE'),
(884, 6, '17E', 'ECONOMY', 'MIDDLE'),
(885, 6, '17F', 'ECONOMY', 'WINDOW'),
(886, 6, '18A', 'ECONOMY', 'WINDOW'),
(887, 6, '18B', 'ECONOMY', 'MIDDLE'),
(888, 6, '18C', 'ECONOMY', 'AISLE'),
(889, 6, '18D', 'ECONOMY', 'AISLE'),
(890, 6, '18E', 'ECONOMY', 'MIDDLE'),
(891, 6, '18F', 'ECONOMY', 'WINDOW'),
(892, 6, '19A', 'ECONOMY', 'WINDOW'),
(893, 6, '19B', 'ECONOMY', 'MIDDLE'),
(894, 6, '19C', 'ECONOMY', 'AISLE'),
(895, 6, '19D', 'ECONOMY', 'AISLE'),
(896, 6, '19E', 'ECONOMY', 'MIDDLE'),
(897, 6, '19F', 'ECONOMY', 'WINDOW'),
(898, 6, '20A', 'ECONOMY', 'WINDOW'),
(899, 6, '20B', 'ECONOMY', 'MIDDLE'),
(900, 6, '20C', 'ECONOMY', 'AISLE'),
(901, 6, '20D', 'ECONOMY', 'AISLE'),
(902, 6, '20E', 'ECONOMY', 'MIDDLE'),
(903, 6, '20F', 'ECONOMY', 'WINDOW'),
(904, 6, '21A', 'ECONOMY', 'WINDOW'),
(905, 6, '21B', 'ECONOMY', 'MIDDLE'),
(906, 6, '21C', 'ECONOMY', 'AISLE'),
(907, 6, '21D', 'ECONOMY', 'AISLE'),
(908, 6, '21E', 'ECONOMY', 'MIDDLE'),
(909, 6, '21F', 'ECONOMY', 'WINDOW'),
(910, 6, '22A', 'ECONOMY', 'WINDOW'),
(911, 6, '22B', 'ECONOMY', 'MIDDLE'),
(912, 6, '22C', 'ECONOMY', 'AISLE'),
(913, 6, '22D', 'ECONOMY', 'AISLE'),
(914, 6, '22E', 'ECONOMY', 'MIDDLE'),
(915, 6, '22F', 'ECONOMY', 'WINDOW'),
(916, 6, '23A', 'ECONOMY', 'WINDOW'),
(917, 6, '23B', 'ECONOMY', 'MIDDLE'),
(918, 6, '23C', 'ECONOMY', 'AISLE'),
(919, 6, '23D', 'ECONOMY', 'AISLE'),
(920, 6, '23E', 'ECONOMY', 'MIDDLE'),
(921, 6, '23F', 'ECONOMY', 'WINDOW'),
(922, 6, '24A', 'ECONOMY', 'WINDOW'),
(923, 6, '24B', 'ECONOMY', 'MIDDLE'),
(924, 6, '24C', 'ECONOMY', 'AISLE'),
(925, 6, '24D', 'ECONOMY', 'AISLE'),
(926, 6, '24E', 'ECONOMY', 'MIDDLE'),
(927, 6, '24F', 'ECONOMY', 'WINDOW');


INSERT INTO flights (flight_id, flight_number, airline_id, aircraft_id, origin_code, destination_code, departure_time, arrival_time, duration_mins, base_fare, status) VALUES
(101, 'AI-101', 1, 1, 'BOM', 'DEL', '2026-10-31 07:00:00', '2026-10-31 09:15:00', 135, 5400.0, 'SCHEDULED'),
(102, 'AI-102', 1, 1, 'DEL', 'BOM', '2026-10-31 18:30:00', '2026-10-31 20:45:00', 135, 5622.0, 'SCHEDULED'),
(103, '6E-205', 2, 2, 'DEL', 'BLR', '2026-10-31 06:15:00', '2026-10-31 09:00:00', 165, 4800.0, 'ON_TIME'),
(104, '6E-206', 2, 2, 'BLR', 'DEL', '2026-10-31 17:00:00', '2026-10-31 19:45:00', 165, 4950.0, 'SCHEDULED'),
(105, 'UK-812', 3, 3, 'BOM', 'BLR', '2026-10-31 08:45:00', '2026-10-31 10:30:00', 105, 5100.0, 'BOARDING'),
(106, 'UK-813', 3, 3, 'BLR', 'HYD', '2026-10-31 12:00:00', '2026-10-31 13:10:00', 70, 3200.0, 'SCHEDULED'),
(107, 'SG-401', 4, 4, 'BOM', 'GOI', '2026-10-31 10:00:00', '2026-10-31 11:15:00', 75, 2900.0, 'SCHEDULED'),
(108, 'EK-501', 5, 5, 'BOM', 'DXB', '2026-10-31 04:30:00', '2026-10-31 06:15:00', 225, 18500.0, 'ON_TIME'),
(109, 'BA-138', 6, 6, 'BOM', 'LHR', '2026-10-31 02:20:00', '2026-10-31 07:15:00', 535, 45000.0, 'SCHEDULED'),
(110, 'AI-187', 1, 1, 'DEL', 'JFK', '2026-10-31 01:50:00', '2026-10-31 07:30:00', 940, 68000.0, 'SCHEDULED');


INSERT INTO passengers (passenger_id, first_name, last_name, email, phone, passport_number, date_of_birth, gender, created_at) VALUES
(1, 'Tanmay', 'Dawande', 'tanmay.dawande@example.com', '+91-9876543210', 'Z1234567', '2003-05-15', 'MALE', '2026-10-19 17:31:08'),
(2, 'Aditi', 'Sharma', 'aditi.sharma@example.com', '+91-9822334455', 'L9876543', '1998-08-22', 'FEMALE', '2026-10-19 17:31:08'),
(3, 'Rahul', 'Verma', 'rahul.verma@example.com', '+91-9765432109', 'M4567890', '1995-11-10', 'MALE', '2026-10-19 17:31:08'),
(4, 'Priya', 'Nair', 'priya.nair@example.com', '+91-9845012345', 'P1122334', '2001-02-18', 'FEMALE', '2026-10-19 17:31:08'),
(5, 'Siddharth', 'Mehta', 'siddharth.m@example.com', '+91-9988776655', 'K5566778', '1992-04-30', 'MALE', '2026-10-19 17:31:08'),
(6, 'Ananya', 'Iyer', 'ananya.iyer@example.com', '+91-9123456780', 'R9988776', '2000-09-05', 'FEMALE', '2026-10-19 17:31:08'),
(7, 'Rohan', 'Kulkarni', 'rohan.k@example.com', '+91-9922110033', 'K9911223', '1997-03-14', 'MALE', '2026-10-19 23:10:09'),
(8, 'A', 'B', 'a@b.com', '12345678', 'P123', '2000-01-01', 'MALE', '2026-10-19 23:10:16'),
(9, 'Rohan', 'Kulkarni', 'rohan.1792431663@example.com', '+91-9922110033', 'K2431663', '1997-03-14', 'MALE', '2026-10-19 23:11:03'),
(10, 'awdawdawd', 'wadawdawd', 'awdadawd@gmail.com', '324354313', 'awdadawd', '2003-05-15', 'MALE', '2026-10-19 23:15:45');


INSERT INTO users (user_id, username, password_hash, role, passenger_id, created_at) VALUES
(1, 'admin', 'pbkdf2:sha256:1000000$TI7rmnJmQATnlHoX$46f6938055e3244a4875d90c14ee0acdbc17483fb9432a25dcfff32966179081', 'ADMIN', NULL, '2026-10-19 17:31:08'),
(2, 'staff_flight', 'pbkdf2:sha256:1000000$1ErTFtMjEgbqYHwD$dbe4fe4c078d32860428cff40ebadfd0a78ed276103f33f1f575ada700da12d1', 'STAFF', NULL, '2026-10-19 17:31:08'),
(3, 'tanmay', 'pbkdf2:sha256:1000000$mBnDi410Ee87cF7m$fed4a20479f653e2a77aa5c72837ba276670166a69848dc195e581751622c7b2', 'PASSENGER', 1, '2026-10-19 17:31:08'),
(4, 'aditi', 'pbkdf2:sha256:1000000$WO2Vvn9EcHG65NYS$a88e748de0c6e16c8f7e469a1a374d57a8e591bf55af9da404cd8354f52e06cf', 'PASSENGER', 2, '2026-10-19 17:31:08');


INSERT INTO bookings (booking_id, pnr, user_id, passenger_id, flight_id, seat_number, travel_class, booking_date, total_amount, status) VALUES
(1, 'AERO101A', 3, 1, 101, '10A', 'ECONOMY', '2026-10-15 10:30:00', 5400.0, 'CONFIRMED'),
(2, 'AERO101B', 4, 2, 101, '2A', 'BUSINESS', '2026-10-15 11:15:00', 10800.0, 'CONFIRMED'),
(3, 'AERO205C', NULL, 3, 103, '1A', 'ECONOMY', '2026-10-16 09:20:00', 4800.0, 'CONFIRMED'),
(4, 'AERO812D', NULL, 4, 105, '10B', 'ECONOMY', '2026-10-16 14:45:00', 5100.0, 'CONFIRMED'),
(5, 'AERO501E', 3, 1, 108, '1A', 'FIRST', '2026-10-17 16:10:00', 37000.0, 'CONFIRMED'),
(6, 'AERO401F', NULL, 5, 107, '12A', 'ECONOMY', '2026-10-17 18:00:00', 2900.0, 'CANCELLED'),
(7, 'AERL1RHA', NULL, 9, 101, '4E', 'ECONOMY', '2026-10-19 23:11:03', 5750.0, 'CANCELLED'),
(8, 'AER7LVE2', NULL, 10, 110, '10D', 'ECONOMY', '2026-10-19 23:15:45', 68350.0, 'CONFIRMED'),
(9, 'AERYLSKN', NULL, 10, 110, '1A', 'FIRST', '2026-10-19 23:52:06', 238350.0, 'CONFIRMED'),
(12, 'AER4A8WP', NULL, 10, 109, '4F', 'BUSINESS', '2026-10-27 14:22:10', 90350.0, 'CONFIRMED'),
(13, 'AER8YEQ9', NULL, 10, 110, '3E', 'BUSINESS', '2026-10-27 18:58:19', 136350.0, 'CONFIRMED');


INSERT INTO payments (payment_id, booking_id, transaction_id, payment_method, amount, payment_status, payment_time) VALUES
(1, 1, 'TXN_AERO_99812401', 'UPI', 5400.0, 'SUCCESS', '2026-10-15 10:32:00'),
(2, 2, 'TXN_AERO_99812402', 'CREDIT_CARD', 10800.0, 'SUCCESS', '2026-10-15 11:17:00'),
(3, 3, 'TXN_AERO_99812403', 'NET_BANKING', 4800.0, 'SUCCESS', '2026-10-16 09:21:00'),
(4, 4, 'TXN_AERO_99812404', 'DEBIT_CARD', 5100.0, 'SUCCESS', '2026-10-16 14:46:00'),
(5, 5, 'TXN_AERO_99812405', 'CREDIT_CARD', 37000.0, 'SUCCESS', '2026-10-17 16:12:00'),
(6, 6, 'TXN_AERO_99812406', 'UPI', 2900.0, 'REFUNDED', '2026-10-17 18:05:00'),
(7, 7, 'TXN_0B8UCVGQ', 'UPI', 5750.0, 'REFUNDED', '2026-10-19 23:11:03'),
(8, 8, 'TXN_TVYD31JP', 'UPI', 68350.0, 'SUCCESS', '2026-10-19 23:15:45'),
(9, 9, 'TXN_X25KBTVT', 'UPI', 238350.0, 'SUCCESS', '2026-10-19 23:52:06'),
(12, 12, 'TXN_OMUX3QFJ', 'UPI', 90350.0, 'SUCCESS', '2026-10-27 14:22:10'),
(13, 13, 'TXN_6G5B5QO4', 'UPI', 136350.0, 'SUCCESS', '2026-10-27 18:58:19');


INSERT INTO audit_logs (log_id, action_type, table_name, record_id, details, timestamp) VALUES
(1, 'INSERT_BOOKING', 'bookings', 1, 'PNR: AERO101A created for Flight ID: 101, Seat: 10A, Amount: INR 5400.0', '2026-10-19 17:31:08'),
(2, 'INSERT_BOOKING', 'bookings', 2, 'PNR: AERO101B created for Flight ID: 101, Seat: 2A, Amount: INR 10800.0', '2026-10-19 17:31:08'),
(3, 'INSERT_BOOKING', 'bookings', 3, 'PNR: AERO205C created for Flight ID: 103, Seat: 1A, Amount: INR 4800.0', '2026-10-19 17:31:08'),
(4, 'INSERT_BOOKING', 'bookings', 4, 'PNR: AERO812D created for Flight ID: 105, Seat: 10B, Amount: INR 5100.0', '2026-10-19 17:31:08'),
(5, 'INSERT_BOOKING', 'bookings', 5, 'PNR: AERO501E created for Flight ID: 108, Seat: 1A, Amount: INR 37000.0', '2026-10-19 23:01:08'),
(6, 'INSERT_BOOKING', 'bookings', 6, 'PNR: AERO401F created for Flight ID: 107, Seat: 12A, Amount: INR 2900.0', '2026-10-19 23:01:08'),
(7, 'INSERT_BOOKING', 'bookings', 7, 'PNR: AERL1RHA created for Flight ID: 101, Seat: 4B, Amount: INR 5750.0', '2026-10-19 23:11:03'),
(8, 'UPDATE_BOOKING_STATUS', 'bookings', 7, 'Booking PNR: AERL1RHA status changed from CONFIRMED to CANCELLED', '2026-10-19 23:11:03'),
(9, 'INSERT_BOOKING', 'bookings', 8, 'PNR: AER7LVE2 created for Flight ID: 110, Seat: 10D, Amount: INR 68350.0', '2026-10-19 23:15:45'),
(10, 'INSERT_BOOKING', 'bookings', 9, 'PNR: AERYLSKN created for Flight ID: 110, Seat: 1A, Amount: INR 238350.0', '2026-10-19 23:52:06'),
(11, 'INSERT_BOOKING', 'bookings', 10, 'PNR: AER9O0F0 created for Flight ID: 101, Seat: 14B, Amount: INR 5750.0', '2026-10-19 23:53:04'),
(12, 'UPDATE_BOOKING_STATUS', 'bookings', 10, 'Booking PNR: AER9O0F0 status changed from CONFIRMED to CANCELLED', '2026-10-19 23:53:04'),
(13, 'INSERT_BOOKING', 'bookings', 11, 'PNR: AERYZGJC created for Flight ID: 101, Seat: 12D, Amount: INR 5750.0', '2026-10-20 00:10:29'),
(14, 'UPDATE_BOOKING_STATUS', 'bookings', 11, 'Booking PNR: AERYZGJC status changed from CONFIRMED to CANCELLED', '2026-10-20 00:10:45'),
(15, 'INSERT_BOOKING', 'bookings', 12, 'PNR: AER4A8WP created for Flight ID: 109, Seat: 4F, Amount: INR 90350.0', '2026-10-27 14:22:10'),
(16, 'INSERT_BOOKING', 'bookings', 13, 'PNR: AER8YEQ9 created for Flight ID: 110, Seat: 3E, Amount: INR 136350.0', '2026-10-27 18:58:19');



-- ------------------------------------------------------------------------------

-- Triggers, stored procedures and views

-- ------------------------------------------------------------------------------

DELIMITER $$

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




-- ------------------------------------------------------------------------------
-- Extra audit triggers for the Assessment 9 demonstration
-- ------------------------------------------------------------------------------
DELIMITER $$

DROP TRIGGER IF EXISTS trg_after_passenger_insert$$
CREATE TRIGGER trg_after_passenger_insert
AFTER INSERT ON passengers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES ('INSERT_PASSENGER', 'passengers', NEW.passenger_id,
            CONCAT('Passenger ', NEW.first_name, ' ', NEW.last_name, ' created'));
END$$

DROP TRIGGER IF EXISTS trg_after_passenger_update$$
CREATE TRIGGER trg_after_passenger_update
AFTER UPDATE ON passengers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES ('UPDATE_PASSENGER', 'passengers', NEW.passenger_id,
            CONCAT('Passenger ', NEW.first_name, ' ', NEW.last_name, ' updated'));
END$$

DROP TRIGGER IF EXISTS trg_after_passenger_delete$$
CREATE TRIGGER trg_after_passenger_delete
AFTER DELETE ON passengers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES ('DELETE_PASSENGER', 'passengers', OLD.passenger_id,
            CONCAT('Passenger ', OLD.first_name, ' ', OLD.last_name, ' deleted'));
END$$

DROP TRIGGER IF EXISTS trg_after_flight_insert$$
CREATE TRIGGER trg_after_flight_insert
AFTER INSERT ON flights
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES ('INSERT_FLIGHT', 'flights', NEW.flight_id,
            CONCAT('Flight ', NEW.flight_number, ' scheduled from ', NEW.origin_code, ' to ', NEW.destination_code));
END$$

DROP TRIGGER IF EXISTS trg_after_flight_delete$$
CREATE TRIGGER trg_after_flight_delete
AFTER DELETE ON flights
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (action_type, table_name, record_id, details)
    VALUES ('DELETE_FLIGHT', 'flights', OLD.flight_id,
            CONCAT('Flight ', OLD.flight_number, ' deleted'));
END$$

DELIMITER ;


-- ------------------------------------------------------------------------------
-- Final verification
-- ------------------------------------------------------------------------------
SELECT 'airline_db setup complete' AS status,
       NOW() AS current_time_ist,
       @@session.time_zone AS session_time_zone;

SELECT 'flights' AS table_name, COUNT(*) AS rows_count FROM flights
UNION ALL SELECT 'passengers', COUNT(*) FROM passengers
UNION ALL SELECT 'bookings', COUNT(*) FROM bookings
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'audit_logs', COUNT(*) FROM audit_logs;
