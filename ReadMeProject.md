# Distributed IoT Classroom Management System

## Team Information

- Member 1 – Master Pi + Admin Functions
- Member 2 – Agent Pi + User Booking System
- Member 3 – Room Pi + MQTT + Sense HAT + Fault Reporting
- Member 4 – Database + Reports + Testing


---

## Project Overview

This project is a distributed IoT classroom management system for a university teaching building using multiple Raspberry Pi devices.

The system includes:

- Master Pi (central controller)
- Agent Pi (user/staff interface)
- Room Pi (classroom access and display)

Communication is implemented using:

- Socket Programming for request-response communication
- MQTT for publish-subscribe real-time updates

The remote database is connected only to the Master Pi.

---

## System Architecture

### Master Pi

- Admin access only
- Hosts web interface
- Handles socket requests
- Connects to remote database
- Publishes MQTT alerts and room status updates

### Agent Pi

- User and security staff access
- Handles registration, login, room booking, and cancellations
- Sends socket requests to Master Pi

### Room Pi

- Classroom display terminal
- Verifies room access token
- Displays room status
- Reports faults
- Receives MQTT updates

---

## Communication Design

### Socket Programming

Used for one-to-one communication:

Examples:

- login verification
- room booking
- token validation
- fault reporting

### MQTT

Used for one-to-many communication:

Examples:

- room status updates
- security alerts
- fault notifications
- Sense HAT warning triggers

---

## Division of Work

### Member 1

- Admin panel
- User management
- Security staff management

### Member 2

- Login/Register system
- Room booking
- Token generation

### Member 3

- Room Pi verification
- MQTT publish/subscribe
- Fault reporting
- Security alerts
- Sense HAT warning system

### Member 4

- Database integration
- Report generation
- Unit testing
- Documentation support

---

## Custom Enhancements

### Enhancement 1: Sense HAT Fault Warning

When a room enters Fault status:

- security staff receives MQTT alert
- Sense HAT triggers visual warning using red alert display

This improves real-time response for maintenance issues.

### Enhancement 2: Room Token Access Verification

Users receive a one-time access token after booking.

Room Pi validates the token before allowing room access.

This improves classroom security and prevents unauthorized usage.

---

## Challenges Encountered

- MQTT broker setup and connection issues
- Flask route management across multiple Pis
- Synchronizing socket communication and MQTT events
- Handling distributed testing across multiple devices
- Managing GitHub collaboration in group development

---

## Lessons Learned

- Distributed IoT systems require strong communication design
- MQTT is highly effective for real-time event handling
- Socket programming works best for direct request-response communication
- Proper Git workflow prevents major project issues
- Testing early prevents serious demo-time failures

---

## Report Generation

Admin users can generate:

- room booking frequency report
- room usage visualization

The report is automatically saved as:

report.png

---

## Testing

Unit tests were created for:

- authentication
- room booking
- room state transitions
- socket request validation

Testing ensures system reliability and improves maintainability.