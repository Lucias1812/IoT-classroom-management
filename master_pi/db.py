import mysql.connector
from mysql.connector import Error


def get_connection():
    try:
        return mysql.connector.connect(
            # host="192.168.1.145",
            host="localhost",
            user="piot_user",
            password="piot_password",
            database="piot_db"
        )
    except Error as error:
        print(f"Database connection failed: {error}")
        return None