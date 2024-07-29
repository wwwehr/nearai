import pymysql
import pymysql.cursors
import logging
from os import getenv
from dotenv import load_dotenv
from pydantic import BaseModel
from enum import Enum

load_dotenv()

logger = logging.getLogger(__name__)


class ChallengeStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class UserChallenge(BaseModel):
    id: str
    account_id: str | None
    challenge_status: ChallengeStatus

    def is_active(self):
        return self.account_id != None and self.challenge_status == ChallengeStatus.ACTIVE

    def is_pending(self):
        return self.challenge_status == ChallengeStatus.PENDING

    def is_valid_auth(self, account_id: str):
        logging.info(
            f"Checking if challenge {self} is valid for account {account_id}")
        return self.is_active() and self.account_id == account_id


class SqlClient:

    def __init__(self):
        self.db = pymysql.connect(
            host=getenv("DATABASE_HOST"),
            user=getenv("DATABASE_USER"),
            password=getenv("DATABASE_PASSWORD"),
            database=getenv("DATABASE_NAME")
        )

    def __fetch_all(self, query: str):
        """
        Fetches all matching rows from the database. Returns a list of dictionaries, the dicts can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchall()

    def add_user_usage(self, account_id: str, query: str, response: str, model: str, provider: str, endpoint: str):
        # Escape single quotes in query and response strings
        query = query.replace("'", "''")
        response = response.replace("'", "''")

        query = f"INSERT INTO completions (account_id, query, response, model, provider, endpoint) VALUES ('{account_id}', '{query}', '{response}', '{model}', '{provider}', '{endpoint}')"
        self.db.cursor().execute(query)
        self.db.commit()

    def get_user_usage(self, account_id: str):
        query = f"SELECT * FROM completions WHERE account_id = '{account_id}'"
        return self.__fetch_all(query)

    def add_challenge(self, challenge: str):
        logging.debug(f"Adding challenge {challenge}")
        query = f"INSERT INTO challenges (id) VALUES ('{challenge}')"
        self.db.cursor().execute(query)
        self.db.commit()

    def assign_challenge(self, challenge: str, account_id: str):
        logging.debug(
            f"Assigning challenge {challenge} to account {account_id}")
        query = f"UPDATE challenges SET account_id = '{account_id}', challenge_status = 'active' WHERE id = '{challenge}'"
        self.db.cursor().execute(query)
        self.db.commit()

    def get_challenge(self, challenge: str):
        logging.debug(f"Getting challenge {challenge}")
        query = f"SELECT * FROM challenges WHERE id = '{challenge}'"
        res = [UserChallenge(**x) for x in self.__fetch_all(query)]
        if len(res) == 0:
            return None
        if len(res) > 1:
            raise ValueError("More than one challenge found")
        return res[0]
