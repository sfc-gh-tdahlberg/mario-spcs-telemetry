-- =============================================================================
-- 02_service.sql
-- Super Mario SPCS Telemetry - Service Deployment
-- Builds and deploys the Mario game container with telemetry sidecar
-- =============================================================================

USE ROLE ACCOUNTADMIN;
USE DATABASE MARIO_DB;
USE SCHEMA PUBLIC;

-- =============================================================================
-- STEP 1: Build & Push Docker Image (run from local terminal, not in Snowflake)
-- =============================================================================
-- From the /mario-spcs/ directory containing the Dockerfile:
--
--   # Authenticate to Snowflake image registry
--   docker login sfseeurope-eu-demo200.registry.snowflakecomputing.com \
--       -u <username>
--
--   # Build the image
--   docker build --platform linux/amd64 -t supermario .
--
--   # Tag for Snowflake registry
--   docker tag supermario \
--       sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
--
--   # Push to Snowflake
--   docker push \
--       sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
-- =============================================================================

-- =============================================================================
-- STEP 2: Create the SPCS Service
-- =============================================================================
CREATE SERVICE IF NOT EXISTS MARIO_DB.PUBLIC.MARIO_SERVICE
    IN COMPUTE POOL MARIO_POOL
    MIN_INSTANCES = 1
    MAX_INSTANCES = 1
    AUTO_RESUME = TRUE
FROM SPECIFICATION $$
spec:
  containers:
  - name: supermario
    image: /mario_db/public/mario_repo/supermario:latest
    readinessProbe:
      port: 8080
      path: /
    resources:
      limits:
        memory: 2Gi
        cpu: "1"
      requests:
        memory: 512Mi
        cpu: 500m
  endpoints:
  - name: mario
    port: 8080
    public: true
  platformMonitor:
    metricConfig:
      groups:
      - system
      - network
      - storage
$$;

-- =============================================================================
-- STEP 3: Verify Service
-- =============================================================================
DESCRIBE SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE;
SHOW ENDPOINTS IN SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE;

-- Check service logs
SELECT SYSTEM$GET_SERVICE_LOGS('MARIO_DB.PUBLIC.MARIO_SERVICE', 0, 'supermario', 50);

-- =============================================================================
-- STEP 4: Grant Public Access (optional - for non-ACCOUNTADMIN users)
-- =============================================================================
-- GRANT USAGE ON SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE TO ROLE <role_name>;
