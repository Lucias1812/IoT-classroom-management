# Test Plan

## Overview

This document describes the testing strategy for the Distributed IoT Classroom
Management System. All tests use `unittest` with `unittest.mock` to isolate
components from the database and MQTT broker, ensuring tests run reliably
without any external infrastructure.

---

## Testing Strategy

### Approach: Unit Testing with Mocking

Each test targets a single handler function in `master_pi/socket_server.py`.
External dependencies (MySQL database, MQTT broker) are replaced with
`unittest.mock.patch` and `MagicMock` objects. This means:

- Tests run without a live database
- Tests run without a running MQTT broker
- Tests are fast, deterministic, and repeatable
- Each test verifies one specific behaviour

---

## Test Files and Coverage

### `test_auth.py` — Authentication & Registration
Covers the minimum requirement: **authentication logic**

| Test | What it verifies |
|------|-----------------|
| `test_login_success` | Valid credentials return ok with user info |
| `test_login_wrong_password` | Wrong password returns error |
| `test_login_missing_university_id` | Missing ID rejected before DB call |
| `test_login_missing_password` | Missing password rejected before DB call |
| `test_login_db_failure` | DB connection failure handled gracefully |
| `test_login_response_contains_user_id` | Response includes user_id field |
| `test_register_missing_fields` | Empty fields rejected before DB call |
| `test_register_invalid_email` | Invalid email format rejected |
| `test_register_success` | Valid data returns ok |
| `test_register_duplicate_id` | Duplicate ID returns error |

---

### `test_booking.py` — Booking Logic
Covers the minimum requirement: **booking logic**

| Test | What it verifies |
|------|-----------------|
| `test_book_room_success` | Valid booking returns ok with token |
| `test_book_room_token_is_string` | Token is a non-empty string |
| `test_book_room_missing_fields` | Missing fields rejected before DB call |
| `test_book_room_conflict` | Double booking returns error |
| `test_book_room_db_failure` | DB failure handled gracefully |
| `test_cancel_booking_success` | Active booking can be cancelled |
| `test_cancel_booking_missing_fields` | Missing booking_id rejected |
| `test_checkin_success` | Valid checkin returns ok |
| `test_checkout_success` | Valid checkout returns ok |
| `test_get_bookings_returns_list` | Returns list of bookings for user |
| `test_get_bookings_missing_user_id` | Missing user_id returns error |

---

### `test_input_validation.py` — User Input Validation
Covers the minimum requirement: **user input validation**

| Test | What it verifies |
|------|-----------------|
| `test_valid_email` | Valid email formats pass |
| `test_invalid_email_no_at` | Email without @ fails |
| `test_invalid_email_no_domain` | Email without domain fails |
| `test_invalid_email_no_tld` | Email without TLD fails |
| `test_invalid_email_empty` | Empty string fails |
| `test_invalid_email_spaces` | Email with spaces fails |
| `test_empty_university_id_rejected` | Empty ID rejected |
| `test_empty_full_name_rejected` | Empty name rejected |
| `test_empty_password_rejected` | Empty password rejected |
| `test_invalid_email_rejected` | Invalid email in registration rejected |
| `test_whitespace_university_id_rejected` | Whitespace-only ID rejected |
| `test_missing_both_fields_rejected` | Both fields missing rejected |

---

### `test_room_state.py` — Room State Transitions
Covers the minimum requirement: **room state transitions** and **error handling**

| Test | What it verifies |
|------|-----------------|
| `test_report_fault_success` | Fault report returns ok and triggers MQTT |
| `test_report_fault_publishes_security_alert` | Security team notified via MQTT |
| `test_report_fault_db_failure` | DB failure handled gracefully |
| `test_status_update_available_to_maintenance` | Status change succeeds |
| `test_status_update_publishes_mqtt` | Status change triggers MQTT |
| `test_status_update_db_failure` | DB failure handled gracefully |
| `test_valid_token_grants_access` | Valid token returns ok |
| `test_used_token_denied` | Already-used token denied |
| `test_invalid_token_denied` | Non-existent token denied |

---

### `test_socket_format.py` — Socket & MQTT Message Format
Covers the minimum requirement: **socket and MQTT message format correctness**

| Test | What it verifies |
|------|-----------------|
| `test_unknown_action_returns_error` | Unknown actions handled gracefully |
| `test_ping_action` | Ping returns pong |
| `test_response_always_has_status` | All responses have status field |
| `test_response_status_is_string` | Status is always a string |
| `test_error_response_has_message` | Error responses have message field |
| `test_login_response_format` | Login response has required fields |
| `test_book_room_response_has_token` | Booking response has token |
| `test_fault_report_mqtt_topic_format` | Fault publishes to correct MQTT topics |
| `test_status_update_mqtt_topic_format` | Status update uses correct topic format |
| `test_mqtt_payload_is_string` | All MQTT payloads are strings |

---

## Additional Feature: Token Security Testing

Beyond the minimum coverage, we chose to add focused tests for the
**one-time token validation system** (tested in `test_room_state.py`).

**Justification:** The token system is a critical security feature — if a token
can be reused or a fake token can grant access, the room security model
completely breaks. Testing that:
- Valid tokens grant access
- Used tokens are rejected
- Invalid tokens are rejected

...ensures the Room Pi access control works correctly under all three conditions.
This directly protects against unauthorized room access during the demo and
in real deployment.

---

## How to Run Tests

From the project root with the virtual environment activated:

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific file
python -m pytest tests/test_auth.py -v

# Run with coverage report
pip install pytest-cov
python -m pytest tests/ --cov=master_pi --cov-report=term-missing
```
