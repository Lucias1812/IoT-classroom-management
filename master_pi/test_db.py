from db import get_connection


conn = get_connection()

if conn:
    cursor = conn.cursor()
    cursor.execute("SELECT room_code, status FROM rooms")

    for row in cursor.fetchall():
        print(row)

    cursor.close()
    conn.close()
else:
    print("Connection failed")