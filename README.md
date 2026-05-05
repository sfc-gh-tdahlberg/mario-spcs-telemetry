# 🍄 Super Mario SPCS Telemetry

> Real-time game telemetry from a containerized Super Mario Bros running on Snowpark Container Services (SPCS), with interactive dashboards, a React analytics app, Cortex AI intelligence, and a live data pipeline powered by Snowflake Interactive Tables.

---

## Architecture

```
Browser (Player — authenticated via SPCS ingress)
    │
    │  telemetry.js — hooks game engine, sends player_name + events
    │
    ▼
SPCS Ingress (https://<INGRESS_HASH>-<YOUR_ACCOUNT>.snowflakecomputing.app)
    │  Injects: Sf-Context-Current-User header
    │
    ▼
nginx (port 8080)
    ├── GET /telemetry?d=...  ──► Python Sidecar (port 9090)
    ├── GET /whoami           ──► Python Sidecar (returns player name)
    └── GET /                 ──► Tomcat (Super Mario HTML5 game, port 8888)
                                        │
                              Python Sidecar
                                        │  OpenTelemetry OTLP gRPC
                                        ▼
                              SPCS Event Table (event_db.event_sh.my_events)
                                        │
                              Dynamic Interactive Tables (DIS_MARIO.PUBLIC.*)
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
             Streamlit SiS        React App           Cortex Agent
          (MARIO_TELEMETRY_    (Next.js 16, JWT)   (MARIO_INTELLIGENCE)
            DASHBOARD)                                     │
                                                    Semantic View
                                              (DIS_MARIO.PUBLIC.MARIO_TELEMETRY)
```

---

## Project Structure

```
mario-spcs/                    # Container application
  Dockerfile                   # Multi-stage: Tomcat + nginx + Python sidecar
  nginx.conf                   # Reverse proxy — exact location matches, header forwarding
  telemetry_sidecar.py         # Python OTel collector (GET pixel, /whoami, player_name)
  telemetry.js                 # Browser game hooks — sends player_name in every event
  jquery.min.js                # Bundled jQuery (SPCS blocks external CDN)
  start.sh                     # nginx + sidecar + Tomcat

mario-streamlit/               # Streamlit in Snowsight dashboard
  streamlit_app.py             # Near-realtime dashboard (10s TTL)
  snowflake.yml                # Deploys to DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD

mario-react-app/               # Next.js analytics dashboard
  src/                         # JWT auth locally, OAuth token in SPCS
  public/branding/             # Snowflake logo, Cortex Code badge, polar bear SVGs

semantic_view_*/               # Cortex Analyst semantic view YAML
  creation/mario_telemetry_semantic_model.yaml

sql/
  01_infrastructure.sql        # MARIO_DB, compute pool, event table, image repo
  02_service.sql               # SPCS service spec
  03_analytics_views.sql       # MARIO_TOP_SCORES (last 24h), MARIO_PLAYER_STATS, etc.
  04_streamlit_dashboard.sql   # Legacy Streamlit deployment
  05_dis_mario_infrastructure.sql  # DIS_MARIO interactive tables, IWH, warehouses
  06_project_showcase.sql      # Demo/showcase queries
```

---

## Snowflake Objects

### Databases
| Database | Purpose |
|----------|---------|
| `MARIO_DB` | Original event views, MARIO_TELEMETRY_DASHBOARD Streamlit |
| `DIS_MARIO` | Interactive tables, React app, Semantic View, Cortex Agent |
| `EVENT_DB` | Raw SPCS event table (`event_db.event_sh.my_events`) |

### Compute
| Object | Type | Details |
|--------|------|---------|
| `MARIO_POOL` | Compute Pool | CPU_X64_XS, 1 node, auto-resume |
| `DIS_MARIO_IWH` | Interactive Warehouse | XSMALL, 24h auto-suspend |
| `DIS_MARIO_WH` | Standard Warehouse | XSMALL, 60s auto-suspend |

### Interactive Tables (DIS_MARIO.PUBLIC)
| Table | Cluster By | Purpose |
|-------|-----------|---------|
| `GAME_EVENTS_LIVE` | EVENT_TIME | All game span events |
| `EVENT_TIMELINE_LIVE` | MINUTE | Event counts per minute |
| `KEY_PRESSES_LIVE` | KEY_NAME | Key press aggregates |
| `DEATHS_BY_LEVEL_LIVE` | LEVEL | Deaths per level |
| `POWERUPS_LIVE` | POWERUP_TYPE | Powerup spawn counts |
| `PLAYER_SESSIONS_LIVE` | SESSION_START | Per-player session summaries |

All tables: `TARGET_LAG = '1 minute'`, associated with `DIS_MARIO_IWH`.

### Analytics Views (MARIO_DB.PUBLIC)
| View | Description |
|------|-------------|
| `MARIO_TOP_SCORES` | Leaderboard — last 24 hours only |
| `MARIO_PLAYER_STATS` | Aggregated totals per player |
| `MARIO_GAME_SESSIONS` | Per-session breakdown |
| `MARIO_AVG_STATS` | Computed KPI averages |
| `MARIO_GAME_LOGS` | Service log messages |
| `MARIO_GAME_METRICS` | Raw platform metrics |
| `MARIO_GAME_TRACES` | Raw span/trace data |

### AI & Intelligence
| Object | Type | Details |
|--------|------|---------|
| `DIS_MARIO.PUBLIC.MARIO_TELEMETRY` | Semantic View | 6 tables, 2 relationships, 10 VQRs |
| `DIS_MARIO.PUBLIC.MARIO_INTELLIGENCE` | Cortex Agent | text-to-SQL over MARIO_TELEMETRY, model: auto |

---

## SPCS Service

**Service:** `MARIO_DB.PUBLIC.MARIO_SERVICE`  
**Ingress:** `https://<INGRESS_HASH>-<YOUR_ACCOUNT>.snowflakecomputing.app` (run `SHOW ENDPOINTS IN SERVICE` to find)  
**Image:** `<YOUR_ACCOUNT>.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest`

### Container Architecture
- **nginx** (port 8080) — SPCS ingress endpoint; routes telemetry to Python, game to Tomcat
- **Tomcat 9** (port 8888) — serves HTML5 Mario game with injected `telemetry.js`
- **Python Sidecar** (port 9090) — receives events, extracts player name, exports via OTel OTLP gRPC

### Player Name Flow
1. SPCS injects `Sf-Context-Current-User: <username>` header on all ingress requests
2. nginx forwards header via `proxy_set_header`
3. Sidecar reads header in `_get_player_name()` — falls back to browser-provided name, then `"unknown"`
4. Browser calls `/whoami` at game init → receives player name → includes in all event payloads
5. `player_name` stored as OTel span attribute → `record_attributes:player_name` in event table

### Rebuilding & Deploying
```bash
# Authenticate (avoids MFA/TOTP issues)
snow spcs image-registry login --connection <YOUR_CONNECTION>

# Build (always use --no-cache to avoid stale layers)
docker build --no-cache --platform linux/amd64 -t supermario ./mario-spcs/

# Tag and push
docker tag supermario <YOUR_ACCOUNT>.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
docker push <YOUR_ACCOUNT>.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest

# Force service to pull new image (suspend/resume does NOT re-pull)
snow spcs compute-pool resume MARIO_POOL --connection <YOUR_CONNECTION>
snow sql --role ACCOUNTADMIN -q "ALTER SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE FROM SPECIFICATION $$ ... $$" --connection <YOUR_CONNECTION>
```

> **Key learnings:**
> - Always use `--no-cache` — Docker silently reuses stale cached layers
> - `suspend/resume` does NOT pull a new image; use `ALTER SERVICE FROM SPECIFICATION`
> - `snow spcs image-registry login` handles MFA/TOTP automatically

---

## Telemetry Data Model

### Game Events (Spans → `record_attributes`)
| Event | Key Attributes |
|-------|---------------|
| `mario.game_start` | lives, player_name |
| `mario.level_start` | level, difficulty, type, lives, coins, player_name |
| `mario.death` | level, lives, coins, large, fire, player_name |
| `mario.level_win` | level, lives, coins, time_left, player_name |
| `mario.game_over` | level, coins, session_duration, player_name |
| `mario.game_win` | session_duration, player_name |
| `mario.coin` | total_coins, player_name |
| `mario.key_press` | key, player_name |
| `mario.powerup_spawn` | type, level, player_name |
| `mario.session_end` | session_duration, player_name |

### Platform Metrics (SPCS native — `platformMonitor.metricConfig`)
`container.cpu.usage`, `container.memory.usage`, `storage.used`, `storage.free`, `system.network.io`, `network.ingress.connections.active`

---

## Dashboards

### Streamlit — `MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD`
Legacy dashboard backed by raw event table views.  
Tabs: **Leaderboard** (top scores, last 24h) · Event Timeline · Deaths & Levels · Controls & Powerups · Platform Metrics

### Streamlit — `DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD`
Modern dashboard backed by Interactive Tables (near-realtime, 10s TTL).  
Tabs: **Leaderboard** · Event Timeline · Deaths & Levels · Controls & Powerups · Sessions · Platform Metrics  
Player dropdown filter · 6 KPI cards · auto-refresh

### React App — `mario-react-app/`
Next.js 16.2.3 dashboard, port 3456 locally.  
JWT auth locally (`~/.snowflake/keys/<YOUR_KEY>/rsa_key.p8`), OAuth token in SPCS.  
Tabs: **Leaderboard** · Overview · Live Events · Analytics · Data Pipeline (animated flow) · SPCS Metrics

---

## Demo Users

Mario-themed usernames for multi-player testing:

```
mario, luigi, peach, daisy, toad, toadette, yoshi, birdo,
wario, waluigi, bowser, bowserjr, rosalina, donkeykong,
diddykong, koopa, kamek, lakitu, boo, goomba
```

---

## Presentation

Generated from `presentation_template/presetation_template.pptx` using Snowflake brand colors:

```bash
python3 build_presentation.py
# Output: Super_Mario_SPCS_Telemetry_Presentation.pptx (12 slides, 20 min)
```

Slides: Cover → Agenda → What We Built → Architecture → Container Stack → Player Identity → Real-time Pipeline → Dashboards & AI → Snowflake Features → Live Demo → Key Learnings → Thank You

---

## Quick Start

### 1. Start SPCS Service
```bash
snow spcs compute-pool resume MARIO_POOL --connection <YOUR_CONNECTION>
snow spcs service resume MARIO_DB.PUBLIC.MARIO_SERVICE --connection <YOUR_CONNECTION>
```

### 2. Start React App (local dev)
```bash
SNOWFLAKE_CONNECTION_NAME=<YOUR_CONNECTION> npm run dev --prefix mario-react-app -- -p 3456
```

### 3. Deploy Streamlit
```bash
uvx --from snowflake-cli snow streamlit deploy --replace --connection <YOUR_CONNECTION> --role ACCOUNTADMIN
```

### 4. Suspend Everything
```bash
snow spcs service suspend MARIO_DB.PUBLIC.MARIO_SERVICE --connection <YOUR_CONNECTION>
snow spcs compute-pool suspend MARIO_POOL --connection <YOUR_CONNECTION>
```

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| GET tracking pixel for telemetry | SPCS ingress blocks POST from browser |
| `location = /telemetry` (exact match) | Prefix match catches `/telemetry.js` |
| Bundled `jquery.min.js` | SPCS egress blocks external CDN URLs |
| Browser sends `player_name` in every event | Fallback when `Sf-Context-Current-User` header unavailable |
| `--no-cache` Docker builds | Cache silently reuses stale layers |
| `ALTER SERVICE FROM SPECIFICATION` to update | `suspend/resume` does not re-pull image |
| Interactive Tables + IWH | Sub-second query latency for dashboard polling |
