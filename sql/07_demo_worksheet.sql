-- =============================================================================
-- 07_demo_worksheet.sql
-- Super Mario SPCS Telemetry — Interactive Demo Queries
-- Run these in a Snowsight worksheet to explore all project tables and views
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- =============================================================================
-- 1. REAL-TIME INTERACTIVE TABLES (DIS_MARIO — sub-second latency)
-- =============================================================================

-- All game events (most recent first)
SELECT * FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
ORDER BY TIMESTAMP DESC
LIMIT 25;

-- Event counts per minute (live timeline)
SELECT * FROM DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE
ORDER BY MINUTE DESC
LIMIT 20;

-- Deaths by level — which level is hardest?
SELECT * FROM DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE
ORDER BY DEATH_COUNT DESC;

-- Key press aggregates — what buttons do players mash?
SELECT * FROM DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE
ORDER BY PRESS_COUNT DESC;

-- Powerup spawns
SELECT * FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE
ORDER BY SPAWN_COUNT DESC;

-- Player sessions — who played and for how long?
SELECT * FROM DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE
ORDER BY SESSION_START DESC;


-- =============================================================================
-- 2. ANALYTICS VIEWS (MARIO_DB — raw event table queries)
-- =============================================================================

-- Leaderboard — top scores in last 24 hours
SELECT * FROM MARIO_DB.PUBLIC.MARIO_TOP_SCORES
LIMIT 20;

-- Player stats — aggregated totals per player
SELECT * FROM MARIO_DB.PUBLIC.MARIO_PLAYER_STATS
ORDER BY TOTAL_COINS DESC;

-- Game sessions breakdown
SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS
ORDER BY SESSION_START DESC
LIMIT 15;

-- Average KPI stats
SELECT * FROM MARIO_DB.PUBLIC.MARIO_AVG_STATS;


-- =============================================================================
-- 3. RAW EVENT TABLE (where all telemetry lands)
-- =============================================================================

-- Recent game spans (last 5 minutes)
SELECT
    TIMESTAMP,
    RECORD:name::STRING AS event_name,
    RECORD_ATTRIBUTES:player_name::STRING AS player_name,
    RECORD_ATTRIBUTES:level::STRING AS level,
    RECORD_ATTRIBUTES:coins::NUMBER AS coins,
    RECORD_ATTRIBUTES:lives::NUMBER AS lives
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'SPAN'
  AND RECORD:name::STRING LIKE 'mario.%'
  AND TIMESTAMP > DATEADD(MINUTE, -5, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC
LIMIT 25;

-- Event type distribution (last hour)
SELECT
    RECORD:name::STRING AS event_type,
    COUNT(*) AS event_count
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'SPAN'
  AND RECORD:name::STRING LIKE 'mario.%'
  AND TIMESTAMP > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 2 DESC;

-- Unique players (last hour)
SELECT DISTINCT
    RECORD_ATTRIBUTES:player_name::STRING AS player_name
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'SPAN'
  AND RECORD:name::STRING LIKE 'mario.%'
  AND TIMESTAMP > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
  AND player_name IS NOT NULL AND player_name != 'unknown';


-- =============================================================================
-- 4. PLATFORM METRICS (SPCS container monitoring)
-- =============================================================================

-- CPU usage (last 30 minutes, 1-min buckets)
SELECT
    TIME_SLICE(TIMESTAMP, 1, 'MINUTE') AS minute,
    ROUND(AVG(VALUE::FLOAT) * 100, 2) AS avg_cpu_pct,
    ROUND(MAX(VALUE::FLOAT) * 100, 2) AS max_cpu_pct
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'METRIC'
  AND RECORD:metric:name::STRING = 'container.cpu.usage'
  AND TIMESTAMP > DATEADD(MINUTE, -30, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1 DESC;

-- Memory usage (last 30 minutes)
SELECT
    TIME_SLICE(TIMESTAMP, 1, 'MINUTE') AS minute,
    ROUND(AVG(VALUE::FLOAT) / 1048576, 1) AS avg_memory_mb,
    ROUND(MAX(VALUE::FLOAT) / 1048576, 1) AS max_memory_mb
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'METRIC'
  AND RECORD:metric:name::STRING = 'container.memory.usage'
  AND TIMESTAMP > DATEADD(MINUTE, -30, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1 DESC;

-- Network ingress connections
SELECT
    TIME_SLICE(TIMESTAMP, 1, 'MINUTE') AS minute,
    MAX(VALUE::NUMBER) AS active_connections
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'METRIC'
  AND RECORD:metric:name::STRING = 'network.ingress.connections.active'
  AND TIMESTAMP > DATEADD(MINUTE, -30, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1 DESC;


-- =============================================================================
-- 5. SERVICE LOGS (container stdout/stderr)
-- =============================================================================

-- Recent service log messages
SELECT
    TIMESTAMP,
    RECORD:severity_text::STRING AS severity,
    VALUE::STRING AS message
FROM EVENT_DB.EVENT_SH.MY_EVENTS
WHERE RECORD_TYPE = 'LOG'
  AND TIMESTAMP > DATEADD(MINUTE, -10, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC
LIMIT 20;


-- =============================================================================
-- 6. INFRASTRUCTURE STATUS
-- =============================================================================

-- Compute pool
SHOW COMPUTE POOLS LIKE 'MARIO%';

-- Service status
SHOW SERVICES IN SCHEMA MARIO_DB.PUBLIC;

-- Service endpoints
SHOW ENDPOINTS IN SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE;

-- Interactive tables health
SELECT SYSTEM$INTERACTIVE_TABLE_STATUS('DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE');

-- Image repository
SHOW IMAGES IN IMAGE REPOSITORY MARIO_DB.PUBLIC.MARIO_REPO;


-- =============================================================================
-- 7. CORTEX AI (Natural Language → SQL)
-- =============================================================================

-- Ask the Cortex Agent a question
SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b',
  'Based on the Mario telemetry data, which player has the most deaths?'
) AS cortex_response;

-- Semantic view metadata
DESCRIBE SEMANTIC VIEW DIS_MARIO.PUBLIC.MARIO_TELEMETRY;
