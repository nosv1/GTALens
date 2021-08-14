from dotenv import load_dotenv
import mysql.connector
import os

load_dotenv()


class DB:
    def __init__(self, connection, cursor):
        self.connection = connection
        self.cursor = cursor


def connect_database(db_name=os.getenv("DB_NAME")) -> DB:

    db_connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),

        database=db_name,
        charset="utf8mb4",
        use_unicode=True,
        buffered=True
    )

    db_cursor = db_connection.cursor()

    return DB(db_connection, db_cursor)


def replace_chars(bad_string: str) -> str:
    return bad_string.replace("'", "''").replace("\\", "\\\\")

