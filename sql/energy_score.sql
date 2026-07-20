-- Relative route energy score fact (Strategy C hybrid index — NOT measured kWh)

CREATE TABLE IF NOT EXISTS fact_route_energy_score (
    energy_score_key    BIGSERIAL PRIMARY KEY,
    date_key            INTEGER NOT NULL REFERENCES dim_date(date_key),
    route_key           INTEGER NOT NULL REFERENCES dim_route(route_key),
    vehicle_type_key    INTEGER NOT NULL REFERENCES dim_vehicle_type(vehicle_type_key),
    region_id           VARCHAR(64) NOT NULL DEFAULT 'all',
    region_name         VARCHAR(128) NOT NULL DEFAULT 'All stops',
    trip_count          INTEGER NOT NULL DEFAULT 0,
    total_km            DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_km              DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_hours         DOUBLE PRECISION NOT NULL DEFAULT 0,
    p90_hours           DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_stops           DOUBLE PRECISION NOT NULL DEFAULT 0,
    delay_hours         DOUBLE PRECISION NOT NULL DEFAULT 0,
    raw_score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    energy_score        DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_flagged          BOOLEAN NOT NULL DEFAULT FALSE,
    flag_reasons        TEXT NOT NULL DEFAULT '',
    data_source         VARCHAR(40) NOT NULL DEFAULT 'estimate_v1',
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (date_key, route_key, region_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_route_energy_date_region
    ON fact_route_energy_score (date_key, region_id);

CREATE INDEX IF NOT EXISTS idx_fact_route_energy_score
    ON fact_route_energy_score (energy_score DESC);
