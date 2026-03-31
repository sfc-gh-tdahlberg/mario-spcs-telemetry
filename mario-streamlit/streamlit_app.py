import streamlit as st
from datetime import timedelta, datetime, timezone

st.set_page_config(page_title="Mario SPCS Telemetry", page_icon=":mushroom:", layout="wide")

conn = st.connection("snowflake")

st.title(":mushroom: Super Mario SPCS Telemetry")
st.caption("Real-time game telemetry from Snowpark Container Services via OpenTelemetry")

@st.cache_data(ttl=timedelta(seconds=30))
def load_stats():
    return conn.query("SELECT * FROM MARIO_DB.PUBLIC.MARIO_PLAYER_STATS")

@st.cache_data(ttl=timedelta(seconds=30))
def load_avg_stats():
    return conn.query("SELECT * FROM MARIO_DB.PUBLIC.MARIO_AVG_STATS")

@st.cache_data(ttl=timedelta(seconds=30))
def load_top_scores():
    return conn.query("SELECT * FROM MARIO_DB.PUBLIC.MARIO_TOP_SCORES ORDER BY RANK")

@st.cache_data(ttl=timedelta(seconds=30))
def load_sessions():
    return conn.query("SELECT * FROM MARIO_DB.PUBLIC.MARIO_GAME_SESSIONS ORDER BY SESSION_START DESC")

@st.cache_data(ttl=timedelta(seconds=30))
def load_events():
    return conn.query("""
        SELECT
            timestamp,
            record:name::STRING AS event_type,
            record_attributes:level::STRING AS level,
            record_attributes:coins::STRING AS coins,
            record_attributes:lives::STRING AS lives,
            record_attributes:key::STRING AS key_name,
            record_attributes:type::STRING AS powerup_type,
            record_attributes:session_duration::STRING AS duration
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'SPAN'
          AND record:name::STRING LIKE 'mario.%'
        ORDER BY timestamp DESC
        LIMIT 500
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_event_timeline():
    return conn.query("""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            record:name::STRING AS event_type,
            COUNT(*) AS event_count
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'SPAN'
          AND record:name::STRING LIKE 'mario.%'
          AND record:name::STRING NOT IN ('mario.key_press')
        GROUP BY 1, 2
        ORDER BY 1
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_deaths_by_level():
    return conn.query("""
        SELECT
            record_attributes:level::STRING AS level,
            COUNT(*) AS deaths
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'SPAN'
          AND record:name::STRING = 'mario.death'
        GROUP BY 1
        ORDER BY deaths DESC
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_key_presses():
    return conn.query("""
        SELECT
            record_attributes:key::STRING AS key_name,
            COUNT(*) AS presses
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'SPAN'
          AND record:name::STRING = 'mario.key_press'
        GROUP BY 1
        ORDER BY presses DESC
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_powerups():
    return conn.query("""
        SELECT
            record_attributes:type::STRING AS powerup_type,
            record_attributes:level::STRING AS level,
            COUNT(*) AS count
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'SPAN'
          AND record:name::STRING = 'mario.powerup_spawn'
        GROUP BY 1, 2
        ORDER BY count DESC
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_cpu_metrics(start_ts: str, end_ts: str):
    return conn.query(f"""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            ROUND(AVG(value::FLOAT) * 100, 2) AS avg_cpu_pct,
            ROUND(MAX(value::FLOAT) * 100, 2) AS max_cpu_pct
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING = 'container.cpu.usage'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1
        ORDER BY 1
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_memory_metrics(start_ts: str, end_ts: str):
    return conn.query(f"""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            ROUND(AVG(value::FLOAT) / 1048576, 1) AS avg_memory_mb,
            ROUND(MAX(value::FLOAT) / 1048576, 1) AS max_memory_mb
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING = 'container.memory.usage'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1
        ORDER BY 1
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_network_metrics(start_ts: str, end_ts: str):
    return conn.query(f"""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.connections.active' THEN value::FLOAT END) AS active_connections,
            MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.cps' THEN value::FLOAT END) AS connections_per_sec
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING IN ('network.ingress.connections.active', 'network.ingress.cps')
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1
        ORDER BY 1
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_storage_metrics(start_ts: str, end_ts: str):
    return conn.query(f"""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            ROUND(AVG(value::FLOAT) / 1048576, 1) AS avg_mb,
            ROUND(MAX(value::FLOAT) / 1048576, 1) AS max_mb
        FROM event_db.event_sh.my_events
        WHERE record_type = 'METRIC'
          AND record:metric.name::STRING = 'storage.used'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1
        ORDER BY 1
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_disk_iops(start_ts: str, end_ts: str):
    return conn.query(f"""
        WITH storage_snapshots AS (
            SELECT
                TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
                SUM(value::FLOAT) AS total_bytes
            FROM event_db.event_sh.my_events
            WHERE record_type = 'METRIC'
              AND record:metric.name::STRING = 'storage.used'
              AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
            GROUP BY 1
        ),
        deltas AS (
            SELECT
                minute,
                total_bytes,
                LAG(total_bytes) OVER (ORDER BY minute) AS prev_bytes,
                DATEDIFF('second', LAG(minute) OVER (ORDER BY minute), minute) AS elapsed_sec
            FROM storage_snapshots
        )
        SELECT
            minute,
            ROUND(ABS(total_bytes - prev_bytes) / NULLIF(elapsed_sec, 0) / 4096, 1) AS iops_estimate
        FROM deltas
        WHERE prev_bytes IS NOT NULL AND elapsed_sec > 0
        ORDER BY minute
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_io_latency(start_ts: str, end_ts: str):
    return conn.query(f"""
        WITH net_snapshots AS (
            SELECT
                TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
                SUM(value::FLOAT) AS total_bytes,
                COUNT(*) AS sample_count
            FROM event_db.event_sh.my_events
            WHERE record_type = 'METRIC'
              AND record:metric.name::STRING = 'system.network.io'
              AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
            GROUP BY 1
        ),
        deltas AS (
            SELECT
                minute,
                total_bytes,
                sample_count,
                LAG(total_bytes) OVER (ORDER BY minute) AS prev_bytes,
                DATEDIFF('second', LAG(minute) OVER (ORDER BY minute), minute) AS elapsed_sec
            FROM net_snapshots
        )
        SELECT
            minute,
            ROUND(ABS(total_bytes - prev_bytes) / NULLIF(elapsed_sec, 0) / 1048576, 2) AS throughput_mbps,
            ROUND(NULLIF(elapsed_sec, 0) * 1000.0 / NULLIF(sample_count, 0), 2) AS avg_latency_ms
        FROM deltas
        WHERE prev_bytes IS NOT NULL AND elapsed_sec > 0
        ORDER BY minute
    """)

@st.cache_data(ttl=timedelta(seconds=30))
def load_network_io_metrics(start_ts: str, end_ts: str):
    return conn.query(f"""
        SELECT
            TIME_SLICE(timestamp, 1, 'MINUTE') AS minute,
            ROUND(AVG(CASE WHEN record_attributes:"direction"::STRING = 'receive' THEN value::FLOAT END) / 1048576, 1) AS avg_rx_mb,
            ROUND(MAX(CASE WHEN record_attributes:"direction"::STRING = 'receive' THEN value::FLOAT END) / 1048576, 1) AS max_rx_mb,
            ROUND(AVG(CASE WHEN record_attributes:"direction"::STRING = 'transmit' THEN value::FLOAT END) / 1048576, 1) AS avg_tx_mb,
            ROUND(MAX(CASE WHEN record_attributes:"direction"::STRING = 'transmit' THEN value::FLOAT END) / 1048576, 1) AS max_tx_mb
        FROM event_db.event_sh.my_events
        WHERE record_type = 'METRIC'
          AND record:metric.name::STRING = 'system.network.io'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1
        ORDER BY 1
    """)

if st.button(":arrows_counterclockwise: Refresh Data"):
    st.cache_data.clear()

stats = load_stats()

with st.container(horizontal=True):
    st.metric("Total Games", int(stats["TOTAL_GAMES"].iloc[0]), border=True)
    st.metric("Total Deaths", int(stats["TOTAL_DEATHS"].iloc[0]), border=True)
    st.metric("Coins Collected", int(stats["TOTAL_COINS_COLLECTED"].iloc[0]), border=True)
    st.metric("Level Attempts", int(stats["TOTAL_LEVEL_ATTEMPTS"].iloc[0]), border=True)
    st.metric("Level Wins", int(stats["TOTAL_LEVEL_WINS"].iloc[0]), border=True)
    st.metric("Powerups", int(stats["TOTAL_POWERUPS"].iloc[0]), border=True)
    st.metric("Key Presses", int(stats["TOTAL_KEY_PRESSES"].iloc[0]), border=True)

avg = load_avg_stats()
if not avg.empty:
    with st.container(horizontal=True):
        st.metric("Avg Playtime", f"{avg['AVG_PLAYTIME_SEC'].iloc[0]:.0f}s", border=True)
        st.metric("Sec / Death", f"{avg['AVG_SEC_PER_DEATH'].iloc[0]:.1f}s", border=True)
        st.metric("Coins / Round", f"{avg['AVG_COINS_PER_ROUND'].iloc[0]:.1f}", border=True)
        st.metric("Avg Level Time", f"{avg['AVG_LEVEL_PLAYED_SEC'].iloc[0]:.0f}s", border=True)
        st.metric("Avg Attempts", f"{avg['AVG_ATTEMPTS_PER_GAME'].iloc[0]:.1f}", border=True)
        st.metric("Win Rate", f"{avg['WIN_RATE_PCT'].iloc[0]:.1f}%", border=True)
        st.metric("Keys / Game", f"{avg['AVG_KEYS_PER_GAME'].iloc[0]:.0f}", border=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    ":trophy: Leaderboard",
    ":chart_with_upwards_trend: Event Timeline",
    ":skull: Deaths & Levels",
    ":joystick: Controls & Powerups",
    ":gear: Platform Metrics"
])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(":trophy: Top Scores")
        top_scores = load_top_scores()
        if not top_scores.empty:
            st.dataframe(
                top_scores,
                column_config={
                    "RANK": st.column_config.NumberColumn("Rank", format="%d"),
                    "GAME_TIME": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
                    "FINAL_LEVEL": "Level Reached",
                    "COINS": st.column_config.NumberColumn("Coins", format="%d"),
                    "DURATION_SECONDS": st.column_config.NumberColumn("Duration (s)", format="%.1f"),
                    "DURATION_MINUTES": st.column_config.NumberColumn("Duration (min)", format="%.1f"),
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No completed games yet. Play some Mario!")

    with col2:
        st.subheader(":video_game: Game Sessions")
        sessions = load_sessions()
        if not sessions.empty:
            st.dataframe(
                sessions,
                column_config={
                    "SESSION_ID": st.column_config.NumberColumn("Session", format="%d"),
                    "SESSION_START": st.column_config.DatetimeColumn("Start", format="HH:mm:ss"),
                    "SESSION_END": st.column_config.DatetimeColumn("End", format="HH:mm:ss"),
                    "DURATION_SECONDS": st.column_config.NumberColumn("Duration (s)", format="%.1f"),
                    "FINAL_LEVEL": "Final Level",
                    "SCORE_COINS": st.column_config.NumberColumn("Coins", format="%d"),
                    "TOTAL_DEATHS": st.column_config.NumberColumn("Deaths", format="%d"),
                    "LEVELS_PLAYED": st.column_config.NumberColumn("Levels", format="%d"),
                    "HIGHEST_LEVEL": "Best Level",
                },
                hide_index=True,
                use_container_width=True,
            )

with tab2:
    st.subheader(":chart_with_upwards_trend: Game Events Over Time")
    timeline = load_event_timeline()
    if not timeline.empty:
        import pandas as pd
        pivot = timeline.pivot_table(
            index="MINUTE",
            columns="EVENT_TYPE",
            values="EVENT_COUNT",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()
        pivot = pivot.set_index("MINUTE")
        rename_map = {c: c.replace("mario.", "").replace("_", " ").title() for c in pivot.columns}
        pivot = pivot.rename(columns=rename_map)
        st.area_chart(pivot)
    else:
        st.info("No events yet.")

with tab3:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(":skull: Deaths by Level")
        deaths = load_deaths_by_level()
        if not deaths.empty:
            st.bar_chart(deaths, x="LEVEL", y="DEATHS", horizontal=True)
        else:
            st.info("No deaths recorded yet. Impressive!")

    with col2:
        st.subheader(":mushroom: Powerups Collected")
        powerups = load_powerups()
        if not powerups.empty:
            st.dataframe(
                powerups,
                column_config={
                    "POWERUP_TYPE": "Type",
                    "LEVEL": "Level",
                    "COUNT": st.column_config.NumberColumn("Count", format="%d"),
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No powerups yet.")

with tab4:
    st.subheader(":joystick: Key Press Distribution")
    keys = load_key_presses()
    if not keys.empty:
        st.bar_chart(keys, x="KEY_NAME", y="PRESSES")
    else:
        st.info("No key presses recorded.")

with tab5:
    st.subheader(":gear: Container Platform Metrics")

    range_options = {"Last 15 min": 15, "Last 1 hour": 60, "Last 6 hours": 360, "Last 24 hours": 1440, "Last 7 days": 10080, "All time": None}
    pcol1, pcol2 = st.columns([3, 1])
    with pcol2:
        selected_range = st.selectbox("Time range", list(range_options.keys()), index=2, key="platform_time_range")
    now_ts = datetime.now(timezone.utc)
    minutes_back = range_options[selected_range]
    if minutes_back is not None:
        start_ts = (now_ts - timedelta(minutes=minutes_back)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_ts = "2020-01-01 00:00:00"
    end_ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**CPU Usage (%)**")
        cpu = load_cpu_metrics(start_ts, end_ts)
        if not cpu.empty:
            st.line_chart(cpu.set_index("MINUTE"), y=["AVG_CPU_PCT", "MAX_CPU_PCT"], color=["#FF6B6B", "#CC3333"])
        else:
            st.info("No CPU metrics in selected range.")

    with col2:
        st.markdown("**Memory Usage (MB)**")
        mem = load_memory_metrics(start_ts, end_ts)
        if not mem.empty:
            st.line_chart(mem.set_index("MINUTE"), y=["AVG_MEMORY_MB", "MAX_MEMORY_MB"], color=["#4ECDC4", "#2A9D8F"])
        else:
            st.info("No memory metrics in selected range.")

    col3, col4 = st.columns(2)

    with col3:
        st.markdown("**Disk Storage Used (MB)**")
        storage = load_storage_metrics(start_ts, end_ts)
        if not storage.empty:
            st.line_chart(storage.set_index("MINUTE"), y=["AVG_MB", "MAX_MB"], color=["#F4A261", "#E76F51"])
        else:
            st.info("No storage metrics in selected range.")

    with col4:
        st.markdown("**Estimated Disk IOPS (4K blocks)**")
        iops = load_disk_iops(start_ts, end_ts)
        if not iops.empty:
            st.line_chart(iops.set_index("MINUTE"), y="IOPS_ESTIMATE", color="#E9C46A")
        else:
            st.info("No IOPS data in selected range.")

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("**I/O Throughput (MB/s) & Latency (ms)**")
        latency = load_io_latency(start_ts, end_ts)
        if not latency.empty:
            st.line_chart(latency.set_index("MINUTE"), color=["#45B7D1", "#E76F51"])
        else:
            st.info("No I/O latency data in selected range.")

    with col6:
        st.markdown("**Network Ingress (Connections)**")
        net = load_network_metrics(start_ts, end_ts)
        if not net.empty:
            st.line_chart(net.set_index("MINUTE"), color=["#45B7D1", "#96CEB4"])
        else:
            st.info("No network metrics in selected range.")

    st.markdown("**Network I/O (MB)**")
    net_io = load_network_io_metrics(start_ts, end_ts)
    if not net_io.empty:
        st.line_chart(net_io.set_index("MINUTE"), color=["#45B7D1", "#264653", "#96CEB4", "#2A9D8F"])
    else:
        st.info("No network I/O metrics in selected range.")

st.divider()

with st.expander(":clipboard: Raw Event Log (latest 500)"):
    events = load_events()
    if not events.empty:
        events["EVENT_TYPE"] = events["EVENT_TYPE"].str.replace("mario.", "", regex=False)
        st.dataframe(events, hide_index=True, use_container_width=True)

st.caption("Data flows: Browser JS -> nginx -> Python sidecar -> OpenTelemetry -> SPCS Event Table")
