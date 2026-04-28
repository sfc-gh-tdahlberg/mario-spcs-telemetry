-- =============================================================================
-- DIS_MARIO Infrastructure Setup
-- Interactive Tables + Interactive Warehouse for real-time telemetry
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- 1. Database
CREATE DATABASE IF NOT EXISTS DIS_MARIO;
USE DATABASE DIS_MARIO;
USE SCHEMA PUBLIC;

-- 2. Standard warehouse (for interactive table refresh operations)
CREATE WAREHOUSE IF NOT EXISTS DIS_MARIO_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- 3. Interactive warehouse (for sub-second queries on interactive tables)
CREATE WAREHOUSE IF NOT EXISTS DIS_MARIO_IWH
  WAREHOUSE_TYPE = 'INTERACTIVE'
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 86400   -- 24h minimum for interactive warehouses
  AUTO_RESUME = TRUE;

-- =============================================================================
-- Views over the Event Table (source layer)
-- =============================================================================

CREATE OR REPLACE VIEW V_GAME_EVENTS AS
SELECT
    timestamp,
    record:name::STRING AS event_type,
    record_attributes:player_name::STRING AS player_name,
    record_attributes:level::STRING AS level,
    record_attributes:coins::STRING AS coins,
    record_attributes:lives::STRING AS lives,
    record_attributes:key::STRING AS key_name,
    record_attributes:type::STRING AS powerup_type,
    record_attributes:session_duration::STRING AS duration,
    record_attributes:session_id::STRING AS session_id
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING LIKE 'mario.%';

CREATE OR REPLACE VIEW V_EVENT_TIMELINE AS
SELECT
    TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
    record:name::STRING AS event_type,
    COUNT(*) AS event_count
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING LIKE 'mario.%'
  AND record:name::STRING NOT IN ('mario.key_press')
GROUP BY 1, 2;

CREATE OR REPLACE VIEW V_KEY_PRESSES AS
SELECT
    record_attributes:player_name::STRING AS player_name,
    record_attributes:key::STRING AS key_name,
    COUNT(*) AS presses
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING = 'mario.key_press'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW V_DEATHS_BY_LEVEL AS
SELECT
    record_attributes:player_name::STRING AS player_name,
    record_attributes:level::STRING AS level,
    COUNT(*) AS deaths
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING = 'mario.death'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW V_POWERUPS AS
SELECT
    record_attributes:player_name::STRING AS player_name,
    record_attributes:type::STRING AS powerup_type,
    record_attributes:level::STRING AS level,
    COUNT(*) AS count
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING = 'mario.powerup_spawn'
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW V_PLAYER_STATS AS
SELECT
    record_attributes:player_name::STRING AS player_name,
    record_attributes:session_id::STRING AS session_id,
    MIN(timestamp) AS session_start,
    MAX(timestamp) AS session_end,
    DATEDIFF('second', MIN(timestamp), MAX(timestamp)) AS duration_seconds,
    COUNT(CASE WHEN record:name::STRING = 'mario.death' THEN 1 END) AS deaths,
    COUNT(CASE WHEN record:name::STRING = 'mario.coin' THEN 1 END) AS coins,
    COUNT(CASE WHEN record:name::STRING = 'mario.level_win' THEN 1 END) AS levels_won,
    MAX(record_attributes:level::STRING) AS highest_level
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
  AND record:name::STRING LIKE 'mario.%'
  AND record_attributes:session_id IS NOT NULL
GROUP BY 1, 2;

-- =============================================================================
-- Interactive Tables (auto-refresh from views, 1-min lag)
-- =============================================================================

CREATE OR REPLACE INTERACTIVE TABLE GAME_EVENTS_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (PLAYER_NAME, EVENT_TYPE, TIMESTAMP)
AS
SELECT * FROM V_GAME_EVENTS;

CREATE OR REPLACE INTERACTIVE TABLE EVENT_TIMELINE_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (EVENT_TYPE, MINUTE)
AS
SELECT * FROM V_EVENT_TIMELINE;

CREATE OR REPLACE INTERACTIVE TABLE KEY_PRESSES_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (PLAYER_NAME, KEY_NAME)
AS
SELECT * FROM V_KEY_PRESSES;

CREATE OR REPLACE INTERACTIVE TABLE DEATHS_BY_LEVEL_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (PLAYER_NAME, LEVEL)
AS
SELECT * FROM V_DEATHS_BY_LEVEL;

CREATE OR REPLACE INTERACTIVE TABLE POWERUPS_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (PLAYER_NAME, POWERUP_TYPE)
AS
SELECT * FROM V_POWERUPS;

CREATE OR REPLACE INTERACTIVE TABLE PLAYER_SESSIONS_LIVE
  TARGET_LAG = '1 minutes'
  WAREHOUSE = DIS_MARIO_WH
  CLUSTER BY (PLAYER_NAME, SESSION_START)
AS
SELECT * FROM V_PLAYER_STATS;

-- =============================================================================
-- Associate interactive tables with the interactive warehouse
-- =============================================================================

ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE SET WAREHOUSE = DIS_MARIO_IWH;
ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE SET WAREHOUSE = DIS_MARIO_IWH;
ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE SET WAREHOUSE = DIS_MARIO_IWH;
ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE SET WAREHOUSE = DIS_MARIO_IWH;
ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.POWERUPS_LIVE SET WAREHOUSE = DIS_MARIO_IWH;
ALTER INTERACTIVE TABLE DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE SET WAREHOUSE = DIS_MARIO_IWH;

-- Verify
SHOW TABLES IN SCHEMA DIS_MARIO.PUBLIC;
