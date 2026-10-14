-- seed.sql

USE piot_db;

-- ─────────────────────────────────────────
-- USERS
-- passwords are hashed with sha256
-- plain text for reference:
--   admin        → admin123
--   students     → password123
--   security     → security123
-- ─────────────────────────────────────────
INSERT INTO users (university_id, full_name, email, password_hash, role) VALUES
('ADMIN',  'System Admin',    'admin@example.com',    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin'),
('S001',      'Alice Johnson',   'alice@example.com',    'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'user'),
('T001',      'Dr. James Lee',   'james@example.com',    'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'user'),
('SEC001',    'Mike Security',   'mike@example.com',     'eae9965e8315dd94b13f0ecf097be92d43fbb5b07f432b824f418d2b84a7de35', 'security');

-- ─────────────────────────────────────────
-- ROOMS
-- ─────────────────────────────────────────
INSERT INTO rooms (room_code, building, capacity, status) VALUES
('10.5.3', 'Building 10', 30, 'available'),
('10.5.25', 'Building 10', 50, 'available'),
('80.7.12', 'Building 80', 20, 'maintenance'),
('80.6.5', 'Building 80', 40, 'available'),
('56.3.2', 'Building 56', 25, 'available'),
('14.12.34', 'Building 14', 60, 'in_use');

INSERT INTO sensor_readings (room_id, temperature, humidity, pressure) VALUES
(1, 22.5, 55.3, 1013.2),
(1, 22.8, 54.9, 1013.0),
(2, 23.1, 60.1, 1012.8),
(2, 23.0, 59.8, 1012.9),
(4, 21.9, 58.2, 1013.5),
(4, 22.1, 57.9, 1013.4);

-- ─────────────────────────────────────────
-- BOOKINGS (historical + upcoming)
-- ─────────────────────────────────────────
INSERT INTO bookings (user_id, room_id, date, start_time, end_time, status) VALUES
(2, 1, '2026-05-01', '09:00:00', '11:00:00', 'completed'),
(3, 2, '2026-05-02', '13:00:00', '15:00:00', 'completed'),
(2, 4, '2026-05-03', '10:00:00', '12:00:00', 'cancelled'),
(3, 1, '2026-05-05', '14:00:00', '16:00:00', 'completed'),
(2, 5, '2026-05-10', '09:00:00', '10:00:00', 'completed'),
(3, 1, CURDATE(),    '10:00:00', '12:00:00', 'active'),
(3, 2, CURDATE(),    '13:00:00', '15:00:00', 'active'),
(2, 4, CURDATE(),    '16:00:00', '18:00:00', 'active');

-- ─────────────────────────────────────────
-- TOKENS (for active bookings)
-- ─────────────────────────────────────────
INSERT INTO tokens (booking_id, token, used) VALUES
(6, 'tok_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4', FALSE),
(7, 'tok_b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5', FALSE),
(8, 'tok_c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6', FALSE);

-- ─────────────────────────────────────────
-- FAULT REPORTS
-- ─────────────────────────────────────────
INSERT INTO fault_reports (room_id, reported_by, description, status) VALUES
(3, 2, 'Projector not working and lights flickering', 'confirmed'),
(6, 3, 'Air conditioning making loud noise',          'pending');

-- ─────────────────────────────────────────
-- ROOM STATUS LOG
-- ─────────────────────────────────────────
INSERT INTO room_status_log (room_id, changed_by, old_status, new_status, reason) VALUES
(3, 1, 'available',  'maintenance', 'Scheduled maintenance'),
(6, 4, 'available',  'in_use',      'Booking check-in');

-- ─────────────────────────────────────────
-- ACTION LOGS
-- ─────────────────────────────────────────
INSERT INTO action_logs (user_id, action, detail) VALUES
(2, 'login',        'User logged in'),
(2, 'book_room',    'Booked room 80.7.12 on 2026-05-01'),
(3, 'book_room',    'Booked room 10.5.25 on 2026-05-02'),
(2, 'cancel',       'Cancelled booking for 80.6.5'),
(4, 'status_change','Changed 80.7.12 to maintenance'),
(4, 'status_change','Changed 14.12.34 to in_use');
