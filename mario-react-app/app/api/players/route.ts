import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const rows = await query<{ PLAYER_NAME: string; SESSIONS: number; LAST_SEEN: string }>(`
      SELECT
        PLAYER_NAME,
        COUNT(CASE WHEN EVENT_TYPE = 'mario.game_start' THEN 1 END) AS SESSIONS,
        TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', MAX(TIMESTAMP)::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS LAST_SEEN
      FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
      WHERE PLAYER_NAME IS NOT NULL AND PLAYER_NAME != 'unknown'
      GROUP BY PLAYER_NAME
      ORDER BY SESSIONS DESC
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Players API error:", error);
    return NextResponse.json({ error: "Failed to fetch players" }, { status: 500 });
  }
}
