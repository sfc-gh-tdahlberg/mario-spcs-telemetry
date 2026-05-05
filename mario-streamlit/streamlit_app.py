import streamlit as st
from datetime import timedelta, datetime, timezone
import base64
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="DIS Mario Telemetry", page_icon=":mushroom:", layout="wide")

SNOWFLAKE_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 40" fill="none"><g transform="translate(0,2)"><path d="M18 0L21.12 6.36L28 7.64L23 12.64L24.24 19.52L18 16.2L11.76 19.52L13 12.64L8 7.64L14.88 6.36L18 0Z" fill="#29B5E8"/><path d="M18 16L21.12 22.36L28 23.64L23 28.64L24.24 35.52L18 32.2L11.76 35.52L13 28.64L8 23.64L14.88 22.36L18 16Z" fill="#29B5E8" opacity="0.7"/><path d="M2 8L5.12 14.36L12 15.64L7 20.64L8.24 27.52L2 24.2L-4.24 27.52L-3 20.64L-8 15.64L-1.12 14.36L2 8Z" fill="#29B5E8" opacity="0.5"/><path d="M34 8L37.12 14.36L44 15.64L39 20.64L40.24 27.52L34 24.2L27.76 27.52L29 20.64L24 15.64L30.88 14.36L34 8Z" fill="#29B5E8" opacity="0.5"/></g><text x="52" y="27" font-family="system-ui, -apple-system, sans-serif" font-size="22" font-weight="700" fill="#29B5E8" letter-spacing="-0.5">snowflake</text></svg>"""

POLAR_BEAR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" fill="none"><style>@keyframes wave{0%,100%{transform:rotate(0)}15%{transform:rotate(14deg)}30%{transform:rotate(-8deg)}45%{transform:rotate(14deg)}60%{transform:rotate(-4deg)}75%{transform:rotate(10deg)}90%{transform:rotate(0)}}@keyframes blink{0%,90%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}@keyframes bodyBounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}.wave-arm{transform-origin:78px 55px;animation:wave 1.5s ease-in-out infinite}.left-eye,.right-eye{animation:blink 3s ease-in-out infinite}.right-eye{animation-delay:.1s}.bear-body{animation:bodyBounce 1.5s ease-in-out infinite}</style><g class="bear-body"><ellipse cx="60" cy="78" rx="28" ry="30" fill="white"/><ellipse cx="60" cy="82" rx="22" ry="22" fill="#F0F4F8"/><circle cx="60" cy="42" r="26" fill="white"/><circle cx="60" cy="44" r="20" fill="#F0F4F8" opacity=".3"/><circle cx="40" cy="22" r="10" fill="white"/><circle cx="40" cy="22" r="6" fill="#B0D4E8"/><circle cx="80" cy="22" r="10" fill="white"/><circle cx="80" cy="22" r="6" fill="#B0D4E8"/><g class="left-eye" transform-origin="50 38"><circle cx="50" cy="38" r="3.5" fill="#2D3748"/><circle cx="51.2" cy="36.8" r="1.2" fill="white"/></g><g class="right-eye" transform-origin="70 38"><circle cx="70" cy="38" r="3.5" fill="#2D3748"/><circle cx="71.2" cy="36.8" r="1.2" fill="white"/></g><ellipse cx="60" cy="46" rx="4" ry="3" fill="#2D3748"/><path d="M54 50Q60 56 66 50" stroke="#2D3748" stroke-width="1.8" fill="none" stroke-linecap="round"/><ellipse cx="46" cy="48" rx="4" ry="2.5" fill="#FFB5B5" opacity=".5"/><ellipse cx="74" cy="48" rx="4" ry="2.5" fill="#FFB5B5" opacity=".5"/><path d="M34 65Q22 70 26 82" stroke="white" stroke-width="10" fill="none" stroke-linecap="round"/><circle cx="26" cy="82" r="6" fill="white"/><ellipse cx="48" cy="106" rx="12" ry="6" fill="white"/><ellipse cx="72" cy="106" rx="12" ry="6" fill="white"/><g transform="translate(60,80)" opacity=".3"><line x1="0" y1="-8" x2="0" y2="8" stroke="#29B5E8" stroke-width="1.5"/><line x1="-7" y1="-4" x2="7" y2="4" stroke="#29B5E8" stroke-width="1.5"/><line x1="-7" y1="4" x2="7" y2="-4" stroke="#29B5E8" stroke-width="1.5"/></g></g><g class="wave-arm"><path d="M86 60Q98 48 94 34" stroke="white" stroke-width="10" fill="none" stroke-linecap="round"/><circle cx="94" cy="34" r="6" fill="white"/></g></svg>"""

def render_svg(svg: str, width: int = 120):
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="{width}"/>'

session = get_active_session()

st.markdown(
    f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:-10px;">{render_svg(POLAR_BEAR_SVG, 56)}<div><h1 style="margin:0;font-size:1.8rem;">\U0001f344 Super Mario SPCS Telemetry \u2014 DIS_MARIO</h1><p style="margin:0;font-size:0.85rem;color:#888;">Real-time game telemetry via Interactive Tables (1-min auto-refresh) \u2022 DIS_MARIO_IWH</p></div></div>',
    unsafe_allow_html=True,
)

@st.cache_data(ttl=timedelta(seconds=10))
def load_players():
    return session.sql("""
        SELECT PLAYER_NAME,
               COUNT(CASE WHEN EVENT_TYPE = 'mario.game_start' THEN 1 END) AS SESSIONS,
               CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', MAX(TIMESTAMP)::TIMESTAMP_NTZ) AS LAST_SEEN
        FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
        WHERE PLAYER_NAME IS NOT NULL AND PLAYER_NAME != 'unknown'
        GROUP BY PLAYER_NAME ORDER BY SESSIONS DESC
    """).to_pandas()

players_df = load_players()
player_list = ["All Players"] + players_df["PLAYER_NAME"].tolist() if not players_df.empty else ["All Players"]
hcol1, hcol2, hcol3 = st.columns([4, 2, 1])
with hcol2:
    selected_player = st.selectbox(":bust_in_silhouette: Player", player_list, index=0)
with hcol3:
    if st.button(":arrows_counterclockwise: Refresh"):
        st.cache_data.clear()

player_filter = f"AND PLAYER_NAME = '{selected_player}'" if selected_player != "All Players" else ""
player_filter_where = f"WHERE PLAYER_NAME = '{selected_player}'" if selected_player != "All Players" else ""

@st.cache_data(ttl=timedelta(seconds=10))
def load_stats(player_filter=""):
    return session.sql(f"""
        SELECT
            (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE 1=1 {player_filter}) AS TOTAL_EVENTS,
            (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.death' {player_filter}) AS TOTAL_DEATHS,
            (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.coin' {player_filter}) AS TOTAL_COINS,
            (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.level_win' {player_filter}) AS TOTAL_LEVELS_WON,
            (SELECT SUM(COUNT) FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE {player_filter.replace('AND', 'WHERE', 1) if player_filter else ''}) AS TOTAL_POWERUPS,
            (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.game_start' {player_filter}) AS TOTAL_SESSIONS
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_leaderboard():
    return session.sql("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY COINS::INT DESC, DURATION::FLOAT ASC) AS RANK,
            PLAYER_NAME, LEVEL AS FINAL_LEVEL, COINS::INT AS COINS,
            ROUND(DURATION::FLOAT, 1) AS DURATION_SECONDS,
            CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIMESTAMP::TIMESTAMP_NTZ) AS GAME_TIME
        FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
        WHERE EVENT_TYPE = 'mario.game_over'
          AND TIMESTAMP >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
          AND PLAYER_NAME IS NOT NULL AND PLAYER_NAME != 'unknown'
        ORDER BY COINS::INT DESC, DURATION::FLOAT ASC
        LIMIT 20
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_events(player_filter=""):
    return session.sql(f"""
        SELECT EVENT_TYPE, PLAYER_NAME, LEVEL, COINS, LIVES, KEY_NAME, POWERUP_TYPE, DURATION, SESSION_ID,
               CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIMESTAMP::TIMESTAMP_NTZ) AS TIMESTAMP
        FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
        WHERE EVENT_TYPE != 'mario.key_press' {player_filter}
        ORDER BY TIMESTAMP DESC
        LIMIT 500
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_event_timeline():
    return session.sql("""
        SELECT CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', MINUTE::TIMESTAMP_NTZ) AS MINUTE, EVENT_TYPE, EVENT_COUNT
        FROM DIS_MARIO.PUBLIC.EVENT_TIMELINE_LIVE
        ORDER BY MINUTE
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_deaths_by_level(player_filter_where=""):
    return session.sql(f"SELECT LEVEL, SUM(DEATHS) AS DEATHS FROM DIS_MARIO.PUBLIC.DEATHS_BY_LEVEL_LIVE {player_filter_where} GROUP BY LEVEL ORDER BY DEATHS DESC").to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_key_presses(player_filter_where=""):
    return session.sql(f"SELECT KEY_NAME, SUM(PRESSES) AS PRESSES FROM DIS_MARIO.PUBLIC.KEY_PRESSES_LIVE {player_filter_where} GROUP BY KEY_NAME ORDER BY PRESSES DESC").to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_powerups(player_filter_where=""):
    return session.sql(f"SELECT POWERUP_TYPE, LEVEL, SUM(COUNT) AS COUNT FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE {player_filter_where} GROUP BY POWERUP_TYPE, LEVEL ORDER BY COUNT DESC").to_pandas()

@st.cache_data(ttl=timedelta(seconds=10))
def load_sessions(player_filter_where=""):
    pf = player_filter_where.replace("WHERE", "AND") if player_filter_where else ""
    return session.sql(f"""
        SELECT PLAYER_NAME,
               TIMESTAMP AS SESSION_START,
               LEVEL, COINS::INT AS COINS, LIVES::INT AS LIVES,
               ROUND(DURATION::FLOAT, 1) AS DURATION_SECONDS
        FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
        WHERE EVENT_TYPE = 'mario.game_over' {pf}
        ORDER BY TIMESTAMP DESC
        LIMIT 50
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=30))
def load_cpu_metrics(start_ts: str, end_ts: str):
    return session.sql(f"""
        SELECT
            CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIME_SLICE(timestamp, 1, 'MINUTE')::TIMESTAMP_NTZ) AS minute,
            ROUND(AVG(value::FLOAT) * 100, 2) AS avg_cpu_pct,
            ROUND(MAX(value::FLOAT) * 100, 2) AS max_cpu_pct
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING = 'container.cpu.usage'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1 ORDER BY 1
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=30))
def load_memory_metrics(start_ts: str, end_ts: str):
    return session.sql(f"""
        SELECT
            CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIME_SLICE(timestamp, 1, 'MINUTE')::TIMESTAMP_NTZ) AS minute,
            ROUND(AVG(value::FLOAT) / 1048576, 1) AS avg_memory_mb,
            ROUND(MAX(value::FLOAT) / 1048576, 1) AS max_memory_mb
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING = 'container.memory.usage'
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1 ORDER BY 1
    """).to_pandas()

@st.cache_data(ttl=timedelta(seconds=30))
def load_network_metrics(start_ts: str, end_ts: str):
    return session.sql(f"""
        SELECT
            CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIME_SLICE(timestamp, 1, 'MINUTE')::TIMESTAMP_NTZ) AS minute,
            MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.connections.active' THEN value::FLOAT END) AS active_connections,
            MAX(CASE WHEN record:metric.name::STRING = 'network.ingress.cps' THEN value::FLOAT END) AS connections_per_sec
        FROM event_db.event_sh.my_events
        WHERE resource_attributes:"snow.service.name"::STRING = 'MARIO_SERVICE'
          AND record_type = 'METRIC'
          AND record:metric.name::STRING IN ('network.ingress.connections.active', 'network.ingress.cps')
          AND timestamp BETWEEN '{start_ts}'::TIMESTAMP_NTZ AND '{end_ts}'::TIMESTAMP_NTZ
        GROUP BY 1 ORDER BY 1
    """).to_pandas()

if st.button(":arrows_counterclockwise: Refresh Data"):
    st.cache_data.clear()

stats = load_stats(player_filter)
if not stats.empty:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("Total Events", int(stats["TOTAL_EVENTS"].iloc[0]))
    with c2:
        st.metric("Deaths", int(stats["TOTAL_DEATHS"].iloc[0]))
    with c3:
        st.metric("Coins", int(stats["TOTAL_COINS"].iloc[0]))
    with c4:
        st.metric("Levels Won", int(stats["TOTAL_LEVELS_WON"].iloc[0]))
    with c5:
        st.metric("Powerups", int(stats["TOTAL_POWERUPS"].iloc[0]) if stats["TOTAL_POWERUPS"].iloc[0] else 0)
    with c6:
        st.metric("Sessions", int(stats["TOTAL_SESSIONS"].iloc[0]))

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    ":trophy: Leaderboard",
    ":chart_with_upwards_trend: Event Timeline",
    ":skull: Deaths & Levels",
    ":joystick: Controls & Powerups",
    ":video_game: Sessions",
    ":gear: Platform Metrics"
])

with tab1:
    st.subheader(":trophy: Leaderboard — Last 24 Hours")
    lb = load_leaderboard()
    if not lb.empty:
        st.dataframe(lb, use_container_width=True)
    else:
        st.info("No games completed in the last 24 hours. Play Mario to get on the board!")

with tab2:
    st.subheader(":chart_with_upwards_trend: Game Events Over Time")
    timeline = load_event_timeline()
    if not timeline.empty:
        import pandas as pd
        pivot = timeline.pivot_table(index="MINUTE", columns="EVENT_TYPE", values="EVENT_COUNT", aggfunc="sum", fill_value=0).reset_index()
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
        deaths = load_deaths_by_level(player_filter_where)
        if not deaths.empty:
            st.bar_chart(deaths, x="LEVEL", y="DEATHS")
        else:
            st.info("No deaths recorded yet.")
    with col2:
        st.subheader(":mushroom: Powerups Collected")
        powerups = load_powerups(player_filter_where)
        if not powerups.empty:
            st.dataframe(powerups, use_container_width=True)
        else:
            st.info("No powerups yet.")

with tab4:
    st.subheader(":joystick: Key Press Distribution")
    keys = load_key_presses(player_filter_where)
    if not keys.empty:
        st.bar_chart(keys, x="KEY_NAME", y="PRESSES")
    else:
        st.info("No key presses recorded.")

with tab5:
    st.subheader(":video_game: Player Sessions")
    sessions = load_sessions(player_filter_where)
    if not sessions.empty:
        st.dataframe(sessions, use_container_width=True)
    else:
        st.info("No sessions yet.")

with tab6:
    st.subheader(":gear: Container Platform Metrics")
    range_options = {"Last 15 min": 15, "Last 1 hour": 60, "Last 6 hours": 360, "Last 24 hours": 1440, "All time": None}
    pcol1, pcol2 = st.columns([3, 1])
    with pcol2:
        selected_range = st.selectbox("Time range", list(range_options.keys()), index=2)
    now_ts = datetime.now(timezone.utc)
    minutes_back = range_options[selected_range]
    start_ts = (now_ts - timedelta(minutes=minutes_back)).strftime("%Y-%m-%d %H:%M:%S") if minutes_back else "2020-01-01 00:00:00"
    end_ts = now_ts.strftime("%Y-%m-%d %H:%M:%S")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**CPU Usage (%)**")
        cpu = load_cpu_metrics(start_ts, end_ts)
        if not cpu.empty:
            st.line_chart(cpu.set_index("MINUTE"), y=["AVG_CPU_PCT", "MAX_CPU_PCT"])
        else:
            st.info("No CPU metrics in selected range.")
    with col2:
        st.markdown("**Memory Usage (MB)**")
        mem = load_memory_metrics(start_ts, end_ts)
        if not mem.empty:
            st.line_chart(mem.set_index("MINUTE"), y=["AVG_MEMORY_MB", "MAX_MEMORY_MB"])
        else:
            st.info("No memory metrics in selected range.")

    st.markdown("**Network Ingress (Connections)**")
    net = load_network_metrics(start_ts, end_ts)
    if not net.empty:
        st.line_chart(net.set_index("MINUTE"))
    else:
        st.info("No network metrics in selected range.")

st.divider()

with st.expander(":clipboard: Raw Event Log (latest 500)"):
    events = load_events(player_filter)
    if not events.empty:
        events["EVENT_TYPE"] = events["EVENT_TYPE"].str.replace("mario.", "", regex=False)
        st.dataframe(events, use_container_width=True)

st.caption("Data flows: Browser JS → nginx → Python sidecar → OpenTelemetry → SPCS Event Table → Interactive Tables → Dashboard")

st.markdown("---")
st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:center;gap:20px;padding:10px 0;">{render_svg(SNOWFLAKE_LOGO_SVG, 140)}<span style="display:inline-flex;align-items:center;gap:6px;padding:4px 14px;border-radius:20px;background:rgba(41,181,232,0.1);border:1px solid rgba(41,181,232,0.3);font-size:12px;color:#29B5E8;">\u2728 Powered by <strong style="color:white;">Cortex Code</strong></span>{render_svg(POLAR_BEAR_SVG, 36)}</div>',
    unsafe_allow_html=True,
)
