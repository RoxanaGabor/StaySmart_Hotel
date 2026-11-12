-- ============================================
-- StaySmart Hotel Management System
-- Example SQL Queries
-- ============================================

-- 1) Views (report-ready outputs)
SELECT * FROM vw_revenue_by_month;
SELECT * FROM vw_upcoming_checkins;

-- 2) Multi-table JOIN (booking details with guest + room)
SELECT
    b.booking_id,
    g.first_name || ' ' || g.last_name AS guest_name,
    r.room_number,
    b.check_in,
    b.check_out,
    b.status
FROM bookings b
JOIN guests g ON b.guest_id = g.guest_id
JOIN rooms r ON b.room_id = r.room_id
ORDER BY b.check_in;

-- 3) GROUP BY + HAVING (room types with strong revenue)
SELECT
    rt.type_name,
    ROUND(SUM(p.amount), 2) AS total_revenue
FROM payments p
JOIN bookings b ON p.booking_id = b.booking_id
JOIN rooms r ON b.room_id = r.room_id
JOIN room_types rt ON r.room_type_id = rt.room_type_id
GROUP BY rt.type_name
HAVING SUM(p.amount) > 300
ORDER BY total_revenue DESC;

-- 4) SQLite function usage (string inspection)
SELECT
    guest_id,
    email,
    LENGTH(email) AS email_length,
    INSTR(email, '@') AS contains_at
FROM guests
ORDER BY email_length DESC;

-- 5) LEFT JOIN + aggregation (bookings per room, including rooms with 0 bookings)
SELECT
    r.room_number,
    COUNT(b.booking_id) AS total_bookings
FROM rooms r
LEFT JOIN bookings b ON r.room_id = b.room_id
GROUP BY r.room_number
ORDER BY total_bookings DESC;

-- 6) Filtering example (active bookings only)
SELECT
    booking_id,
    room_id,
    check_in,
    check_out,
    status
FROM bookings
WHERE status <> 'Cancelled'
ORDER BY check_in;

-- 7) Example literal output (used in reports / scripts)
SELECT 'Report generated successfully' AS message;

-- ============================================
-- Data Integrity Evidence (Constraints/Triggers)
-- ============================================

-- A) Attempt to insert overlapping booking (should fail via trigger)
-- NOTE: Adjust dates/room_id to intentionally overlap an existing booking if needed.
-- INSERT INTO bookings (guest_id, room_id, check_in, check_out, status, preferences_xml, num_guests)
-- VALUES (1, 1, '2026-01-11', '2026-01-12', 'Booked', '<preferences></preferences>', 2);

-- B) Booking status update (should update room status via trigger)
-- UPDATE bookings SET status = 'CheckedIn' WHERE booking_id = 1;
-- SELECT room_id, status FROM rooms WHERE room_id = (SELECT room_id FROM bookings WHERE booking_id = 1);

-- ============================================
-- Optimisation (Indexes + Query Plan Evidence)
-- ============================================

-- Indexes to improve performance on frequent joins/filters
CREATE INDEX IF NOT EXISTS idx_bookings_room_dates
ON bookings(room_id, check_in, check_out);

CREATE INDEX IF NOT EXISTS idx_payments_booking_id
ON payments(booking_id);

-- Evidence: query plan for a heavier aggregation query
EXPLAIN QUERY PLAN
SELECT
    rt.type_name,
    ROUND(SUM(p.amount), 2) AS total_revenue
FROM payments p
JOIN bookings b ON p.booking_id = b.booking_id
JOIN rooms r ON b.room_id = r.room_id
JOIN room_types rt ON r.room_type_id = rt.room_type_id
GROUP BY rt.type_name
HAVING SUM(p.amount) > 300;
