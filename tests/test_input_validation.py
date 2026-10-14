import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from master_pi.socket_server import is_valid_email, handle_register, handle_login


class TestEmailValidation(unittest.TestCase):

    def test_valid_email(self):
        """Standard email addresses pass validation."""
        self.assertTrue(is_valid_email("alice@example.com"))
        self.assertTrue(is_valid_email("user.name@example.com"))

    def test_invalid_email_no_at(self):
        """Email without @ fails."""
        self.assertFalse(is_valid_email("notanemail"))

    def test_invalid_email_no_domain(self):
        """Email without domain fails."""
        self.assertFalse(is_valid_email("user@"))

    def test_invalid_email_no_tld(self):
        """Email without TLD fails."""
        self.assertFalse(is_valid_email("user@domain"))

    def test_invalid_email_empty(self):
        """Empty string fails."""
        self.assertFalse(is_valid_email(""))

    def test_invalid_email_spaces(self):
        """Email with spaces fails."""
        self.assertFalse(is_valid_email("user @domain.com"))


class TestRegistrationValidation(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_empty_university_id_rejected(self, mock_get_conn):
        """Empty university_id is rejected before DB call."""
        response = handle_register({
            "university_id": "",
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        })
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_empty_full_name_rejected(self, mock_get_conn):
        """Empty full_name is rejected before DB call."""
        response = handle_register({
            "university_id": "S999",
            "full_name": "",
            "email": "test@example.com",
            "password": "password123"
        })
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_empty_password_rejected(self, mock_get_conn):
        """Empty password is rejected before DB call."""
        response = handle_register({
            "university_id": "S999",
            "full_name": "Test User",
            "email": "test@example.com",
            "password": ""
        })
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_invalid_email_rejected(self, mock_get_conn):
        """Invalid email format is rejected before DB call."""
        response = handle_register({
            "university_id": "S999",
            "full_name": "Test User",
            "email": "bademail",
            "password": "password123"
        })
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()


class TestLoginValidation(unittest.TestCase):

    @patch('master_pi.socket_server.get_connection')
    def test_whitespace_university_id_rejected(self, mock_get_conn):
        """Whitespace-only university_id is rejected."""
        response = handle_login({"university_id": "   ", "password": "password123"})
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()

    @patch('master_pi.socket_server.get_connection')
    def test_missing_both_fields_rejected(self, mock_get_conn):
        """Both fields missing is rejected."""
        response = handle_login({"university_id": "", "password": ""})
        self.assertEqual(response["status"], "error")
        mock_get_conn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
