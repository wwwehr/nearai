from datetime import time
from typing import Union, Any, List, Optional


import base64
import hashlib
import base58
import nacl.signing
import requests
from serializer import BinarySerializer

class Payload:
    def __init__(  # noqa: D107
        self, message: str, nonce: Union[bytes, str, List[int]], recipient: str, callback_url: Optional[str] = None
    ):
        self.tag = 2147484061
        self.message = message
        self.nonce = validate_nonce(nonce)
        self.recipient = recipient
        self.callbackUrl = callback_url


PAYLOAD_SCHEMA: list[list[Any]] = [
    [
        Payload,
        {
            "kind": "struct",
            "fields": [
                ["tag", "u32"],
                ["message", "string"],
                ["nonce", [32]],
                ["recipient", "string"],
                [
                    "callbackUrl",
                    {
                        "kind": "option",
                        "type": "string",
                    },
                ],
            ],
        },
    ]
]
def validate_signature(public_key: str, signature: str, payload: Payload):
    """Validates a cryptographic signature for a given payload using a specified public key."""
    borsh_payload = BinarySerializer(dict(PAYLOAD_SCHEMA)).serialize(payload)
    to_sign = hashlib.sha256(borsh_payload).digest()
    real_signature = base64.b64decode(signature)

    verify_key: nacl.signing.VerifyKey = nacl.signing.VerifyKey(base58.b58decode(public_key[len(ED_PREFIX) :]))

    try:
        verify_key.verify(to_sign, real_signature)
        # print("Signature is valid.")
        return True
    except nacl.exceptions.BadSignatureError:
        # print("Signature was forged or corrupt.")
        return False


def convert_nonce(value: Union[str, bytes, list[int]]):
    """Converts a given value to a 32-byte nonce."""
    if isinstance(value, bytes):
        if len(value) > 32:
            raise ValueError("Invalid nonce length")
        if len(value) < 32:
            value = value.rjust(32, b"0")
        return value
    elif isinstance(value, str):
        nonce_bytes = value.encode("utf-8")
        if len(nonce_bytes) > 32:
            raise ValueError("Invalid nonce length")
        if len(nonce_bytes) < 32:
            nonce_bytes = nonce_bytes.rjust(32, b"0")
        return nonce_bytes
    elif isinstance(value, list):
        if len(value) != 32:
            raise ValueError("Invalid nonce length")
        return bytes(value)
    else:
        raise ValueError("Invalid nonce format")

def validate_nonce(value: Union[str, bytes, list[int]]):
    """Ensures that the nonce is a valid timestamp."""
    nonce = convert_nonce(value)
    nonce_int = int(nonce.decode("utf-8"))

    now = int(time.time() * 1000)

    if nonce_int > now:
        raise ValueError("Nonce is in the future")
    if now - nonce_int > 10 * 365 * 24 * 60 * 60 * 1000:
        """If the timestamp is older than 10 years, it is considered invalid. Forcing apps to use unique nonces."""
        raise ValueError("Nonce is too old")

    return nonce

def verify_access_key_owner(public_key, account_id):
    """Verifies if a given public key belongs to a specified account ID using FastNEAR API."""
    try:
        url = f"https://api.fastnear.com/v0/public_key/{public_key}"
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        account_ids = content.get("account_ids", [])
        key_owner_verified = account_id in account_ids
        if not key_owner_verified:
            print("Key's owner verification failed. Only NEAR Mainnet accounts are supported.")
        return key_owner_verified
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")

    return False


def verify_signed_message(account_id, public_key, signature, message, nonce, recipient, callback_url):
    """Verifies a signed message and ensures the public key belongs to the specified account."""
    is_valid = validate_signature(public_key, signature, Payload(message, nonce, recipient, callback_url))

    if not is_valid and callback_url is not None:
        is_valid = validate_signature(public_key, signature, Payload(message, nonce, recipient, None))

    if is_valid:
        # verify that key belongs to `account_id`
        return verify_access_key_owner(public_key, account_id)

    return False