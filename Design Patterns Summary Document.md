# Design Patterns Summary Document

## Pattern 1: Observer Pattern

### What pattern was used

The Observer Pattern was implemented using MQTT publish-subscribe communication.

### Where and how it was implemented

The Master Pi acts as the publisher and Agent Pi / Room Pi act as subscribers.

Examples include:

- room status updates (`room/1/status`)
- security alerts (`security/alerts`)

When a room status changes, the Master Pi publishes MQTT messages automatically, and subscribed devices receive updates instantly without directly requesting them.

### Why this pattern was suitable

Observer Pattern is suitable because the system requires real-time updates across multiple distributed devices.

Instead of direct communication between every device, MQTT allows loose coupling and efficient event-driven updates.

This improves scalability and reflects real IoT system design.

### Challenges and alternatives considered

An alternative approach was using direct socket communication for all updates.

However, socket programming is better for one-to-one request-response communication, while MQTT is better for one-to-many notifications.

Therefore, Observer Pattern with MQTT was the better choice.

---

## Pattern 2: State Pattern

### What pattern was used

The State Pattern was implemented for classroom room status management.

### Where and how it was implemented

Each room moves between multiple states:

- Available
- In Use
- Fault
- Maintenance

Examples include:

- successful token verification changes room from Available → In Use
- fault reporting changes room from In Use → Fault
- security staff can change room to Maintenance
- checkout changes room back to Available

These transitions are managed through Master Pi logic and MQTT updates.

### Why this pattern was suitable

State Pattern is suitable because room behavior depends on its current state.

Different actions are allowed depending on whether the room is available, occupied, faulty, or under maintenance.

This makes system logic cleaner and easier to manage.

### Challenges and alternatives considered

An alternative was using simple if-else checks without formal state management.

However, as the number of room states increased, the logic became harder to maintain.

Using the State Pattern provided better structure and clearer system behavior.