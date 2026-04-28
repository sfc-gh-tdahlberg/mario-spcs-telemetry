-- =====================================================================================
-- SUPER MARIO SPCS TELEMETRY — PROJECT SHOWCASE & INVENTORY
-- =====================================================================================
-- This worksheet provides a complete guided tour of every Snowflake object created
-- for the Mario SPCS Telemetry demo. Run sections top-to-bottom in Snowsight or
-- Snowflake Workspaces to explore the full architecture.
--
-- Architecture:
--   Browser (Mario Game) → nginx → Python OTel Sidecar → gRPC → Event Table
--   Event Table → Views → Dynamic Interactive Tables → React App / Streamlit
--
-- Project GitHub: https://github.com/sfc-gh-tdahlberg/mario-spcs-telemetry
-- =====================================================================================

USE ROLE ACCOUNTADMIN;

-- =====================================================================================
-- 1. DATABASES
-- =====================================================================================
-- MARIO_DB     — Original database: SPCS service, image repo, views, Streamlit app
-- DIS_MARIO    — Real-time demo database: Interactive tables, interactive warehouse
-- EVENT_DB     — Account-level event table (telemetry sink for all SPCS services)

SHOW DATABASES LIKE 'MARIO%';
SHOW DATABASES LIKE 'EVENT%';


-- =====================================================================================
-- 2. WAREHOUSES
-- =====================================================================================
-- DIS_MARIO_WH  — Standard XS warehouse for dynamic table refresh operations
--                 Auto-suspend: 60s | Used by: interactive table TARGET_LAG refresh
-- DIS_MARIO_IWH — Interactive warehouse for sub-second queries on interactive tables
--                 Auto-suspend: 24h (minimum for interactive) | Used by: React app, Streamlit

SHOW WAREHOUSES LIKE '%MARIO%';

-- Compare warehouse types side by side
SELECT 'DIS_MARIO_WH'  AS warehouse, 'STANDARD'    AS type, 'XSMALL' AS size, '60s'  AS auto_suspend, 'Dynamic table refresh'         AS purpose
UNION ALL
SELECT 'DIS_MARIO_IWH', 'INTERACTIVE', 'XSMALL', '24h', 'Sub-second queries on interactive tables';


-- =====================================================================================
-- 3. COMPUTE POOLS (SPCS)
-- =====================================================================================
-- MARIO_POOL              — CPU_X64_XS, runs the Mario game container
-- SYSTEM_COMPUTE_POOL_CPU — System pool, runs Streamlit in Snowsight apps

SHOW COMPUTE POOLS LIKE 'MARIO%';

SELECT SYSTEM$GET_SERVICE_STATUS('MARIO_DB.PUBLIC.MARIO_SERVICE') AS service_status;


-- =====================================================================================
-- 4. SPCS CONTAINER SERVICE
-- =====================================================================================
-- MARIO_SERVICE — Single-container service running:
--   • nginx (port 8080) — reverse proxy, serves game assets + routes /telemetry
--   • Tomcat (port 8888) — Java Super Mario Bros game server
--   • Python sidecar (port 9090) — receives telemetry, forwards via OTel gRPC
--
-- Public endpoint: https://ei53mb-sfseeurope-eu-demo200.snowflakecomputing.app

SHOW SERVICES IN SCHEMA MARIO_DB.PUBLIC;
SHOW ENDPOINTS IN SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE;


-- =====================================================================================
-- 5. IMAGE REPOSITORY
-- =====================================================================================
-- MARIO_REPO — Stores the Docker image for the game container
-- Image: sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest

SHOW IMAGE REPOSITORIES IN SCHEMA MARIO_DB.PUBLIC;
SHOW IMAGES IN IMAGE REPOSITORY MARIO_DB.PUBLIC.MARIO_REPO;


-- =====================================================================================
-- 6. EVENT TABLE (Telemetry Sink)
-- =====================================================================================
-- All OpenTelemetry data lands here: spans, metrics, logs
-- This is the single source of truth for the entire telemetry pipeline

SHOW EVENT TABLES IN SCHEMA EVENT_DB.EVENT_SH;

-- Record type distribution
SELECT record_type, COUNT(*) AS total_records
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
GROUP BY 1
ORDER BY 2 DESC;

-- Available metrics breakdown
SELECT
    record:metric.name::STRING AS metric_name,
    COUNT(*)                   AS data_points,
    MIN(timestamp)             AS first_seen,
    MAX(timestamp)             AS last_seen
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'METRIC'
GROUP BY 1
ORDER BY 2 DESC;


-- =====================================================================================
-- 7. MARIO_DB — VIEWS (Original Analytics Layer)
-- =====================================================================================
-- These views query the raw event table directly for the original Streamlit dashboard

SHOW VIEWS IN SCHEMA MARIO_DB.PUBLIC;

-- MARIO_GAME_METRICS — All METRIC records (CPU, memory, network, game counters)
SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_METRICS LIMIT 5;

-- MARIO_GAME_LOGS — Sidecar log output (HTTP requests, event processing)
SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_LOGS LIMIT 5;

-- MARIO_GAME_TRACES — SPAN records (individual game events with attributes)
SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_TRACES LIMIT 5;

-- MARIO_GAME_SESSIONS — Player session aggregations
SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS;

-- MARIO_PLAYER_STATS — Per-session stats (deaths, coins, levels, duration)
SELECT * FROM MARIO_DB.PUBLIC.MARIO_PLAYER_STATS;

-- MARIO_TOP_SCORES — Leaderboard: coins collected per session
SELECT * FROM MARIO_DB.PUBLIC.MARIO_TOP_SCORES;

-- MARIO_AVG_STATS — Average metrics across all sessions
SELECT * FROM MARIO_DB.PUBLIC.MARIO_AVG_STATS;


-- =====================================================================================
-- 8. DIS_MARIO — VIEWS (Source Layer for Interactive Tables)
-- =====================================================================================
-- These views parse the event table and feed the dynamic interactive tables

SHOW VIEWS IN SCHEMA DIS_MARIO.PUBLIC;

-- V_GAME_EVENTS — All game SPAN events parsed into columns
SELECT * FROM DIS_MARIO.PUBLIC.V_GAME_EVENTS LIMIT 10;

-- V_EVENT_TIMELINE — Events bucketed by minute for time-series charts
SELECT * FROM DIS_MARIO.PUBLIC.V_EVENT_TIMELINE ORDER BY MINUTE DESC LIMIT 10;

-- V_KEY_PRESSES — Keyboard input aggregation
SELECT * FROM DIS_MARIO.PUBLIC.V_KEY_PRESSES;

-- V_DEATHS_BY_LEVEL — Death count per game level
SELECT * FROM DIS_MARIO.PUBLIC.V_DEATHS_BY_LEVEL;

-- V_POWERUPS — Powerup spawns by type and level
SELECT * FROM DIS_MARIO.PUBLIC.V_POWERUPS;

-- V_PLAYER_STATS — Session-level player statistics
SELECT * FROM DIS_MARIO.PUBLIC.V_PLAYER_STATS;


-- =====================================================================================
-- 9. DIS_MARIO — DYNAMIC INTERACTIVE TABLES (Real-Time Layer)
-- =====================================================================================
-- These are the heart of the DIS_MARIO demo:
--   • DYNAMIC — auto-refresh from source views every 1 minute (TARGET_LAG)
--   • INTERACTIVE — sub-second query performance via DIS_MARIO_IWH
--   • CLUSTERED — optimized for the most common WHERE/ORDER BY patterns
--
-- Refresh: DIS_MARIO_WH (standard) pushes data every ~1 minute
-- Queries: DIS_MARIO_IWH (interactive) serves reads in <100ms

SHOW TABLES IN SCHEMA DIS_MARIO.PUBLIC;

-- Verify all tables are interactive
SELECT "name", "rows", "bytes", "cluster_by", "is_dynamic", "is_interactive", "created_on"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));

-- GAME_EVENTS_LIVE — All parsed game events (clustered by EVENT_TYPE, TIMESTAMP)
SELECT COUNT(*) AS total_rows FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE;
SELECT * FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE ORDER BY TIMESTAMP DESC LIMIT 10;

-- EVENT_TIMELINE_LIVE — Per-minute event counts (clustered by EVENT_TYPE, MINUTE)
SELECT * FROM DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE ORDER BY MINUTE DESC LIMIT 10;

-- KEY_PRESSES_LIVE — Key press totals (clustered by KEY_NAME)
SELECT * FROM DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE ORDER BY PRESSES DESC;

-- DEATHS_BY_LEVEL_LIVE — Deaths per level (clustered by LEVEL)
SELECT * FROM DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE ORDER BY DEATHS DESC;

-- POWERUPS_LIVE — Powerup counts by type (clustered by POWERUP_TYPE)
SELECT * FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE ORDER BY COUNT DESC;

-- PLAYER_SESSIONS_LIVE — Active sessions (clustered by SESSION_START)
SELECT * FROM DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE;


-- =====================================================================================
-- 10. INTERACTIVE WAREHOUSE ↔ TABLE ASSOCIATION
-- =====================================================================================
-- Interactive tables must be explicitly associated with an interactive warehouse.
-- Only DIS_MARIO_IWH can query these tables; standard warehouses cannot.

SELECT 'DIS_MARIO_IWH' AS interactive_warehouse;
SHOW TABLES IN SCHEMA DIS_MARIO.PUBLIC;
SELECT "name" AS table_name, "is_interactive" AS interactive
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "is_interactive" = 'Y';


-- =====================================================================================
-- 11. STREAMLIT DASHBOARDS
-- =====================================================================================
-- Two Streamlit in Snowsight (SiS) apps, both using container runtime

SHOW STREAMLITS LIKE '%MARIO%' IN ACCOUNT;

-- MARIO_TELEMETRY_DASHBOARD (MARIO_DB)
--   Original 5-tab dashboard: Event Timeline, Deaths & Levels, Controls & Powerups,
--   Sessions, Platform Metrics
--   URL: https://app.snowflake.com/SFSEEUROPE/eu_demo200/#/streamlit-apps/MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD

-- DIS_MARIO_TELEMETRY_DASHBOARD (DIS_MARIO)
--   Updated dashboard querying interactive tables with 10s cache TTL
--   URL: https://app.snowflake.com/SFSEEUROPE/eu_demo200/#/streamlit-apps/DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD


-- =====================================================================================
-- 12. CONTAINER PLATFORM METRICS (SPCS Monitoring)
-- =====================================================================================
-- These queries power the "SPCS Metrics" tab in both dashboards.
-- All data comes from the event table's METRIC record type.

-- CPU Usage (last 30 minutes)
SELECT
    TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
    ROUND(AVG(value::FLOAT) * 100, 2)  AS avg_cpu_pct,
    ROUND(MAX(value::FLOAT) * 100, 2)  AS max_cpu_pct
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'METRIC'
  AND record:metric.name::STRING = 'container.cpu.usage'
  AND timestamp >= DATEADD('MINUTE', -30, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;

-- Memory Usage (last 30 minutes)
SELECT
    TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
    ROUND(AVG(value::FLOAT) / 1048576, 1) AS avg_memory_mb,
    ROUND(MAX(value::FLOAT) / 1048576, 1) AS max_memory_mb
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'METRIC'
  AND record:metric.name::STRING = 'container.memory.usage'
  AND timestamp >= DATEADD('MINUTE', -30, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;

-- Network Ingress (last 30 minutes)
SELECT
    TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
    MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.connections.active'
             THEN value::FLOAT END) AS active_connections,
    MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.cps'
             THEN value::FLOAT END) AS connections_per_sec
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'METRIC'
  AND record:metric.name::STRING IN ('network.ingress.connections.active', 'network.ingress.cps')
  AND timestamp >= DATEADD('MINUTE', -30, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;

-- OTel Sidecar Throughput (last 30 minutes)
SELECT
    TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
    MAX(CASE WHEN record:metric.name::STRING = 'otel.sdk.span.started'
             THEN value::FLOAT END) AS spans_started,
    MAX(CASE WHEN record:metric.name::STRING = 'otel.sdk.span.live'
             THEN value::FLOAT END) AS spans_live
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'METRIC'
  AND record:metric.name::STRING IN ('otel.sdk.span.started', 'otel.sdk.span.live')
  AND timestamp >= DATEADD('MINUTE', -30, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;

-- Sidecar Log Health (last 6 hours)
SELECT
    TIME_SLICE(timestamp, 5, 'MINUTE') AS period,
    COUNT(*)                                                        AS log_count,
    SUM(CASE WHEN value::STRING ILIKE '%ERROR%' THEN 1 ELSE 0 END) AS error_count,
    SUM(CASE WHEN value::STRING ILIKE '%WARN%'  THEN 1 ELSE 0 END) AS warn_count
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'LOG'
  AND timestamp >= DATEADD('HOUR', -6, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1;


-- =====================================================================================
-- 13. END-TO-END DATA FLOW VERIFICATION
-- =====================================================================================
-- Trace a single event from the raw event table through to the interactive table

-- Step 1: Latest raw event in the event table
SELECT timestamp, record_type, record:name::STRING AS event_name, record_attributes
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
ORDER BY timestamp DESC
LIMIT 1;

-- Step 2: Same event visible through the DIS_MARIO view
SELECT * FROM DIS_MARIO.PUBLIC.V_GAME_EVENTS ORDER BY TIMESTAMP DESC LIMIT 1;

-- Step 3: Same event materialized in the interactive table
SELECT * FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE ORDER BY TIMESTAMP DESC LIMIT 1;


-- =====================================================================================
-- 14. PROJECT OBJECT INVENTORY (Summary)
-- =====================================================================================

SELECT *
FROM (
    SELECT 1 AS seq, 'DATABASE'             AS object_type, 'MARIO_DB'                          AS name, 'Original SPCS + views + Streamlit'              AS description
    UNION ALL SELECT 2, 'DATABASE',             'DIS_MARIO',                          'Interactive tables + real-time dashboards'
    UNION ALL SELECT 3, 'DATABASE',             'EVENT_DB',                            'Account event table (telemetry sink)'
    UNION ALL SELECT 4, 'WAREHOUSE (Standard)', 'DIS_MARIO_WH',                       'XS, 60s suspend — dynamic table refresh'
    UNION ALL SELECT 5, 'WAREHOUSE (Interactive)', 'DIS_MARIO_IWH',                   'XS, 24h suspend — sub-second interactive queries'
    UNION ALL SELECT 6, 'COMPUTE POOL',         'MARIO_POOL',                          'CPU_X64_XS — runs Mario game container'
    UNION ALL SELECT 7, 'SPCS SERVICE',         'MARIO_DB.PUBLIC.MARIO_SERVICE',       'nginx + Tomcat + Python OTel sidecar'
    UNION ALL SELECT 8, 'SERVICE ENDPOINT',     'ei53mb-sfseeurope-eu-demo200.snowflakecomputing.app', 'Public game URL'
    UNION ALL SELECT 9, 'IMAGE REPOSITORY',     'MARIO_DB.PUBLIC.MARIO_REPO',          'supermario:latest Docker image'
    UNION ALL SELECT 10, 'EVENT TABLE',         'EVENT_DB.EVENT_SH.MY_EVENTS',         '~58M rows — all SPCS telemetry'
    UNION ALL SELECT 11, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_GAME_METRICS',  'All METRIC records (CPU, memory, game counters)'
    UNION ALL SELECT 12, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_GAME_LOGS',     'Sidecar log output'
    UNION ALL SELECT 13, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_GAME_TRACES',   'SPAN records (game events)'
    UNION ALL SELECT 14, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS', 'Player session aggregations'
    UNION ALL SELECT 15, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_PLAYER_STATS',  'Per-session stats'
    UNION ALL SELECT 16, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_TOP_SCORES',    'Leaderboard by coins'
    UNION ALL SELECT 17, 'VIEW',                'MARIO_DB.PUBLIC.MARIO_AVG_STATS',     'Cross-session averages'
    UNION ALL SELECT 18, 'VIEW',                'DIS_MARIO.PUBLIC.V_GAME_EVENTS',      'Parsed game events from event table'
    UNION ALL SELECT 19, 'VIEW',                'DIS_MARIO.PUBLIC.V_EVENT_TIMELINE',   'Per-minute event bucketing'
    UNION ALL SELECT 20, 'VIEW',                'DIS_MARIO.PUBLIC.V_KEY_PRESSES',      'Key press aggregation'
    UNION ALL SELECT 21, 'VIEW',                'DIS_MARIO.PUBLIC.V_DEATHS_BY_LEVEL',  'Death count per level'
    UNION ALL SELECT 22, 'VIEW',                'DIS_MARIO.PUBLIC.V_POWERUPS',         'Powerups by type and level'
    UNION ALL SELECT 23, 'VIEW',                'DIS_MARIO.PUBLIC.V_PLAYER_STATS',     'Session-level player stats'
    UNION ALL SELECT 24, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE',   'Dynamic, 1-min lag, clustered (EVENT_TYPE, TIMESTAMP)'
    UNION ALL SELECT 25, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE','Dynamic, 1-min lag, clustered (EVENT_TYPE, MINUTE)'
    UNION ALL SELECT 26, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE',   'Dynamic, 1-min lag, clustered (KEY_NAME)'
    UNION ALL SELECT 27, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE','Dynamic, 1-min lag, clustered (LEVEL)'
    UNION ALL SELECT 28, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.POWERUPS_LIVE',      'Dynamic, 1-min lag, clustered (POWERUP_TYPE)'
    UNION ALL SELECT 29, 'INTERACTIVE TABLE',   'DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE','Dynamic, 1-min lag, clustered (SESSION_START)'
    UNION ALL SELECT 30, 'STREAMLIT APP',       'MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD',     'Original 5-tab dashboard (container runtime)'
    UNION ALL SELECT 31, 'STREAMLIT APP',       'DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD', 'DIS_MARIO dashboard with interactive tables'
    UNION ALL SELECT 32, 'REACT APP',           'mario-react-app/ (local / SPCS)',     'Next.js 16 — 4 tabs, Mario theme, 5s auto-refresh'
) inventory
ORDER BY seq;


-- =====================================================================================
-- 15. QUICK HEALTH CHECK
-- =====================================================================================
-- Run this block to verify the entire pipeline is operational

SELECT
    (SELECT COUNT(*) FROM event_db.event_sh.my_events
     WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE')   AS total_event_table_rows,
    (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE)                    AS interactive_table_rows,
    (SELECT MAX(timestamp) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE)              AS latest_event,
    DATEDIFF('MINUTE', (SELECT MAX(timestamp) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE), CURRENT_TIMESTAMP()) AS minutes_since_last_event,
    (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE)                AS active_sessions,
    (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE)                AS levels_with_deaths,
    (SELECT SUM(PRESSES) FROM DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE)                AS total_key_presses;
