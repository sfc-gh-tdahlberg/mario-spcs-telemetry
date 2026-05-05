-- =============================================================================
-- 01_infrastructure.sql
-- Super Mario SPCS Telemetry - Infrastructure Setup
-- Creates database, warehouse, compute pool, image repository, and event table
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- -----------------------------------------------------------------------------
-- 1. Database & Schema
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS MARIO_DB;
CREATE SCHEMA IF NOT EXISTS MARIO_DB.PUBLIC;
USE DATABASE MARIO_DB;
USE SCHEMA PUBLIC;

-- -----------------------------------------------------------------------------
-- 2. Warehouse (for Streamlit queries and analytics)
-- -----------------------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE;

-- -----------------------------------------------------------------------------
-- 3. Event Database & Table (for OpenTelemetry telemetry ingestion)
-- -----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS EVENT_DB;
CREATE SCHEMA IF NOT EXISTS EVENT_DB.EVENT_SH;

CREATE EVENT TABLE IF NOT EXISTS EVENT_DB.EVENT_SH.MY_EVENTS;

ALTER ACCOUNT SET EVENT_TABLE = EVENT_DB.EVENT_SH.MY_EVENTS;

-- -----------------------------------------------------------------------------
-- 4. Image Repository (for Docker images)
-- -----------------------------------------------------------------------------
CREATE IMAGE REPOSITORY IF NOT EXISTS MARIO_DB.PUBLIC.MARIO_REPO;

-- Get the repository URL for Docker push:
SHOW IMAGE REPOSITORIES IN SCHEMA MARIO_DB.PUBLIC;
-- Note the repository_url column, e.g.:
--   <YOUR_ACCOUNT>.registry.snowflakecomputing.com/mario_db/public/mario_repo

-- -----------------------------------------------------------------------------
-- 5. Compute Pool (for running the SPCS service)
-- -----------------------------------------------------------------------------
CREATE COMPUTE POOL IF NOT EXISTS MARIO_POOL
    MIN_NODES = 1
    MAX_NODES = 1
    INSTANCE_FAMILY = CPU_X64_XS
    AUTO_RESUME = TRUE
    AUTO_SUSPEND_SECS = 3600;

DESCRIBE COMPUTE POOL MARIO_POOL;

-- -----------------------------------------------------------------------------
-- 6. PyPI External Access Integration (for Streamlit in Snowsight)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE NETWORK RULE PYPI_NETWORK_RULE
    MODE = EGRESS
    TYPE = HOST_PORT
    VALUE_LIST = ('pypi.org', 'files.pythonhosted.org');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION PYPI_ACCESS_INTEGRATION
    ALLOWED_NETWORK_RULES = (PYPI_NETWORK_RULE)
    ENABLED = TRUE;
