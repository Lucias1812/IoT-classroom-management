-- schema.sql

CREATE DATABASE IF NOT EXISTS piot_db;
USE piot_db;

-- ─────────────────────────────────────────
-- USERS
-- covers students, teachers, security staff
-- admin is a separate hardcoded account
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    university_id    VARCHAR(20)  NOT NULL UNIQUE,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('user', 'security', 'admin') NOT NULL DEFAULT 'user',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- ROOMS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rooms (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    room_code  VARCHAR(20)  NOT NULL UNIQUE,
    building   VARCHAR(100),
    capacity   INT,
    status     ENUM('available', 'in_use', 'maintenance', 'fault') NOT NULL DEFAULT 'available',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- SENSOR READINGS
-- recorded every 10 seconds by each Room Pi
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sensor_readings (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    room_id      INT NOT NULL,
    temperature  DECIMAL(5,2),
    humidity     DECIMAL(5,2),
    pressure     DECIMAL(7,2),
    recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- ─────────────────────────────────────────
-- BOOKINGS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    room_id    INT NOT NULL,
    date       DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time   TIME NOT NULL,
    status     ENUM('active', 'cancelled', 'completed') NOT NULL DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

-- ─────────────────────────────────────────
-- TOKENS
-- one-time use token issued on booking
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tokens (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    token      VARCHAR(64) NOT NULL UNIQUE,
    used       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- ─────────────────────────────────────────
-- ROOM STATUS LOG
-- tracks every status change on a room
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS room_status_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    room_id    INT NOT NULL,
    changed_by INT,
    old_status ENUM('available', 'in_use', 'maintenance', 'fault'),
    new_status ENUM('available', 'in_use', 'maintenance', 'fault'),
    reason     VARCHAR(255),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id)    REFERENCES rooms(id),
    FOREIGN KEY (changed_by) REFERENCES users(id)
);

-- ─────────────────────────────────────────
-- FAULT REPORTS
-- submitted by users via Agent Pi
-- reviewed by admin via Master Pi
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fault_reports (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    room_id     INT NOT NULL,
    reported_by INT NOT NULL,
    description VARCHAR(500),
    status      ENUM('pending', 'confirmed', 'dismissed') NOT NULL DEFAULT 'pending',
    reviewed_by INT,
    reviewed_at DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id)     REFERENCES rooms(id),
    FOREIGN KEY (reported_by) REFERENCES users(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

-- ─────────────────────────────────────────
-- ACTION LOGS
-- every significant action logged here
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS action_logs (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT,
    action     VARCHAR(100) NOT NULL,
    detail     VARCHAR(500),
    ip_address VARCHAR(45),
    logged_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
