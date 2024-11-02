from datetime import datetime, timedelta
from typing import List

from openapi_client.api.delegation_api import Delegation, DelegationApi


def delegate(account_id: str, expires_at: datetime | timedelta):
    if isinstance(expires_at, timedelta):
        expires_at = datetime.now() + expires_at
    DelegationApi().delegate_v1_delegation_delegate_post(account_id, expires_at)


def list_delegations() -> List[Delegation]:
    return DelegationApi().list_delegation_v1_delegation_list_delegations_post()


def revoke_delegation(delegate_account_id: str):
    """Revoke delegation to a specific account."""
    DelegationApi().revoke_delegation_v1_delegation_revoke_delegation_post(delegate_account_id)
