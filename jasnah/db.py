import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import pymysql

from jasnah.config import CONFIG


@dataclass
class Experiment:
    id: int
    name: str
    author: str
    time: datetime
    repository: str
    commit: str
    diff: Optional[str]
    command: str
    assigned: Optional[str]
    status: str

    @staticmethod
    def from_db(row) -> Optional["Experiment"]:
        if row is None:
            return None

        return Experiment(*row)


@dataclass
class Supervisor:
    id: str
    endpoint: str
    available: bool

    @staticmethod
    def from_db(row) -> Optional["Supervisor"]:
        if row is None:
            return None

        return Supervisor(*row)


@dataclass
class Log:
    id: int
    origin: str
    time: datetime
    content: str

    @staticmethod
    def from_db(row) -> Optional["Log"]:
        if row is None:
            return None

        return Log(*row)


class DB:
    def __init__(self, host, port, user, password, database):
        self.connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database
        )

    def close(self):
        self.connection.close()

    def log(self, origin: str, content):
        content = json.dumps(content)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (origin, content) VALUES (%s, %s)", (origin, content)
            )
        self.connection.commit()

    def new_experiment(
        self,
        name: str,
        author: str,
        repository: str,
        commit: str,
        command: str,
        diff: str = None,
    ) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO experiments (name, author, repository, commit, command, diff, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, author, repository, commit, command, diff, "pending"),
            )
            self.connection.commit()
            return cursor.lastrowid

    def get_experiment(self, experiment_id: int) -> Optional[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM experiments WHERE id=%s LIMIT 1", (experiment_id,)
            )
            return Experiment.from_db(cursor.fetchone())

    def get_assignment(self, supervisor_id: str) -> Optional[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM experiments WHERE assigned=%s LIMIT 1", (supervisor_id,)
            )
            return Experiment.from_db(cursor.fetchone())

    def pending_experiments(self, total: int = 1) -> List[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM experiments WHERE status='pending' ORDER BY time LIMIT %s",
                (total,),
            )
            return [Experiment.from_db(row) for row in cursor.fetchall()]

    def available_supervisors(self, total: int = 1) -> List[Supervisor]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM supervisors WHERE available=1 LIMIT %s", (total,)
            )
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def add_supervisors(self, supervisors: List[Supervisor]):
        with self.connection.cursor() as cursor:
            for supervisor in supervisors:
                cursor.execute(
                    "INSERT IGNORE INTO supervisors (id, endpoint, available) VALUES (%s, %s, %s)",
                    (supervisor.id, supervisor.endpoint, supervisor.available),
                )
        self.connection.commit()

    def get_work_unit(self) -> Optional[Tuple[Experiment, Supervisor]]:
        with self.connection.cursor() as cursor:
            # TODO: Unsafe operation. Use FOR UPDATE in a single transaction
            # See here: https://www.singlestore.com/forum/t/concurrent-atomic-processing-with-select-for-update/2874

            cursor.execute("SELECT * FROM experiments WHERE status='pending' LIMIT 1")
            experiment = Experiment.from_db(cursor.fetchone())

            if not experiment:
                return None

            cursor.execute(
                "UPDATE experiments SET status='assigned' WHERE id=%s", (experiment.id,)
            )

            def release_experiment():
                cursor.execute(
                    "UPDATE experiments SET status='pending' WHERE id=%s",
                    (experiment.id,),
                )

            # TODO: Unsafe operation. See above.
            # TODO: Fetch as many supervisors as required
            cursor.execute("SELECT * FROM supervisors WHERE available=1 LIMIT 1")
            supervisor = Supervisor.from_db(cursor.fetchone())

            if not supervisor:
                release_experiment()
                return None

            cursor.execute(
                "UPDATE supervisors SET available=0 WHERE id=%s", (supervisor.id,)
            )

            # Update the experiment with the supervisor
            cursor.execute(
                "UPDATE experiments SET assigned=%s WHERE id=%s",
                (supervisor.id, experiment.id),
            )

            self.connection.commit()

            return experiment, supervisor

    def set_experiment_status(self, experiment_id: str, status: str):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE experiments SET status=%s WHERE id=%s", (status, experiment_id)
            )
        self.connection.commit()

    def set_supervisor_available(self, supervisor_id: str, available: bool = True):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE supervisors SET available=%s WHERE id=%s",
                (available, supervisor_id),
            )
        self.connection.commit()

    def _create(self):
        """Create tables if they don't exist"""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS supervisors(
                            id VARCHAR(255) NOT NULL PRIMARY KEY,
                            cluster VARCHAR(255) NOT NULL,
                            endpoint VARCHAR(255) NOT NULL,
                            available BOOLEAN NOT NULL
                            )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS experiments(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            author VARCHAR(255) NOT NULL,
                            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            repository VARCHAR(255) NOT NULL,
                            commit VARCHAR(255) NOT NULL,
                            diff TEXT,
                            command TEXT NOT NULL,
                            assigned VARCHAR(255),
                            status VARCHAR(255) NOT NULL
                            )"""
            )

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS logs(
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            origin VARCHAR(255) NOT NULL,
                            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            content JSON
                            )"""
            )

        self.connection.commit()

    def _drop(self):
        """Drop tables"""
        assert os.environ["JASNAH_I_KNOW_WHAT_I_AM_DOING"] == "yes"

        with self.connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS supervisors")
            cursor.execute("DROP TABLE IF EXISTS experiments")
            cursor.execute("DROP TABLE IF EXISTS logs")

        self.connection.commit()

    def _check_all(self):
        """Check all tables"""
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM supervisors LIMIT 16")
            print("Supervisors:")
            for supervisor in map(Supervisor.from_db, cursor.fetchall()):
                print(supervisor)

            print("\nExperiments:")
            cursor.execute("SELECT * FROM experiments LIMIT 16")
            for experiment in map(Experiment.from_db, cursor.fetchall()):
                print(experiment)

            print("\nLogs:")
            cursor.execute("SELECT * FROM logs LIMIT 16")
            for log in map(Log.from_db, cursor.fetchall()):
                print(log)
            print()


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
    # db._drop()
    # db._create()
    db.add_supervisors(
        [Supervisor("setup@10.141.0.11", "http://10.141.0.11:8000", "lambda", False)]
    )
    # db.new_experiment(
    #     "test-000", "marcelo", "github/repository", "123456", "python3 a.py", None
    # )
    # print(db.get_work_unit())
    db._check_all()
