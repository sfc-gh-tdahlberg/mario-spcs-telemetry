-- =============================================================================
-- 04_streamlit_dashboard.sql
-- Super Mario SPCS Telemetry - Streamlit Dashboard Deployment
-- Deploys the telemetry dashboard as a Streamlit in Snowsight (SIS) app
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARIO_DB;
USE SCHEMA PUBLIC;

-- =============================================================================
-- Option A: Deploy via Snowflake CLI (recommended)
-- =============================================================================
-- From the /mario-streamlit/ directory:
--
--   uvx --from snowflake-cli snow streamlit deploy \
--       --replace \
--       --connection <connection_name> \
--       --role ACCOUNTADMIN
--
-- This reads snowflake.yml and uploads:
--   - streamlit_app.py
--   - pyproject.toml

-- =============================================================================
-- Option B: Deploy via SQL (manual)
-- =============================================================================

-- 1. Create a stage to hold the Streamlit files
CREATE STAGE IF NOT EXISTS MARIO_DB.PUBLIC.STREAMLIT_STAGE
    DIRECTORY = (ENABLE = TRUE);

-- 2. Upload files to stage (run from SnowSQL or CLI):
--    PUT file:///tmp/mario-streamlit/streamlit_app.py @MARIO_DB.PUBLIC.STREAMLIT_STAGE/mario_telemetry AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--    PUT file:///tmp/mario-streamlit/pyproject.toml @MARIO_DB.PUBLIC.STREAMLIT_STAGE/mario_telemetry AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- 3. Create the Streamlit app
CREATE OR REPLACE STREAMLIT MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD
    ROOT_LOCATION = '@MARIO_DB.PUBLIC.STREAMLIT_STAGE/mario_telemetry'
    MAIN_FILE = 'streamlit_app.py'
    QUERY_WAREHOUSE = COMPUTE_WH
    RUNTIME_NAME = 'SYSTEM$ST_CONTAINER_RUNTIME_PY3_11'
    COMPUTE_POOL = SYSTEM_COMPUTE_POOL_CPU
    EXTERNAL_ACCESS_INTEGRATIONS = (PYPI_ACCESS_INTEGRATION);

-- =============================================================================
-- Verify
-- =============================================================================
SHOW STREAMLITS IN MARIO_DB.PUBLIC;
-- Access URL: https://app.snowflake.com/<org>/<account>/#/streamlit-apps/MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD
