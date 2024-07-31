USE hub;

-- nonce represents a 32 bytes array 
-- https://github.com/near/NEPs/blob/master/neps/nep-0413.md#input-interface
-- account_id is a near account, max 64 characters
CREATE TABLE nonces (
    nonce VARCHAR(32),
    account_id VARCHAR(64),
    nonce_status ENUM('active', 'revoked') NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, nonce)
);