import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from shared.near.sign import validate_nonce, verify_signed_message
from sqlmodel import select

from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.models import Delegation, get_session
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
    recipient: str = "ai.near"
    """Message Recipient"""
    nonce: bytes
    """Nonce of the signed message, it must be 32 bytes long."""
    message: str  # noqa: N815
    """The plain message that was signed."""

    @field_validator("nonce")
    @classmethod
    def validate_and_convert_nonce(cls, value: str):  # noqa: D102
        return validate_nonce(value)


class RawAuthToken(AuthToken):
    on_behalf_of: Optional[str] = None
    """The account ID on behalf of which the request is made."""

    def unwrap(self) -> AuthToken:
        """Unwrap the raw auth token."""
        return AuthToken(
            account_id=self.account_id,
            public_key=self.public_key,
            signature=self.signature,
            callback_url=self.callback_url,
            recipient=self.recipient,
            nonce=self.nonce,
            message=self.message,
        )


async def get_auth(token: HTTPAuthorizationCredentials = Depends(bearer)):
    if token.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    if token.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme")
    try:
        token.credentials = token.credentials.replace("Bearer ", "")
        logger.debug(f"Token: {token.credentials}")
        return RawAuthToken.model_validate_json(token.credentials)
    except Exception as e:
        raise TokenValidationError(detail=str(e)) from None


async def validate_signature(auth: RawAuthToken = Depends(get_auth)):
    logging.debug(f"account_id {auth.account_id}: verifying signature")
    is_valid = verify_signed_message(
        auth.account_id,
        auth.public_key,
        auth.signature,
        auth.message,
        auth.nonce,
        auth.recipient,
        auth.callback_url,
    )
    if not is_valid:
        logging.error(f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    if auth.on_behalf_of is not None:
        # Query is trying to perform an action on behalf of another account. Check if it has permission to do so.

        query = (
            select(Delegation)
            .where(Delegation.original_account_id == auth.on_behalf_of)
            .where(Delegation.delegation_account_id == auth.account_id)
            .limit(1)
        )

        with get_session() as session:
            result = session.exec(query).first()

            if result is None:
                err_msg = f"{auth.account_id} don't have permission to execute action on behalf of {auth.on_behalf_of}."
                raise HTTPException(status_code=401, detail=err_msg)

            if result.expires_at is not None and result.expires_at < datetime.now():
                err_msg = f"{auth.account_id} permission to operate on behalf of {auth.on_behalf_of} expired."
                raise HTTPException(status_code=401, detail=err_msg)

        # TODO(517): Instead of altering the account_id we should keep the object as is, and instead have a method that returns
        #            the account_id that the request is being made on behalf of.
        auth.account_id = auth.on_behalf_of

    return auth.unwrap()


async def revokable_auth(auth: AuthToken = Depends(validate_signature)):
    logger.debug(f"Validating auth token: {auth}")

    user_nonce = db.get_account_nonce(auth.account_id, auth.nonce)

    if user_nonce and user_nonce.is_revoked():
        logging.error(f"account_id {auth.account_id}: nonce is revoked")
        raise HTTPException(status_code=401, detail="Revoked nonce")

    if not user_nonce:
        db.store_nonce(auth.account_id, auth.nonce, auth.message, auth.recipient, auth.callback_url)

    return auth
