"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area
} from "recharts";
import { Gamepad2, Skull, Trophy, Zap, Clock, RefreshCw, Cpu, HardDrive, Wifi, Activity, FileText, Users, Database, ArrowRight, Server, BarChart3, Globe, Layers } from "lucide-react";

const COLORS = ["#E52521", "#FFD700", "#1B8C1B", "#0051A8", "#FF6B35", "#9B59B6", "#1ABC9C", "#E67E22"];
const REFRESH_MS = 5000;

interface Stats {
  TOTAL_EVENTS: number; TOTAL_DEATHS: number; TOTAL_COINS: number;
  TOTAL_LEVELS_WON: number; TOTAL_POWERUPS: number; TOTAL_SESSIONS: number;
}
interface GameEvent {
  EVENT_TYPE: string; PLAYER_NAME: string; LEVEL: string; COINS: string; LIVES: string;
  KEY_NAME: string; POWERUP_TYPE: string; DURATION: string;
  SESSION_ID: string; TIMESTAMP: string;
}
interface TimelineRow { MINUTE: string; EVENT_TYPE: string; EVENT_COUNT: number; }
interface DeathRow { LEVEL: string; DEATHS: number; }
interface KeyRow { KEY_NAME: string; PRESSES: number; }
interface PowerupRow { POWERUP_TYPE: string; LEVEL: string; COUNT: number; }
interface PlayerRow { PLAYER_NAME: string; SESSIONS: number; LAST_SEEN: string; }
interface CpuRow { MINUTE: string; AVG_CPU_PCT: number; MAX_CPU_PCT: number; }
interface MemoryRow { MINUTE: string; AVG_MEMORY_MB: number; MAX_MEMORY_MB: number; }
interface NetworkRow { MINUTE: string; ACTIVE_CONNECTIONS: number; CONNECTIONS_PER_SEC: number; }
interface ThroughputRow { MINUTE: string; SPANS_STARTED: number; SPANS_LIVE: number; }
interface LogRow { MINUTE: string; LOG_COUNT: number; ERROR_COUNT: number; WARN_COUNT: number; }
interface LeaderboardRow { RANK: number; PLAYER_NAME: string; GAME_TIME: string; FINAL_LEVEL: string; COINS: number; DURATION: number; }

function eventIcon(type: string) {
  const map: Record<string, string> = {
    "mario.death": "/characters/skull.svg",
    "mario.coin": "/characters/coin.svg",
    "mario.powerup_spawn": "/characters/star.svg",
    "mario.level_win": "/characters/pipe.svg",
    "mario.game_start": "/characters/mario.svg",
    "mario.level_start": "/characters/question-block.svg",
    "mario.game_over": "/characters/goomba.svg",
    "mario.game_win": "/characters/star.svg",
  };
  return map[type] || "/characters/question-block.svg";
}

function eventLabel(type: string) {
  return type.replace("mario.", "").replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

function stockholmNow() {
  return new Date(new Date().toLocaleString("en-US", { timeZone: "Europe/Stockholm" }));
}

function timeAgo(ts: string) {
  const eventTime = new Date(ts);
  const now = stockholmNow();
  const diff = now.getTime() - eventTime.getTime();
  if (diff < 0) return "just now";
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  return `${Math.floor(diff / 3600000)}h ago`;
}

function KpiCard({ icon, label, value, color, img }: {
  icon?: React.ReactNode; label: string; value: number | string; color: string; img?: string;
}) {
  return (
    <div className="kpi-card">
      <div className="flex items-center justify-center gap-2 mb-2">
        {img ? <Image src={img} alt="" width={28} height={28} className="float-anim" /> : icon}
      </div>
      <div className="text-3xl font-bold" style={{ color }}>{typeof value === "number" ? value.toLocaleString() : value}</div>
      <div className="text-xs text-gray-400 mt-1 uppercase tracking-wider">{label}</div>
    </div>
  );
}

export default function MarioDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [timeline, setTimeline] = useState<TimelineRow[]>([]);
  const [deaths, setDeaths] = useState<DeathRow[]>([]);
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [powerups, setPowerups] = useState<PowerupRow[]>([]);
  const [cpu, setCpu] = useState<CpuRow[]>([]);
  const [memory, setMemory] = useState<MemoryRow[]>([]);
  const [network, setNetwork] = useState<NetworkRow[]>([]);
  const [throughput, setThroughput] = useState<ThroughputRow[]>([]);
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [players, setPlayers] = useState<PlayerRow[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [selectedPlayer, setSelectedPlayer] = useState<string>("");
  const [metricsRange, setMetricsRange] = useState("360");
  const [activeTab, setActiveTab] = useState("overview");
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const pq = selectedPlayer ? `?player=${encodeURIComponent(selectedPlayer)}` : "";
      const nc = { cache: "no-store" as RequestCache };
      const cb = `_t=${Date.now()}`;
      const sep = (s: string) => s.includes("?") ? "&" : "?";
      const [sRes, eRes, tRes, dRes, kRes, pRes, cpuRes, memRes, netRes, thruRes, logRes, plRes, lbRes] = await Promise.all([
        fetch(`/api/stats${pq}${sep(`/api/stats${pq}`)}${cb}`, nc), fetch(`/api/events${pq}${sep(`/api/events${pq}`)}${cb}`, nc), fetch(`/api/timeline?${cb}`, nc),
        fetch(`/api/deaths${pq}${sep(`/api/deaths${pq}`)}${cb}`, nc), fetch(`/api/keys${pq}${sep(`/api/keys${pq}`)}${cb}`, nc), fetch(`/api/powerups${pq}${sep(`/api/powerups${pq}`)}${cb}`, nc),
        fetch(`/api/metrics/cpu?minutes=${metricsRange}&${cb}`, nc),
        fetch(`/api/metrics/memory?minutes=${metricsRange}&${cb}`, nc),
        fetch(`/api/metrics/network?minutes=${metricsRange}&${cb}`, nc),
        fetch(`/api/metrics/throughput?minutes=${metricsRange}&${cb}`, nc),
        fetch(`/api/metrics/logs?minutes=${metricsRange}&${cb}`, nc),
        fetch(`/api/players?${cb}`, nc),
        fetch(`/api/leaderboard?${cb}`, nc),
      ]);
      const [s, e, t, d, k, p, cpuD, memD, netD, thruD, logD, plD, lbD] = await Promise.all([
        sRes.json(), eRes.json(), tRes.json(), dRes.json(), kRes.json(), pRes.json(),
        cpuRes.json(), memRes.json(), netRes.json(), thruRes.json(), logRes.json(),
        plRes.json(), lbRes.json(),
      ]);
      setStats(s);
      setEvents(Array.isArray(e) ? e : []);
      setTimeline(Array.isArray(t) ? t : []);
      setDeaths(Array.isArray(d) ? d : []);
      setKeys(Array.isArray(k) ? k : []);
      setPowerups(Array.isArray(p) ? p : []);
      setCpu(Array.isArray(cpuD) ? cpuD : []);
      setMemory(Array.isArray(memD) ? memD : []);
      setNetwork(Array.isArray(netD) ? netD : []);
      setThroughput(Array.isArray(thruD) ? thruD : []);
      setLogs(Array.isArray(logD) ? logD : []);
      setPlayers(Array.isArray(plD) ? plD : []);
      setLeaderboard(Array.isArray(lbD) ? lbD : []);
      setLastRefresh(new Date());
      setLoading(false);
    } catch (err) {
      console.error("Fetch error:", err);
      setLoading(false);
    }
  }, [metricsRange, selectedPlayer]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const timelineChartData = (() => {
    const byMinute: Record<string, Record<string, number>> = {};
    timeline.forEach(r => {
      const m = r.MINUTE;
      if (!byMinute[m]) byMinute[m] = {};
      byMinute[m][r.EVENT_TYPE] = r.EVENT_COUNT;
    });
    return Object.entries(byMinute)
      .map(([minute, evts]) => ({ minute: minute.substring(11, 16), ...evts }))
      .sort((a, b) => a.minute.localeCompare(b.minute))
      .slice(-30);
  })();

  const allEventTypes = [...new Set(timeline.map(r => r.EVENT_TYPE))];

  const tabs = [
    { id: "leaderboard", label: "Leaderboard", icon: <Trophy size={16} /> },
    { id: "overview", label: "Overview", icon: <Gamepad2 size={16} /> },
    { id: "events", label: "Live Events", icon: <Zap size={16} /> },
    { id: "analytics", label: "Analytics", icon: <BarChart3 size={16} /> },
    { id: "pipeline", label: "Data Pipeline", icon: <Layers size={16} /> },
    { id: "platform", label: "SPCS Metrics", icon: <Cpu size={16} /> },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Image src="/characters/mario.svg" alt="Mario" width={80} height={80} className="mx-auto float-anim mb-4" />
          <div className="text-xl text-mario-yellow font-bold" style={{ color: "#FFD700" }}>Loading Telemetry...</div>
          <div className="text-sm text-gray-400 mt-2">Connecting to Snowflake Interactive Tables</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-6 relative overflow-hidden">
      <div className="cloud" style={{ top: "5%", animationDelay: "0s" }}>☁️</div>
      <div className="cloud" style={{ top: "15%", animationDelay: "15s", fontSize: "2rem" }}>☁️</div>
      <div className="cloud" style={{ top: "8%", animationDelay: "25s", fontSize: "1.5rem" }}>☁️</div>

      <header className="flex flex-wrap items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-4">
          <Image src="/characters/mario.svg" alt="Mario" width={56} height={56} className="float-anim" />
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
              <span style={{ color: "#E52521" }}>Super Mario</span>{" "}
              <span style={{ color: "#FFD700" }}>SPCS</span>{" "}
              <span className="text-white">Telemetry</span>
            </h1>
            <p className="text-sm text-gray-400 flex items-center gap-2">
              <span className="live-dot" />
              Real-time streaming via Interactive Tables &bull; Auto-refresh {REFRESH_MS / 1000}s
            </p>
          </div>
          <Image src="/branding/polar-bear-wave.svg" alt="Snowflake Bear" width={52} height={52} className="polar-bear-float ml-2 hidden md:block" />
        </div>
        <div className="flex items-center gap-3 text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <Users size={14} className="text-yellow-400" />
            <select
              value={selectedPlayer}
              onChange={e => setSelectedPlayer(e.target.value)}
              className="bg-white/10 text-white text-xs rounded-lg px-2 py-1 border border-white/20 focus:border-yellow-400 outline-none cursor-pointer"
            >
              <option value="" className="bg-gray-900">All Players</option>
              {players.map(p => (
                <option key={p.PLAYER_NAME} value={p.PLAYER_NAME} className="bg-gray-900">
                  {p.PLAYER_NAME} ({p.SESSIONS} sessions)
                </option>
              ))}
            </select>
          </div>
          <Clock size={14} />
          <span>Last: {lastRefresh.toLocaleTimeString()}</span>
          <button onClick={fetchAll} className="p-1.5 rounded-lg hover:bg-white/10 transition" title="Refresh now">
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map(t => (
          <button key={t.id} className={`tab-btn flex items-center gap-2 ${activeTab === t.id ? "active" : ""}`}
            onClick={() => setActiveTab(t.id)}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {activeTab === "leaderboard" && (
        <div className="space-y-4">
          <div className="mario-card p-4">
            <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Trophy size={16} className="text-yellow-400" /> Leaderboard — Last 24 Hours
            </h3>
            {leaderboard.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No games completed in the last 24 hours. Play Mario to get on the board!</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700 text-gray-400">
                      <th className="text-left py-2 px-3">#</th>
                      <th className="text-left py-2 px-3">Player</th>
                      <th className="text-left py-2 px-3">Level</th>
                      <th className="text-right py-2 px-3">Coins</th>
                      <th className="text-right py-2 px-3">Duration</th>
                      <th className="text-left py-2 px-3">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((row) => (
                      <tr key={`${row.RANK}-${row.GAME_TIME}`} className={`border-b border-gray-800 ${row.RANK <= 3 ? "bg-yellow-900/10" : ""}`}>
                        <td className="py-2 px-3 font-bold" style={{ color: row.RANK === 1 ? "#FFD700" : row.RANK === 2 ? "#C0C0C0" : row.RANK === 3 ? "#CD7F32" : "#9ca3af" }}>
                          {row.RANK === 1 ? "🥇" : row.RANK === 2 ? "🥈" : row.RANK === 3 ? "🥉" : row.RANK}
                        </td>
                        <td className="py-2 px-3 font-semibold text-white">{row.PLAYER_NAME}</td>
                        <td className="py-2 px-3 text-gray-300">{row.FINAL_LEVEL}</td>
                        <td className="py-2 px-3 text-right text-yellow-400 font-bold">{row.COINS}</td>
                        <td className="py-2 px-3 text-right text-gray-300">{row.DURATION}s</td>
                        <td className="py-2 px-3 text-gray-500 text-xs">{new Date(row.GAME_TIME).toLocaleTimeString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "overview" && stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <KpiCard img="/characters/question-block.svg" label="Total Events" value={stats.TOTAL_EVENTS} color="#FFD700" />
            <KpiCard img="/characters/skull.svg" label="Deaths" value={stats.TOTAL_DEATHS} color="#E52521" />
            <KpiCard img="/characters/coin.svg" label="Coins" value={stats.TOTAL_COINS} color="#FFD700" />
            <KpiCard img="/characters/pipe.svg" label="Levels Won" value={stats.TOTAL_LEVELS_WON} color="#1B8C1B" />
            <KpiCard img="/characters/star.svg" label="Powerups" value={stats.TOTAL_POWERUPS} color="#FF6B35" />
            <KpiCard icon={<Gamepad2 size={28} className="text-blue-400" />} label="Sessions" value={stats.TOTAL_SESSIONS} color="#0051A8" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Image src="/characters/question-block.svg" alt="" width={18} height={18} />
                Event Timeline
              </h3>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={timelineChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  {allEventTypes.map((et, i) => (
                    <Area key={et} type="monotone" dataKey={et} stackId="1"
                      fill={COLORS[i % COLORS.length]} stroke={COLORS[i % COLORS.length]}
                      fillOpacity={0.6} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Image src="/characters/skull.svg" alt="" width={18} height={18} />
                Deaths by Level
              </h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={deaths} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis dataKey="LEVEL" type="category" tick={{ fill: "#9ca3af", fontSize: 10 }} width={60} />
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  <Bar dataKey="DEATHS" radius={[0, 6, 6, 0]}>
                    {deaths.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Gamepad2 size={16} /> Key Presses
              </h3>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={keys} dataKey="PRESSES" nameKey="KEY_NAME" cx="50%" cy="50%"
                    outerRadius={90} innerRadius={40} paddingAngle={3} label={({ KEY_NAME }) => KEY_NAME}>
                    {keys.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Image src="/characters/star.svg" alt="" width={18} height={18} />
                Powerups Spawned
              </h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={powerups}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="POWERUP_TYPE" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  <Bar dataKey="COUNT" radius={[6, 6, 0, 0]}>
                    {powerups.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {activeTab === "events" && (
        <div className="mario-card p-4">
          <h3 className="text-sm font-semibold mb-4 text-gray-300 uppercase tracking-wider flex items-center gap-2">
            <Zap size={16} className="text-yellow-400" /> Live Event Feed
            <span className="live-dot ml-1" />
            <span className="text-xs font-normal text-gray-500 ml-2">{events.length} events</span>
          </h3>
          <div className="max-h-[70vh] overflow-y-auto scrollbar-hide space-y-1">
            {events.map((ev, i) => (
              <div key={i} className="event-row flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/5 transition"
                style={{ animationDelay: `${i * 30}ms` }}>
                <Image src={eventIcon(ev.EVENT_TYPE)} alt="" width={28} height={28} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm" style={{
                      color: ev.EVENT_TYPE === "mario.death" ? "#E52521"
                        : ev.EVENT_TYPE === "mario.coin" ? "#FFD700"
                        : ev.EVENT_TYPE === "mario.level_win" ? "#1B8C1B"
                        : "#fff"
                    }}>
                      {eventLabel(ev.EVENT_TYPE)}
                    </span>
                    {ev.LEVEL && <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-gray-300">World {ev.LEVEL}</span>}
                    {ev.PLAYER_NAME && <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-400/20 text-yellow-300">{ev.PLAYER_NAME}</span>}
                  </div>
                  <div className="flex gap-3 text-xs text-gray-500 mt-0.5">
                    {ev.COINS && <span>🪙 {ev.COINS}</span>}
                    {ev.LIVES && <span>❤️ {ev.LIVES}</span>}
                    {ev.POWERUP_TYPE && <span>⭐ {ev.POWERUP_TYPE}</span>}
                    {ev.KEY_NAME && <span>🎮 {ev.KEY_NAME}</span>}
                  </div>
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap">{timeAgo(ev.TIMESTAMP)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "analytics" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider">Event Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={(() => {
                    const counts: Record<string, number> = {};
                    events.forEach(e => { counts[e.EVENT_TYPE] = (counts[e.EVENT_TYPE] || 0) + 1; });
                    return Object.entries(counts).map(([name, value]) => ({ name: eventLabel(name), value }));
                  })()} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} label>
                    {Object.keys(
                      events.reduce((a, e) => ({ ...a, [e.EVENT_TYPE]: 1 }), {} as Record<string, number>)
                    ).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider">Event Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timelineChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  <Legend />
                  {allEventTypes.map((et, i) => (
                    <Line key={et} type="monotone" dataKey={et}
                      stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mario-card p-4 text-center">
            <p className="text-sm text-gray-400">
              See the <button onClick={() => setActiveTab("pipeline")} className="text-blue-400 underline hover:text-blue-300 transition">Data Pipeline</button> tab for the full animated architecture diagram
            </p>
          </div>
        </div>
      )}

      {activeTab === "platform" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Cpu size={16} className="text-red-400" /> SPCS Container Monitoring — MARIO_SERVICE
            </h3>
            <div className="flex gap-2">
              {[{l:"15m",v:"15"},{l:"1h",v:"60"},{l:"6h",v:"360"},{l:"24h",v:"1440"},{l:"All",v:"all"}].map(r => (
                <button key={r.v} onClick={() => setMetricsRange(r.v)}
                  className={`px-3 py-1 text-xs rounded-full transition ${metricsRange === r.v ? "bg-red-600 text-white" : "bg-white/10 text-gray-400 hover:bg-white/20"}`}>
                  {r.l}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Cpu size={16} className="text-red-400" /> CPU Usage (%)
              </h3>
              {cpu.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={cpu.map(r => ({ ...r, minute: r.MINUTE.substring(11, 16) }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} unit="%" />
                    <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                    <Legend />
                    <Area type="monotone" dataKey="AVG_CPU_PCT" name="Avg CPU" stroke="#FF6B6B" fill="#FF6B6B" fillOpacity={0.3} />
                    <Area type="monotone" dataKey="MAX_CPU_PCT" name="Max CPU" stroke="#CC3333" fill="#CC3333" fillOpacity={0.15} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p className="text-gray-500 text-sm text-center py-12">No CPU metrics in selected range</p>}
            </div>

            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <HardDrive size={16} className="text-teal-400" /> Memory Usage (MB)
              </h3>
              {memory.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={memory.map(r => ({ ...r, minute: r.MINUTE.substring(11, 16) }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} unit="MB" />
                    <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                    <Legend />
                    <Area type="monotone" dataKey="AVG_MEMORY_MB" name="Avg Memory" stroke="#4ECDC4" fill="#4ECDC4" fillOpacity={0.3} />
                    <Area type="monotone" dataKey="MAX_MEMORY_MB" name="Max Memory" stroke="#2A9D8F" fill="#2A9D8F" fillOpacity={0.15} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p className="text-gray-500 text-sm text-center py-12">No memory metrics in selected range</p>}
            </div>
          </div>

          <div className="mario-card p-4">
            <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Wifi size={16} className="text-blue-400" /> Network Ingress
            </h3>
            {network.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={network.map(r => ({ ...r, minute: r.MINUTE.substring(11, 16) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis yAxisId="left" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="ACTIVE_CONNECTIONS" name="Active Connections" stroke="#45B7D1" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="CONNECTIONS_PER_SEC" name="Conn/sec" stroke="#96CEB4" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-500 text-sm text-center py-12">No network metrics in selected range</p>}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Activity size={16} className="text-yellow-400" /> OTel Sidecar Throughput
              </h3>
              {throughput.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={throughput.map(r => ({ ...r, minute: r.MINUTE.substring(11, 16) }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                    <Legend />
                    <Area type="monotone" dataKey="SPANS_STARTED" name="Spans Started" stroke="#FFD700" fill="#FFD700" fillOpacity={0.3} />
                    <Area type="monotone" dataKey="SPANS_LIVE" name="Spans Live" stroke="#FF6B35" fill="#FF6B35" fillOpacity={0.3} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p className="text-gray-500 text-sm text-center py-12">No throughput data in selected range</p>}
            </div>

            <div className="mario-card p-4">
              <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <FileText size={16} className="text-green-400" /> Sidecar Log Health
              </h3>
              {logs.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={logs.map(r => ({ ...r, minute: r.MINUTE.substring(11, 16) }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="minute" tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: "#16213e", border: "1px solid rgba(255,215,0,0.3)", borderRadius: 8, color: "white" }} />
                    <Legend />
                    <Bar dataKey="LOG_COUNT" name="Logs" fill="#1B8C1B" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="ERROR_COUNT" name="Errors" fill="#E52521" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="WARN_COUNT" name="Warnings" fill="#FFD700" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : <p className="text-gray-500 text-sm text-center py-12">No log data in selected range</p>}
            </div>
          </div>

          <div className="mario-card p-4">
            <h3 className="text-sm font-semibold mb-3 text-gray-300 uppercase tracking-wider flex items-center gap-2">
              <Image src="/characters/pipe.svg" alt="" width={18} height={18} /> Container Info
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-gray-500 text-xs">Service</div>
                <div className="text-white font-semibold">MARIO_SERVICE</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-gray-500 text-xs">Compute Pool</div>
                <div className="text-white font-semibold">MARIO_POOL</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-gray-500 text-xs">Database</div>
                <div className="text-white font-semibold">MARIO_DB</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-gray-500 text-xs">Telemetry Pipeline</div>
                <div className="text-white font-semibold">OpenTelemetry gRPC</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "pipeline" && <DataPipelineTab stats={stats} />}

      <footer className="mt-8 flex flex-col items-center gap-3">
        <div className="flex items-center gap-4">
          <Image src="/branding/snowflake-logo.svg" alt="Snowflake" width={140} height={28} className="snowflake-logo-pulse" />
          <span className="powered-badge">
            <span className="dot" />
            Powered by <strong style={{ color: "white" }}>Cortex Code</strong>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Image src="/branding/polar-bear-wave.svg" alt="" width={28} height={28} />
          <span className="text-xs text-gray-600">Interactive Tables &bull; DIS_MARIO_IWH &bull; 1-min TARGET_LAG &bull; SPCS + OpenTelemetry</span>
        </div>
      </footer>
    </div>
  );
}

function DataPipelineTab({ stats }: { stats: Stats | null }) {
  const stages = [
    {
      id: "game",
      title: "Super Mario Bros",
      subtitle: "SPCS Container",
      icon: "/characters/mario.svg",
      color: "#E52521",
      details: [
        { label: "Platform", value: "Snowpark Container Services" },
        { label: "Compute Pool", value: "MARIO_POOL" },
        { label: "Container", value: "nginx + Tomcat + Java" },
        { label: "Ingress", value: "HTTPS (Snowflake Auth)" },
      ],
      dataTypes: ["Game Start", "Death", "Coin", "Level Win", "Key Press", "Powerup"],
    },
    {
      id: "telemetry",
      title: "Telemetry Sidecar",
      subtitle: "OTel Collector",
      icon: "/characters/pipe.svg",
      color: "#1B8C1B",
      details: [
        { label: "Capture", value: "telemetry.js (Browser)" },
        { label: "Transport", value: "GET /telemetry?d={json}" },
        { label: "Processing", value: "Python HTTP → OTel Spans" },
        { label: "Identity", value: "Sf-Context-Current-User" },
        { label: "Export", value: "OTLP gRPC to Event Table" },
      ],
      dataTypes: ["player_name", "session_id", "level", "coins", "lives"],
    },
    {
      id: "eventtable",
      title: "Event Table",
      subtitle: "Raw Telemetry Store",
      icon: "/characters/question-block.svg",
      color: "#FFD700",
      details: [
        { label: "Table", value: "event_db.event_sh.my_events" },
        { label: "Schema", value: "TIMESTAMP, RECORD, RECORD_ATTRIBUTES" },
        { label: "Filter", value: "snow.service.name = MARIO_SERVICE" },
        { label: "Scale", value: "~58M+ rows" },
      ],
      dataTypes: ["Spans (record_type=SPAN)", "Metrics", "Logs"],
    },
    {
      id: "interactive",
      title: "Interactive Tables",
      subtitle: "DIS_MARIO (Auto-refresh)",
      icon: "/characters/star.svg",
      color: "#29B5E8",
      details: [
        { label: "Warehouse", value: "DIS_MARIO_IWH (Interactive)" },
        { label: "Refresh", value: "TARGET_LAG = 1 minute" },
        { label: "Tables", value: "6 Interactive Tables" },
        { label: "Clustering", value: "By TIMESTAMP, PLAYER_NAME" },
      ],
      dataTypes: ["GAME_EVENTS_LIVE", "KEY_PRESSES_LIVE", "DEATHS_BY_LEVEL_LIVE", "POWERUPS_LIVE", "PLAYER_SESSIONS_LIVE", "EVENT_TIMELINE_LIVE"],
    },
    {
      id: "semantic",
      title: "Semantic View",
      subtitle: "MARIO_TELEMETRY",
      icon: "/branding/snowflake-logo.svg",
      color: "#9B59B6",
      details: [
        { label: "View", value: "DIS_MARIO.PUBLIC.MARIO_TELEMETRY" },
        { label: "Entities", value: "6 tables, 2 relationships" },
        { label: "Agent", value: "MARIO_INTELLIGENCE (Cortex)" },
        { label: "VQRs", value: "5 verified queries" },
      ],
      dataTypes: ["Natural Language → SQL", "Text-to-SQL", "Cortex Agent"],
    },
    {
      id: "dashboard",
      title: "Dashboards",
      subtitle: "React + Streamlit",
      icon: "/characters/mushroom.svg",
      color: "#FF6B35",
      details: [
        { label: "React", value: "Next.js + Recharts (this app)" },
        { label: "Streamlit", value: "DIS_MARIO_TELEMETRY_DASHBOARD" },
        { label: "Refresh", value: "5s polling (React), 10s TTL (SiS)" },
        { label: "Features", value: "Player filter, KPIs, Charts" },
      ],
      dataTypes: ["Charts", "KPIs", "Live Events", "SPCS Metrics"],
    },
  ];

  return (
    <div className="space-y-6 data-stream-bg p-4 rounded-xl">
      <div className="text-center mb-8">
        <h2 className="text-xl font-bold text-white mb-2 flex items-center justify-center gap-3">
          <Layers size={24} className="text-blue-400" />
          End-to-End Data Pipeline
          <Image src="/branding/polar-bear-wave.svg" alt="" width={40} height={40} className="polar-bear-float" />
        </h2>
        <p className="text-sm text-gray-400">Real-time telemetry flowing from the Mario game to your screen</p>
        {stats && (
          <div className="flex justify-center gap-6 mt-4 text-sm">
            <span className="text-yellow-400 font-semibold">{stats.TOTAL_EVENTS.toLocaleString()} events</span>
            <span className="text-red-400 font-semibold">{stats.TOTAL_DEATHS.toLocaleString()} deaths</span>
            <span className="text-green-400 font-semibold">{stats.TOTAL_SESSIONS.toLocaleString()} sessions</span>
          </div>
        )}
      </div>

      {stages.map((stage, idx) => (
        <div key={stage.id}>
          <div className="pipeline-stage">
            <div className="flex flex-col md:flex-row items-start gap-6">
              <div className="flex flex-col items-center min-w-[120px] pt-2">
                <div className="relative">
                  <Image src={stage.icon} alt="" width={48} height={48} className="stage-icon-glow" />
                  <span className="absolute -top-2 -left-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
                    style={{ background: stage.color }}>
                    {idx + 1}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mt-3">{stage.title}</h3>
                <span className="text-xs mt-1 px-2 py-0.5 rounded-full" style={{ color: stage.color, background: `${stage.color}20` }}>{stage.subtitle}</span>
              </div>

              <div className="flex-1 w-full">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
                  {stage.details.map(d => (
                    <div key={d.label} className="detail-row">
                      <span className="text-xs text-gray-500 uppercase tracking-wider">{d.label}</span>
                      <div className="text-sm text-white font-medium">{d.value}</div>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {stage.dataTypes.map(dt => (
                    <span key={dt} className="text-xs px-2.5 py-1 rounded-full border font-medium"
                      style={{ borderColor: `${stage.color}60`, color: stage.color, background: `${stage.color}10` }}>
                      {dt}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {idx < stages.length - 1 && (
            <div className="flex flex-col items-center py-1">
              <div className="connector-vertical">
                <div className="data-particle" style={{ animationDelay: "0s" }} />
                <div className="data-particle gold" style={{ animationDelay: "0.7s" }} />
                <div className="data-particle red" style={{ animationDelay: "1.4s" }} />
              </div>
              <div className="flex items-center gap-2 my-1">
                <ArrowRight size={14} style={{ color: stages[idx + 1].color }} className="animate-pulse" />
                <span className="text-xs text-gray-500">
                  {idx === 0 ? "Browser JS captures events" :
                   idx === 1 ? "OTel gRPC export" :
                   idx === 2 ? "View + Interactive Table refresh" :
                   idx === 3 ? "Cortex Analyst text-to-SQL" :
                   "API queries via Snowflake SDK"}
                </span>
                <ArrowRight size={14} style={{ color: stages[idx + 1].color }} className="animate-pulse" />
              </div>
              <div className="connector-vertical" style={{ animationDelay: "0.5s" }}>
                <div className="data-particle" style={{ animationDelay: "0.3s" }} />
                <div className="data-particle gold" style={{ animationDelay: "1s" }} />
              </div>
            </div>
          )}
        </div>
      ))}

      <div className="mario-card p-6 text-center mt-8">
        <div className="flex items-center justify-center gap-4 mb-4">
          <Image src="/branding/snowflake-logo.svg" alt="Snowflake" width={160} height={32} className="snowflake-logo-pulse" />
        </div>
        <p className="text-sm text-gray-400 mb-3">This entire pipeline runs on Snowflake — from game hosting to real-time analytics</p>
        <div className="flex justify-center gap-3 flex-wrap">
          {["SPCS", "Event Tables", "Interactive Tables", "Interactive Warehouse", "Semantic Views", "Cortex Agent", "Streamlit in Snowflake"].map(tag => (
            <span key={tag} className="text-xs px-3 py-1.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30 font-medium">{tag}</span>
          ))}
        </div>
        <div className="flex items-center justify-center gap-2 mt-4">
          <Image src="/branding/polar-bear-wave.svg" alt="" width={36} height={36} className="polar-bear-float" />
          <span className="powered-badge">
            <span className="dot" />
            Powered by <strong style={{ color: "white" }}>Cortex Code</strong>
          </span>
        </div>
      </div>
    </div>
  );
}
