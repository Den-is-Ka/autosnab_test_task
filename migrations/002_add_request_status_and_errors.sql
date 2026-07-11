ALTER TABLE requests_history
    ALTER COLUMN result DROP NOT NULL;

ALTER TABLE requests_history
    ADD COLUMN IF NOT EXISTS status VARCHAR(20),
    ADD COLUMN IF NOT EXISTS external_response JSONB,
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

UPDATE requests_history
SET
    status = 'completed',
    completed_at = COALESCE(completed_at, created_at),
    external_response = COALESCE(external_response, jsonb_build_object('result', result))
WHERE status IS NULL;

ALTER TABLE requests_history
    ALTER COLUMN status SET DEFAULT 'processing',
    ALTER COLUMN status SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'requests_history_status_check'
    ) THEN
        ALTER TABLE requests_history
            ADD CONSTRAINT requests_history_status_check
            CHECK (status IN ('processing', 'completed', 'timeout', 'failed'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'requests_history_duration_ms_check'
    ) THEN
        ALTER TABLE requests_history
            ADD CONSTRAINT requests_history_duration_ms_check
            CHECK (duration_ms IS NULL OR duration_ms >= 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_requests_history_created_at
    ON requests_history (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_requests_history_cadastral_created
    ON requests_history (cadastral_number, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_requests_history_status
    ON requests_history (status);
