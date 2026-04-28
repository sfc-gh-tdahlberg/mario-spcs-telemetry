import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const rows = await query<{ PLAYER_NAME: string; SESSIONS: number; LAST_SEEN: string }>(`
      SELECT
        PLAYER_NAME,
        COUNT(*) AS SESSIONS,
        TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', MAX(SESSION_START)::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS LAST_SEEN
      FROM DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE
      WHERE PLAYER_NAME IS NOT NULL
      GROUP BY PLAYER_NAME
      ORDER BY SESSIONS DESC
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Players API error:", error);
    return NextResponse.json({ error: "Failed to fetch players" }, { status: 500 });
  }
}
