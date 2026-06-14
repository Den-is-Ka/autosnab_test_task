CREATE TABLE IF NOT EXISTS requests_history (
    id SERIAL PRIMARY KEY,
    cadastral_number VARCHAR(100) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    result BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_requests_history_cadastral_number
ON requests_history (cadastral_number);
