import unittest

# how to run:
# python -m unittest discover -s hub/tests
from hub.api.near.sign import Payload, validate_signature, verify_signed_message


class TestSignatureVerification(unittest.TestCase):
    def setUp(self): # noqa: D102
        self.account_id = "dev.near"
        self.callback_url = "https://dev.near.social/dev.near/widget/Hub"
        self.message = "Welcome to NEAR.AI"
        self.recipient = "ai.near"
        self.nonce = bytes("1", "utf-8") * 32

        self.public_key = "ed25519:2aPrik9S1qCnnfNo2doETrNa61ZaBwZYC8baschK5din"
        self.signature = "pyiixiWS3zHNhPFhd6EJy2oenB2WfxT5MTcOtNnreA/hqTgRCDKIMxu+6MjmDif7jbC+U1/V7VOT2oSv6kfXBQ=="

    def test_verify_signed_message(self): # noqa: D102
        self.assertTrue(
            verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                self.message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

        illegal_message = ""
        self.assertFalse(
            verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                illegal_message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

    def test_verify_signed_message_with_timestamp_nonce(self): # noqa: D102
        self.account_id = "zavodil.near"
        self.callback_url = "http://localhost:5173?message=Welcome+to+NEAR+AI+Hub%21&recipient=ai.near&nonce=00000000000000000001722333704261&type=remote"
        self.message = "Welcome to NEAR AI Hub!"
        self.recipient = "ai.near"
        self.nonce = "1722333704261"
        self.public_key = "ed25519:HFd5upW3ppKKqwmNNbm56JW7VHXzEoDpwFKuetXLuNSq"
        self.signature = "f527uJAg0o60I1BozX+zo0NrAmOdw9UdXvmLGQoA2i/gkOGTeR9AMH1sJQQdCSA4RGrOnyyKfaLTbjGWW6uTAQ=="

        self.assertTrue(
            verify_signed_message(
                self.account_id,
                self.public_key,
                self.signature,
                self.message,
                self.nonce,
                self.recipient,
                self.callback_url,
            )
        )

    def test_validate_signature(self): # noqa: D102
        payload = Payload(self.message, self.nonce, self.recipient, self.callback_url)
        self.assertTrue(validate_signature(self.public_key, self.signature, payload))


if __name__ == "__main__":
    unittest.main()
