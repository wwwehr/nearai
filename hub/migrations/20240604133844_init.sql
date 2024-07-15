-- Add migration script here
CREATE DATABASE IF NOT EXISTS router;

CREATE TABLE completions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX completions_account_id_idx ON completions(account_id(255));
