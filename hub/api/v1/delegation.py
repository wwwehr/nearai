from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import delete, select

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Delegation, get_session

v1_router = APIRouter(
    prefix="/delegation",
    tags=["delegation"],
)


@v1_router.post("/delegate")
def delegate(delegate_account_id: str, expires_at: datetime, auth: AuthToken = Depends(revokable_auth)):
    # First revoke any existing delegation to this account
    revoke_delegation(delegate_account_id, auth)

    # Then create a new delegation
    with get_session() as session:
        delegation = Delegation(
            original_account_id=auth.account_id,
            delegation_account_id=delegate_account_id,
            expires_at=expires_at,
        )
        session.add(delegation)
        session.commit()


@v1_router.post("/list_delegations")
def list_delegation(auth: AuthToken = Depends(revokable_auth)) -> List[Delegation]:
    with get_session() as session:
        query = select(Delegation).where(Delegation.original_account_id == auth.account_id)
        return session.exec(query).all()


@v1_router.post("/revoke_delegation")
def revoke_delegation(
    delegate_account_id: str,
    auth: AuthToken = Depends(revokable_auth),
):
    with get_session() as session:
        query = delete(Delegation).where(Delegation.original_account_id == auth.account_id)

        # If delegate_account_id is not empty, then only revoke delegation to that account
        # Otherwise revoke all delegations.
        if delegate_account_id != "":
            query = query.where(Delegation.delegation_account_id == delegate_account_id)

        session.exec(query)
        session.commit()
