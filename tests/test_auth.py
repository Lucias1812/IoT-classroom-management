import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Allow imports from master_pi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from master_pi.socket_server import handle_login, handle_register


def make_mock_conn(fetchone_return=None, fetchall_return=None):
    """Helper: build a mock DB connection with a configurable cursor."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return or []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


class TestLogin(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_login_success(self, mock_get_conn):
        """Valid credentials return ok status with user info."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 1, "full_name": "Alice Johnson", "role": "user"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_login({"university_id": "S001", "password": "password123"})

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["role"], "user")
        self.assertIn("full_name", response)

    @patch('master_pi.socket_server.get_connection')
    def test_login_wrong_password(self, mock_get_conn):
        """Wrong password returns error status."""
        mock_conn, _ = make_mock_conn(fetchone_return=None)
        mock_get_conn.return_value = mock_conn

        response = handle_login({"university_id": "S001", "password": "wrongpassword"})

        self.assertEqual(response["status"], "error")

    @patch('master_pi.socket_server.get_connection')
    def test_login_missing_university_id(self, mock_get_conn):
        """Missing university_id returns error without hitting DB."""
        response = handle_login({"university_id": "", "password": "password123"})

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_login_missing_password(self, mock_get_conn):
        """Missing password returns error without hitting DB."""
        response = handle_login({"university_id": "S001", "password": ""})

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_login_db_failure(self, mock_get_conn):
        """DB connection failure returns error."""
        mock_get_conn.return_value = None

        response = handle_login({"university_id": "S001", "password": "password123"})

        self.assertEqual(response["status"], "error")

    @patch('master_pi.socket_server.get_connection')
    def test_login_response_contains_user_id(self, mock_get_conn):
        """Successful login response includes user_id."""
        mock_conn, _ = make_mock_conn(
            fetchone_return={"id": 2, "full_name": "Dr. James Lee", "role": "user"}
        )
        mock_get_conn.return_value = mock_conn

        response = handle_login({"university_id": "T001", "password": "password123"})

        self.assertIn("user_id", response)


class TestRegister(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_register_missing_fields(self, mock_get_conn):
        """Registration with missing fields returns error."""
        response = handle_register({
            "university_id": "",
            "full_name": "",
            "email": "",
            "password": ""
        })

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_register_invalid_email(self, mock_get_conn):
        """Registration with invalid email returns error."""
        response = handle_register({
            "university_id": "S999",
            "full_name": "Test User",
            "email": "notanemail",
            "password": "password123"
        })

        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_register_success(self, mock_get_conn):
        """Valid registration data returns ok status."""
        mock_conn, mock_cursor = make_mock_conn(fetchone_return=None)
        mock_get_conn.return_value = mock_conn

        response = handle_register({
            "university_id": "S999",
            "full_name": "New User",
            "email": "newuser@example.com",
            "password": "password123"
        })

        self.assertEqual(response["status"], "ok")

    @patch('master_pi.socket_server.get_connection')
    def test_register_duplicate_id(self, mock_get_conn):
        """Duplicate university_id returns error."""
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.execute.side_effect = Exception("Duplicate entry")
        mock_get_conn.return_value = mock_conn

        response = handle_register({
            "university_id": "S001",
            "full_name": "Duplicate User",
            "email": "dup@example.com",
            "password": "password123"
        })

        self.assertEqual(response["status"], "error")


if __name__ == "__main__":
    unittest.main()
