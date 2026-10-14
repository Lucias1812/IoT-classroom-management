import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from master_pi.socket_server import (
    handle_book_room,
    handle_cancel_booking,
    handle_checkin,
    handle_checkout,
    handle_get_bookings
)


def make_mock_conn(fetchone_return=None, fetchall_return=None):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return or []
    mock_cursor.lastrowid = 1

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


class TestBookRoom(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_success(self, mock_get_conn):
        """Valid booking returns ok status with a token."""
        mock_conn, mock_cursor = make_mock_conn(fetchone_return=None)
        mock_get_conn.return_value = mock_conn

        response = handle_book_room({
            "user_id": 1,
            "room_id": 1,
            "date": "2026-06-01",
            "start_time": "10:00",
            "end_time": "12:00"
        })

        self.assertEqual(response["status"], "ok")
        self.assertIn("token", response)

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_token_is_string(self, mock_get_conn):
        """Token returned on booking is a non-empty string."""
        mock_conn, _ = make_mock_conn(fetchone_return=None)
        mock_get_conn.return_value = mock_conn

        response = handle_book_room({
            "user_id": 1,
            "room_id": 1,
            "date": "2026-06-01",
            "start_time": "10:00",
            "end_time": "12:00"
        })

        self.assertIsInstance(response["token"], str)
        self.assertGreater(len(response["token"]), 0)

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_missing_fields(self, mock_get_conn):
        """Booking with missing fields returns error."""
        response = handle_book_room({
            "user_id": 1,
            "room_id": None,
            "date": "",
            "start_time": "",
            "end_time": ""
        })

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_conflict(self, mock_get_conn):
        """Booking a room that already has a booking at that time returns error."""
        # fetchone returns an existing booking (conflict)
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 5}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_book_room({
            "user_id": 2,
            "room_id": 1,
            "date": "2026-06-01",
            "start_time": "10:00",
            "end_time": "12:00"
        })

        self.assertEqual(response["status"], "error")

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_db_failure(self, mock_get_conn):
        """DB failure returns error."""
        mock_get_conn.return_value = None

        response = handle_book_room({
            "user_id": 1,
            "room_id": 1,
            "date": "2026-06-01",
            "start_time": "10:00",
            "end_time": "12:00"
        })

        self.assertEqual(response["status"], "error")


class TestCancelBooking(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_cancel_booking_success(self, mock_get_conn):
        """Cancelling an active booking returns ok."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 1, "user_id": 1, "status": "active"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_cancel_booking({"booking_id": 1, "user_id": 1})

        self.assertEqual(response["status"], "ok")

    @patch('master_pi.socket_server.get_connection')
    def test_cancel_booking_missing_fields(self, mock_get_conn):
        """Cancel with missing booking_id returns error."""
        response = handle_cancel_booking({"booking_id": None, "user_id": 1})

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()


class TestCheckinCheckout(unittest.TestCase):

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_checkin_success(self, mock_get_conn, mock_publish):
        """Valid checkin returns ok and publishes MQTT."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 1, "user_id": 1, "room_id": 1, "status": "active"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_checkin({"booking_id": 1, "user_id": 1})

        self.assertEqual(response["status"], "ok")

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_checkout_success(self, mock_get_conn, mock_publish):
        """Valid checkout returns ok and publishes MQTT."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 1, "user_id": 1, "room_id": 1, "status": "active"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_checkout({"booking_id": 1, "user_id": 1})

        self.assertEqual(response["status"], "ok")


class TestGetBookings(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_get_bookings_returns_list(self, mock_get_conn):
        """get_bookings returns a list of bookings."""
        mock_conn, mock_cursor = make_mock_conn(
            fetchall_return=[
                {"id": 1, "room_code": "10.5.3", "date": "2026-05-01",
                 "start_time": "09:00", "end_time": "11:00",
                 "status": "completed", "token": None}
            ]
        )
        mock_get_conn.return_value = mock_conn

        response = handle_get_bookings({"user_id": 1})

        self.assertEqual(response["status"], "ok")
        self.assertIn("bookings", response)
        self.assertIsInstance(response["bookings"], list)

    @patch('master_pi.socket_server.get_connection')
    def test_get_bookings_missing_user_id(self, mock_get_conn):
        """get_bookings without user_id returns error."""
        response = handle_get_bookings({"user_id": None})

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
