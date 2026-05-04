# Mario SPCS Telemetry — Cortex Code Session Context

## Project Overview

Real-time game telemetry platform: Super Mario Bros running on Snowpark Container Services (SPCS) with OpenTelemetry instrumentation, Interactive Tables for sub-second analytics, Cortex AI for natural language queries, and multiple dashboard frontends.

## Snowflake Connection

- **Connection name:** `eu_demo200`
- **Account:** SFSEEUROPE-EU_DEMO200
- **User:** thomas
- **Auth:** SNOWFLAKE_JWT (keypair)
- **Role:** ACCOUNTADMIN

## Key Snowflake Objects

| Object | Fully Qualified Name |
|--------|---------------------|
| Compute Pool | `MARIO_POOL` (CPU_X64_XS, 1 node) |
| Service | `MARIO_DB.PUBLIC.MARIO_SERVICE` |
| Event Table | `EVENT_DB.EVENT_SH.MY_EVENTS` |
| Interactive Tables (6) | `DIS_MARIO.PUBLIC.*_LIVE` |
| Interactive Warehouse | `DIS_MARIO_IWH` |
| Semantic View | `DIS_MARIO.PUBLIC.MARIO_TELEMETRY` |
| Cortex Agent | `DIS_MARIO.PUBLIC.MARIO_INTELLIGENCE` |
| Streamlit (legacy) | `MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD` |
| Streamlit (live) | `DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD` |

## URLs

- **Game:** https://ei53mb-sfseeurope-eu-demo200.snowflakecomputing.app
- **Docker registry:** sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
- **React app (local):** http://localhost:3456
- **GitHub:** https://github.com/sfc-gh-tdahlberg/mario-spcs-telemetry

## Common Operations

### Start services
```sql
USE ROLE ACCOUNTADMIN;
ALTER COMPUTE POOL MARIO_POOL RESUME;
ALTER SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE RESUME;
```

### Suspend services
```sql
USE ROLE ACCOUNTADMIN;
ALTER SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE SUSPEND;
ALTER COMPUTE POOL MARIO_POOL SUSPEND;
```

### Start React app
```bash
SNOWFLAKE_CONNECTION_NAME=eu_demo200 npm run dev --prefix mario-react-app -- -p 3456
```

### Rebuild Docker image
```bash
snow spcs image-registry login --connection eu_demo200
docker build --no-cache --platform linux/amd64 -t supermario ./mario-spcs/
docker tag supermario sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
docker push sfseeurope-eu-demo200.registry.snowflakecomputing.com/mario_db/public/mario_repo/supermario:latest
```

### Force service to pull new image
```sql
ALTER SERVICE MARIO_DB.PUBLIC.MARIO_SERVICE FROM SPECIFICATION $$
spec:
  containers:
  - name: supermario
    image: /mario_db/public/mario_repo/supermario:latest
    resources:
      requests: {cpu: 500m, memory: 512Mi}
      limits: {cpu: "1", memory: 2Gi}
  endpoints:
  - name: game
    port: 8080
    public: true
  platformMonitor:
    metricConfig:
      groups:
      - system
      - network
      - storage
$$;
```

### Regenerate presentation
```bash
python3 build_presentation.py
```

## Key Learnings & Gotchas

1. **Docker --no-cache**: Always use it. Cached layers silently persist old code.
2. **suspend/resume ≠ re-pull**: Service must use `ALTER SERVICE FROM SPECIFICATION` to pull new image.
3. **nginx exact match**: Use `location = /telemetry` not `location /telemetry` (prefix catches .js files).
4. **SPCS blocks egress**: Bundle all dependencies (jQuery, etc.) inside the Docker image.
5. **JWT for headless auth**: EXTERNALBROWSER fails in Node.js. Use SNOWFLAKE_JWT keypair.
6. **snow spcs image-registry login**: Handles MFA/TOTP automatically (vs manual docker login).
7. **Interactive Tables**: `CREATE INTERACTIVE TABLE` syntax. Associate with IWH via `ALTER INTERACTIVE TABLE ... SET WAREHOUSE`.
8. **Player name priority**: Sf-Context-Current-User header → browser payload → "unknown".

## Project Structure

```
mario-spcs/             # Docker container (nginx + Tomcat + Python sidecar)
mario-react-app/        # Next.js 16.2.3 analytics dashboard
mario-streamlit/        # Streamlit in Snowsight app
sql/                    # All SQL setup scripts (01-06)
semantic_view_*/        # Cortex Analyst semantic model YAML
docs/                   # HTML documentation (landscape, dark-themed)
presentation_template/  # Snowflake branded PPTX template
build_presentation.py   # Generates the 12-slide event presentation
```

## Demo Users (Mario-themed)

```
mario, luigi, peach, daisy, toad, toadette, yoshi, birdo,
wario, waluigi, bowser, bowserjr, rosalina, donkeykong,
diddykong, koopa, kamek, lakitu, boo, goomba
```

## Lint / Test Commands

- **React:** `npm run build --prefix mario-react-app`
- **Presentation:** `python3 build_presentation.py`
- **SQL validation:** Use `snowflake_sql_execute` with `only_compile=true`
