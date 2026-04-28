import { NextResponse } from "next/server";
import { query } from "@/lib/snowflake";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const player = searchParams.get("player");
    const playerFilter = player ? `WHERE PLAYER_NAME = '${player.replace(/'/g, "''")}'` : "";

    const rows = await query(`
      SELECT POWERUP_TYPE, LEVEL, SUM(COUNT) AS COUNT
      FROM DIS_MARIO.PUBLIC.POWERUPS_LIVE
      ${playerFilter}
      GROUP BY POWERUP_TYPE, LEVEL
      ORDER BY COUNT DESC
    `);
    return NextResponse.json(rows);
  } catch (error) {
    console.error("Powerups API error:", error);
    return NextResponse.json({ error: "Failed to fetch powerups" }, { status: 500 });
  }
}
