-- =============================================================================
-- 03_analytics_views.sql
-- Super Mario SPCS Telemetry - Analytics Views
-- Creates all views used by the Streamlit telemetry dashboard
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARIO_DB;
USE SCHEMA PUBLIC;

-- -----------------------------------------------------------------------------
-- 1. MARIO_PLAYER_STATS - Aggregated totals across all games
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_PLAYER_STATS AS
SELECT
    COUNT(CASE WHEN record:name::STRING = 'mario.game_start' THEN 1 END) AS total_games,
    COUNT(CASE WHEN record:name::STRING = 'mario.death' THEN 1 END) AS total_deaths,
    COUNT(CASE WHEN record:name::STRING = 'mario.coin' THEN 1 END) AS total_coins_collected,
    COUNT(CASE WHEN record:name::STRING = 'mario.level_start' THEN 1 END) AS total_level_attempts,
    COUNT(CASE WHEN record:name::STRING = 'mario.level_win' THEN 1 END) AS total_level_wins,
    COUNT(CASE WHEN record:name::STRING = 'mario.game_win' THEN 1 END) AS total_game_wins,
    COUNT(CASE WHEN record:name::STRING = 'mario.powerup_spawn' THEN 1 END) AS total_powerups,
    COUNT(CASE WHEN record:name::STRING = 'mario.key_press' THEN 1 END) AS total_key_presses,
    MIN(timestamp) AS first_event,
    MAX(timestamp) AS last_event
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING LIKE 'mario.%';

-- -----------------------------------------------------------------------------
-- 2. MARIO_TOP_SCORES - Leaderboard ranked by coins (desc) and time (asc)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_TOP_SCORES AS
SELECT
    ROW_NUMBER() OVER (ORDER BY record_attributes:coins::INT DESC, record_attributes:session_duration::FLOAT ASC) AS rank,
    timestamp AS game_time,
    record_attributes:level::STRING AS final_level,
    record_attributes:coins::INT AS coins,
    ROUND(record_attributes:session_duration::FLOAT, 1) AS duration_seconds,
    ROUND(record_attributes:session_duration::FLOAT / 60, 1) AS duration_minutes
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING = 'mario.game_over';

-- -----------------------------------------------------------------------------
-- 3. MARIO_GAME_SESSIONS - Per-session breakdown with deaths, levels, coins
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS AS
WITH game_starts AS (
    SELECT
        timestamp AS session_start,
        record_attributes:lives::INT AS starting_lives,
        ROW_NUMBER() OVER (ORDER BY timestamp) AS session_id,
        LEAD(timestamp) OVER (ORDER BY timestamp) AS next_session_start
    FROM event_db.event_sh.my_events
    WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
      AND record_type = 'SPAN'
      AND record:name::STRING = 'mario.game_start'
),
game_overs AS (
    SELECT
        timestamp AS session_end,
        record_attributes:level::STRING AS final_level,
        record_attributes:coins::INT AS final_coins,
        record_attributes:session_duration::FLOAT AS duration_seconds
    FROM event_db.event_sh.my_events
    WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
      AND record_type = 'SPAN'
      AND record:name::STRING = 'mario.game_over'
),
matched AS (
    SELECT
        gs.session_id,
        gs.session_start,
        gs.starting_lives,
        gs.next_session_start,
        go.session_end,
        go.final_level,
        go.final_coins,
        go.duration_seconds,
        ROW_NUMBER() OVER (PARTITION BY gs.session_id ORDER BY go.session_end ASC) AS rn
    FROM game_starts gs
    LEFT JOIN game_overs go
      ON go.session_end > gs.session_start
      AND (gs.next_session_start IS NULL OR go.session_end < gs.next_session_start)
),
sessions AS (
    SELECT * FROM matched WHERE rn = 1
),
deaths_per_session AS (
    SELECT
        s.session_id,
        COUNT(*) AS total_deaths
    FROM sessions s
    JOIN event_db.event_sh.my_events e
      ON e.timestamp BETWEEN s.session_start AND COALESCE(s.session_end, CURRENT_TIMESTAMP())
    WHERE e.resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
      AND e.record_type = 'SPAN'
      AND e.record:name::STRING = 'mario.death'
    GROUP BY s.session_id
),
levels_per_session AS (
    SELECT
        s.session_id,
        COUNT(DISTINCT e.record_attributes:level::STRING) AS levels_played,
        MAX(e.record_attributes:level::STRING) AS highest_level
    FROM sessions s
    JOIN event_db.event_sh.my_events e
      ON e.timestamp BETWEEN s.session_start AND COALESCE(s.session_end, CURRENT_TIMESTAMP())
    WHERE e.resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
      AND e.record_type = 'SPAN'
      AND e.record:name::STRING = 'mario.level_start'
    GROUP BY s.session_id
)
SELECT
    s.session_id,
    s.session_start,
    s.session_end,
    ROUND(s.duration_seconds, 1) AS duration_seconds,
    s.final_level,
    s.final_coins AS score_coins,
    COALESCE(d.total_deaths, 0) AS total_deaths,
    COALESCE(l.levels_played, 0) AS levels_played,
    COALESCE(l.highest_level, '1-1') AS highest_level
FROM sessions s
LEFT JOIN deaths_per_session d ON s.session_id = d.session_id
LEFT JOIN levels_per_session l ON s.session_id = l.session_id;

-- -----------------------------------------------------------------------------
-- 4. MARIO_AVG_STATS - Average KPIs computed from sessions and totals
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_AVG_STATS AS
SELECT
    ROUND(AVG(s.DURATION_SECONDS), 1) AS avg_playtime_sec,
    ROUND(NULLIF(SUM(s.DURATION_SECONDS), 0) / NULLIF(SUM(s.TOTAL_DEATHS), 0), 1) AS avg_sec_per_death,
    ROUND(AVG(s.SCORE_COINS), 1) AS avg_coins_per_round,
    ROUND(NULLIF(SUM(s.DURATION_SECONDS), 0) / NULLIF(SUM(s.LEVELS_PLAYED), 0), 1) AS avg_level_played_sec,
    ROUND(AVG(s.LEVELS_PLAYED), 1) AS avg_attempts_per_game,
    ROUND(p.TOTAL_LEVEL_WINS * 1.0 / NULLIF(p.TOTAL_LEVEL_ATTEMPTS, 0) * 100, 1) AS win_rate_pct,
    ROUND(p.TOTAL_KEY_PRESSES * 1.0 / NULLIF(p.TOTAL_GAMES, 0), 0) AS avg_keys_per_game
FROM MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS s
CROSS JOIN MARIO_DB.PUBLIC.MARIO_PLAYER_STATS p
WHERE s.DURATION_SECONDS IS NOT NULL
GROUP BY p.TOTAL_LEVEL_WINS, p.TOTAL_LEVEL_ATTEMPTS, p.TOTAL_KEY_PRESSES, p.TOTAL_GAMES;

-- -----------------------------------------------------------------------------
-- 5. MARIO_GAME_LOGS - Service log messages
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_GAME_LOGS AS
SELECT
    timestamp,
    value::STRING AS log_message,
    record:severity_text::STRING AS severity
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name" = 'MARIO_SERVICE'
  AND record_type = 'LOG';

-- -----------------------------------------------------------------------------
-- 6. MARIO_GAME_METRICS - All raw metrics from the service
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_GAME_METRICS AS
SELECT
    timestamp,
    record:metric.name::STRING AS metric_name,
    CAST(value AS FLOAT) AS metric_value,
    scope:"name"::STRING AS scope,
    record_attributes
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name" = 'MARIO_SERVICE'
  AND record_type = 'METRIC';

-- -----------------------------------------------------------------------------
-- 7. MARIO_GAME_TRACES - Raw span/trace data
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW MARIO_DB.PUBLIC.MARIO_GAME_TRACES AS
SELECT
    timestamp,
    start_timestamp,
    record:name::STRING AS span_name,
    record_attributes,
    trace:"trace_id"::STRING AS trace_id,
    trace:"span_id"::STRING AS span_id
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name" = 'MARIO_SERVICE'
  AND record_type = 'SPAN';
