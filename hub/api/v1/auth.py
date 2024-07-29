import json
import logging

from typing import Optional, Union
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from hub.api.near.sign import verify_signed_message
from hub.api.v1.sql import SqlClient

bearer = HTTPBearer()
logger = logging.getLogger(__name__)
db = SqlClient()


class AuthToken(BaseModel):
    """Model for auth callback."""
    account_id: str
    """The account ID."""
    public_key: str
    """The public key."""
    signature: str
    """The signature."""
    callback_url: Optional[str] = None
    """The callback URL."""
    recipient: Optional[str] = "ai.near"
    """Message Recipient"""
    nonce: bytes = Field(default=bytes("1", "utf-8") *
                         32, min_length=32, max_length=32)
    plainMsg: str
    """The plain message that was signed."""

    @classmethod
    def validate_nonce(cls, value: Union[str, list[int]]):
        if isinstance(value, str):
            return bytes.fromhex(value)
        elif isinstance(value, list):
            return bytes(value)
        else:
            raise ValueError("Invalid nonce format")

    @classmethod
    def model_validate_json(cls, json_str: str):
        data = json.loads(json_str)
        if 'nonce' in data:
            data['nonce'] = cls.validate_nonce(data['nonce'])
        return cls(**data)


async def get_auth(token: HTTPAuthorizationCredentials = Depends(bearer)):
    if token.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return AuthToken.model_validate_json(token.credentials)
    except Exception as e:
        logging.error(f"Error parsing token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def validate_auth(auth: AuthToken = Depends(get_auth)):
    is_valid = verify_signed_message(auth.account_id, auth.public_key, auth.signature, auth.plainMsg, auth.nonce,
                                     auth.recipient, auth.callback_url)
    if not is_valid:
        logging.error(
            f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    challenge = db.get_challenge(auth.plainMsg)

    if challenge is None:
        logging.error(
            f"account_id {auth.account_id}: challenge not found")
        raise HTTPException(status_code=401, detail="Invalid challenge")

    if challenge.is_pending():
        logging.info(
            f"account_id {auth.account_id}: challenge is pending, assigning")
        db.assign_challenge(auth.plainMsg, auth.account_id)
    elif not challenge.is_valid_auth(auth.account_id):
        logging.error(
            f"account_id {auth.account_id}: challenge is not a valid auth")
        raise HTTPException(status_code=401, detail="Invalid challenge")

    return auth
