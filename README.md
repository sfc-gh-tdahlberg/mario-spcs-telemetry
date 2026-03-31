# Super Mario SPCS Telemetry - Complete Setup Guide

> Real-time game telemetry from a containerized Super Mario Bros running on Snowpark Container Services (SPCS), with an interactive Streamlit dashboard in Snowsight.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Step 1: Infrastructure Setup](#step-1-infrastructure-setup)
5. [Step 2: Build & Push Docker Image](#step-2-build--push-docker-image)
6. [Step 3: Deploy SPCS Service](#step-3-deploy-spcs-service)
7. [Step 4: Create Analytics Views](#step-4-create-analytics-views)
8. [Step 5: Deploy Streamlit Dashboard](#step-5-deploy-streamlit-dashboard)
9. [Step 6: Play & Verify](#step-6-play--verify)
10. [Telemetry Data Model](#telemetry-data-model)
11. [Dashboard Features](#dashboard-features)
12. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Browser (Player)
    |
    |  JavaScript (telemetry.js) hooks into game engine
    |  Captures: game_start, death, level_win, coin, key_press, etc.
    |
    v
SPCS Ingress (port 8080)
    |
    |  nginx reverse proxy
    |  - GET /telemetry?d=... -> Python sidecar (port 9090)
    |  - GET / (everything else) -> Tomcat game server (port 8888)
    |
    +---> Tomcat 9 (Super Mario HTML5 game)
    |
    +---> Python Telemetry Sidecar
              |
              |  OpenTelemetry SDK
              |  - Spans (game events)
              |  - Metrics (counters, histograms)
              |  - Logs (structured game logs)
              |
              v
         OTLP gRPC Exporter -> SPCS Event Table
                                (event_db.event_sh.my_events)
                                    |
                                    v
                              Analytics Views (MARIO_DB.PUBLIC)
                                    |
                                    v
                              Streamlit Dashboard (Snowsight)
```

### Key Design Decisions

- **Tracking pixel pattern**: Browser sends telemetry via `GET /telemetry?d=<json>` using an Image pixel. This avoids CORS issues and works even when SPCS blocks certain POST requests.
- **Exact nginx location match**: `location = /telemetry` prevents the route from catching requests to `/telemetry.js`.
- **Bundled jQuery**: External CDN URLs are blocked by SPCS egress rules, so `jquery.min.js` is bundled locally.
- **Platform metrics groups**: `system`, `network`, `storage` are enabled in the service spec to get container CPU, memory, disk, and network telemetry.

---

## Prerequisites

- Snowflake account with ACCOUNTADMIN role
- Docker Desktop (for building the container image)
- Snowflake CLI (`snow`) or `uvx --from snowflake-cli` for Streamlit deployment
- A configured Snowflake CLI connection (e.g., `eu_demo200`)

---

## Project Structure

```
mario-spcs/                       # Container application
  Dockerfile                      # Multi-stage build: game + telemetry
  nginx.conf                      # Reverse proxy routing
  telemetry_sidecar.py            # Python OpenTelemetry collector
  telemetry.js                    # Browser-side game event hooks
  jquery.min.js                   # Bundled jQuery (CDN blocked in SPCS)
  start.sh                        # Container entrypoint
  requirements.txt                # Python dependencies (OTel SDK)

mario-streamlit/                  # Streamlit dashboard
  streamlit_app.py                # Main dashboard application
  pyproject.toml                  # Python dependencies
  snowflake.yml                   # Snowflake CLI deployment config

sql/                              # SQL setup scripts (run in order)
  01_infrastructure.sql           # Database, warehouse, compute pool, event table
  02_service.sql                  # SPCS service creation
  03_analytics_views.sql          # 7 analytics views
  04_streamlit_dashboard.sql      # Streamlit app deployment
```

---

## Step 1: Infrastructure Setup

Run `sql/01_infrastructure.sql` in a Snowflake worksheet or SnowSQL:

```sql
-- Creates:
--   MARIO_DB database and PUBLIC schema
--   COMPUTE_WH warehouse (X-Small)
--   EVENT_DB.EVENT_SH.MY_EVENTS event table
--   MARIO_DB.PUBLIC.MARIO_REPO image repository
--   MARIO_POOL compute pool (CPU_X64_XS, 1 node)
--   PYPI_ACCESS_INTEGRATION for Streamlit pip installs
```

After running, note the **image repository URL** from:
```sql
SHOW IMAGE REPOSITORIES IN SCHEMA MARIO_DB.PUBLIC;
-- e.g.: sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo
```

---

## Step 2: Build & Push Docker Image

From the `mario-spcs/` directory:

```bash
# 1. Login to Snowflake registry
docker login <registry_url> -u <username>

# 2. Build for linux/amd64 (required by SPCS)
docker build --platform linux/amd64 -t supermario .

# 3. Tag for Snowflake
docker tag supermario <registry_url>/supermario:latest

# 4. Push
docker push <registry_url>/supermario:latest
```

### What the Dockerfile Does

1. **Stage 1** (`pengbai/docker-supermario:latest`): Copies the game files, injects `telemetry.js`, replaces CDN jQuery with local copy.
2. **Stage 2** (`tomcat:9.0-jdk11-openjdk`): Installs Python 3 + pip + nginx, copies telemetry sidecar, nginx config, and game files from stage 1.
3. **Entrypoint** (`start.sh`): Reconfigures Tomcat to port 8888, starts nginx (port 8080), starts telemetry sidecar (port 9090), starts Tomcat.

---

## Step 3: Deploy SPCS Service

Run `sql/02_service.sql`:

```sql
CREATE SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE
    IN COMPUTE POOL MARIO_POOL
    ...
```

### Service Specification Highlights

| Setting | Value | Notes |
|---------|-------|-------|
| CPU Limit | 1 core | |
| Memory Limit | 2 GiB | |
| CPU Request | 500m | |
| Memory Request | 512 MiB | |
| Public Endpoint | port 8080 | Exposed via SPCS ingress |
| Platform Monitor | system, network, storage | Enables 90+ metric types |

After creation, get the ingress URL:
```sql
SHOW ENDPOINTS IN SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE;
-- ingress_url: https://<hash>-<org>-<account>.snowflakecomputing.app
```

---

## Step 4: Create Analytics Views

Run `sql/03_analytics_views.sql` to create all 7 views:

| View | Purpose |
|------|---------|
| `MARIO_PLAYER_STATS` | Aggregated totals (games, deaths, coins, etc.) |
| `MARIO_TOP_SCORES` | Leaderboard ranked by coins desc, time asc |
| `MARIO_GAME_SESSIONS` | Per-session breakdown with deaths, levels, coins |
| `MARIO_AVG_STATS` | Computed averages (playtime, coins/round, win rate) |
| `MARIO_GAME_LOGS` | Service log messages |
| `MARIO_GAME_METRICS` | Raw metric data from all 90+ metric types |
| `MARIO_GAME_TRACES` | Raw span/trace data |

---

## Step 5: Deploy Streamlit Dashboard

### Option A: Snowflake CLI (Recommended)

From the `mario-streamlit/` directory:

```bash
uvx --from snowflake-cli snow streamlit deploy \
    --replace \
    --connection <connection_name> \
    --role ACCOUNTADMIN
```

### Option B: SQL

See `sql/04_streamlit_dashboard.sql` for manual stage upload and `CREATE STREAMLIT` command.

### Dashboard URL

After deployment:
```
https://app.snowflake.com/<org>/<account>/#/streamlit-apps/MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD
```

---

## Step 6: Play & Verify

1. Open the **game** at the SPCS ingress URL
2. Press **S** to start playing
3. Open the **Streamlit dashboard** in Snowsight
4. Verify telemetry flows by checking:

```sql
-- Count telemetry records
SELECT record_type, COUNT(*)
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
GROUP BY 1;

-- Check latest events
SELECT timestamp, record:name::STRING AS event
FROM event_db.event_sh.my_events
WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
  AND record_type = 'SPAN'
ORDER BY timestamp DESC
LIMIT 10;
```

---

## Telemetry Data Model

### Game Events (Spans)

| Event | Attributes | When |
|-------|-----------|------|
| `mario.game_start` | lives | Player presses S on title screen |
| `mario.level_start` | level, difficulty, type, lives, coins | Level begins loading |
| `mario.death` | level, lives, coins, large, fire | Mario dies |
| `mario.level_win` | level, lives, coins, time_left | Level flag reached |
| `mario.game_over` | level, coins, session_duration | All lives lost |
| `mario.game_win` | session_duration | Final level completed |
| `mario.coin` | total_coins | Coin collected |
| `mario.powerup_spawn` | type, level | Powerup block hit |
| `mario.key_press` | key | Player key press (throttled 500ms) |
| `mario.session_end` | session_duration | Browser tab closing |

### Platform Metrics (SPCS Native)

| Metric | Unit | Description |
|--------|------|-------------|
| `container.cpu.usage` | CPU cores | Container CPU utilization |
| `container.memory.usage` | bytes | Container memory usage |
| `storage.used` | bytes | Disk storage used |
| `storage.free` | bytes | Disk storage available |
| `system.network.io` | bytes | Network I/O (with direction: receive/transmit) |
| `network.ingress.connections.active` | count | Active ingress connections |
| `network.ingress.cps` | count/sec | Connections per second |

### Derived Metrics (Computed in Dashboard)

| Metric | Derivation |
|--------|-----------|
| Disk IOPS | `ABS(storage_delta) / elapsed_seconds / 4096` |
| I/O Throughput | `ABS(network_delta) / elapsed_seconds / 1MB` |
| Avg Latency | `elapsed_seconds * 1000 / sample_count` |

---

## Dashboard Features

### KPI Rows
- **Row 1 (Totals)**: Total Games, Deaths, Coins, Level Attempts, Level Wins, Powerups, Key Presses
- **Row 2 (Averages)**: Avg Playtime, Sec/Death, Coins/Round, Avg Level Time, Avg Attempts, Win Rate, Keys/Game

### Tabs
1. **Leaderboard**: Top scores table + game sessions table (latest first)
2. **Event Timeline**: Stacked area chart of game events over time
3. **Deaths & Levels**: Deaths by level bar chart + powerups table
4. **Controls & Powerups**: Key press distribution bar chart
5. **Platform Metrics** (with time range selector: 15m / 1h / 6h / 24h / 7d / all):
   - CPU Usage (avg + max %)
   - Memory Usage (avg + max MB)
   - Disk Storage (avg + max MB)
   - Estimated Disk IOPS (4K blocks)
   - I/O Throughput (MB/s) & Latency (ms)
   - Network Ingress (connections)
   - Network I/O (RX + TX, avg + max MB)

### Raw Event Log
- Expandable section showing latest 500 raw game events

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| `telemetry.js` not loading | Check nginx uses `location = /telemetry` (exact match), not `location /telemetry` (prefix) |
| No telemetry data | Check service logs: `SELECT SYSTEM$GET_SERVICE_LOGS(...)`. Verify OTLP exporter can reach event table. |
| Compute pool full | Check `SHOW COMPUTE POOLS` for capacity. Use `ALTER COMPUTE POOL ... MAX_NODES = 2` if needed. |
| CDN scripts failing | SPCS blocks external egress. Bundle JS dependencies in Docker image. |
| Streamlit deploy fails | Ensure `compute_pool` and `PYPI_ACCESS_INTEGRATION` exist. Use `runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`. |
| Platform metrics empty | Verify `platformMonitor.metricConfig.groups` includes `system`, `network`, `storage` in service spec. |
| CLI version too old | Use `uvx --from snowflake-cli snow ...` to run latest CLI without installing. |
