USE hub;

-- challenge is a uuid4
-- account_id is a near account, max 64 characters
CREATE TABLE challenges (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(64),
    challenge_status ENUM('pending', 'expired', 'active', 'revoked') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);