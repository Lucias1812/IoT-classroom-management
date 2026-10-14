import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from master_pi.socket_server import route


class TestSocketMessageFormat(unittest.TestCase):
    """Tests that socket messages follow the expected request/response format."""

    def test_unknown_action_returns_error(self):
        """Unknown action returns error with message."""
        response = route("nonexistent_action", {})

        self.assertEqual(response["status"], "error")
        self.assertIn("message", response)

    def test_ping_action(self):
        """Ping action returns ok with pong message."""
        response = route("ping", {})

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["message"], "pong")

    def test_response_always_has_status(self):
        """Every route response contains a status field."""
        actions = ["ping", "login", "register", "search_rooms",
                   "book_room", "cancel_booking", "get_bookings"]

        for action in actions:
            response = route(action, {})
            self.assertIn("status", response,
                          f"Response for '{action}' missing 'status' field")

    def test_response_status_is_string(self):
        """Status field is always a string."""
        response = route("ping", {})
        self.assertIsInstance(response["status"], str)

    def test_error_response_has_message(self):
        """Error responses always include a message."""
        response = route("login", {"university_id": "", "password": ""})

        self.assertEqual(response["status"], "error")
        self.assertIn("message", response)
        self.assertIsInstance(response["message"], str)

    @patch('master_pi.socket_server.get_connection')
    def test_login_response_format(self, mock_get_conn):
        """Successful login response has required fields."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, "full_name": "Alice Johnson", "role": "user"
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        response = route("login", {"university_id": "S001", "password": "password123"})

        self.assertEqual(response["status"], "ok")
        self.assertIn("user_id", response)
        self.assertIn("full_name", response)
        self.assertIn("role", response)

    @patch('master_pi.socket_server.get_connection')
    def test_book_room_response_has_token(self, mock_get_conn):
        """Successful booking response contains a token."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.lastrowid = 1
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        response = route("book_room", {
            "user_id": 1,
            "room_id": 1,
            "date": "2026-06-01",
            "start_time": "10:00",
            "end_time": "12:00"
        })

        self.assertEqual(response["status"], "ok")
        self.assertIn("token", response)


class TestMQTTMessageFormat(unittest.TestCase):
    """Tests that MQTT messages are published with correct topics and payloads."""

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_fault_report_mqtt_topic_format(self, mock_get_conn, mock_publish):
        """Fault report publishes to correct room topic."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        route("report_fault", {
            "room_id": 5,
            "user_id": 1,
            "description": "Lights not working"
        })

        topics = [call.args[0] for call in mock_publish.call_args_list]
        self.assertIn("room/5/status", topics)
        self.assertIn("security/alerts", topics)

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_status_update_mqtt_topic_format(self, mock_get_conn, mock_publish):
        """Status update publishes to correct room/id/status topic."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status": "available"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        route("update_status", {
            "room_id": 3,
            "new_status": "maintenance",
            "changed_by": 1
        })

        topics = [call.args[0] for call in mock_publish.call_args_list]
        self.assertIn("room/3/status", topics)

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_mqtt_payload_is_string(self, mock_get_conn, mock_publish):
        """MQTT payloads are always strings."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        route("report_fault", {
            "room_id": 1,
            "user_id": 1,
            "description": "Test fault"
        })

        for call in mock_publish.call_args_list:
            payload = call.args[1]
            self.assertIsInstance(payload, str,
                                  f"MQTT payload should be string, got {type(payload)}")


if __name__ == "__main__":
    unittest.main()
