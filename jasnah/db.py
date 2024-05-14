import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import backoff
import pymysql

from jasnah.config import CONFIG


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


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
    num_nodes: int = 1
    status: str = "pending"

    @staticmethod
    def from_db(row) -> Optional["Experiment"]:
        if row is None:
            return None

        return Experiment(*row)


@dataclass
class Supervisor:
    id: str
    experiment_id: int
    cluster: str
    endpoint: str
    status: str

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
        content = json.dumps(content, default=datetime_serializer)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO logs (origin, content) VALUES (%s, %s)", (origin, content)
            )
        self.connection.commit()

    def add_experiment(
        self,
        name: str,
        author: str,
        repository: str,
        commit: str,
        diff: Optional[str],
        command: str,
        num_nodes: int,
    ) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO experiments (name, author, repository, commit, diff, command, num_nodes, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    name,
                    author,
                    repository,
                    commit,
                    diff,
                    command,
                    num_nodes,
                    "pending",
                ),
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
                "SELECT experiment_id FROM supervisors WHERE id=%s AND status='assigned'",
                (supervisor_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            experiment_id = row[0]

            cursor.execute(
                "SELECT * FROM experiments WHERE id=%s LIMIT 1", (experiment_id,)
            )

            return Experiment.from_db(cursor.fetchone())

    def last_experiments(self, total: int) -> List[Experiment]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM experiments ORDER BY id DESC LIMIT %s", (total,)
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
            supervisors_d = [
                (s.id, s.endpoint, s.cluster, s.status) for s in supervisors
            ]
            cursor.executemany(
                "INSERT IGNORE INTO supervisors (id, endpoint, cluster, status) VALUES (%s, %s, %s, %s)",
                supervisors_d,
            )
        self.connection.commit()

    def num_nodes(self, experiment_id) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT num_nodes FROM experiments WHERE id=%s LIMIT 1",
                (experiment_id,),
            )
            return cursor.fetchone()[0]

    def set_experiment_status(self, experiment_id: str, status: str):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE experiments SET status=%s WHERE id=%s", (status, experiment_id)
            )
        self.connection.commit()

    def set_supervisor_status(self, supervisor_id: str, status: str):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE supervisors SET status=%s WHERE id=%s",
                (status, supervisor_id),
            )
        self.connection.commit()

    def get_assigned_supervisors(self, experiment_id: int) -> List[Supervisor]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM supervisors WHERE experiment_id=%s AND status='assigned' ORDER BY id",
                (experiment_id,),
            )
            return [Supervisor.from_db(row) for row in cursor.fetchall()]

    def set_all_supervisors_unavailable(self):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE supervisors SET status='unavailable' WHERE status='available'"
            )
        self.connection.commit()

    @backoff.on_predicate(backoff.expo, lambda x: x is None, max_tries=7)
    def _lock_supervisors(
        self, experiment_id: int, total: int
    ) -> Optional[List[Supervisor]]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM supervisors WHERE status='available' ORDER BY id LIMIT %s OFFSET %s",
                (1, total - 1),
            )
            result = cursor.fetchone()

            if result is None:
                # There are not enough supervisors. Don't backoff
                return []

            supervisor_id = result[0]

            cursor.execute(
                "UPDATE supervisors SET experiment_id=%s, status='preassigned' WHERE status='available' AND id <= %s",
                (
                    experiment_id,
                    supervisor_id,
                ),
            )

            self.connection.commit()

            cursor.execute(
                "SELECT * FROM supervisors WHERE experiment_id=%s AND status='preassigned'",
                (experiment_id,),
            )

            selected = cursor.fetchall()

            if len(selected) == total:
                cursor.execute(
                    "UPDATE supervisors SET status='assigned' WHERE experiment_id=%s",
                    (experiment_id,),
                )
                self.connection.commit()
                return [Supervisor.from_db(row) for row in selected]

            else:
                cursor.execute(
                    "UPDATE supervisors SET status='available' WHERE experiment_id=%s",
                    (experiment_id,),
                )
                self.connection.commit()
                return None

    def exists_in_registry(self, s3_path: str) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM registry WHERE s3_path=%s", (s3_path,))
            return cursor.fetchone() is not None

    def add_to_registry(self, s3_path: str):
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO registry (s3_path) VALUES (%s)", (s3_path,))
        self.connection.commit()

    def _create(self):
        """Create tables if they don't exist"""
        with self.connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS supervisors(
                            id VARCHAR(255) NOT NULL PRIMARY KEY,
                            experiment_id INT,
                            cluster VARCHAR(255) NOT NULL,
                            endpoint VARCHAR(255) NOT NULL,
                            status VARCHAR(255) NOT NULL
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
                            num_nodes INT NOT NULL,
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

            cursor.execute(
                """CREATE TABLE IF NOT EXISTS registry(
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        s3_path VARCHAR(255) NOT NULL
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
            print("\nSupervisors:")
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
    # db._check_all()
    pass
