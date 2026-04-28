import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const player = searchParams.get("player");
    const playerFilter = player ? `AND PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";
    const playerFilterWhere = player ? `WHERE PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";

    const [totals] = await query<{
      TOTAL_EVENTS: number; TOTAL_DEATHS: number; TOTAL_COINS: number;
      TOTAL_LEVELS_WON: number; TOTAL_POWERUPS: number; TOTAL_SESSIONS: number;
    }>(`
      SELECT
        (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE 1=1 ${playerFilter}) AS TOTAL_EVENTS,
        (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.death' ${playerFilter}) AS TOTAL_DEATHS,
        (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.coin' ${playerFilter}) AS TOTAL_COINS,
        (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.GAME_EVENTS_LIVE WHERE EVENT_TYPE='mario.level_win' ${playerFilter}) AS TOTAL_LEVELS_WON,
        (SELECT SUM(COUNT) FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE ${playerFilterWhere}) AS TOTAL_POWERUPS,
        (SELECT COUNT(*) FROM DIS_MARIO.PUBLIC.PLAYER_SESSIONS_LIVE ${playerFilterWhere}) AS TOTAL_SESSIONS
    `);
    return NextResponse.json(totals);
  } catch (error) {
    console.error("Stats API error:", error);
    return NextResponse.json({ error: "Failed to fetch stats" }, { status: 500 });
  }
}
