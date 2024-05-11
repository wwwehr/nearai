import json

import pymysql

from jasnah.config import CONFIG


class DB:
    def __init__(self, host, port, user, password, database):
        self.connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database
        )

    def close(self):
        self.connection.close()

    def _create(self):
        """Create tables if they don't exist"""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS supervisors
                        (host VARCHAR(255) NOT NULL PRIMARY KEY,
                        available BOOLEAN NOT NULL)"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS experiments
                            (id INT AUTO_INCREMENT PRIMARY KEY,
                            experiment VARCHAR(255) NOT NULL,
                            author VARCHAR(255) NOT NULL,
                            commit VARCHAR(255) NOT NULL,
                            diff TEXT,
                            assigned VARCHAR(255),
                            status VARCHAR(255) NOT NULL)"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS logs
                            (id INT AUTO_INCREMENT PRIMARY KEY,
                            origin VARCHAR(255) NOT NULL,
                            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            content JSON)"""
            )

        self.connection.commit()

    def log(self, origin: str, content):
        content = json.dumps(content)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (origin, content) VALUES (%s, %s)", (origin, content)
            )
        self.connection.commit()

    def _drop(self):
        """Drop tables"""
        with self.connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS supervisors")
            cursor.execute("DROP TABLE IF EXISTS experiments")
            cursor.execute("DROP TABLE IF EXISTS logs")

        self.connection.commit()

    def _check_all(self):
        """Check all tables"""
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM supervisors LIMIT 100")
            print(cursor.fetchall())

            cursor.execute("SELECT * FROM experiments LIMIT 100")
            print(cursor.fetchall())

            cursor.execute("SELECT * FROM logs LIMIT 100")
            print(cursor.fetchall())


def connect() -> "DB":
    return DB(
        CONFIG.db_host,
        CONFIG.db_port,
        CONFIG.db_user,
        CONFIG.db_password,
        CONFIG.db_name,
    )


try:
    db = connect()
except Exception as e:
    print("Could not connect to the database")
    print(e)
    db = None


if __name__ == "__main__":
    print(db)
    # db._create()
    db.log("test", {"hello": "world", "life": 42})
    db._check_all()
