-- 0010_phase1_3_hardening.sql
-- VANA Phase 4: Cloud Infrastructure & Database Hardening (PostgreSQL + PostGIS)
-- Adds sensor calibration registry, statutory dispatch ledger, and PostGIS spatial indexing.

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Hardware Calibration Registry
CREATE TABLE IF NOT EXISTS sensor_calibration_registry (
    device_id TEXT PRIMARY KEY,
    sensor_type TEXT NOT NULL,
    calibration_cert_sha256 TEXT NOT NULL,
    calibrated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('VERIFIED', 'NOT_VERIFIED', 'EXPIRED')),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sensor_calib_status ON sensor_calibration_registry (status);
CREATE INDEX IF NOT EXISTS idx_sensor_calib_device ON sensor_calibration_registry (device_id);

-- 2. Statutory Dispatch Ledger (Two-Man Rule Quorum & Flight Simulator)
CREATE TABLE IF NOT EXISTS statutory_dispatch_ledger (
    dispatch_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observation(observation_id),
    mission_id TEXT,
    target_zone TEXT,
    proposed_action TEXT NOT NULL,
    officer_id TEXT,
    admin_id TEXT,
    quorum_met INTEGER NOT NULL DEFAULT 0 CHECK (quorum_met IN (0, 1)),
    dispatch_mode TEXT NOT NULL CHECK (dispatch_mode IN ('DRY_RUN', 'PHYSICAL_GATED')),
    status TEXT NOT NULL CHECK (status IN ('PENDING_QUORUM', 'AUTHORIZED_DISPATCHED', 'PHYSICAL_HARDWARE_DETACHED', 'REJECTED')),
    flight_plan_json TEXT,
    receipt_sha256 TEXT NOT NULL,
    dispatched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dispatch_obs ON statutory_dispatch_ledger (observation_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_status ON statutory_dispatch_ledger (status);
CREATE INDEX IF NOT EXISTS idx_dispatch_quorum ON statutory_dispatch_ledger (quorum_met);

-- 3. PostGIS Spatial GIST Index on Geo-Location
CREATE INDEX IF NOT EXISTS idx_geo_location_geom_gist ON geo_location USING GIST (geom);

-- 4. Schema Version Record
INSERT INTO schema_version (version, applied_at, description)
VALUES ('0.9.8', NOW(), 'Adds sensor calibration registry, statutory dispatch ledger, and PostGIS GIST spatial indexing (Phase 4)')
ON CONFLICT (version) DO NOTHING;
