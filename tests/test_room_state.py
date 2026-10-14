import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from master_pi.socket_server import (
    handle_report_fault,
    handle_update_status,
    handle_validate_token,
    handle_get_room_info
)


def make_mock_conn(fetchone_return=None, fetchall_return=None):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return or []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


class TestFaultReporting(unittest.TestCase):

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_report_fault_success(self, mock_get_conn, mock_publish):
        """Valid fault report returns ok and triggers MQTT alert."""
        mock_conn, _ = make_mock_conn()
        mock_get_conn.return_value = mock_conn

        response = handle_report_fault({
            "room_id": 1,
            "user_id": 1,
            "description": "Projector not working"
        })

        self.assertEqual(response["status"], "ok")
        # MQTT should be published for fault
        mock_publish.assert_called()

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_report_fault_publishes_security_alert(self, mock_get_conn, mock_publish):
        """Fault report publishes to security/alerts topic."""
        mock_conn, _ = make_mock_conn()
        mock_get_conn.return_value = mock_conn

        handle_report_fault({
            "room_id": 2,
            "user_id": 1,
            "description": "AC making loud noise"
        })

        topics = [call.args[0] for call in mock_publish.call_args_list]
        self.assertIn("security/alerts", topics)

    @patch('master_pi.socket_server.get_connection')
    def test_report_fault_db_failure(self, mock_get_conn):
        """DB failure on fault report returns error."""
        mock_get_conn.return_value = None

        response = handle_report_fault({
            "room_id": 1,
            "user_id": 1,
            "description": "Issue"
        })

        self.assertEqual(response["status"], "error")


class TestRoomStatusUpdate(unittest.TestCase):

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_status_update_available_to_maintenance(self, mock_get_conn, mock_publish):
        """Room status can be changed to maintenance."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"status": "available"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_update_status({
            "room_id": 1,
            "new_status": "maintenance",
            "changed_by": 1
        })

        self.assertEqual(response["status"], "ok")

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_status_update_publishes_mqtt(self, mock_get_conn, mock_publish):
        """Status update publishes to room MQTT topic."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"status": "available"}
        )
        mock_get_conn.return_value = mock_conn

        handle_update_status({
            "room_id": 3,
            "new_status": "fault",
            "changed_by": 1
        })

        topics = [call.args[0] for call in mock_publish.call_args_list]
        self.assertIn("room/3/status", topics)

    @patch('master_pi.socket_server.get_connection')
    def test_status_update_db_failure(self, mock_get_conn):
        """DB failure on status update returns error."""
        mock_get_conn.return_value = None

        response = handle_update_status({
            "room_id": 1,
            "new_status": "maintenance",
            "changed_by": 1
        })

        self.assertEqual(response["status"], "error")


class TestTokenValidation(unittest.TestCase):

    @patch('master_pi.socket_server.publish_message')
    @patch('master_pi.socket_server.get_connection')
    def test_valid_token_grants_access(self, mock_get_conn, mock_publish):
        """Valid unused token returns ok."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={
                "token_id": 1,
                "used": False,
                "booking_id": 1,
                "room_id": 1,
                "end_time": None,
                "date": "2026-06-01",
                "user_id": 1,
                "full_name": "Alice Johnson"
            }
        )
        mock_get_conn.return_value = mock_conn

        response = handle_validate_token({"token": "tok_abc123", "room_id": 1})

        self.assertEqual(response["status"], "ok")

    @patch('master_pi.socket_server.get_connection')
    def test_used_token_denied(self, mock_get_conn):
        """Already used token returns failed status."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={
                "token_id": 1,
                "used": True,
                "booking_id": 1,
                "room_id": 1,
                "end_time": None,
                "date": "2026-06-01",
                "user_id": 1,
                "full_name": "Alice Johnson"
            }
        )
        mock_get_conn.return_value = mock_conn

        response = handle_validate_token({"token": "tok_abc123", "room_id": 1})

        self.assertEqual(response["status"], "failed")

    @patch('master_pi.socket_server.get_connection')
    def test_invalid_token_denied(self, mock_get_conn):
        """Non-existent token returns failed status."""
        mock_conn, _ = make_mock_conn(fetchone_return=None)
        mock_get_conn.return_value = mock_conn

        response = handle_validate_token({"token": "tok_invalid", "room_id": 1})

        self.assertEqual(response["status"], "failed")


if __name__ == "__main__":
    unittest.main()
