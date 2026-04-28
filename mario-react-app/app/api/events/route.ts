import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const player = searchParams.get("player");
    const playerFilter = player ? `AND PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";

    const rows = await query(`
      SELECT EVENT_TYPE, PLAYER_NAME, LEVEL, COINS, LIVES, KEY_NAME, POWERUP_TYPE, DURATION, SESSION_ID,
             TO_CHAR(CONVERT_TIMEZONE('UTC', 'Europe/Stockholm', TIMESTAMP::TIMESTAMP_NTZ), 'YYYY-MM-DD"T"HH24:MI:SS') AS TIMESTAMP
      FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE
      WHERE EVENT_TYPE != 'mario.key_press' ${playerFilter}
      ORDER BY TIMESTAMP DESC
      LIMIT 200
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Events API error:", error);
    return NextResponse.json({ error: "Failed to fetch events" }, { status: 500 });
  }
}
