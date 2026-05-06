import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const rows = await query<{
      RANK: number;
      PLAYER_NAME: string;
      GAME_TIME: string;
      FINAL_LEVEL: string;
      COINS: number;
      DURATION: number;
    }>(`
      SELECT
        ROW_NUMBER() OVER (ORDER BY COINS::INT DESC, DURATION::FLOAT ASC) AS RANK,
        PLAYER_NAME,
        TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIMESTAMP::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS GAME_TIME,
        LEVEL AS FINAL_LEVEL,
        COINS::INT AS COINS,
        ROUND(DURATION::FLOAT, 1) AS DURATION
      FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
      WHERE EVENT_TYPE = 'mario.game_over'
        AND TIMESTAMP >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
        AND PLAYER_NAME IS NOT NULL
        AND PLAYER_NAME != 'unknown'
      ORDER BY COINS::INT DESC, DURATION::FLOAT ASC
      LIMIT 20
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Leaderboard API error:", error);
    return NextResponse.json({ error: "Failed to fetch leaderboard" }, { status: 500 });
  }
}
