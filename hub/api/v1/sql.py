from typing import List
import pymysql
import pymysql.cursors
import logging
from os import getenv
from dotenv import load_dotenv
from pydantic import BaseModel, RootModel
from enum import Enum
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)


class NonceStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class UserNonce(BaseModel):
    nonce: str
    account_id: str
    nonce_status: NonceStatus
    first_seen_at: datetime

    def is_revoked(self):
        return self.nonce_status == NonceStatus.REVOKED


class UserNonces(RootModel):
    root: List[UserNonce]


class SqlClient:

    def __init__(self):
        self.db = pymysql.connect(
            host=getenv("DATABASE_HOST"),
            user=getenv("DATABASE_USER"),
            password=getenv("DATABASE_PASSWORD"),
            database=getenv("DATABASE_NAME"),
            autocommit=True
        )

    def __fetch_all(self, query: str):
        """
        Fetches all matching rows from the database. Returns a list of dictionaries, the dicts can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchall()

    def __fetch_one(self, query: str):
        """
        Fetches one row from the database. Returns a dictionary, the dict can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchone()

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

    def store_nonce(self, account_id: str, nonce: bytes):
        logging.info(f"Storing nonce {nonce} for account {account_id}")
        query = f"INSERT INTO nonces (nonce, account_id, nonce_status) VALUES ('{nonce.decode()}', '{account_id}', 'active')"
        self.db.cursor().execute(query)
        self.db.commit()

    def get_account_nonces(self, account_id: str):
        query = f"SELECT * FROM nonces WHERE account_id = '{account_id}'"
        nonces = [UserNonce(**x) for x in self.__fetch_all(query)]
        user_nonces = UserNonces(root=nonces) if nonces else None
        return user_nonces

    def get_account_nonce(self, account_id: str, nonce: bytes):
        query = f"SELECT * FROM nonces WHERE account_id = '{account_id}' AND nonce = '{nonce.decode()}'"
        res = self.__fetch_one(query)
        user_nonce = UserNonce(**res) if res else None
        return user_nonce

    def revoke_nonce(self, account_id: str, nonce: bytes):
        logging.info(f"Revoking nonce {nonce} for account {account_id}")
        query = f"UPDATE nonces SET nonce_status = 'revoked' WHERE account_id = '{account_id}' AND nonce = '{nonce.decode()}'"
        self.db.cursor().execute(query)
        self.db.commit()

    def revoke_all_nonces(self, account_id):
        logging.info(
            f"Revoking all nonces  for account {account_id}")
        query = f"UPDATE nonces SET nonce_status = 'revoked' WHERE account_id = '{account_id}'"
        self.db.cursor().execute(query)
        self.db.commit()
