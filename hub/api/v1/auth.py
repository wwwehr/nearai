
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.near.sign import verify_signed_message
from typing import Optional

import logging

bearer = HTTPBearer()
logger = logging.getLogger(__name__)


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
    plainMsg: str
    """The plain message that was signed."""


async def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer)):
    logging.debug(f"Received token: {token.credentials}")
    auth = AuthToken.model_validate_json(token.credentials)

    is_valid = verify_signed_message(auth.account_id, auth.public_key, auth.signature, auth.plainMsg, bytes(
        "1", "utf-8") * 32, "ai.near", auth.callback_url)
    if not is_valid:
        logging.error(
            f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid token")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    return auth
